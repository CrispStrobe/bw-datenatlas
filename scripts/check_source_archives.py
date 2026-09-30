#!/usr/bin/env python3
"""Hat jede Quelle dieses Atlas einen Schnappschuss im Internet Archive?

Dieser Atlas verspricht, dass an jeder Zahl steht, woher sie kommt. Das Versprechen
hält nur, solange die Adresse dorthin führt. Behörden-PDFs wandern: die
Veröffentlichung wechselt den Pfad, der Bericht bekommt eine neue Auflage, das
Fachportal wird umgebaut. Eine Fußnote, die ins Leere zeigt, ist keine Fundstelle.

Dieses Skript fragt nur ab, es archiviert nichts. Es nimmt die Adressen, die die
Seite tatsächlich zeigt, und fragt die Verfügbarkeits-Schnittstelle des Internet
Archive, ob es dazu einen Schnappschuss gibt und von wann. Das Ergebnis ist eine
Liste: was gesichert ist, was nicht, und wie alt das Gesicherte ist.

Was damit geschieht, entscheidet ein Mensch. Etwas ins Internet Archive zu geben ist
eine Handlung nach außen; sie gehört nicht in ein Skript, das "prüfen" heißt.
"""
from __future__ import annotations
import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Die Verfügbarkeits-Schnittstelle (archive.org/wayback/available) antwortet zurzeit
# durchgehend mit 429 und lieferte deshalb für jede einzelne Adresse "kein
# Schnappschuss" — ein Ergebnis, das nach einem Befund aussieht und keiner ist. Der
# CDX-Index beantwortet dieselbe Frage und ist belastbarer; gefragt wird nach der
# letzten Aufnahme, die mit 200 beantwortet wurde.
CDX = ('http://web.archive.org/cdx/search/cdx?output=json&fl=timestamp'
       '&filter=statuscode:200&limit=-1&url=')
UA = {'User-Agent': 'BW-Datenatlas/1.0'}


def quellen() -> dict[str, str]:
    """Jede Adresse, die die Seite als Quelle nennt, mit einem Titel dazu.

    Gelesen wird aus den erzeugten Datendateien, nicht aus einer gepflegten Liste —
    dieselbe Regel wie im Quellenabschnitt der Seite selbst.
    """
    raus: dict[str, str] = {}

    def dazu(url, titel):
        if url and url.startswith('http'):
            raus.setdefault(url, titel or url)

    atlas = json.loads((ROOT / 'docs/data/atlas.json').read_text(encoding='utf-8'))
    for s in atlas['sources'].values():
        dazu(s.get('url'), s.get('title'))

    # Die Kartenebenen tragen ihre Quellen im Programm; hier reicht das Auslesen der
    # Adressen, eine Auswertung des Programms wäre für diesen Zweck zu viel.
    js = (ROOT / 'docs/assets/app.js').read_text(encoding='utf-8')
    for m in re.finditer(r"sourceInfo:\{title:'([^']+)'.*?url:'([^']+)'", js):
        dazu(m.group(2), m.group(1))

    for datei in sorted((ROOT / 'docs/data').glob('*.json')):
        try:
            d = json.loads(datei.read_text(encoding='utf-8'))
        except Exception:
            continue
        if isinstance(d, dict):
            dazu(d.get('source_url'), d.get('source'))
            for b in (d.get('blocks') or []):
                for i in b.get('items', []):
                    dazu(i.get('source_url'), i.get('source_title'))
    return raus


def schnappschuss(url: str, versuche: int = 4) -> dict | None:
    """Die letzte erfolgreiche Aufnahme dieser Adresse, oder None.

    Bei 429 wird gewartet und erneut gefragt. Ein Abbruch nach dem ersten Fehlschlag
    hätte die Drosselung in einen Befund verwandelt.
    """
    ziel = CDX + urllib.parse.quote(url, safe='')
    warte = 3.0
    for _ in range(versuche):
        try:
            with urllib.request.urlopen(urllib.request.Request(ziel, headers=UA),
                                        timeout=60) as r:
                zeilen = json.loads(r.read().decode() or '[]')
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                return None
            time.sleep(warte)
            warte *= 2
        except Exception:
            time.sleep(warte)
            warte *= 2
    else:
        return {'unreachable': True}
    if len(zeilen) < 2:
        return None
    stand = zeilen[-1][0]
    return {'url': f'https://web.archive.org/web/{stand}/{url}',
            'timestamp': stand}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path,
                    default=ROOT / 'docs/data/source-archives.json')
    ap.add_argument('--pause', type=float, default=2.0)
    args = ap.parse_args()

    alle = quellen()
    print(f'{len(alle)} Quelladressen auf der Seite\n')
    treffer, ohne = {}, []
    for n, (url, titel) in enumerate(sorted(alle.items()), 1):
        s = schnappschuss(url)
        if s and s.get('unreachable'):
            # Nicht dasselbe wie "nicht archiviert": hier hat die Abfrage versagt.
            ohne.append({'url': url, 'title': titel, 'lookup_failed': True})
            print(f'  {n:3d} ??????????  {titel[:64]}   ABFRAGE FEHLGESCHLAGEN')
            continue
        if s:
            stand = s['timestamp']
            treffer[url] = {'url': s['url'],
                            'captured': f'{stand[:4]}-{stand[4:6]}-{stand[6:8]}',
                            'title': titel}
            print(f'  {n:3d} {treffer[url]["captured"]}  {titel[:64]}')
        else:
            ohne.append({'url': url, 'title': titel})
            print(f'  {n:3d} ----------  {titel[:64]}   KEIN SCHNAPPSCHUSS')
        time.sleep(args.pause)

    doc = {
        'type': 'source_archives',
        'schema_version': '1.0',
        'what_this_is': (
            'Zu jeder Quelladresse dieses Atlas der jüngste Schnappschuss im Internet '
            'Archive, soweit es einen gibt. Damit bleibt eine Fundstelle auffindbar, '
            'auch wenn die Behörde ihre Veröffentlichung verschiebt.'),
        'not_an_archiving_run': (
            'Abgefragt, nicht archiviert. Ob eine Adresse neu ins Internet Archive '
            'gegeben wird, ist eine Handlung nach außen und keine Entscheidung dieses '
            'Skripts.'),
        'checked_on': time.strftime('%Y-%m-%d'),
        'count': len(alle),
        'with_snapshot': len(treffer),
        'archives': treffer,
        'without_snapshot': ohne,
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                        encoding='utf-8')
    args.out.with_name('source-archives-data.js').write_text(
        'window.ATLAS_SOURCE_ARCHIVES=' + json.dumps(
            doc, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
    print(f'\n{len(treffer)} von {len(alle)} Adressen haben einen Schnappschuss.')
    if ohne:
        print('Ohne Schnappschuss:')
        for x in ohne:
            print('  -', x['title'][:70])
            print('    ', x['url'][:110])


if __name__ == '__main__':
    main()

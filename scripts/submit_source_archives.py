#!/usr/bin/env python3
"""Die Quelladressen ohne Schnappschuss bei den Archivdiensten einreichen.

Das Gegenstück zu check_source_archives.py, und bewusst ein eigener Aufruf: dort
wird gefragt, hier wird etwas nach außen getan. Eingereicht wird nur, was die
Prüfung als "ohne Schnappschuss" geführt hat, und nur öffentliche Behörden- und
Institutsdokumente, die der Atlas ohnehin zitiert.

Zwei Dienste:

  web.archive.org/save  nimmt Einreichungen ohne Anmeldung an, drosselt aber
      hart. Bei 429 wird gewartet und erneut versucht.
  archive.ph            wehrt Automaten ab. Der Versuch läuft mit der ehrlichen
      Kennung dieses Projekts; wird er abgewiesen, steht das im Ergebnis. Eine
      Abwehr zu umgehen, indem man sich als Browser ausgibt, wäre etwas anderes
      als ein Zitat zu sichern.

Am Ende wird nicht geglaubt, sondern nachgesehen: für jede eingereichte Adresse
fragt das Skript den CDX-Index, ob nun wirklich eine Aufnahme existiert. Was der
Dienst quittiert hat, ist eine Quittung; was im Index steht, ist ein Schnappschuss.
"""
from __future__ import annotations
import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAVE = 'https://web.archive.org/save/'
ARCHIVE_PH = 'https://archive.ph/submit/?url='
CDX = ('http://web.archive.org/cdx/search/cdx?output=json&fl=timestamp'
       '&filter=statuscode:200&limit=-1&url=')
UA = {'User-Agent': 'BW-Datenatlas/1.0 (Quellensicherung; postmaster@crispstro.be)'}


def hole(url: str, timeout: int = 120) -> tuple[int | str, str]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                    timeout=timeout) as r:
            return r.status, r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, ''
    except Exception as e:
        return type(e).__name__, ''


def einreichen(url: str, versuche: int = 3) -> dict:
    ergebnis = {'url': url}
    warte = 20.0
    for n in range(versuche):
        code, ziel = hole(SAVE + url)
        ergebnis['wayback_status'] = code
        if code == 200:
            ergebnis['wayback_result'] = ziel
            break
        if code in (429, 503, 520, 'HTTPError'):
            time.sleep(warte)
            warte *= 2
            continue
        break
    code, ziel = hole(ARCHIVE_PH + urllib.parse.quote(url, safe=''), timeout=90)
    ergebnis['archive_ph_status'] = code
    if code == 200 and 'archive.' in ziel:
        ergebnis['archive_ph_result'] = ziel
    return ergebnis


def im_index(url: str) -> str | None:
    try:
        with urllib.request.urlopen(
                urllib.request.Request(CDX + urllib.parse.quote(url, safe=''),
                                       headers=UA), timeout=60) as r:
            zeilen = json.loads(r.read().decode() or '[]')
    except Exception:
        return None
    return zeilen[-1][0] if len(zeilen) > 1 else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--datei', type=Path,
                    default=ROOT / 'docs/data/source-archives.json')
    ap.add_argument('--pause', type=float, default=8.0)
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()

    doc = json.loads(args.datei.read_text(encoding='utf-8'))
    offen = [x for x in doc['without_snapshot'] if not x.get('lookup_failed')]
    if args.limit:
        offen = offen[:args.limit]
    print(f'{len(offen)} Adressen ohne Schnappschuss werden eingereicht.\n')

    quittungen = []
    for n, x in enumerate(offen, 1):
        e = einreichen(x['url'])
        e['title'] = x['title']
        quittungen.append(e)
        print(f"  {n:2d} wayback {str(e['wayback_status']):>12}  "
              f"archive.ph {str(e['archive_ph_status']):>12}  {x['title'][:46]}")
        time.sleep(args.pause)

    print('\nNachsehen, was wirklich im Index steht (nicht, was quittiert wurde):')
    neu, weiterhin_ohne = {}, []
    for x in quittungen:
        time.sleep(3)
        stand = im_index(x['url'])
        if stand:
            neu[x['url']] = {
                'url': f"https://web.archive.org/web/{stand}/{x['url']}",
                'captured': f'{stand[:4]}-{stand[4:6]}-{stand[6:8]}',
                'title': x['title'], 'submitted_by_this_project': True}
            print(f"  ✓ {neu[x['url']]['captured']}  {x['title'][:56]}")
        else:
            weiterhin_ohne.append({'url': x['url'], 'title': x['title']})
            print(f"  – kein Eintrag   {x['title'][:56]}")

    doc['archives'].update(neu)
    # Nur die bearbeiteten Adressen anfassen. Ein Lauf mit --limit hat die Liste
    # der offenen Adressen einmal durch die eine ersetzt, die er geprüft hatte, und
    # damit zwanzig aus der Datei geworfen — wiederhergestellt wurden sie aus dem
    # Tag v0.36.0. Was nicht bearbeitet wurde, bleibt stehen.
    bearbeitet = {x['url'] for x in quittungen}
    doc['without_snapshot'] = [x for x in doc['without_snapshot']
                               if x['url'] not in bearbeitet] + weiterhin_ohne
    doc['with_snapshot'] = len(doc['archives'])
    if len(doc['archives']) + len(doc['without_snapshot']) != doc['count']:
        raise SystemExit(
            f"Die Datei geht nicht auf: {len(doc['archives'])} gesichert plus "
            f"{len(doc['without_snapshot'])} offen ergeben nicht {doc['count']}.")
    doc['submitted_on'] = time.strftime('%Y-%m-%d')
    doc['submission_note'] = (
        'Adressen ohne Schnappschuss wurden bei web.archive.org eingereicht; ein '
        'Versuch bei archive.ph lief mit der Kennung dieses Projekts. Aufgenommen '
        'ist nur, was danach wirklich im Index stand — eine Quittung des Dienstes '
        'ist kein Schnappschuss.')
    args.datei.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                          encoding='utf-8')
    args.datei.with_name('source-archives-data.js').write_text(
        'window.ATLAS_SOURCE_ARCHIVES=' + json.dumps(
            doc, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
    ph = sum(1 for x in quittungen if x.get('archive_ph_result'))
    print(f"\n{len(neu)} neu gesichert, {len(weiterhin_ohne)} weiterhin ohne. "
          f"archive.ph hat {ph} von {len(quittungen)} angenommen.")
    print(f"Insgesamt jetzt {doc['with_snapshot']} von {doc['count']}.")


if __name__ == '__main__':
    main()

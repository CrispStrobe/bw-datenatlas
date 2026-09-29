#!/usr/bin/env python3
"""Eine echte Alterspyramide: ausländische Bevölkerung Baden-Württembergs nach Generation.

Die Frage war, ob die amtliche Statistik eine Alterspyramide hergibt. Für die
muslimische Bevölkerung nicht — keine deutsche Statistik erhebt die Religion in
einer Form, die das zuließe. Für die AUSLÄNDISCHE Bevölkerung dagegen schon, und
zwar in einer Feinheit, die das Thema wirklich weiterbringt.

Tabelle 12521-0023 des Ausländerzentralregisters weist je Bundesland aus: Alter in
Einzeljahren, Geschlecht, Staatsangehörigkeitsgruppe — und die MIGRANTENGENERATION.
Das letzte Merkmal ist der eigentliche Gewinn. Der übliche Einwand gegen jede
Passzahl lautet, dass die hier Geborenen fehlen; hier stehen sie als eigene Gruppe,
und man sieht auf einen Blick, dass die ausländische Bevölkerung Baden-Württembergs
unter den Kindern fast vollständig aus in Deutschland Geborenen besteht und ab dem
jungen Erwachsenenalter fast vollständig aus Zugewanderten.

Was die Pyramide NICHT zeigt, steht ebenso deutlich dabei: Eingebürgerte. Das
Register führt nur Menschen ohne deutschen Pass. Wer eingebürgert wurde, verschwindet
daraus — und das sind gerade in den lange ansässigen Gemeinschaften viele. Die
zweite Generation im Register ist deshalb nur der Teil, der keinen deutschen Pass
hat, nicht die zweite Generation überhaupt.

Register, keine Stichprobe und kein Modell: Stichtag 31.12.2025.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Fünfjahresgruppen wie in der vorhandenen Pyramide nach Einwanderungsgeschichte,
# damit die beiden nebeneinander lesbar sind.
def gruppe(bezeichnung: str):
    if bezeichnung.startswith('unter 1'):
        return '0–4'
    if 'unbekannt' in bezeichnung:
        return None
    if '95 Jahre und mehr' in bezeichnung:
        return '95 u. älter'
    m = re.match(r'(\d+)', bezeichnung)
    if not m:
        return None
    j = int(m.group(1))
    if j >= 95:
        return '95 u. älter'
    u = (j // 5) * 5
    return f'{u}–{u + 4}'


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path,
                    default=ROOT / 'inputs/genesis-12521-0023-auslaender-alter-generation.csv.gz',
                    help='CSV oder CSV.GZ der GENESIS-Tabelle 12521-0023')
    ap.add_argument('--land', default='Baden-Württemberg')
    ap.add_argument('--out', type=Path,
                    default=ROOT / 'docs/data/foreign-age-pyramid.json')
    args = ap.parse_args()

    # Die Quelldatei liegt gepackt im Repository: 1,4 MB roh, ein Zehntel davon
    # gepackt, und ohne sie wäre der Aufbau nicht wiederholbar.
    if args.input.suffix == '.gz':
        import gzip
        fh = gzip.open(args.input, 'rt', encoding='utf-8-sig')
    else:
        fh = args.input.open(encoding='utf-8-sig')
    with fh:
        zeilen = list(csv.reader(fh, delimiter=';'))
    kopf = next(i for i, r in enumerate(zeilen)
                if any('unter 1 Jahr' in (x or '') for x in r))
    # Je Altersjahr zwei Spalten: Wert und Qualitätskennzeichen.
    spalten = [(i, b) for i, b in enumerate(zeilen[kopf]) if i >= 5 and b]
    spalten = [(i, b) for i, b in spalten if i % 2 == 1] or spalten[::2]

    def zahl(t):
        t = (t or '').strip()
        return int(t) if t.isdigit() else None

    pyramide: dict[str, dict] = {}
    gesamt = {'1. Generation': 0, '2. Generation': 0}
    unbekannt = 0
    for r in zeilen:
        if len(r) < 7 or r[1] != args.land or r[2] != 'Insgesamt':
            continue
        gen = '2. Generation' if r[3].startswith('2.') else '1. Generation'
        sex = 'm' if r[4] == 'männlich' else 'w'
        for i, bez in spalten:
            if i >= len(r):
                continue
            w = zahl(r[i])
            if w is None:
                continue
            g = gruppe(bez)
            if g is None:
                unbekannt += w
                continue
            eintrag = pyramide.setdefault(g, {f'{s}_{k}': 0 for s in ('m', 'w')
                                               for k in ('gen1', 'gen2')})
            eintrag[f'{sex}_{"gen2" if gen == "2. Generation" else "gen1"}'] += w
            gesamt[gen] += w

    def sortier(g):
        if g.startswith('95'):
            return 95
        return int(g.split('–')[0])

    reihe = [{'group': g, **pyramide[g]} for g in sorted(pyramide, key=sortier)]
    summe = sum(v for e in reihe for k, v in e.items() if k != 'group')

    # Anteil der zweiten Generation je Altersgruppe — die eigentliche Aussage.
    for e in reihe:
        zwei = e['m_gen2'] + e['w_gen2']
        alle = zwei + e['m_gen1'] + e['w_gen1']
        e['second_generation_pct'] = round(100 * zwei / alle, 1) if alle else None

    doc = {
        'type': 'foreign_age_pyramid_by_generation',
        'schema_version': '1.0',
        'geography': args.land,
        'what_this_is': ('Ausländische Bevölkerung nach Alter, Geschlecht und '
                         'Migrantengeneration. Erste Generation heißt im Ausland '
                         'geboren, zweite Generation in Deutschland geboren.'),
        'why_the_generation_matters': (
            'Der übliche Einwand gegen jede Passzahl lautet, dass die hier Geborenen '
            'fehlen. Hier stehen sie als eigene Gruppe: unter den Kindern besteht die '
            'ausländische Bevölkerung fast vollständig aus in Deutschland Geborenen, '
            'ab dem jungen Erwachsenenalter fast vollständig aus Zugewanderten.'),
        'who_is_missing': (
            'Das Register führt nur Menschen ohne deutschen Pass. Es fehlen damit zwei '
            'große Gruppen: Eingebürgerte, und Kinder ausländischer Eltern, die nach '
            '§ 4 Absatz 3 des Staatsangehörigkeitsgesetzes schon bei der Geburt '
            'deutsche Staatsangehörige werden. Gerade bei den Jüngsten fällt das ins '
            'Gewicht. Die zweite Generation in dieser Pyramide ist deshalb nur ihr '
            'Teil ohne deutschen Pass, nicht die zweite Generation überhaupt — und '
            'warum ihr Anteil zwischen den Altersgruppen so stark schwankt, sagt diese '
            'Quelle nicht. Dies ist außerdem keine Pyramide der muslimischen '
            'Bevölkerung: Religion steht im Register nicht.'),
        'measurement': 'Register, keine Stichprobe und kein Modell',
        'reference_date': '2025-12-31',
        'source': ('Statistisches Bundesamt (Destatis), GENESIS-Online, Tabelle '
                   '12521-0023: Ausländer nach Bundesländern, Geschlecht, Altersjahren, '
                   'Migrantengeneration und Staatsangehörigkeit'),
        'source_url': ('https://www-genesis.destatis.de/datenbank/online/statistic/'
                       '12521/table/12521-0023'),
        'licence': ('Datenlizenz Deutschland – Namensnennung – Version 2.0 '
                    '(dl-de/by-2-0), © Statistisches Bundesamt (Destatis)'),
        'totals': {'first_generation': gesamt['1. Generation'],
                   'second_generation': gesamt['2. Generation'],
                   'total': summe, 'age_unknown': unbekannt},
        'count': len(reihe),
        'bands': reihe,
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                        encoding='utf-8')
    args.out.with_name('foreign-age-data.js').write_text(
        'window.ATLAS_FOREIGN_AGE=' + json.dumps(doc, ensure_ascii=False,
                                                 separators=(',', ':')) + ';\n',
        encoding='utf-8')

    print(f'{args.land}: {summe:,} ausländische Personen, davon '
          f'{gesamt["2. Generation"]:,} in Deutschland geboren '
          f'({100*gesamt["2. Generation"]/summe:.1f} %)'.replace(',', '.'))
    print(f'Alter unbekannt: {unbekannt}')
    print('\nAltersgruppe   männl.1  weibl.1  männl.2  weibl.2   2. Gen.')
    for e in reihe:
        print(f"  {e['group']:11s} {e['m_gen1']:8d} {e['w_gen1']:8d} "
              f"{e['m_gen2']:8d} {e['w_gen2']:8d}   {e['second_generation_pct']:5.1f} %")


if __name__ == '__main__':
    main()

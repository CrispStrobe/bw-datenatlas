#!/usr/bin/env python3
"""Two small state-level series that say something the rest of the atlas cannot.

Both come from the charts on the Statistisches Landesamt's migration page, and neither is
visible in the page's text: they are loaded by the chart script from CSV files beside it.
A reader of the page sees a picture; the numbers are in the files.

WHY THESE TWO, out of everything on that page.

  Average length of residence by nationality. The atlas models a population by origin and
  says nothing about how long anyone has been here, which leaves the impression that
  origin and recency are the same thing. They are not, and the figures say so plainly:
  Italian nationals have been resident 32 years on average, Turkish nationals 30, while
  Ukrainian nationals have been here 3. A map of mosques next to a claim about "recent
  immigration" is exactly where that difference matters.

  Naturalisations per year since 2000. The model corrects for naturalised residents,
  because a German passport removes someone from the foreign-nationals count without
  removing them from the population being estimated. That correction is a number in a
  formula; this is the series behind it, and it is not flat — 16,068 in 2004, 39,790 in
  2025.

Licence: © Statistisches Landesamt Baden-Württemberg; reproduction permitted with
attribution. robots.txt allows /fileadmin/.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESIDENCE = ROOT / 'inputs/stala-aufenthaltsdauer-staatsangehoerigkeit-2024.csv'
NATURALISATIONS = ROOT / 'inputs/stala-einbuergerungen-2000-2025.csv'
OUTPUT = ROOT / 'docs/data/bw-migration-context.json'
BASE = ('https://www.statistik-bw.de/leben-und-arbeiten/bevoelkerung-und-gebiet/'
        'migration-und-nationalitaet/')


def rows(path: Path) -> list[list[str]]:
    text = path.read_text(encoding='utf-8-sig')
    return [r for r in csv.reader(text.splitlines(), delimiter=';') if r and r[0].strip()]


def number(value: str) -> float:
    return float(value.strip().replace('.', '').replace(',', '.'))


def main() -> None:
    residence = [{'nationality': r[0].strip(), 'years': number(r[1])}
                 for r in rows(RESIDENCE)[1:]]
    naturalisations = [{'year': r[0].strip(), 'count': int(number(r[1]))}
                       for r in rows(NATURALISATIONS)[1:]]
    residence.sort(key=lambda r: -r['years'])

    doc = {
        'type': 'bw_migration_context',
        'schema_version': '1.0',
        'source': 'Statistisches Landesamt Baden-Württemberg',
        'source_url': BASE,
        'licence': ('© Statistisches Landesamt Baden-Württemberg; Vervielfältigung und '
                    'Verbreitung mit Quellenangabe gestattet'),
        'average_residence_years': {
            'reference_date': '2024-12-31',
            'measures': ('Durchschnittliche Aufenthaltsdauer der in Baden-Württemberg '
                         'gemeldeten Ausländerinnen und Ausländer nach '
                         'Staatsangehörigkeit, Ausländerzentralregister.'),
            'caveat': ('Gilt nur für Personen ohne deutschen Pass. Wer eingebürgert ist, '
                       'zählt hier nicht mit — und das sind gerade bei den lange '
                       'ansässigen Gruppen viele, sodass die wahre Verweildauer der '
                       'Herkunftsgruppe eher unterschätzt wird.'),
            'rows': residence,
        },
        'naturalisations': {
            'measures': 'Einbürgerungen in Baden-Württemberg je Jahr.',
            'why_it_matters': ('Die Modellrechnung dieses Atlas korrigiert um '
                               'Eingebürgerte: Ein deutscher Pass nimmt eine Person aus '
                               'der Ausländerstatistik, nicht aus der Bevölkerung, die '
                               'geschätzt wird. Dies ist die Reihe hinter dieser '
                               'Korrektur.'),
            'rows': naturalisations,
        },
    }
    OUTPUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                      encoding='utf-8')
    # Die Seite liest die JS-Fassung. Sie hier mitzuschreiben ist der Unterschied
    # zwischen einem Bauschritt und einem Handgriff, den man einmal vergisst.
    OUTPUT.with_name('bw-migration-data.js').write_text(
        'window.ATLAS_BW_MIGRATION=' + json.dumps(doc, ensure_ascii=False,
                                                  separators=(',', ':')) + ';\n',
        encoding='utf-8')
    print(f'{len(residence)} Staatsangehörigkeiten, {len(naturalisations)} Jahre '
          f'geschrieben nach {OUTPUT.name}')


if __name__ == '__main__':
    main()

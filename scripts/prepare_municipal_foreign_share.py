#!/usr/bin/env python3
"""Share of foreign nationals per municipality.

The atlas had this for the 44 districts and not for the 1 101 municipalities, and said
so. The Statistisches Landesamt publishes it per municipality on its migration page, as
the CSV behind one of the charts.

It matters here beyond completeness. The religion model works at municipal level by
distributing a district figure using census patterns, and every such distribution is a
guess constrained by what is known. This is a directly measured quantity at the same
resolution — not the same quantity, and emphatically not a religion figure, but a real
measurement where the model has an estimate. A reader can hold one against the other.

WHAT IT IS NOT. The share of people without German citizenship. Naturalised residents
and their German-born children are counted as German here and are invisible, which in
the long-settled communities is most of them. A municipality with a low foreign share may
have a long-established migrant population; the two are different questions.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / 'inputs/stala-auslaenderanteil-gemeinden-2025.csv'
GEOMETRY = ROOT / 'docs/data/geometry.json'
OUTPUT = ROOT / 'docs/data/municipal-foreign-share-2025.json'
PAGE = ('https://www.statistik-bw.de/leben-und-arbeiten/bevoelkerung-und-gebiet/'
        'migration-und-nationalitaet/')


def main() -> None:
    rows = list(csv.reader(SOURCE_FILE.read_text(encoding='utf-8-sig').splitlines(),
                           delimiter=';'))
    shares = {}
    for row in rows[2:]:
        if len(row) < 3 or not row[0].strip().isdigit():
            continue
        raw = row[2].strip().replace(',', '.')
        # A dash is not a zero. The source uses it where no value is published, and
        # painting those municipalities as 0 % would invent the strongest possible
        # statement about them.
        shares[row[0].strip()] = {
            'name': row[1].strip(),
            'foreign_share_percent': float(raw) if raw not in ('-', '', '.') else None,
        }

    known = {f['properties']['id'] for f in
             json.loads(GEOMETRY.read_text(encoding='utf-8'))['municipalities']}
    unknown = sorted(set(shares) - known)
    missing = sorted(known - set(shares))
    # Both sides must describe the same 1 103 units, or the map would silently leave
    # municipalities uncoloured and look like missing data rather than a broken join.
    if unknown or missing:
        raise SystemExit(f'{len(unknown)} Schlüssel ohne Geometrie, '
                         f'{len(missing)} Gemeinden ohne Wert — der Abgleich trägt nicht')

    values = sorted(v['foreign_share_percent'] for v in shares.values()
                    if v['foreign_share_percent'] is not None)
    doc = {
        'type': 'municipal_foreign_share',
        'schema_version': '1.0',
        'reference_period': '2025',
        'source': 'Statistisches Landesamt Baden-Württemberg',
        'source_page': PAGE,
        'licence': ('© Statistisches Landesamt Baden-Württemberg; Vervielfältigung und '
                    'Verbreitung, auch auszugsweise, mit Quellenangabe gestattet'),
        'measures': ('Anteil der Einwohnerinnen und Einwohner ohne deutsche '
                     'Staatsangehörigkeit an der Bevölkerung der Gemeinde.'),
        'not_a_religion_measure': (
            'Staatsangehörigkeit ist keine Religionszugehörigkeit und keine Herkunft. '
            'Eingebürgerte und ihre in Deutschland geborenen Kinder zählen hier als '
            'Deutsche und sind unsichtbar — in den lange ansässigen Gemeinschaften ist '
            'das die Mehrheit. Eine Gemeinde mit niedrigem Ausländeranteil kann eine '
            'lange ansässige Zuwanderungsbevölkerung haben.'),
        'municipalities_without_a_published_value': sum(
            1 for v in shares.values() if v['foreign_share_percent'] is None),
        'range': {'min': values[0], 'max': values[-1],
                  'median': values[len(values) // 2]},
        'municipalities': shares,
    }
    OUTPUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    OUTPUT.with_name('municipal-foreign-data.js').write_text(
        'window.ATLAS_MUNICIPAL_FOREIGN=' + json.dumps(doc, ensure_ascii=False,
                                                       separators=(',', ':')) + ';\n',
        encoding='utf-8')
    without = sum(1 for v in shares.values() if v['foreign_share_percent'] is None)
    print(f'{len(shares)} Gemeinden, {values[0]} bis {values[-1]} Prozent, '
          f'Median {doc["range"]["median"]}'
          + (f', {without} ohne veröffentlichten Wert' if without else ''))


if __name__ == '__main__':
    main()

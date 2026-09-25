#!/usr/bin/env python3
"""Foreign population by district and country grouping, from GENESIS table 12521-0041.

The atlas distributes its published state total across districts using nationality counts
from the state report A I 4-j. That report names twenty-five countries, and twenty-five
countries are 83.3 % of Baden-Württemberg's foreign population — as little as 67 % in
Heidelberg, 71 % in Freiburg, 76 % in Karlsruhe. A sixth of the people the model reasons
about sit in a residual it cannot describe, and the residual is largest exactly in the
university cities.

This table covers all of them. It reports no individual countries — GENESIS offers the
same table with either country groupings or nationalities, and this export carries the
groupings — but the groupings are exhaustive: Europa, Vorderasien, Nordafrika, Asien,
Afrika, Amerika, the former Yugoslavia, the recruitment countries. Every foreign resident
of every district falls into them.

So this does not replace the country detail and is not used to. It measures the part the
country list leaves over, at the same regional depth, one year later, from the same
register.

A NOTE ON THE GROUPINGS. They overlap by design. "Europa" contains "Gebiet des ehemaligen
Jugoslawien"; "Gastarbeiterländer" cuts across Europe, Africa and Asia; the EU vintages
(EU-27 as of 2020, EU-28 to 2020, EU-25 to 2006 …) are alternative definitions of the
same boundary at different dates, not successive groups. They must never be summed.
Only the categories this file marks as disjoint may be added together.

Licence: Datenlizenz Deutschland – Namensnennung – Version 2.0 (dl-de/by-2-0),
© Statistisches Bundesamt (Destatis).
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / 'inputs/genesis-12521-0041-auslaender-kreise-2025.csv'
OUTPUT = ROOT / 'docs/data/district-origin-groups-2025.json'
TABLE = 'https://genesis.destatis.de/datenbank/online/statistic/12521/table/12521-0041'

# The continents plus Australia partition the foreign population; everything else in the
# table is an overlapping view of it. Naming the disjoint set explicitly is the only
# thing that stops a later reader summing "Europa" and "Gastarbeiterländer".
DISJOINT = ['Europa', 'Afrika', 'Amerika', 'Asien', 'Australien und Ozeanien']
KEEP = DISJOINT + [
    'Insgesamt', 'EU-27 (seit 01.02.2020)', 'Drittstaaten zu EU-27 (seit 01.02.2020)',
    'Nordafrika', 'Westafrika', 'Zentralafrika', 'Ostafrika', 'Südafrika',
    'Nordamerika', 'Mittelamerika und Karibik', 'Südamerika',
    'Vorderasien', 'Süd- und Südostasien', 'Ost- und Zentralasien',
    'Gastarbeiterländer', 'Gebiet des ehemaligen Jugoslawien',
    'Gebiet der ehemaligen Sowjetunion',
]


def main() -> None:
    districts: dict[str, dict] = {}
    dates: set[str] = set()
    for row in csv.reader(SOURCE_FILE.read_text(encoding='utf-8-sig').splitlines(),
                          delimiter=';'):
        # A data row starts with a date and carries the total in the ninth column.
        if len(row) < 9 or row[0].count('.') != 2 or not row[1].startswith('08'):
            continue
        dates.add(row[0])
        entry = districts.setdefault(row[1], {'id': row[1], 'name': row[2], 'groups': {}})
        if row[3] in KEEP:
            value = row[8].strip().replace('.', '')
            entry['groups'][row[3]] = int(value) if value.isdigit() else None

    if len(districts) != 44:
        raise SystemExit(f'{len(districts)} Kreise gelesen, erwartet sind 44')
    if len(dates) != 1:
        raise SystemExit(f'mehrere Stichtage in einer Datei: {sorted(dates)}')

    # The disjoint groups must add up to the total, or the partition is not what this
    # file claims it is.
    for entry in districts.values():
        total = entry['groups'].get('Insgesamt')
        parts = [entry['groups'].get(name) for name in DISJOINT]
        if total and all(p is not None for p in parts):
            drift = abs(sum(parts) - total) / total
            if drift > 0.02:
                raise SystemExit(f'{entry["name"]}: Kontinente summieren sich zu '
                                 f'{sum(parts)}, die Gesamtzahl ist {total}')

    doc = {
        'type': 'district_foreign_population_by_origin_group',
        'schema_version': '1.0',
        'reference_date': sorted(dates)[0],
        'source': ('Statistisches Bundesamt (Destatis), GENESIS-Online, Tabelle '
                   '12521-0041: Ausländer: Kreise, Stichtag, Geschlecht, '
                   'Ländergruppierungen'),
        'source_url': TABLE,
        'licence': ('Datenlizenz Deutschland – Namensnennung – Version 2.0 '
                    '(dl-de/by-2-0), © Statistisches Bundesamt (Destatis)'),
        'licence_url': 'https://www.govdata.de/dl-de/by-2-0',
        'why_this_exists': (
            'Die 25 im Landesbericht genannten Staatsangehörigkeiten decken 83,3 Prozent '
            'der ausländischen Bevölkerung Baden-Württembergs ab, in Heidelberg nur 67 '
            'Prozent. Diese Gruppierungen decken sie vollständig ab und messen damit '
            'genau den Teil, den die Länderliste offenlässt.'),
        'groups_overlap': (
            'Die Gruppen überschneiden sich absichtlich: „Europa“ enthält das Gebiet des '
            'ehemaligen Jugoslawien, „Gastarbeiterländer“ reicht über Europa, Afrika und '
            'Asien hinweg. Sie dürfen nicht addiert werden. Nur die unter '
            'disjoint_groups genannten Kontinente ergeben zusammen die Gesamtzahl.'),
        'disjoint_groups': DISJOINT,
        'not_a_religion_measure': (
            'Staatsangehörigkeit ist keine Religionszugehörigkeit. Eingebürgerte und hier '
            'geborene Nachkommen haben einen deutschen Pass und stehen in keiner dieser '
            'Zahlen.'),
        'districts': [districts[k] for k in sorted(districts)],
    }
    OUTPUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    OUTPUT.with_name('origin-groups-data.js').write_text(
        'window.ATLAS_ORIGIN_GROUPS=' + json.dumps(doc, ensure_ascii=False,
                                                   separators=(',', ':')) + ';\n',
        encoding='utf-8')
    print(f'{len(districts)} Kreise, {len(KEEP)} Gruppen, Stichtag {sorted(dates)[0]}')


if __name__ == '__main__':
    main()

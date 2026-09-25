#!/usr/bin/env python3
"""Every nationality, in every district: GENESIS 12521-0041.

The atlas distributes its published state total across districts by nationality. Until
now the finest source available was the state report A I 4-j, which names twenty-five
countries — 83.3 % of Baden-Württemberg's foreign population, and as little as 67 % in
Heidelberg, 71 % in Freiburg, 76 % in Karlsruhe. The remaining sixth had no country and
could only be handled as a lump, and the lump was largest in the university cities.

This is the same register at the same regional depth with the full classification: 208
nationalities per district, reference date 31 December 2025. Nothing is left over.

Only Baden-Württemberg's 44 districts are kept, from an export covering all 477, and the
file is stored compressed. A public repository should not carry seven megabytes of
national data it does not publish.

WHAT IT STILL IS NOT. A nationality is not a religion and not an origin. Naturalised
residents and their German-born children hold German passports and appear in none of
these counts — in the long-settled communities that is most of the people the religion
model is about, which is exactly why the model corrects for them rather than reading
these numbers as if they were the population.

Licence: Datenlizenz Deutschland – Namensnennung – Version 2.0 (dl-de/by-2-0),
© Statistisches Bundesamt (Destatis).
"""
from __future__ import annotations
import csv
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / 'inputs/genesis-12521-0041-staatsangehoerigkeit-bw-2025.csv.gz'
COMPARE = ROOT / 'docs/data/district-origins-2024-12.json'
OUTPUT = ROOT / 'docs/data/district-nationalities-2025.json'
TABLE = 'https://genesis.destatis.de/datenbank/online/statistic/12521/table/12521-0041'


def number(value: str) -> int | None:
    value = (value or '').strip().replace('.', '')
    return int(value) if value.isdigit() else None


def main() -> None:
    districts: dict[str, dict] = {}
    dates: set[str] = set()
    with gzip.open(SOURCE_FILE, 'rt', encoding='utf-8') as handle:
        for row in csv.DictReader(handle, delimiter=';'):
            dates.add(row['stichtag'])
            entry = districts.setdefault(row['kreis_id'],
                                         {'id': row['kreis_id'], 'name': row['kreis'],
                                          'nationalities': {}})
            value = number(row['insgesamt'])
            if row['staatsangehoerigkeit'] == 'Insgesamt':
                entry['foreign_total'] = value
            elif value:
                entry['nationalities'][row['staatsangehoerigkeit']] = value

    if len(districts) != 44:
        raise SystemExit(f'{len(districts)} Kreise gelesen, erwartet sind 44')
    if len(dates) != 1:
        raise SystemExit(f'mehrere Stichtage: {sorted(dates)}')

    # The named nationalities must account for the district total. Where they do not,
    # the classification is not exhaustive and the file must say so rather than let a
    # reader assume it is.
    coverage = []
    for entry in districts.values():
        named = sum(entry['nationalities'].values())
        total = entry.get('foreign_total') or 0
        if not total:
            raise SystemExit(f'{entry["name"]}: keine Gesamtzahl')
        entry['named_share_percent'] = round(100 * named / total, 1)
        coverage.append(entry['named_share_percent'])
        if entry['named_share_percent'] < 95:
            raise SystemExit(f'{entry["name"]}: nur {entry["named_share_percent"]} % '
                             'der Ausländer haben eine Staatsangehörigkeit — die '
                             'Klassifikation ist nicht vollständig')

    previous = {r['id']: r for r in json.loads(COMPARE.read_text('utf-8'))['districts']}
    ignore = {'id', 'name', 'name_in_source', 'reference_period', 'foreign_total',
              'europe', 'eu_states'}
    before = []
    for key, entry in districts.items():
        old = previous.get(key)
        if old:
            named = sum(v for k, v in old.items()
                        if k not in ignore and isinstance(v, (int, float)))
            before.append(100 * named / old['foreign_total'])

    doc = {
        'type': 'district_foreign_population_by_nationality',
        'schema_version': '1.0',
        'reference_date': sorted(dates)[0],
        'source': ('Statistisches Bundesamt (Destatis), GENESIS-Online, Tabelle '
                   '12521-0041: Ausländer: Kreise, Stichtag, Geschlecht, '
                   'Staatsangehörigkeit'),
        'source_url': TABLE,
        'licence': ('Datenlizenz Deutschland – Namensnennung – Version 2.0 '
                    '(dl-de/by-2-0), © Statistisches Bundesamt (Destatis)'),
        'licence_url': 'https://www.govdata.de/dl-de/by-2-0',
        'coverage': {
            'nationalities': len({n for e in districts.values() for n in e['nationalities']}),
            'named_share_percent_min': min(coverage),
            'named_share_percent_max': max(coverage),
            'previous_source_named_share_percent': round(sum(before) / len(before), 1)
            if before else None,
            'note': ('Der bisher feinste Stand, der Landesbericht A I 4-j, nannte 25 '
                     'Staatsangehörigkeiten je Kreis. Diese Tabelle nennt alle.'),
        },
        'not_a_religion_measure': (
            'Staatsangehörigkeit ist keine Religionszugehörigkeit und keine Herkunft. '
            'Eingebürgerte und ihre in Deutschland geborenen Kinder haben einen '
            'deutschen Pass und stehen in keiner dieser Zahlen.'),
        'districts': [districts[k] for k in sorted(districts)],
    }
    OUTPUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f"{len(districts)} Kreise, {doc['coverage']['nationalities']} "
          f"Staatsangehörigkeiten, Abdeckung {min(coverage)}–{max(coverage)} % "
          f"(bisher im Mittel {doc['coverage']['previous_source_named_share_percent']} %)")


if __name__ == '__main__':
    main()

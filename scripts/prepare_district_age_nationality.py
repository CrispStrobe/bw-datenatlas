#!/usr/bin/env python3
"""Population by age group and nationality, per district: GENESIS 12411-03-03-4-B.

Two gaps close here.

A CURRENT DENOMINATOR. The atlas computes its foreign share per district from the
Fortschreibung at 30 November 2024, while its nationality counts now come from the
register at 31 December 2025. Two dates, two denominators, and any ratio between them is
slightly wrong. This table is the Fortschreibung at the same date as the register.

THE AGE OF THE FOREIGN POPULATION, PER DISTRICT. The atlas knows the age structure of
the state and, through the Mikrozensus, the age structure of people with a migration
background per district. It did not know the age structure of foreign nationals per
district, and that is the population every nationality figure in this atlas describes.

It matters for what this atlas is about. A community whose members are mostly over fifty
and one whose members are mostly under thirty need different things from a mosque, and
the map cannot tell them apart from a count of buildings.

WHAT IT IS NOT. "Ausländisch" means without a German passport. Naturalised residents and
their German-born children are counted as German here, so the age structure of an origin
group is not the age structure shown — the older cohorts of long-settled communities are
systematically missing from the foreign column.

Licence: Datenlizenz Deutschland – Namensnennung – Version 2.0 (dl-de/by-2-0),
© Statistisches Bundesamt (Destatis).
"""
from __future__ import annotations
import csv
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / 'inputs/genesis-12411-bevoelkerung-alter-nationalitaet-bw-2025.csv.gz'
OUTPUT = ROOT / 'docs/data/district-age-nationality-2025.json'
TABLE = ('https://genesis.destatis.de/datenbank/online/statistic/12411/'
         'table/12411-03-03-4-B')


def number(value: str) -> int | None:
    value = (value or '').strip().replace('.', '')
    return int(value) if value.lstrip('-').isdigit() else None


def main() -> None:
    districts: dict[str, dict] = {}
    dates: set[str] = set()
    order: list[str] = []
    with gzip.open(SOURCE_FILE, 'rt', encoding='utf-8') as handle:
        for row in csv.DictReader(handle, delimiter=';'):
            group = row['altersgruppe'].strip()
            if not group:
                continue
            dates.add(row['stichtag'])
            entry = districts.setdefault(row['kreis_id'],
                                         {'id': row['kreis_id'], 'name': row['kreis'],
                                          'age_groups': {}})
            values = {'total': number(row['ges']), 'german': number(row['de']),
                      'foreign': number(row['aus'])}
            if group == 'Insgesamt':
                entry.update({'population': values['total'],
                              'german': values['german'],
                              'foreign': values['foreign']})
            else:
                if group not in order:
                    order.append(group)
                entry['age_groups'][group] = values

    if len(districts) != 44:
        raise SystemExit(f'{len(districts)} Kreise gelesen, erwartet sind 44')

    # The age groups must reconstruct the district total, or they are not a partition
    # and the shares computed from them would be meaningless.
    for entry in districts.values():
        summed = sum(v['total'] for v in entry['age_groups'].values() if v['total'])
        if entry['population'] and abs(summed - entry['population']) > 2:
            raise SystemExit(f'{entry["name"]}: Altersgruppen summieren sich zu '
                             f'{summed}, die Gesamtzahl ist {entry["population"]}')
        entry['foreign_share_percent'] = round(100 * entry['foreign'] / entry['population'], 1)
        # Under 25 is where the difference between a settled and a recent community
        # shows most plainly.
        young = [g for g in order if g.startswith(('unter', '3 bis', '6 bis', '10 bis',
                                                   '15 bis', '18 bis', '20 bis'))]
        f_young = sum(entry['age_groups'][g]['foreign'] or 0 for g in young)
        d_young = sum(entry['age_groups'][g]['german'] or 0 for g in young)
        entry['under_25_share_foreign_percent'] = round(100 * f_young / entry['foreign'], 1)
        entry['under_25_share_german_percent'] = round(100 * d_young / entry['german'], 1)

    doc = {
        'type': 'district_population_by_age_and_nationality',
        'schema_version': '1.0',
        'reference_date': '2025-12-31',
        'source': ('Statistisches Bundesamt (Destatis), GENESIS-Online, Tabelle '
                   '12411-03-03-4-B: Bevölkerung nach Geschlecht, Nationalität und '
                   'Altersgruppen, Fortschreibung des Bevölkerungsstandes'),
        'source_url': TABLE,
        'licence': ('Datenlizenz Deutschland – Namensnennung – Version 2.0 '
                    '(dl-de/by-2-0), © Statistisches Bundesamt (Destatis)'),
        'licence_url': 'https://www.govdata.de/dl-de/by-2-0',
        'what_foreign_means': (
            '„Ausländisch“ heißt ohne deutschen Pass. Eingebürgerte und ihre in '
            'Deutschland geborenen Kinder zählen hier als Deutsche. Der Altersaufbau '
            'einer Herkunftsgruppe ist deshalb nicht der hier gezeigte: Gerade die '
            'älteren Jahrgänge lange ansässiger Gemeinschaften fehlen in der Spalte.'),
        'age_group_order': order,
        'districts': [districts[k] for k in sorted(districts)],
    }
    OUTPUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    OUTPUT.with_name('district-age-nationality-data.js').write_text(
        'window.ATLAS_DISTRICT_AGE_NAT=' + json.dumps(doc, ensure_ascii=False,
                                                      separators=(',', ':')) + ';\n',
        encoding='utf-8')
    print(f'{len(districts)} Kreise, {len(order)} Altersgruppen, Stichtag 31.12.2025')


if __name__ == '__main__':
    main()

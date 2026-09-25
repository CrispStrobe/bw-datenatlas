#!/usr/bin/env python3
"""The eighteen BAMF origin groups, per district, from the full nationality register.

The model needs, per district, the number of people holding the citizenship of each
origin group the BAMF publishes a muslim share for. Until now the finest district source
named twenty-five countries and covered eight of the eighteen groups; this builds all
eighteen from GENESIS 12521-0041, which names every nationality.

Two decisions are worth stating, because both could be made differently.

DEFUNCT NATIONALITIES. The register still carries people recorded under states that no
longer exist: "Serbien und Montenegro (2003-2006)" holds 2 270 people in this state,
"Serbien (einschl. Kosovo)" another 770. They are not added to Serbien, Montenegro or
Kosovo — nobody knows how they would split, and assigning them would put a guess inside
a number that reads as a count. They stay out, and this file records how many that is.

COMPOSITE GROUPS. The BAMF publishes one muslim share for "Ägypten/Algerien/Libyen/
Tunesien" and one for "Jemen/Saudi-Arabien/Vereinigte Arabische Emirate". Those are sums
of their member states here, which is what the share was computed for.

The result has the same shape as the state report's extract, so the model can read either
and the two can be compared.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIONALITIES = ROOT / 'docs/data/district-nationalities-2025.json'
GROUPS = ROOT / 'docs/data/district-origin-groups-2025.json'
OUTPUT = ROOT / 'docs/data/district-origins-full-2025.json'

# Column name in the output -> BAMF origin group -> the nationalities that make it up.
BAMF_GROUPS: dict[str, tuple[str, list[str]]] = {
    'turkey': ('Türkei', ['Türkei']),
    'syria': ('Syrien', ['Syrien']),
    'kosovo': ('Kosovo', ['Kosovo']),
    'serbia': ('Serbien', ['Serbien']),
    'iraq': ('Irak', ['Irak']),
    'afghanistan': ('Afghanistan', ['Afghanistan']),
    'bosnia_herzegovina': ('Bosnien-Herzegowina', ['Bosnien und Herzegowina']),
    'north_macedonia': ('Nordmazedonien', ['Nordmazedonien']),
    'albania': ('Albanien', ['Albanien']),
    'montenegro': ('Montenegro', ['Montenegro (ab 03.06.2006)']),
    'morocco': ('Marokko', ['Marokko']),
    'iran': ('Iran', ['Iran, Islamische Republik']),
    'pakistan': ('Pakistan', ['Pakistan']),
    'bangladesh': ('Bangladesch', ['Bangladesch']),
    'lebanon': ('Libanon', ['Libanon']),
    'jordan': ('Jordanien', ['Jordanien']),
    'gulf': ('Jemen/Saudi-Arabien/Vereinigte Arabische Emirate',
             ['Jemen', 'Saudi-Arabien', 'Vereinigte Arabische Emirate']),
    'north_africa': ('Ägypten/Algerien/Libyen/Tunesien',
                     ['Ägypten', 'Algerien', 'Libyen', 'Tunesien']),
}
# Recorded, not assigned: successor states cannot be reconstructed from these.
DEFUNCT = ['Serbien und Montenegro (05.02.2003-02.06.2006)',
           'Serbien (einschl. Kosovo) (03.06.2006-16.02.2008)']


def main() -> None:
    nat = json.loads(NATIONALITIES.read_text(encoding='utf-8'))
    grp = {d['id']: d for d in json.loads(GROUPS.read_text(encoding='utf-8'))['districts']}

    known = {n for d in nat['districts'] for n in d['nationalities']}
    missing = {name for _, names in BAMF_GROUPS.values() for name in names} - known
    if missing:
        raise SystemExit(f'Staatsangehörigkeit nicht in der Quelle: {sorted(missing)}')

    districts, unassigned = [], 0
    for d in nat['districts']:
        counts = d['nationalities']
        groups = grp.get(d['id'], {}).get('groups', {})
        row = {'id': d['id'], 'name': d['name'],
               'reference_period': nat['reference_date'],
               'foreign_total': d['foreign_total'],
               # Needed for the two fallback naturalisation ratios.
               'europe': groups.get('Europa'),
               'eu_states': groups.get('EU-27 (seit 01.02.2020)')}
        for column, (_, names) in BAMF_GROUPS.items():
            row[column] = sum(counts.get(n, 0) for n in names)
        districts.append(row)
        unassigned += sum(counts.get(n, 0) for n in DEFUNCT)

    doc = {
        'type': 'district_origins_all_bamf_groups',
        'schema_version': '1.0',
        'reference_period': nat['reference_date'],
        'source': nat['source'],
        'source_table': '12521-0041',
        'source_url': nat['source_url'],
        'licence': nat['licence'],
        'measurement': ('Ausländische Bevölkerung nach Staatsangehörigkeit, '
                        'Ausländerzentralregister, zusammengefasst zu den 18 '
                        'Herkunftsgruppen des BAMF-Forschungsberichts 55.'),
        'columns': list(BAMF_GROUPS),
        'group_labels': {c: g for c, (g, _) in BAMF_GROUPS.items()},
        'group_members': {c: n for c, (_, n) in BAMF_GROUPS.items()},
        'defunct_nationalities_not_assigned': {
            'nationalities': DEFUNCT, 'persons': unassigned,
            'why': ('Im Register geführte Staatsangehörigkeiten untergegangener Staaten. '
                    'Wie sie sich auf Serbien, Montenegro und Kosovo verteilen, weiß '
                    'niemand; eine Zuordnung wäre eine Schätzung innerhalb einer Zahl, '
                    'die wie eine Zählung aussieht.'),
        },
        'districts': districts,
    }
    OUTPUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    total = sum(sum(r[c] for c in BAMF_GROUPS) for r in districts)
    print(f'{len(districts)} Kreise, {len(BAMF_GROUPS)} Herkunftsgruppen, '
          f'{total:,} Personen erfasst, {unassigned:,} in untergegangenen '
          f'Staatsangehörigkeiten nicht zugeordnet'.replace(',', '.'))


if __name__ == '__main__':
    main()

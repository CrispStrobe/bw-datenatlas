#!/usr/bin/env python3
"""Second generation and marital status by migration status per BW district.

Source: Statistisches Landesamt Baden-Württemberg, GENESIS-Online table 12211-0504,
"Bevölkerung nach Migrationsstatus, Geschlecht und Familienstand", population in
private main-residence households, both sexes.

The valuable series here is "mit Migrationshintergrund / ohne eigene
Migrationserfahrung / Deutsche": people with a migration background who were born in
Germany and hold German citizenship. They are exactly the group the
Ausländerzentralregister cannot see, and the reason the modelled estimate needs a
naturalisation-and-descendants correction at all.

This file therefore serves two purposes. It is published as context, and it provides an
independent check on the correction: the population with migration background that is
invisible to citizenship statistics is MH minus foreign citizens, and the second
generation should account for a large, stable part of it in every district.

Nothing here enters the modelled Muslim figures. Marital status in particular is
published as context only and is not a religious indicator.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ('Statistisches Landesamt Baden-Württemberg, GENESIS-Online 12211-0504, '
          'Grundprogramm des Mikrozensus')
SOURCE_URL = 'https://daten.statistik-bw.de/genesisonline/online?operation=table&code=12211-0504'
COMBINED = {'08217KRSI': ['08211', '08216']}
SECOND_GENERATION = 'mit Migrationshintergrund | ohne eigene Migrationserfahrung | Deutsche'
MARITAL = ['ledig', 'verheiratet', 'geschieden', 'verwitwet']


def value(token: str):
    token = (token or '').strip()
    return None if token in {'', '/', '.', '-', '–', 'x'} else int(token)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path,
                    default=ROOT / 'inputs/mikrozensus-12211-0504-generationen-familienstand-kreise.csv')
    ap.add_argument('--year', default='2024')
    ap.add_argument('--output', type=Path,
                    default=ROOT / 'docs/data/district-generations-2024.json')
    args = ap.parse_args()

    cells: dict[tuple, int | None] = {}
    labels: dict[str, str] = {}
    for r in csv.DictReader(args.input.open(encoding='utf-8')):
        if r['year'] != args.year:
            continue
        labels[r['region_code']] = r['region_label']
        cells[(r['region_code'], r['series'], r['migration_status'], r['detail'])] = \
            value(r['value_thousand'])
    if not cells:
        raise SystemExit(f'No rows for year {args.year} in {args.input}')

    atlas = json.loads((ROOT / 'docs/data/atlas.json').read_text(encoding='utf-8'))
    names = {d['id']: d['name'] for d in atlas['districts']}
    origins = json.loads((ROOT / 'docs/data/district-origins-2024-12.json').read_text(encoding='utf-8'))
    foreign = {d['id']: d['foreign_total'] for d in origins['districts']}

    districts, anomalies = [], []
    for code in sorted(labels):
        ids = COMBINED.get(code, [code[:5]])
        mh_total = cells.get((code, 'by_marital_status', 'mit Migrationshintergrund', 'Insgesamt'))
        second = cells.get((code, 'second_generation_german', SECOND_GENERATION, 'Insgesamt'))
        marital = {m: cells.get((code, 'by_marital_status', 'mit Migrationshintergrund', m))
                   for m in MARITAL}

        # People with a migration background whom citizenship statistics cannot see.
        foreign_here = sum(foreign[i] for i in ids if i in foreign)
        invisible = (mh_total * 1000 - foreign_here) if mh_total is not None else None
        if invisible is not None and invisible < 0:
            anomalies.append({'region_label': labels[code],
                              'migration_background_persons': mh_total * 1000,
                              'foreign_citizens_persons': foreign_here,
                              'note': 'Migrationshintergrund kleiner als Ausländerbestand'})

        known = {k: v for k, v in marital.items() if v is not None}
        marital_sum = sum(known.values()) if known else None
        row = {
            'mikrozensus_region_code': code,
            'mikrozensus_region_label': labels[code],
            'shared_region': len(ids) > 1,
            'migration_background_thousand': mh_total,
            'second_generation_german_thousand': second,
            'second_generation_share_of_mh_percent': round(100 * second / mh_total, 1)
            if mh_total and second is not None else None,
            'foreign_citizens_persons': foreign_here,
            'invisible_to_citizenship_persons': invisible,
            'second_generation_share_of_invisible_percent': round(100 * second * 1000 / invisible, 1)
            if invisible and invisible > 0 and second is not None else None,
            'marital_status_thousand': marital,
            'marital_status_complete': len(known) == len(MARITAL),
            # A suppressed category stays missing rather than becoming a zero share.
            'marital_status_share_percent': {
                k: (round(100 * v / marital_sum, 1) if marital_sum and v is not None else None)
                for k, v in marital.items()} if marital_sum else None,
        }
        for i in ids:
            districts.append({'id': i, 'name': names[i], **row})

    if len(districts) != 44:
        raise ValueError(f'Expected 44 districts, produced {len(districts)}')
    if anomalies:
        raise ValueError(f'Migration background below foreign citizens: {anomalies}')
    for d in districts:
        s = d['second_generation_share_of_mh_percent']
        if s is not None and not 10 < s < 60:
            raise ValueError(f'Implausible second-generation share in {d["name"]}: {s}')

    data = {
        'type': 'district_generations_and_marital_status',
        'schema_version': '1.0',
        'reference_period': args.year,
        'source': SOURCE,
        'source_url': SOURCE_URL,
        'population_base': 'Bevölkerung in Hauptwohnsitzhaushalten, beide Geschlechter',
        'second_generation_definition': (
            'Mit Migrationshintergrund, ohne eigene Migrationserfahrung, deutsche '
            'Staatsangehörigkeit: hier geboren und deutscher Pass.'),
        'invisible_definition': (
            'Bevölkerung mit Migrationshintergrund abzüglich der ausländischen '
            'Staatsangehörigen desselben Kreises. Diese Menschen sind in der '
            'Ausländerstatistik nicht sichtbar.'),
        'why_it_matters': (
            'Genau diese Gruppe begründet die Korrektur der Modellrechnung um '
            'Eingebürgerte und hier geborene Nachkommen.'),
        'not_used_for_religion_model': (
            'Diese Angaben gehen nicht in die Modellrechnung ein. Der Familienstand ist '
            'kein Merkmal der Religionszugehörigkeit.'),
        'survey_note': 'Stichprobenerhebung mit Zufallsfehler; Angaben in Tausend.',
        'combined_regions': COMBINED,
        'districts': districts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    view = {
        'meta': {k: data[k] for k in ('reference_period', 'source', 'source_url',
                                      'second_generation_definition', 'invisible_definition',
                                      'why_it_matters', 'not_used_for_religion_model',
                                      'survey_note')},
        'districts': {d['id']: {
            'second_pct': d['second_generation_share_of_mh_percent'],
            'second_thousand': d['second_generation_german_thousand'],
            'invisible': d['invisible_to_citizenship_persons'],
            'second_of_invisible_pct': d['second_generation_share_of_invisible_percent'],
            'marital': d['marital_status_share_percent'],
        } for d in districts},
    }
    args.output.with_name('generation-data.js').write_text(
        'window.ATLAS_GENERATIONS=' + json.dumps(view, ensure_ascii=False,
                                                 separators=(',', ':')) + ';\n', encoding='utf-8')

    shares = [d['second_generation_share_of_mh_percent'] for d in districts
              if d['second_generation_share_of_mh_percent'] is not None]
    inv = sum(d['invisible_to_citizenship_persons'] for d in districts
              if not d['shared_region'] and d['invisible_to_citizenship_persons'])
    inv += next(d['invisible_to_citizenship_persons'] for d in districts if d['shared_region'])
    print(f'{len(districts)} districts, year {args.year}.')
    print(f'Second generation with German citizenship: {min(shares):.1f}-{max(shares):.1f} % of the '
          f'population with migration background.')
    print(f'Invisible to citizenship statistics, BW: {inv:,}'.replace(',', '.'))


if __name__ == '__main__':
    main()

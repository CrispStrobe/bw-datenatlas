#!/usr/bin/env python3
"""Employment and education by migration status per BW district, from the Mikrozensus.

Source: Statistisches Landesamt Baden-Württemberg, GENESIS-Online table 12211-0513,
"Bevölkerung ab 15 Jahren nach Migrationsstatus, Erwerbsbeteiligung und Bildungsstand
(nach ISCED)", population aged 15+ in private main-residence households.

WHAT THIS IS NOT USED FOR: this table does not enter the modelled Muslim population,
and it must not. Education and employment are not indicators of religion, and deriving
a religious affiliation from them would be exactly the inference this project refuses
to make. The figures are published here as context about the population with migration
background, side by side with the population without it, and nothing more.

The Mikrozensus is a sample survey published in thousands. "Erwerbslose" is suppressed
in almost every district because the counts are too small, so an unemployment rate is
deliberately not derived. Rastatt and Baden-Baden again share one survey region.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ('Statistisches Landesamt Baden-Württemberg, GENESIS-Online 12211-0513, '
          'Grundprogramm des Mikrozensus')
SOURCE_URL = 'https://daten.statistik-bw.de/genesisonline/online?operation=table&code=12211-0513'
COMBINED = {'08217KRSI': ['08211', '08216']}
EDUCATION = {'niedrig': 'low', 'mittel': 'medium', 'hoch': 'high'}


def value(token: str):
    token = (token or '').strip()
    return None if token in {'', '/', '.', '-', '–', 'x'} else int(token)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path,
                    default=ROOT / 'inputs/mikrozensus-12211-0513-erwerb-bildung-kreise.csv')
    ap.add_argument('--year', default='2024')
    ap.add_argument('--output', type=Path,
                    default=ROOT / 'docs/data/district-socioeconomics-2024.json')
    args = ap.parse_args()

    cells: dict[tuple, int | None] = {}
    labels: dict[str, str] = {}
    for r in csv.DictReader(args.input.open(encoding='utf-8')):
        if r['year'] != args.year:
            continue
        labels[r['region_code']] = r['region_label']
        cells[(r['region_code'], r['labour_status'], r['migration_status'],
               r['education_isced'])] = value(r['value_thousand'])
    if not cells:
        raise SystemExit(f'No rows for year {args.year} in {args.input}')

    atlas = json.loads((ROOT / 'docs/data/atlas.json').read_text(encoding='utf-8'))
    names = {d['id']: d['name'] for d in atlas['districts']}

    districts, incomplete = [], []
    for code in sorted(labels):
        ids = COMBINED.get(code, [code[:5]])
        for i in ids:
            if i not in names:
                raise ValueError(f'Mikrozensus region {code} maps to unknown district {i}')
        row = {'mikrozensus_region_code': code, 'mikrozensus_region_label': labels[code],
               'shared_region': len(ids) > 1}
        for status, key in (('mit Migrationshintergrund', 'with_migration_background'),
                            ('ohne Migrationshintergrund', 'without_migration_background')):
            total = cells.get((code, 'Insgesamt', status, 'Insgesamt'))
            employed = cells.get((code, 'Erwerbstätige', status, 'Insgesamt'))
            education = {out: cells.get((code, 'Insgesamt', status, src))
                         for src, out in EDUCATION.items()}
            known = [v for v in education.values() if v is not None]
            row[key] = {
                'population_15plus_thousand': total,
                'employed_thousand': employed,
                # Share of the 15+ population in work. Not an unemployment rate: the
                # source suppresses "Erwerbslose" in almost every district.
                'employed_share_percent': round(100 * employed / total, 1)
                if total and employed is not None else None,
                'education_thousand': education,
                'education_high_share_percent': round(100 * education['high'] / total, 1)
                if total and education['high'] is not None else None,
                'education_incomplete': len(known) != len(EDUCATION),
            }
            if len(known) != len(EDUCATION):
                incomplete.append({'region_label': labels[code], 'migration_status': status})
        for i in ids:
            districts.append({'id': i, 'name': names[i], **row})

    if len(districts) != 44:
        raise ValueError(f'Expected 44 districts, produced {len(districts)}')
    for d in districts:
        for key in ('with_migration_background', 'without_migration_background'):
            s = d[key]['employed_share_percent']
            if s is not None and not 20 < s < 90:
                raise ValueError(f'Implausible employment share in {d["name"]}: {s}')

    data = {
        'type': 'district_socioeconomics_by_migration_status',
        'schema_version': '1.0',
        'reference_period': args.year,
        'source': SOURCE,
        'source_url': SOURCE_URL,
        'population_base': 'Bevölkerung ab 15 Jahren in Hauptwohnsitzhaushalten',
        'unit_note': 'Die Quelle veröffentlicht in Tausend.',
        'survey_note': 'Stichprobenerhebung mit Zufallsfehler.',
        'not_used_for_religion_model': (
            'Diese Angaben gehen nicht in die Modellrechnung zur muslimischen Bevölkerung '
            'ein. Bildung und Erwerbsbeteiligung sind keine Merkmale der '
            'Religionszugehörigkeit und werden nicht dafür verwendet.'),
        'no_unemployment_rate': (
            'Eine Erwerbslosenquote wird nicht gebildet: die Quelle hält die Erwerbslosen '
            'in fast allen Kreisen wegen zu kleiner Fallzahlen geheim.'),
        'education_classification': 'ISCED 2011, zusammengefasst zu niedrig, mittel und hoch.',
        'combined_regions': COMBINED,
        'incomplete_education_breakdowns': incomplete,
        'districts': districts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    # Compact view for the browser.
    view = {
        'meta': {k: data[k] for k in ('reference_period', 'source', 'source_url',
                                      'population_base', 'survey_note',
                                      'not_used_for_religion_model', 'no_unemployment_rate',
                                      'education_classification')},
        'districts': {d['id']: {
            'mh': {'pop': d['with_migration_background']['population_15plus_thousand'],
                   'employed_pct': d['with_migration_background']['employed_share_percent'],
                   'high_pct': d['with_migration_background']['education_high_share_percent']},
            'no_mh': {'pop': d['without_migration_background']['population_15plus_thousand'],
                      'employed_pct': d['without_migration_background']['employed_share_percent'],
                      'high_pct': d['without_migration_background']['education_high_share_percent']},
            'shared_region': d['shared_region'],
        } for d in districts},
    }
    args.output.with_name('context-data.js').write_text(
        'window.ATLAS_CONTEXT=' + json.dumps(view, ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')

    mit = [d['with_migration_background']['employed_share_percent'] for d in districts
           if d['with_migration_background']['employed_share_percent'] is not None]
    ohne = [d['without_migration_background']['employed_share_percent'] for d in districts
            if d['without_migration_background']['employed_share_percent'] is not None]
    print(f'{len(districts)} districts, year {args.year}.')
    print(f'Employed share 15+: with migration background {min(mit):.1f}-{max(mit):.1f} %, '
          f'without {min(ohne):.1f}-{max(ohne):.1f} %.')
    if incomplete:
        print(f'Education breakdown incomplete in {len(incomplete)} case(s).')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Age structure by migration status per BW district, from the Mikrozensus.

Source: Statistisches Landesamt Baden-Württemberg, GENESIS-Online table 12211-0503,
"Bevölkerung nach Migrationsstatus, Geschlecht und Alter", population in private
main-residence households, both sexes.

This answers how young the population with migration background is in each district,
and how that compares with the population without it.

WHAT IT IS NOT: an age structure of the modelled Muslim population. No source in this
collection publishes the age composition of Muslims for Baden-Württemberg or for
Germany, so none is derived here. Migration background is a much broader group than
the modelled Muslim population, and its age profile must not be read as theirs.

The Mikrozensus is a sample published in thousands and suppresses small cells. Age
groups that are suppressed stay missing; a district's shares are only computed from
the age groups the source actually publishes, and the covered fraction is reported so
a partly suppressed district cannot be mistaken for a complete one.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ('Statistisches Landesamt Baden-Württemberg, GENESIS-Online 12211-0503, '
          'Grundprogramm des Mikrozensus')
SOURCE_URL = 'https://daten.statistik-bw.de/genesisonline/online?operation=table&code=12211-0503'
COMBINED = {'08217KRSI': ['08211', '08216']}
# Printed order, and the key used in the output.
AGE_GROUPS = [
    ('unter 15 Jahre', 'under_15'),
    ('15 bis unter 25 Jahre', '15_to_24'),
    ('25 bis unter 35 Jahre', '25_to_34'),
    ('35 bis unter 45 Jahre', '35_to_44'),
    ('45 bis unter 55 Jahre', '45_to_54'),
    ('55 bis unter 65 Jahre', '55_to_64'),
    ('65 Jahre und mehr', '65_plus'),
]
YOUNG = {'under_15', '15_to_24'}
# The source publishes the total and the population with migration background. The
# population without it is the difference, computed only where both are published.
MIN_COVERAGE_PERCENT = 90.0

def value(token: str):
    token = (token or '').strip()
    return None if token in {'', '/', '.', '-', '–', 'x'} else int(token)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path,
                    default=ROOT / 'inputs/mikrozensus-12211-0503-migrationsstatus-kreise.csv')
    ap.add_argument('--year', default='2024')
    ap.add_argument('--output', type=Path, default=ROOT / 'docs/data/district-age-2024.json')
    args = ap.parse_args()

    cells: dict[tuple, int | None] = {}
    labels: dict[str, str] = {}
    for r in csv.DictReader(args.input.open(encoding='utf-8')):
        if r['year'] != args.year:
            continue
        labels[r['region_code']] = r['region_label']
        cells[(r['region_code'], r['migration_status'], r['age_group'])] = value(r['value_thousand'])
    if not cells:
        raise SystemExit(f'No rows for year {args.year} in {args.input}')

    atlas = json.loads((ROOT / 'docs/data/atlas.json').read_text(encoding='utf-8'))
    names = {d['id']: d['name'] for d in atlas['districts']}

    districts, partial = [], []
    for code in sorted(labels):
        ids = COMBINED.get(code, [code[:5]])
        row = {'mikrozensus_region_code': code, 'mikrozensus_region_label': labels[code],
               'shared_region': len(ids) > 1}

        total_groups = {out: cells.get((code, 'Insgesamt', src)) for src, out in AGE_GROUPS}
        mh_groups = {out: cells.get((code, 'mit Migrationshintergrund', src)) for src, out in AGE_GROUPS}
        # Without migration background is a difference, so it exists only where both sides do.
        no_groups = {k: (total_groups[k] - mh_groups[k])
                     if total_groups[k] is not None and mh_groups[k] is not None else None
                     for k in total_groups}

        for key, groups, published_total in (
                ('total', total_groups, cells.get((code, 'Insgesamt', 'Insgesamt'))),
                ('with_migration_background', mh_groups,
                 cells.get((code, 'mit Migrationshintergrund', 'Insgesamt'))),
                ('without_migration_background', no_groups, None)):
            known = {k: v for k, v in groups.items() if v is not None}
            covered = sum(known.values()) if known else None
            coverage = (round(100 * covered / published_total, 1)
                        if published_total and covered is not None else None)
            complete = len(known) == len(AGE_GROUPS)
            # A share computed from half the age groups is not a share of anything
            # meaningful, so it is withheld rather than published with a caveat.
            reportable = complete or (coverage is not None and coverage >= MIN_COVERAGE_PERCENT)
            young = sum(v for k, v in known.items() if k in YOUNG) if known else None
            under15 = known.get('under_15')
            row[key] = {
                'population_thousand': published_total,
                'age_groups_thousand': groups,
                'published_groups': len(known),
                'complete': complete,
                'covered_thousand': covered,
                'coverage_of_total_percent': coverage,
                'shares_reportable': reportable,
                'under_25_share_of_covered_percent': round(100 * young / covered, 1)
                if reportable and covered and young is not None else None,
                'under_15_share_of_covered_percent': round(100 * under15 / covered, 1)
                if reportable and covered and under15 is not None else None,
                'suppressed_groups': [k for k, v in groups.items() if v is None],
            }
            if not complete:
                partial.append({'region_label': labels[code], 'series': key,
                                'suppressed': row[key]['suppressed_groups'],
                                'shares_withheld': not reportable})
        for i in ids:
            districts.append({'id': i, 'name': names[i], **row})

    if len(districts) != 44:
        raise ValueError(f'Expected 44 districts, produced {len(districts)}')
    for d in districts:
        for key in ('total', 'with_migration_background', 'without_migration_background'):
            s = d[key]['under_25_share_of_covered_percent']
            if s is not None and not 0 < s < 70:
                raise ValueError(f'Implausible under-25 share in {d["name"]} ({key}): {s}')

    data = {
        'type': 'district_age_structure_by_migration_status',
        'schema_version': '1.0',
        'reference_period': args.year,
        'source': SOURCE,
        'source_url': SOURCE_URL,
        'population_base': 'Bevölkerung in Hauptwohnsitzhaushalten, beide Geschlechter',
        'unit_note': 'Die Quelle veröffentlicht in Tausend.',
        'survey_note': 'Stichprobenerhebung mit Zufallsfehler; kleine Altersgruppen werden geheim gehalten.',
        'share_basis': ('Anteile beziehen sich auf die Summe der veröffentlichten '
                        'Altersgruppen, nicht auf die Gesamtbevölkerung. Der Deckungsgrad '
                        'steht je Kreis daneben.'),
        'not_a_muslim_age_structure': (
            'Dies ist die Altersgliederung der Bevölkerung mit Migrationshintergrund, '
            'nicht die der modellierten muslimischen Bevölkerung. Für diese veröffentlicht '
            'keine hier verwendete Quelle eine Altersgliederung; es wird auch keine '
            'abgeleitet.'),
        'age_groups': [out for _, out in AGE_GROUPS],
        'minimum_coverage_for_shares_percent': MIN_COVERAGE_PERCENT,
        'derived_without_migration_background': 'Insgesamt minus mit Migrationshintergrund, nur wo beide veröffentlicht sind.',
        'combined_regions': COMBINED,
        'partially_suppressed': partial,
        'districts': districts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    view = {
        'meta': {k: data[k] for k in ('reference_period', 'source', 'source_url',
                                      'survey_note', 'share_basis',
                                      'not_a_muslim_age_structure')},
        'age_groups': [out for _, out in AGE_GROUPS],
        'labels': {out: src for src, out in AGE_GROUPS},
        'districts': {d['id']: {
            'mh': {'u25': d['with_migration_background']['under_25_share_of_covered_percent'],
                   'u15': d['with_migration_background']['under_15_share_of_covered_percent'],
                   'groups': d['with_migration_background']['age_groups_thousand'],
                   'coverage': d['with_migration_background']['coverage_of_total_percent']},
            'no_mh': {'u25': d['without_migration_background']['under_25_share_of_covered_percent'],
                      'u15': d['without_migration_background']['under_15_share_of_covered_percent'],
                      'groups': d['without_migration_background']['age_groups_thousand'],
                      'coverage': d['without_migration_background']['coverage_of_total_percent']},
        } for d in districts},
    }
    args.output.with_name('age-data.js').write_text(
        'window.ATLAS_AGE=' + json.dumps(view, ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')

    mh = [d['with_migration_background']['under_25_share_of_covered_percent'] for d in districts
          if d['with_migration_background']['under_25_share_of_covered_percent'] is not None]
    no = [d['without_migration_background']['under_25_share_of_covered_percent'] for d in districts
          if d['without_migration_background']['under_25_share_of_covered_percent'] is not None]
    print(f'{len(districts)} districts, year {args.year}.')
    print(f'Under 25, with migration background: {min(mh):.1f}-{max(mh):.1f} % '
          f'(median {sorted(mh)[len(mh)//2]:.1f}); without: {min(no):.1f}-{max(no):.1f} % '
          f'(median {sorted(no)[len(no)//2]:.1f}).')
    print(f'Partially suppressed age breakdowns: {len(partial)}')


if __name__ == '__main__':
    main()

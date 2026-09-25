#!/usr/bin/env python3
"""Population with migration background per BW district, from the Mikrozensus.

Source: Statistisches Landesamt Baden-Württemberg, GENESIS-Online table 12211-0503,
"Bevölkerung nach Migrationsstatus, Geschlecht und Alter" (Grundprogramm des
Mikrozensus), population in private main-residence households.

Why this matters: the Ausländerzentralregister records citizenship, so naturalised
residents and their German-born children are invisible there. "Migrationshintergrund"
includes them, and BAMF's definition of the Muslim population is built on migration
background, not on passports. This table is therefore the key that can carry the part
of the population the citizenship data cannot see.

Two properties of the source are handled explicitly rather than smoothed over:

1. The Mikrozensus reports Rastatt and Baden-Baden as one combined region
   (08217KRSI), so BW has 43 survey regions for 44 districts. Both districts receive
   the combined region's rate; they are never given separate, invented rates.
2. For that combined region the published "Insgesamt" value is inconsistent with its
   own "mit Migrationshintergrund" value (55 vs 115 thousand; 55 is Baden-Baden
   alone). Its denominator is therefore taken from the atlas population of the two
   districts, and the substitution is recorded in the output.

The Mikrozensus is a sample survey published in thousands. Values carry sampling error
and are unsuitable as exact counts; they are used here only as a spatial key.
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
# The one Mikrozensus region that is not a single district.
COMBINED = {'08217KRSI': ['08211', '08216']}


def value(token: str):
    """'/' and '.' mark values the survey does not publish (too few cases)."""
    token = (token or '').strip()
    if token in {'', '/', '.', '-', '–', 'x'}:
        return None
    return int(token)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path,
                    default=ROOT / 'inputs/mikrozensus-12211-0503-migrationsstatus-kreise.csv')
    ap.add_argument('--year', default='2024')
    ap.add_argument('--output', type=Path, default=ROOT / 'docs/data/district-migration-2024.json')
    args = ap.parse_args()

    # The input now also carries the age breakdown; this script uses the all-ages rows.
    rows = [r for r in csv.DictReader(args.input.open(encoding='utf-8'))
            if r['year'] == args.year and r.get('age_group', 'Insgesamt') == 'Insgesamt']
    if not rows:
        raise SystemExit(f'No rows for year {args.year} in {args.input}')

    by_region: dict[str, dict] = {}
    for r in rows:
        rec = by_region.setdefault(r['region_code'], {'label': r['region_label']})
        key = 'total' if r['migration_status'] == 'Insgesamt' else 'migration_background'
        rec[key] = value(r['value_thousand'])

    atlas = json.loads((ROOT / 'docs/data/atlas.json').read_text(encoding='utf-8'))
    population = {d['id']: d['population'] for d in atlas['districts']}

    districts, notes = [], []
    for code, rec in sorted(by_region.items()):
        ids = COMBINED.get(code, [code[:5]])
        for i in ids:
            if i not in population:
                raise ValueError(f'Mikrozensus region {code} maps to unknown district {i}')
        total, mh = rec.get('total'), rec.get('migration_background')
        if mh is None:
            raise ValueError(f'No migration-background value for {code} ({rec["label"]})')

        # A total below its own subgroup cannot be the denominator for that subgroup.
        denominator_source = 'mikrozensus'
        if total is None or mh > total:
            denominator_source = 'atlas_district_population'
            notes.append({'region_code': code, 'region_label': rec['label'],
                          'published_total_thousand': total,
                          'published_migration_background_thousand': mh,
                          'reason': 'published total is inconsistent with its own subgroup',
                          'denominator_used': 'sum of atlas district population'})
            denominator = sum(population[i] for i in ids) / 1000
        else:
            denominator = total

        share = 100 * mh / denominator if denominator else None
        for i in ids:
            districts.append({
                'id': i,
                'name': next(d['name'] for d in atlas['districts'] if d['id'] == i),
                'mikrozensus_region_code': code,
                'mikrozensus_region_label': rec['label'],
                'shared_region': len(ids) > 1,
                'migration_background_thousand': mh,
                'reference_population_thousand': round(denominator, 1),
                'denominator_source': denominator_source,
                'migration_background_share_percent': round(share, 2) if share is not None else None,
            })

    if len(districts) != 44:
        raise ValueError(f'Expected 44 districts, produced {len(districts)}')
    for d in districts:
        s = d['migration_background_share_percent']
        if s is None or not (5 < s < 80):
            raise ValueError(f'Implausible migration-background share in {d["name"]}: {s}')

    data = {
        'type': 'district_migration_background',
        'schema_version': '1.0',
        'reference_period': args.year,
        'source': SOURCE,
        'source_url': SOURCE_URL,
        'population_base': 'Bevölkerung in Hauptwohnsitzhaushalten',
        'unit_note': 'Die Quelle veröffentlicht in Tausend.',
        'survey_note': ('Stichprobenerhebung mit Zufallsfehler. Geeignet als räumlicher '
                        'Schlüssel, nicht als exakte Personenzahl.'),
        'measurement': 'migration_background_includes_naturalised',
        'not_a_religion_dataset': ('Migrationshintergrund ist keine Religionszugehörigkeit. '
                                   'Diese Tabelle enthält keine Angaben zur Religion.'),
        'regions_in_source': len(by_region),
        'combined_regions': COMBINED,
        'denominator_substitutions': notes,
        'districts': districts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    total_mh = sum(d['migration_background_thousand'] for d in districts if not d['shared_region'])
    total_mh += next(d['migration_background_thousand'] for d in districts if d['shared_region'])
    print(f'{len(districts)} districts from {len(by_region)} Mikrozensus regions, year {args.year}.')
    print(f'Migration background total: {total_mh} thousand.')
    if notes:
        print(f'Denominator substituted for {len(notes)} region(s):',
              ', '.join(n['region_label'] for n in notes))


if __name__ == '__main__':
    main()

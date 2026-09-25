#!/usr/bin/env python3
"""Migration background per BW district over time, 2021 to 2025.

Source: Statistisches Landesamt Baden-Württemberg, GENESIS-Online table 12211-0503,
Grundprogramm des Mikrozensus, population in private main-residence households.

Only one series is built here, because only one is comparable across all five years in
the data at hand: the population with migration background, and its share of the
district population. The modelled Muslim figures are NOT extended backwards. Doing so
would require the origin data and the published state total for each year, and the
state total exists only for 2025.

The Mikrozensus is a sample. Year-to-year movements in a single district are often
smaller than the sampling error, so changes are reported as differences in percentage
points over the full period rather than as annual rates, and the reader is told that
short movements should not be over-read.
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


def value(token: str):
    token = (token or '').strip()
    return None if token in {'', '/', '.', '-', '–', 'x'} else int(token)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path,
                    default=ROOT / 'inputs/mikrozensus-12211-0503-migrationsstatus-kreise.csv')
    ap.add_argument('--output', type=Path, default=ROOT / 'docs/data/district-timeseries.json')
    args = ap.parse_args()

    rows = [r for r in csv.DictReader(args.input.open(encoding='utf-8'))
            if r['age_group'] == 'Insgesamt']
    years = sorted({r['year'] for r in rows})
    labels: dict[str, str] = {}
    cells: dict[tuple, int | None] = {}
    for r in rows:
        labels[r['region_code']] = r['region_label']
        cells[(r['year'], r['region_code'], r['migration_status'])] = value(r['value_thousand'])

    atlas = json.loads((ROOT / 'docs/data/atlas.json').read_text(encoding='utf-8'))
    names = {d['id']: d['name'] for d in atlas['districts']}
    population = {d['id']: d['population'] for d in atlas['districts']}

    districts, unusable = [], []
    for code in sorted(labels):
        ids = COMBINED.get(code, [code[:5]])
        series = {}
        for y in years:
            mh = cells.get((y, code, 'mit Migrationshintergrund'))
            total = cells.get((y, code, 'Insgesamt'))
            # The combined region's published total is inconsistent with its own
            # subgroup, as documented in prepare_district_migration.py; fall back to
            # the atlas population for the denominator there.
            if total is None or (mh is not None and total < mh):
                total = sum(population[i] for i in ids) / 1000
            series[y] = {
                'migration_background_thousand': mh,
                'share_percent': round(100 * mh / total, 2) if mh is not None and total else None,
            }
        first = series[years[0]]['share_percent']
        last = series[years[-1]]['share_percent']
        if first is None or last is None:
            unusable.append(labels[code])
        row = {
            'mikrozensus_region_code': code,
            'mikrozensus_region_label': labels[code],
            'shared_region': len(ids) > 1,
            'series': series,
            'change_points': round(last - first, 2) if first is not None and last is not None else None,
        }
        for i in ids:
            districts.append({'id': i, 'name': names[i], **row})

    if len(districts) != 44:
        raise ValueError(f'Expected 44 districts, produced {len(districts)}')
    for d in districts:
        for y, v in d['series'].items():
            s = v['share_percent']
            if s is not None and not 5 < s < 80:
                raise ValueError(f'Implausible share for {d["name"]} in {y}: {s}')

    changes = [d['change_points'] for d in districts if d['change_points'] is not None]
    data = {
        'type': 'district_migration_background_timeseries',
        'schema_version': '1.0',
        'years': years,
        'source': SOURCE,
        'source_url': SOURCE_URL,
        'population_base': 'Bevölkerung in Hauptwohnsitzhaushalten',
        'series_note': ('Nur eine Reihe ist über alle Jahre vergleichbar: Bevölkerung mit '
                        'Migrationshintergrund und ihr Anteil.'),
        'no_modelled_backcast': (
            'Die Modellrechnung zur muslimischen Bevölkerung wird nicht in die Vergangenheit '
            'fortgeschrieben. Dafür fehlen die Herkunftsdaten und die veröffentlichte '
            'Landessumme für die früheren Jahre; letztere existiert nur für 2025.'),
        'sampling_note': ('Stichprobenerhebung. Veränderungen einzelner Jahre liegen oft '
                          'innerhalb des Zufallsfehlers; ausgewiesen wird die Veränderung '
                          'über den gesamten Zeitraum in Prozentpunkten.'),
        'districts_without_usable_endpoints': unusable,
        'change_points_range': [min(changes), max(changes)] if changes else None,
        'districts': districts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    view = {
        'meta': {k: data[k] for k in ('years', 'source', 'source_url', 'series_note',
                                      'no_modelled_backcast', 'sampling_note')},
        'districts': {d['id']: {
            'shares': {y: d['series'][y]['share_percent'] for y in years},
            'change': d['change_points'],
        } for d in districts},
    }
    args.output.with_name('timeseries-data.js').write_text(
        'window.ATLAS_TIMESERIES=' + json.dumps(view, ensure_ascii=False,
                                                separators=(',', ':')) + ';\n', encoding='utf-8')

    print(f'{len(districts)} districts, {years[0]}–{years[-1]}.')
    print(f'Change in the migration-background share: {min(changes):+.1f} to {max(changes):+.1f} points.')
    ranked = sorted((d for d in districts if d['change_points'] is not None),
                    key=lambda d: -d['change_points'])
    for d in ranked[:5]:
        first = d['series'][years[0]]['share_percent']
        last = d['series'][years[-1]]['share_percent']
        print(f'  {d["name"]:<30}{first:>6.1f} % -> {last:>6.1f} %  ({d["change_points"]:+.1f})')


if __name__ == '__main__':
    main()

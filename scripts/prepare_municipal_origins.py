#!/usr/bin/env python3
"""Aggregate the Zensus 2022 100 m citizenship grid onto BW municipalities.

Source: Statistisches Bundesamt, Zensus 2022, "Staatsangehörigkeit nach ausgewählten
Ländern" in 100-Meter-Gitterzellen, reference date 15.05.2022, EPSG:3035.

Why the grid: no published table gives citizenship by country for all 1101 BW
municipalities. The grid does, and it can be assigned to municipalities with the same
official BKG boundaries the map already uses. Each cell is assigned by its published
midpoint, so a cell belongs to exactly one municipality and nothing is split.

Only two of the grid's twelve countries are Muslim-majority origins of any size:
Türkei and Bosnien-Herzegowina. Syria, Afghanistan, Iraq and Kosovo are NOT in this
grid, so this file cannot carry the whole model. It is used only to give
within-district variation to the largest origin group; see build_municipal_estimate.py.

Statistical confidentiality: the Zensus applies a cell-key method, so individual cell
values carry deliberate noise. Aggregating hundreds of cells per municipality averages
much of it out, but small municipalities stay noisier than large ones.
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ('Statistisches Bundesamt, Zensus 2022, Staatsangehörigkeit nach ausgewählten '
          'Ländern in 100-Meter-Gitterzellen')
SOURCE_URL = ('https://www.destatis.de/static/DE/zensus/gitterdaten/'
              'Staatsangehoerigkeit_nach_ausgewaehlten_Laendern.zip')
# Grid column -> output name. Only the columns the model can actually use.
COLUMNS = {'Insgesamt_Bevoelkerung': 'population', 'Tuerkei': 'turkey',
           'Bosn_u_Herzegowina': 'bosnia_herzegovina'}


def value(token: str) -> int:
    token = (token or '').strip()
    return 0 if token in {'', '–', '-', '.', 'x'} else int(token)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--grid', type=Path, required=True,
                    help='Zensus2022_Staatsangehoerigkeit_nach_Laendern_100m-Gitter.csv')
    ap.add_argument('--geometry', type=Path, default=ROOT / 'docs/data/geometry.json')
    ap.add_argument('--output', type=Path, default=ROOT / 'docs/data/municipal-origins-2022.json')
    args = ap.parse_args()

    try:
        from pyproj import Transformer
        from shapely.geometry import shape, Point
        from shapely.strtree import STRtree
        from shapely.ops import transform as shp_transform
    except ImportError as e:
        raise SystemExit('Install: python -m pip install -r requirements-geography.txt') from e

    geo = json.loads(args.geometry.read_text(encoding='utf-8'))
    to_3035 = Transformer.from_crs(4326, 3035, always_xy=True).transform

    polygons, meta = [], []
    for f in geo['municipalities']:
        gid = f['properties'].get('statistical_geo_id')
        if not gid:
            continue  # areas without population statistics, e.g. unincorporated areas
        polygons.append(shp_transform(to_3035, shape(f['geometry'])))
        meta.append({'geo_id': gid, 'ags': f['properties']['id'],
                     'name': f['properties']['name'],
                     'district_code': f['properties']['district_code']})
    if not polygons:
        raise SystemExit('No municipalities with statistical ids; build geometry first.')
    tree = STRtree(polygons)
    minx = min(p.bounds[0] for p in polygons); maxx = max(p.bounds[2] for p in polygons)
    miny = min(p.bounds[1] for p in polygons); maxy = max(p.bounds[3] for p in polygons)

    totals = {m['geo_id']: dict.fromkeys(COLUMNS.values(), 0) for m in meta}
    read = inside = outside = 0
    with args.grid.open(encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh, delimiter=';')
        for row in reader:
            read += 1
            x = float(row['x_mp_100m']); y = float(row['y_mp_100m'])
            if not (minx <= x <= maxx and miny <= y <= maxy):
                continue
            point = Point(x, y)
            hit = None
            for idx in tree.query(point):
                if polygons[idx].contains(point):
                    hit = idx
                    break
            if hit is None:
                outside += 1
                continue
            inside += 1
            bucket = totals[meta[hit]['geo_id']]
            for column, name in COLUMNS.items():
                bucket[name] += value(row.get(column, ''))
            if inside % 50000 == 0:
                print(f'  {inside:,} cells assigned...'.replace(',', '.'), file=sys.stderr, flush=True)

    municipalities = [{**m, **totals[m['geo_id']]} for m in meta]
    covered = sum(m['population'] for m in municipalities)
    turkey = sum(m['turkey'] for m in municipalities)
    if covered < 9_000_000:
        raise ValueError(f'Only {covered} people assigned; expected the BW population of ~11 million')
    if not 150_000 < turkey < 400_000:
        raise ValueError(f'Implausible Turkish citizenship total: {turkey}')

    data = {
        'type': 'municipal_citizenship_from_zensus_grid',
        'schema_version': '1.0',
        'reference_period': '2022-05-15',
        'source': SOURCE,
        'source_url': SOURCE_URL,
        'attribution': '© Statistische Ämter des Bundes und der Länder',
        'geometry_reference': geo.get('geometry_reference'),
        'assignment': 'Gitterzelle nach veröffentlichtem Mittelpunkt genau einer Gemeinde zugeordnet.',
        'confidentiality': ('Zensus-Geheimhaltung nach dem Cell-Key-Verfahren: Einzelzellen sind '
                            'bewusst überlagert. Die Summe je Gemeinde mittelt das teilweise aus, '
                            'kleine Gemeinden bleiben unsicherer.'),
        'countries_available': sorted(COLUMNS.values()),
        'countries_not_in_this_grid': ['Syrien', 'Afghanistan', 'Irak', 'Kosovo', 'Nordmazedonien'],
        'not_a_religion_dataset': 'Staatsangehörigkeit, keine Religionszugehörigkeit.',
        'cells_read': read, 'cells_assigned': inside, 'cells_in_bbox_outside_municipalities': outside,
        'population_assigned': covered,
        'municipalities': sorted(municipalities, key=lambda m: m['ags']),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'{len(municipalities)} municipalities; {inside:,} cells assigned, {outside:,} in bbox '
          f'but outside BW.'.replace(',', '.'))
    print(f'Population assigned {covered:,}; Türkei {turkey:,}; '
          f'Bosnien {sum(m["bosnia_herzegovina"] for m in municipalities):,}'.replace(',', '.'))


if __name__ == '__main__':
    main()

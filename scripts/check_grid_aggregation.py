#!/usr/bin/env python3
"""Verify the grid-to-municipality aggregation against an officially published table.

The municipal layer of the model depends on one piece of machinery: assigning Zensus
100-metre grid cells to municipalities by their published midpoint, using the BKG
boundaries. If that assignment is wrong, the Türkei/Bosnien settlement pattern is wrong,
and with it every municipal value.

That machinery can be tested exactly, because the Zensus publishes the SAME quantity
twice: once as a 100-metre grid (Religion in Gitterzellen) and once as a municipal
table (Bevölkerung nach Religionszugehörigkeit, Anteil je Gemeinde). Aggregating the
grid must reproduce the published municipal table.

Source: Statistische Ämter des Bundes und der Länder, Zensus 2022, "Religion in
Gitterzellen", erschienen 07.04.2025, and the municipal special evaluation already used
for the upper-bound check.

Two known reasons for small differences, both from the source:

  * At 277 addresses in 163 municipalities nationwide the data could not be fully
    processed. Those residents are counted in the municipal population but NOT at grid
    level, so the grid total is slightly lower.
  * Cell-key confidentiality is applied independently to each publication.

The test therefore checks agreement within a tolerance rather than exact equality, and
reports the worst cases so a systematic problem would be visible rather than averaged
away.
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ('Statistische Ämter des Bundes und der Länder, Zensus 2022, '
          'Religion in Gitterzellen')
# Share of the published municipal population the aggregated grid must reach.
MIN_COVERAGE = 0.90
# Allowed deviation of the residual SHARE in percentage points, per municipality.
SHARE_TOLERANCE_POINTS = 3.0


def value(token: str) -> int:
    token = (token or '').strip()
    return 0 if token in {'', '–', '-', '.', 'x'} else int(token)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--grid', type=Path, required=True,
                    help='Zensus2022_Religion_100m-Gitter.csv')
    ap.add_argument('--published', type=Path,
                    default=ROOT / 'inputs/zensus2022-religion-gemeinden-bw.csv')
    ap.add_argument('--geometry', type=Path, default=ROOT / 'docs/data/geometry.json')
    ap.add_argument('--output', type=Path,
                    default=ROOT / 'docs/data/grid-aggregation-check.json')
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
            continue
        polygons.append(shp_transform(to_3035, shape(f['geometry'])))
        meta.append({'geo_id': gid, 'ags': f['properties']['id'], 'name': f['properties']['name']})
    tree = STRtree(polygons)
    minx = min(p.bounds[0] for p in polygons); maxx = max(p.bounds[2] for p in polygons)
    miny = min(p.bounds[1] for p in polygons); maxy = max(p.bounds[3] for p in polygons)

    totals = {m['ags']: {'population': 0, 'catholic': 0, 'evangelical': 0, 'other': 0}
              for m in meta}
    assigned = 0
    with args.grid.open(encoding='utf-8-sig', newline='') as fh:
        for row in csv.DictReader(fh, delimiter=';'):
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
                continue
            assigned += 1
            b = totals[meta[hit]['ags']]
            b['population'] += value(row['Insgesamt_Bevoelkerung'])
            b['catholic'] += value(row['Roemisch_katholisch'])
            b['evangelical'] += value(row['Evangelisch'])
            b['other'] += value(row['Sonstige_keine_ohneAngabe'])
            if assigned % 50000 == 0:
                print(f'  {assigned:,} cells...'.replace(',', '.'), file=sys.stderr, flush=True)

    published = {r['ags']: r for r in csv.DictReader(args.published.open(encoding='utf-8'))}
    rows, coverage_fail, share_fail = [], [], []
    for m in meta:
        pub = published.get(m['ags'])
        if not pub:
            continue
        agg = totals[m['ags']]
        pub_pop = int(pub['population'])
        pub_other = int(pub['other_none_unstated'])
        coverage = agg['population'] / pub_pop if pub_pop else None
        agg_share = 100 * agg['other'] / agg['population'] if agg['population'] else None
        pub_share = 100 * pub_other / pub_pop if pub_pop else None
        delta = (agg_share - pub_share) if agg_share is not None and pub_share is not None else None
        row = {'ags': m['ags'], 'name': m['name'],
               'published_population': pub_pop, 'aggregated_population': agg['population'],
               'coverage': round(coverage, 4) if coverage is not None else None,
               'published_residual_share': round(pub_share, 2) if pub_share is not None else None,
               'aggregated_residual_share': round(agg_share, 2) if agg_share is not None else None,
               'share_difference_points': round(delta, 2) if delta is not None else None}
        rows.append(row)
        if coverage is not None and coverage < MIN_COVERAGE:
            coverage_fail.append(row)
        if delta is not None and abs(delta) > SHARE_TOLERANCE_POINTS:
            share_fail.append(row)

    if len(rows) != 1101:
        raise ValueError(f'Expected 1101 municipalities, compared {len(rows)}')
    # A handful of small municipalities may drift; a systematic failure must not pass.
    if len(share_fail) > 20:
        raise ValueError(f'Residual share disagrees in {len(share_fail)} municipalities; '
                         'the grid-to-municipality assignment is suspect')
    if len(coverage_fail) > 40:
        raise ValueError(f'Grid covers less than {MIN_COVERAGE:.0%} of the published '
                         f'population in {len(coverage_fail)} municipalities')

    deltas = sorted(abs(r['share_difference_points']) for r in rows
                    if r['share_difference_points'] is not None)
    coverages = sorted(r['coverage'] for r in rows if r['coverage'] is not None)
    median = lambda xs: xs[len(xs) // 2]

    data = {
        'type': 'grid_to_municipality_aggregation_check',
        'schema_version': '1.0',
        'purpose': ('Prüft die Zuordnung von Gitterzellen zu Gemeinden gegen eine amtlich '
                    'veröffentlichte Gemeindetabelle derselben Größe.'),
        'source': SOURCE,
        'why_it_matters': ('Dieselbe Zuordnung erzeugt das türkisch-bosnische '
                           'Siedlungsmuster, auf dem die Gemeindewerte des Modells beruhen.'),
        'known_differences': [
            'An 277 Anschriften in bundesweit 163 Gemeinden konnten die Daten nicht '
            'vollständig verarbeitet werden; diese Personen zählen nur bei der '
            'Gemeindebevölkerung, nicht auf Gitterebene.',
            'Die Geheimhaltung nach dem Cell-Key-Verfahren wird je Veröffentlichung '
            'eigenständig angewendet.',
        ],
        'cells_assigned': assigned,
        'municipalities_compared': len(rows),
        'median_coverage': round(median(coverages), 4),
        'median_absolute_share_difference_points': round(median(deltas), 2),
        'municipalities_outside_share_tolerance': len(share_fail),
        'municipalities_below_coverage_floor': len(coverage_fail),
        'share_tolerance_points': SHARE_TOLERANCE_POINTS,
        'worst_share_differences': sorted(
            (r for r in rows if r['share_difference_points'] is not None),
            key=lambda r: -abs(r['share_difference_points']))[:10],
        'municipalities': rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')),
                           encoding='utf-8')

    print(f'{assigned:,} cells assigned to {len(rows)} municipalities.'.replace(',', '.'))
    print(f'Median coverage of the published population: {median(coverages):.1%}')
    print(f'Median absolute difference in the residual share: '
          f'{median(deltas):.2f} points')
    print(f'Outside the {SHARE_TOLERANCE_POINTS} point tolerance: {len(share_fail)}')
    for r in data['worst_share_differences'][:5]:
        print(f'  {r["name"]:<24}{r["published_residual_share"]:>6.1f} % published vs '
              f'{r["aggregated_residual_share"]:>6.1f} % aggregated '
              f'({r["share_difference_points"]:+.1f})')


if __name__ == '__main__':
    main()

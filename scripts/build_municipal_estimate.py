#!/usr/bin/env python3
"""Modelled Muslim population per BW municipality, as a downscale of the district model.

This inherits every limitation of the district model and adds one of its own: no
source gives origin composition for all 1101 municipalities. Only Türkei and
Bosnien-Herzegowina are available per municipality (Zensus 2022 grid); Syrien,
Afghanistan, Irak, Kosovo and Nordmazedonien are not.

So the municipal layer estimates nothing new. It distributes each district's
already-calibrated figure among its municipalities, splitting that figure in two:

  * the share of the district figure contributed by Türkei and Bosnien follows the
    Turkish and Bosnian settlement pattern measured by the Zensus;
  * everything else follows population, because for those origins no municipal
    figures exist at all.

Letting the Turkish pattern carry the whole district figure would over-concentrate the
estimate in towns of historic Turkish settlement and understate places whose Muslim
population is mainly Syrian, Afghan or Iraqi. That split is the central estimate.

The published band additionally spans a purely flat distribution, in which every
municipality of a district receives the district rate. That is the "no within-district
information" case. A wide band therefore means the answer depends strongly on a
settlement pattern we can only observe for one origin group.

Zensus shares are taken as shares of the Zensus population of the same municipality, so
the level difference between the 2022 census and the 2024 population figures cancels
out and only the spatial pattern is carried over.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The two grid origins, with their BAMF origin-group counterparts.
GRID_ORIGINS = {'turkey': 'Türkei', 'bosnia_herzegovina': 'Bosnien-Herzegowina'}
# Zensus 2022 confidentiality noise plus the gap to the 2024 population figures.
CENSUS_TOLERANCE_POINTS = 1.0


def immigration_history() -> dict:
    """People with an immigration history per municipality, Zensus 2022.

    Used as the key for the part of a district's figure that has no municipal origin
    data of its own — Syrians, Afghans, Iraqis and the rest. They live where immigrants
    live, not spread evenly across a district by headcount, so this is a much better
    key than population.

    Note the classification: the Zensus reports "Einwanderungsgeschichte", not the
    "Migrationshintergrund" used for the district figures. Here it serves only as a
    relative spatial key WITHIN a district, so the difference in definition does not
    propagate into the values; it would if the two were ever added together.
    """
    path = ROOT / 'inputs/zensus2022-einwanderungsgeschichte-gemeinden-bw.csv'
    if not path.is_file():
        return {}
    out = {}
    for r in csv.DictReader(path.open(encoding='utf-8')):
        v = r['immigration_history_total'].strip()
        if v.isdigit():
            out[r['ags']] = int(v)
    return out


def census_ceilings() -> dict:
    """Largest Muslim share each municipality can have, from the census residual.

    The Zensus publishes only Catholic, Protestant and "Sonstige, keine, ohne Angabe"
    per municipality. Muslims necessarily fall in that residual, so it is a ceiling.
    It is not an estimate: the residual is mostly people of no religion.
    """
    path = ROOT / 'inputs/zensus2022-religion-gemeinden-bw.csv'
    if not path.is_file():
        return {}
    out = {}
    for r in csv.DictReader(path.open(encoding='utf-8')):
        pop = int(r['population'])
        if pop:
            out[r['ags']] = 100 * int(r['other_none_unstated']) / pop
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=ROOT / 'docs/data/municipal-estimate.json')
    args = ap.parse_args()

    atlas = json.loads((ROOT / 'docs/data/atlas.json').read_text(encoding='utf-8'))
    district = json.loads((ROOT / 'docs/data/district-estimate.json').read_text(encoding='utf-8'))
    grid = json.loads((ROOT / 'docs/data/municipal-origins-2022.json').read_text(encoding='utf-8'))
    shares = {g['origin_group']: g['share_percent']
              for g in json.loads((ROOT / 'inputs/muslim-shares-fb55-table2.json')
                                  .read_text(encoding='utf-8'))['origin_groups']}
    ratios = {g: v['ratio'] for g, v in district['naturalisation_ratios'].items()}

    ceilings = census_ceilings()
    history = immigration_history()
    crosswalk = {}
    cw_path = ROOT / 'docs/data/municipality-ags-crosswalk.json'
    if cw_path.is_file():
        crosswalk = {c['geo_id']: c['ags'] for c in json.loads(cw_path.read_text(encoding='utf-8'))}
    by_id = {m['geo_id']: m for m in atlas['municipalities']}
    grid_by_id = {m['geo_id']: m for m in grid['municipalities']}
    districts = {d['id']: d for d in district['districts']}

    # Origin weight per municipality: Zensus shares applied to the current population,
    # corrected for naturalisation and weighted by the Muslim share of each origin.
    weights, no_grid = {}, []
    for geo_id, m in by_id.items():
        pop = m['population_total'] or 0
        g = grid_by_id.get(geo_id)
        if not g or not g['population']:
            no_grid.append(geo_id)
            weights[geo_id] = None
            continue
        w = 0.0
        for column, group in GRID_ORIGINS.items():
            rate = g[column] / g['population']
            w += rate * pop * ratios.get(group, 1.0) * shares[group] / 100
        weights[geo_id] = w

    # Spatial key for the origins with no municipal figures of their own.
    residual_key = {}
    for geo_id in by_id:
        ags = crosswalk.get(geo_id)
        residual_key[geo_id] = history.get(ags) if ags else None

    grouped: dict[str, list[str]] = {}
    for geo_id, m in by_id.items():
        grouped.setdefault(m['district_code'], []).append(geo_id)

    municipalities = []
    for code, ids in sorted(grouped.items()):
        d = districts.get(code)
        if d is None:
            raise ValueError(f'District {code} missing from the district estimate')
        pop_sum = sum(by_id[i]['population_total'] or 0 for i in ids)
        # A municipality without grid data falls back to its population share; it must
        # not silently receive a zero origin weight.
        usable = [i for i in ids if weights[i] is not None]
        weight_sum = sum(weights[i] for i in usable)
        residual_usable = [i for i in ids if residual_key[i] is not None]
        residual_sum = sum(residual_key[i] for i in residual_usable)
        residual_complete = len(residual_usable) == len(ids) and residual_sum > 0
        for geo_id in ids:
            m = by_id[geo_id]
            pop = m['population_total'] or 0
            pop_share = pop / pop_sum if pop_sum else 0
            if weights[geo_id] is None or not weight_sum:
                origin_share = pop_share
                key_status = 'population_only_no_grid_data'
            else:
                origin_share = weights[geo_id] / weight_sum
                key_status = 'origin_and_population'

            # Only the part of the district figure that comes from Türkei and
            # Bosnien may follow the Türkei/Bosnien settlement pattern. Using that
            # pattern for the whole figure would over-concentrate the estimate in
            # towns with historic Turkish settlement and understate places whose
            # Muslim population is mainly Syrian, Afghan or Iraqi.
            grid_part = sum(d['by_origin_with_naturalisation'].get(g, 0) for g in GRID_ORIGINS.values())
            explained = d['explained_with_naturalisation'] or 1
            grid_fraction = min(1.0, grid_part / explained)

            # The remainder follows where people with an immigration history live,
            # falling back to population only where the census gives nothing.
            if residual_complete and residual_key[geo_id] is not None:
                rest_share = residual_key[geo_id] / residual_sum
                rest_basis = 'immigration_history'
            else:
                rest_share = pop_share
                rest_basis = 'population'

            bounds = []
            for variant in d['variants'].values():
                for total in (variant['persons_low'], variant['persons_high']):
                    flat = total * pop_share
                    mixed = total * (grid_fraction * origin_share + (1 - grid_fraction) * rest_share)
                    bounds.extend((flat, mixed))
            low, high = min(bounds), max(bounds)
            mid_variant = d['variants']['migration_background']
            mid_total = (mid_variant['persons_low'] + mid_variant['persons_high']) / 2
            central = mid_total * (grid_fraction * origin_share + (1 - grid_fraction) * rest_share)

            # The census ceiling is a fact about the area: Muslims necessarily fall in
            # the "Sonstige, keine, ohne Angabe" category, so a value above it is
            # impossible rather than merely unlikely. Clip and record that we did.
            ceiling_pct = ceilings.get(crosswalk.get(geo_id))
            clipped = False
            if ceiling_pct is not None and pop:
                ceiling_persons = (ceiling_pct + CENSUS_TOLERANCE_POINTS) / 100 * pop
                if high > ceiling_persons:
                    high = max(low, ceiling_persons)
                    clipped = True
                if central > high:
                    central = high
                    clipped = True

            municipalities.append({
                'geo_id': geo_id,
                'ags': grid_by_id.get(geo_id, {}).get('ags'),
                'name': m['municipality_name'],
                'district_code': code,
                'district_name': m['district_name'],
                'population': pop,
                'key_status': key_status,
                'grid_fraction_of_district': round(grid_fraction, 3),
                'remainder_key': rest_basis,
                'census_ceiling_percent': round(ceiling_pct, 2) if ceiling_pct is not None else None,
                'clipped_to_census_ceiling': clipped,
                'persons_central': round(central),
                'percent_central': round(100 * central / pop, 2) if pop else None,
                'persons_low': round(low), 'persons_high': round(high),
                'percent_low': round(100 * low / pop, 2) if pop else None,
                'percent_high': round(100 * high / pop, 2) if pop else None,
            })

    if len(municipalities) != 1101:
        raise ValueError(f'Expected 1101 municipalities, produced {len(municipalities)}')
    for m in municipalities:
        if m['percent_low'] is not None and not 0 <= m['percent_low'] <= m['percent_high'] < 70:
            raise ValueError(f'Implausible municipal estimate: {m}')
        if m['percent_central'] is not None and not m['percent_low'] <= m['percent_central'] <= m['percent_high']:
            raise ValueError(f'Central value outside its own band: {m}')

    data = {
        'type': 'modelled_municipal_muslim_population',
        'schema_version': '1.0',
        'is_model_not_measurement': True,
        'is_downscale_of_district_model': True,
        'headline': ('Modellrechnung, keine amtliche Messung. Die Gemeindewerte verteilen den '
                     'jeweiligen Kreiswert; sie sind keine eigene Erhebung.'),
        'keys': {
            'population': 'Kreiswert nach Einwohnerzahl verteilt; keine Unterschiede innerhalb des Kreises.',
            'origin': ('Nur der türkische und bosnische Anteil des Kreiswerts folgt dem im '
                       'Zensus gemessenen Siedlungsmuster; der Rest folgt der Einwohnerzahl, '
                       'weil für die übrigen Herkünfte keine Gemeindedaten existieren.'),
        },
        'band_meaning': ('Die Spanne umfasst die veröffentlichte Landesspanne, beide '
                         'Kreisvarianten und beide Verteilungsschlüssel.'),
        'grid_source': {'source': grid['source'], 'reference_period': grid['reference_period'],
                        'countries_available': grid['countries_available'],
                        'countries_not_in_this_grid': grid['countries_not_in_this_grid'],
                        'confidentiality': grid['confidentiality']},
        'municipalities_without_grid_data': no_grid,
        'limitations': district['limitations'] + [
            'Nur Türkei und Bosnien-Herzegowina liegen je Gemeinde vor, nicht die übrigen Herkünfte.',
            'Die Gemeindewerte sind eine Verteilung des Kreiswerts, keine eigene Schätzung.',
            'Die Zensus-Geheimhaltung macht kleine Gemeinden unsicherer als große.',
            'Bezugszeit des Herkunftsmusters ist 2022, die der Einwohnerzahlen 30.06.2024.',
        ],
        'municipalities': sorted(municipalities, key=lambda m: m['geo_id']),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

    # Compact view for the browser: only what the map and the selection profile read.
    def slim_district(d):
        return {'central': round((d['variants']['migration_background']['persons_low']
                                  + d['variants']['migration_background']['persons_high']) / 2),
                'low': d['combined_low_persons'], 'high': d['combined_high_persons'],
                'pct_low': d['combined_low_percent'], 'pct_high': d['combined_high_percent'],
                'variants': {k: {'pct_low': v['percent_low'], 'pct_high': v['percent_high'],
                                 'low': v['persons_low'], 'high': v['persons_high']}
                             for k, v in d['variants'].items()},
                'by_origin': d['by_origin_with_naturalisation']}

    view = {
        'meta': {
            'is_model_not_measurement': True,
            'state_total': district['state_total'],
            'coverage': district['coverage'],
            'naturalisation_ratios': district['naturalisation_ratios'],
            'variants': district['variants'],
            'keys': data['keys'],
            'band_meaning': data['band_meaning'],
            'limitations': data['limitations'],
            'origin_reference_period': district['origin_source']['reference_period'],
            'grid_reference_period': grid['reference_period'],
            'countries_not_in_grid': grid['countries_not_in_this_grid'],
        },
        'districts': {d['id']: slim_district(d) for d in district['districts']},
        'municipalities': {m['geo_id']: {
            'central': m['persons_central'], 'pct': m['percent_central'],
            'low': m['persons_low'], 'high': m['persons_high'],
            'pct_low': m['percent_low'], 'pct_high': m['percent_high'],
        } for m in municipalities},
    }
    js = args.output.with_name('estimate-data.js')
    js.write_text('window.ATLAS_ESTIMATE=' + json.dumps(view, ensure_ascii=False,
                                                        separators=(',', ':')) + ';\n', encoding='utf-8')

    ranked = sorted((m for m in municipalities if m['population'] >= 20000),
                    key=lambda m: -(m['percent_central'] or 0))
    print(f'{len(municipalities)} municipalities; {len(no_grid)} without grid data.')
    print(f"\n{'Gemeinde (ab 20.000 Ew.)':<30}{'zentral':>9}{'Spanne':>16}{'Einwohner':>12}")
    for m in ranked[:10]:
        print(f"  {m['name']:<28}{m['percent_central']:>8.1f}{m['percent_low']:>9.1f}-{m['percent_high']:<6.1f}"
              f"{m['population']:>12,}".replace(',', '.'))


if __name__ == '__main__':
    main()

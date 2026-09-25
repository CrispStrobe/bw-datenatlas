#!/usr/bin/env python3
"""Age structure and the census revision per BW municipality, from the Zensus 2022.

Sources, both freely downloadable from the destatis delivery path and both under the
Datenlizenz Deutschland – Namensnennung – Version 2.0:

  * Zensus 2022, Regionaltabelle Demografie — population by sex, citizenship, eleven age
    groups, marital status and immigration history, down to municipality level.
  * Zensus 2022, Regionaltabelle Bevölkerung — the census count against the population
    projection that was still based on Zensus 2011.

Two things are built here.

1. AGE STRUCTURE PER MUNICIPALITY. The district age figures elsewhere in this atlas
   come from the Mikrozensus, which is a sample and suppresses so many cells that eight
   districts get no reportable share at all. These census figures are a full count and
   are complete for all 1101 municipalities bar two suppressed cells, which stay
   missing rather than becoming zero.

2. THE CENSUS REVISION. The 2022 census corrected the population that had been carried
   forward from the 2011 census. Per municipality that correction is often several
   percent. It is published here because the atlas mixes figures resting on different
   population bases, and the size of that difference should be visible rather than
   implied.

Neither enters the modelled Muslim figures. Age is not an indicator of religion.
"""
from __future__ import annotations
import argparse
import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ('Statistische Ämter des Bundes und der Länder, Zensus 2022, '
          'Regionaltabellen Demografie und Bevölkerung')
SOURCE_URL = 'https://www.destatis.de/static/DE/zensus/gitterdaten/Regionaltabelle_Demografie.xlsx'
AGE_GROUPS = ['u3', 'a3_5', 'a6_9', 'a10_15', 'a16_18', 'a19_24',
              'a25_39', 'a40_59', 'a60_66', 'a67_74', 'a75plus']
AGE_LABELS = {'u3': 'unter 3', 'a3_5': '3–5', 'a6_9': '6–9', 'a10_15': '10–15',
              'a16_18': '16–18', 'a19_24': '19–24', 'a25_39': '25–39',
              'a40_59': '40–59', 'a60_66': '60–66', 'a67_74': '67–74',
              'a75plus': '75 und älter'}
UNDER_25 = ['u3', 'a3_5', 'a6_9', 'a10_15', 'a16_18', 'a19_24']


def number(token):
    token = (token or '').strip()
    if not token or token in {'–', '-', '.', '/', 'x'}:
        return None
    try:
        return int(float(token))
    except ValueError:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path,
                    default=ROOT / 'inputs/zensus2022-demografie-gemeinden-bw.csv')
    ap.add_argument('--output', type=Path,
                    default=ROOT / 'docs/data/municipal-demography-2022.json')
    args = ap.parse_args()

    crosswalk = {c['ags']: c['geo_id'] for c in json.loads(
        (ROOT / 'docs/data/municipality-ags-crosswalk.json').read_text(encoding='utf-8'))}

    municipalities, suppressed, unmatched = [], [], []
    for r in csv.DictReader(args.input.open(encoding='utf-8')):
        geo_id = crosswalk.get(r['ags'])
        if geo_id is None:
            unmatched.append(r['ags'])
            continue
        pop = number(r['population'])
        groups = {k: number(r[k]) for k in AGE_GROUPS}
        missing = [k for k, v in groups.items() if v is None]
        if missing:
            suppressed.append({'ags': r['ags'], 'name': r['name'], 'groups': missing})
        young = (sum(groups[k] for k in UNDER_25)
                 if all(groups[k] is not None for k in UNDER_25) else None)

        census = number(r['census_population'])
        projection = number(r['projection_population_2022'])
        revision = (round(100 * (census - projection) / projection, 2)
                    if census is not None and projection else None)

        municipalities.append({
            'ags': r['ags'], 'geo_id': geo_id, 'name': r['name'],
            'population': pop,
            'age_groups': groups,
            'age_complete': not missing,
            'under_25': young,
            'under_25_share_percent': round(100 * young / pop, 2) if young and pop else None,
            'census_population': census,
            'projection_population_2022': projection,
            'census_revision_percent': revision,
        })

    if unmatched:
        raise ValueError(f'Municipalities without a geo id: {unmatched[:5]}')
    if len(municipalities) != 1101:
        raise ValueError(f'Expected 1101 municipalities, produced {len(municipalities)}')
    for m in municipalities:
        s = m['under_25_share_percent']
        if s is not None and not 5 < s < 45:
            raise ValueError(f'Implausible under-25 share in {m["name"]}: {s}')

    shares = [m['under_25_share_percent'] for m in municipalities
              if m['under_25_share_percent'] is not None]
    revisions = [m['census_revision_percent'] for m in municipalities
                 if m['census_revision_percent'] is not None]

    data = {
        'type': 'municipal_demography_census_2022',
        'schema_version': '1.0',
        'reference_period': '2022-05-15',
        'source': SOURCE,
        'source_url': SOURCE_URL,
        'licence': 'Datenlizenz Deutschland – Namensnennung – Version 2.0',
        'attribution': '© Statistische Ämter des Bundes und der Länder, 2024',
        'why_census_and_not_survey': (
            'Die Altersgliederung je Kreis stammt sonst aus dem Mikrozensus, einer '
            'Stichprobe, die so viele Zellen geheim hält, dass acht Kreise gar keinen '
            'belastbaren Anteil erhalten. Diese Zensuswerte sind eine Vollerhebung und '
            'für alle 1.101 Gemeinden vorhanden.'),
        'census_revision_note': (
            'Der Zensus 2022 korrigierte die aus dem Zensus 2011 fortgeschriebene '
            'Bevölkerung. Die Größe dieser Korrektur je Gemeinde steht hier, weil der '
            'Atlas Zahlen mit unterschiedlichen Bevölkerungsgrundlagen zeigt.'),
        'not_a_religion_dataset': (
            'Alter ist kein Merkmal der Religionszugehörigkeit. Diese Angaben gehen '
            'nicht in die Modellrechnung ein.'),
        'age_group_labels': AGE_LABELS,
        'suppressed_cells': suppressed,
        'under_25_share_median_percent': round(statistics.median(shares), 2),
        'census_revision_median_percent': round(statistics.median(revisions), 2),
        'census_revision_range_percent': [min(revisions), max(revisions)],
        'municipalities': municipalities,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')),
                           encoding='utf-8')

    view = {
        'meta': {k: data[k] for k in ('reference_period', 'source', 'licence', 'attribution',
                                      'why_census_and_not_survey', 'census_revision_note',
                                      'not_a_religion_dataset')},
        'labels': AGE_LABELS,
        'age_groups': AGE_GROUPS,
        'municipalities': {m['geo_id']: {
            'u25': m['under_25_share_percent'],
            'groups': m['age_groups'],
            'revision': m['census_revision_percent'],
        } for m in municipalities},
    }
    args.output.with_name('demography-data.js').write_text(
        'window.ATLAS_DEMOGRAPHY=' + json.dumps(view, ensure_ascii=False,
                                                separators=(',', ':')) + ';\n', encoding='utf-8')

    print(f'{len(municipalities)} municipalities; {len(suppressed)} with a suppressed age cell.')
    print(f'Under 25: median {statistics.median(shares):.1f} %, '
          f'{min(shares):.1f}–{max(shares):.1f} %')
    print(f'Census revision against the old projection: median '
          f'{statistics.median(revisions):+.1f} %, range {min(revisions):+.1f} to {max(revisions):+.1f} %')


if __name__ == '__main__':
    main()

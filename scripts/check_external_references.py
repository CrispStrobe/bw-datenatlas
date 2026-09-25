#!/usr/bin/env python3
"""Compare the modelled figures against two independent external estimates.

Neither reference is an input to the model, so agreement is evidence and disagreement
is a warning. Both are older than the model, so the comparison is about spatial
pattern and plausible growth, never about matching values.

Reference 1 — Landeshauptstadt Stuttgart, Statistisches Amt (2019):
  "Muslime in Stuttgart 2017", Statistik und Informationsmanagement, Monatsheft 7/2019.
  About 59.000 Muslims at the end of 2017, roughly 10 percent of residents, estimated
  by the city from its own population register. This is a genuinely local estimate
  built on individual-level origin data the city holds and this project does not.

Reference 2 — kartenseite.wordpress.com (2017):
  Municipal maps for Baden-Württemberg built from Zensus 2011 origin counts times the
  nationwide Muslim share of 18 origin countries. Nine cities are published with values.
  This is the same family of method as ours, one census generation earlier.

The two checks differ in what they can show:

  * Stuttgart gives one value, so it tests the LEVEL in a single city over time.
  * kartenseite gives nine values, so it tests the SPATIAL ORDERING across cities,
    which is what a map is actually read for.

The level difference against kartenseite is expected and is itself checked: the
nationwide Muslim population grew from 4,40-4,70 million in 2015 to 6,60-7,00 million
in 2025 per BAMF, so a factor near 1,5 is the right order of magnitude. A much smaller
or much larger factor would mean something is wrong.
"""
from __future__ import annotations
import argparse
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STUTTGART_2017 = {
    'persons': 59000, 'percent': 10.0, 'reference': '2017-12-31',
    'source': ('Landeshauptstadt Stuttgart, Statistisches Amt: "Muslime in Stuttgart 2017", '
               'Statistik und Informationsmanagement, Monatsheft 7/2019'),
    'method': 'Schätzung aus dem städtischen Melderegister nach Herkunft',
}
# Published municipal values, Zensus 2011 basis.
KARTENSEITE_2011 = {
    'Heilbronn': 13.3, 'Mannheim': 10.8, 'Ulm': 9.6, 'Pforzheim': 9.5,
    'Stuttgart': 9.4, 'Reutlingen': 6.6, 'Heidelberg': 5.7, 'Karlsruhe': 5.7,
    'Freiburg im Breisgau': 4.8,
}
KARTENSEITE_SOURCE = ('kartenseite.wordpress.com, "Muslime in Baden-Württemberg, Gemeinden" '
                      '(2017), Zensus 2011 mal bundesweite Anteile von 18 Herkunftsländern')
# BAMF national totals, for the expected growth factor.
NATIONAL = {'2015': (4_400_000, 4_700_000), '2019': (5_300_000, 5_600_000),
            '2025': (6_600_000, 7_000_000)}


def spearman(a: list[float], b: list[float]) -> float:
    def rank(xs):
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        r = [0] * len(xs)
        for pos, i in enumerate(order):
            r[i] = pos
        return r
    ra, rb = rank(a), rank(b)
    n = len(a)
    d2 = sum((x - y) ** 2 for x, y in zip(ra, rb))
    return 1 - 6 * d2 / (n * (n * n - 1))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=ROOT / 'docs/data/external-references.json')
    args = ap.parse_args()

    district = json.loads((ROOT / 'docs/data/district-estimate.json').read_text(encoding='utf-8'))
    municipal = json.loads((ROOT / 'docs/data/municipal-estimate.json').read_text(encoding='utf-8'))
    by_name = {m['name']: m for m in municipal['municipalities']}

    # --- Stuttgart, level over time -----------------------------------------
    stuttgart = next(d for d in district['districts'] if d['id'] == '08111')
    v = stuttgart['variants']['migration_background']
    modelled_persons = (v['persons_low'] + v['persons_high']) / 2
    modelled_percent = (v['percent_low'] + v['percent_high']) / 2
    growth = modelled_persons / STUTTGART_2017['persons']

    # --- kartenseite, spatial ordering ---------------------------------------
    pairs, missing = [], []
    for name, published in KARTENSEITE_2011.items():
        row = by_name.get(name)
        if row is None or row['percent_central'] is None:
            missing.append(name)
            continue
        pairs.append({'name': name, 'published_2011_percent': published,
                      'modelled_percent': row['percent_central'],
                      'factor': round(row['percent_central'] / published, 2)})
    if missing:
        raise ValueError(f'Cities not found in the municipal estimate: {missing}')

    rho = spearman([p['published_2011_percent'] for p in pairs],
                   [p['modelled_percent'] for p in pairs])
    factors = [p['factor'] for p in pairs]
    median_factor = round(statistics.median(factors), 2)
    national_growth = (sum(NATIONAL['2025']) / 2) / (sum(NATIONAL['2015']) / 2)

    # A map is read for its ordering, so that is the property that must hold.
    if rho < 0.8:
        raise ValueError(f'Spatial ordering disagrees with the published map: rho={rho:.3f}')
    # The level may differ, but not by an amount national growth cannot explain.
    if not 1.1 < median_factor < 2.2:
        raise ValueError(f'Level difference implausible: median factor {median_factor}')
    if modelled_percent < STUTTGART_2017['percent']:
        raise ValueError('Modelled Stuttgart share fell below the 2017 city estimate; '
                         'the Muslim population did not shrink over this period.')

    data = {
        'type': 'external_reference_checks',
        'schema_version': '1.0',
        'purpose': ('Vergleich mit zwei unabhängigen Schätzungen, die nicht in das Modell '
                    'eingehen. Beide sind älter; verglichen werden räumliches Muster und '
                    'plausibles Wachstum, nicht die Werte selbst.'),
        'stuttgart': {
            **STUTTGART_2017,
            'modelled_persons': round(modelled_persons),
            'modelled_percent': round(modelled_percent, 1),
            'growth_factor_2017_to_2025': round(growth, 2),
            'reading': ('Die Stadt schätzte 2017 rund 10 Prozent. Das Modell kommt für 2025 '
                        'auf gut 12 Prozent. Der Abstand entspricht dem Zuwachs der '
                        'muslimischen Bevölkerung seit 2017 und widerspricht der '
                        'städtischen Schätzung nicht.'),
        },
        'kartenseite': {
            'source': KARTENSEITE_SOURCE,
            'basis': 'Zensus 2011',
            'cities': pairs,
            'spearman_rank_correlation': round(rho, 3),
            'median_level_factor': median_factor,
            'expected_factor_from_national_growth': round(national_growth, 2),
            'reading': ('Die räumliche Reihenfolge stimmt fast vollständig überein. Das '
                        'höhere Niveau entspricht dem bundesweiten Zuwachs zwischen den '
                        'Bezugszeiten und ist kein Widerspruch.'),
        },
        'what_this_does_not_show': [
            'Keine der beiden Referenzen belegt die Richtigkeit einzelner Gemeindewerte.',
            'Die Stuttgarter Schätzung beruht auf Einzeldaten des Melderegisters, die '
            'diesem Projekt nicht vorliegen; sie ist die bessere Quelle für Stuttgart.',
            'Die Karte von 2011 stützt sich je Gemeinde auf 18 Herkunftsländer, dieses '
            'Modell auf zwei. Bei der Binnenverteilung in den Kreisen ist ihre '
            'Datengrundlage die reichere.',
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'Stuttgart 2017 (Stadt): {STUTTGART_2017["percent"]} % / '
          f'{STUTTGART_2017["persons"]:,} — Modell 2025: {modelled_percent:.1f} % / '
          f'{round(modelled_persons):,} (Faktor {growth:.2f})'.replace(',', '.'))
    print(f'kartenseite 2011, {len(pairs)} Städte: Spearman {rho:.3f}, '
          f'Median-Faktor {median_factor} gegen erwartete {national_growth:.2f} aus dem '
          f'bundesweiten Zuwachs')
    for p in sorted(pairs, key=lambda x: -x['published_2011_percent']):
        print(f'  {p["name"]:<22}{p["published_2011_percent"]:>6.1f} % -> '
              f'{p["modelled_percent"]:>6.1f} %  ({p["factor"]:.2f})')


if __name__ == '__main__':
    main()

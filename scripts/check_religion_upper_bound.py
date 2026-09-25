#!/usr/bin/env python3
"""Test the modelled municipal estimates against a hard ceiling from the census.

Source: Statistische Ämter des Bundes und der Länder, Zensus 2022, Sonderauswertung
"Bevölkerung nach Religionszugehörigkeit, Anteil je Gemeinde", reference date
15.05.2022. Terms: storage, reproduction and distribution with attribution permitted.

The census publishes only three categories per municipality: Roman Catholic Church
(public-law), Protestant Church (public-law), and "Sonstige, keine, ohne Angabe".
Islam is NOT a category, so this cannot give a Muslim share. What it does give is an
upper bound: every Muslim resident necessarily falls in the residual category, so

    modelled Muslim share  <=  residual share

must hold in every municipality. A model value above the residual would be impossible
rather than merely uncertain, so this is a real falsification test, not a plausibility
comment. Violations fail the run.

Two caveats are handled explicitly. The census counts 15.05.2022 while the estimate
uses the 30.06.2024 population, so the comparison is between shares, not counts. And
the census applies cell-key confidentiality, so the residual carries noise of its own;
a margin is therefore allowed before a difference is treated as a violation.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ('Statistische Ämter des Bundes und der Länder, Zensus 2022, '
          'Bevölkerung nach Religionszugehörigkeit, Anteil je Gemeinde')
SOURCE_URL = ('https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/'
              'Zensus2022/Publikationen/Downloads-Publikationen/Sonderauswertungen/'
              'bevoelkerung_religionszugehoerigkeit_je_gemeinde.xlsx')
# Confidentiality noise plus the two-year gap between the census and the population
# figures; only a difference beyond this counts as an impossibility.
TOLERANCE_POINTS = 1.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path,
                    default=ROOT / 'inputs/zensus2022-religion-gemeinden-bw.csv')
    ap.add_argument('--output', type=Path,
                    default=ROOT / 'docs/data/municipal-religion-bound.json')
    args = ap.parse_args()

    census = {}
    for r in csv.DictReader(args.input.open(encoding='utf-8')):
        pop = int(r['population'])
        other = int(r['other_none_unstated'])
        census[r['ags']] = {
            'name': r['name'], 'population': pop,
            'catholic': int(r['catholic']), 'evangelical': int(r['evangelical']),
            'other_none_unstated': other,
            'residual_share_percent': round(100 * other / pop, 2) if pop else None,
        }

    estimate = json.loads((ROOT / 'docs/data/municipal-estimate.json').read_text(encoding='utf-8'))
    crosswalk = {c['geo_id']: c['ags'] for c in json.loads(
        (ROOT / 'docs/data/municipality-ags-crosswalk.json').read_text(encoding='utf-8'))}

    rows, violations, unmatched = [], [], []
    for m in estimate['municipalities']:
        ags = crosswalk.get(m['geo_id'])
        c = census.get(ags)
        if not c:
            unmatched.append({'geo_id': m['geo_id'], 'name': m['name'], 'ags': ags})
            continue
        ceiling = c['residual_share_percent']
        central, high = m['percent_central'], m['percent_high']
        headroom = round(ceiling - central, 2) if ceiling is not None and central is not None else None
        row = {
            'geo_id': m['geo_id'], 'ags': ags, 'name': m['name'],
            'district_code': m['district_code'],
            'modelled_percent_central': central,
            'modelled_percent_high': high,
            'census_residual_share_percent': ceiling,
            'headroom_points': headroom,
            'central_within_bound': ceiling is None or central is None or central <= ceiling + TOLERANCE_POINTS,
            'upper_within_bound': ceiling is None or high is None or high <= ceiling + TOLERANCE_POINTS,
        }
        if not row['central_within_bound']:
            violations.append(row)
        rows.append(row)

    if unmatched:
        raise ValueError(f'Municipalities without a census counterpart: {unmatched[:5]}')
    if len(rows) != 1101:
        raise ValueError(f'Expected 1101 comparisons, made {len(rows)}')
    if violations:
        raise ValueError(
            'Modelled central values exceed what the census allows in '
            f'{len(violations)} municipalities: '
            + ', '.join(f'{v["name"]} {v["modelled_percent_central"]}% > {v["census_residual_share_percent"]}%'
                        for v in violations[:5]))

    tight = sorted((r for r in rows if r['headroom_points'] is not None),
                   key=lambda r: r['headroom_points'])
    over_upper = [r for r in rows if not r['upper_within_bound']]

    data = {
        'type': 'municipal_religion_upper_bound_check',
        'schema_version': '1.0',
        'reference_period': '2022-05-15',
        'source': SOURCE,
        'source_url': SOURCE_URL,
        'attribution': '© Statistische Ämter des Bundes und der Länder, 2024',
        'terms': 'Speicherung, Vervielfältigung und Verbreitung mit Quellenangabe gestattet.',
        'what_the_census_publishes': (
            'Nur drei Kategorien je Gemeinde: römisch-katholisch, evangelisch sowie '
            '"Sonstige, keine, ohne Angabe". Der Islam ist keine eigene Kategorie.'),
        'why_this_is_an_upper_bound': (
            'Muslimische Einwohnerinnen und Einwohner fallen zwangsläufig in die '
            'Restkategorie. Der modellierte Anteil kann daher nicht über dem Anteil '
            'dieser Restkategorie liegen. Die Restkategorie ist KEINE Schätzung des '
            'Muslimanteils: sie enthält überwiegend Konfessionslose.'),
        'not_a_muslim_share': (
            'Die Restkategorie umfasst Konfessionslose, andere Religionen und fehlende '
            'Angaben. Sie darf nicht als Muslimanteil gelesen werden.'),
        'confidentiality': ('Zensus-Geheimhaltung nach dem Cell-Key-Verfahren; die '
                            'Restkategorie trägt eigenes Rauschen.'),
        'tolerance_points': TOLERANCE_POINTS,
        'date_mismatch_note': ('Zensus 15.05.2022, Einwohnerzahlen der Modellrechnung '
                               '30.06.2024. Verglichen werden Anteile, keine Personenzahlen.'),
        'municipalities_checked': len(rows),
        'central_violations': len(violations),
        'upper_bound_violations': len(over_upper),
        'tightest': tight[:15],
        'municipalities': rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

    view = {
        'meta': {k: data[k] for k in ('reference_period', 'source', 'source_url',
                                      'what_the_census_publishes', 'why_this_is_an_upper_bound',
                                      'not_a_muslim_share', 'confidentiality',
                                      'date_mismatch_note', 'tolerance_points')},
        'municipalities': {r['geo_id']: {'ceiling': r['census_residual_share_percent'],
                                         'headroom': r['headroom_points'],
                                         'ok': r['central_within_bound']} for r in rows},
    }
    args.output.with_name('bound-data.js').write_text(
        'window.ATLAS_BOUND=' + json.dumps(view, ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')

    print(f'{len(rows)} municipalities checked against the census ceiling.')
    print(f'Central values above the ceiling: {len(violations)}')
    print(f'Upper band edge above the ceiling: {len(over_upper)}')
    print('\nTightest headroom (modelled central vs census residual):')
    for r in tight[:8]:
        print(f'  {r["name"]:<26}{r["modelled_percent_central"]:>6.1f} % vs '
              f'{r["census_residual_share_percent"]:>6.1f} %  ->{r["headroom_points"]:>6.1f} pt')


if __name__ == '__main__':
    main()

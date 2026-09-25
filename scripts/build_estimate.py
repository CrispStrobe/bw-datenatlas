#!/usr/bin/env python3
"""Modelled Muslim population per BW district, in two explicit variants.

This is a MODEL, not a measurement. No official statistic records religion per
district in Baden-Württemberg, and BAMF states that analyses within a federal state
are not possible from the MLD data. What can be done honestly is to distribute the
*published* state figure across districts using an origin key, and to show how much
the result depends on the key that is chosen.

Method, following the established approach (origin population x nationwide Muslim
share of that origin, cf. Zensus-based municipal maps):

    E_k = sum over origin groups c of  A(k,c) * s(c)

with A(k,c) the foreign population of citizenship c in district k
(Ausländerzentralregister, 31.12.2024) and s(c) the nationwide Muslim share of
origin group c (BAMF FB55, Table 2; the five conflicting Table 1 cells are excluded).

On the age of s(c): FB55's own Table 2 is headed "MLD 2020 | Anteil der muslimischen
Religionsangehörigen ... in %". BAMF computes its published 2025 figures by applying
those 2019/2020 survey shares to 2025 migration-background counts. No newer shares
exist to use; this is a limitation of the official method, inherited here rather than
introduced here, and it is the largest single source of error in the result.

Note also that BAMF applies s(c) to people with MIGRATION BACKGROUND, not to foreign
citizens. The r(c) correction below is precisely the step that converts the citizenship
counts we have per district into the migration-background base BAMF uses.

E explains only part of the published state total T, because citizenship misses
naturalised residents and their German-born children, and because only some of the
18 BAMF origin groups appear in the district table. The residual R = T - sum(E) is
where the two variants differ:

  Variant "citizenship"          R is distributed like E itself.
                                 Equivalent to M_k = T * E_k / sum(E).
                                 Assumes naturalised residents live where
                                 non-naturalised residents of the same origins live.

  Variant "migration_background" R is distributed by population with migration
                                 background per district (Mikrozensus 12211-0503),
                                 which does include naturalised residents.

Neither variant is a measurement of local religious affiliation. The spread between
them is reported as part of the uncertainty, alongside the published range of T.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# District citizenship column -> BAMF FB55 Table 2 origin group.
# Only groups that exist in BOTH sources are usable; the rest of the published
# origin groups have no district-level counterpart and fall into the residual.
# Mikrozensus label for the same origin, where the state-level table publishes it.
# The ratio (migration background / citizenship) is the naturalisation-and-descendants
# factor for that origin: people born here or naturalised hold German passports and are
# therefore absent from the citizenship source entirely.
MIKROZENSUS_ORIGIN = {
    'Türkei': 'Türkei',
    'Syrien': 'Syrien',
    'Kosovo': 'Kosovo',
    'Serbien': 'Serbien',
    'Irak': 'Irak',
    'Afghanistan': 'Afghanistan',
}
# Bosnien-Herzegowina and Nordmazedonien are not published separately. Both are
# non-EU European origins of the same migration vintage as Kosovo and Serbien, so the
# published "Sonstiges Europa" aggregate ratio is used and recorded as a fallback.
FALLBACK_RATIO_GROUPS = ['Bosnien-Herzegowina', 'Nordmazedonien']

ORIGIN_COLUMNS = {
    'turkey': 'Türkei',
    'syria': 'Syrien',
    'kosovo': 'Kosovo',
    'bosnia_herzegovina': 'Bosnien-Herzegowina',
    'serbia': 'Serbien',
    'iraq': 'Irak',
    'afghanistan': 'Afghanistan',
    'north_macedonia': 'Nordmazedonien',
}


def load_shares() -> dict:
    """Muslim share per origin group from FB55 Table 2, excluding blocked parameters.

    Read from the committed parameter extract so the model is reproducible without the
    full data collection, which is not redistributed (it contains unmodified source
    PDFs). The extract is generated from data package v4: v3 still blocks the Syrien
    and Irak cells that the review later confirmed against FB38, and a model without
    those two origins would be badly wrong.
    """
    path = ROOT / 'inputs/muslim-shares-fb55-table2.json'
    if not path.is_file():
        raise SystemExit(f'Parameter extract not found: {path}')
    doc = json.loads(path.read_text(encoding='utf-8'))
    shares = {}
    for g in doc['origin_groups']:
        if 'no_automatic_parameter_use' in (g.get('quality_flags') or []):
            continue
        shares[g['origin_group']] = {
            'share_percent': g['share_percent'],
            'observation_id': g.get('observation_id'),
            'source_locator': g.get('source_locator'),
            'quality_flags': g.get('quality_flags') or [],
        }
    missing = set(ORIGIN_COLUMNS.values()) - set(shares)
    if missing:
        raise SystemExit(f'Usable Muslim shares missing for: {sorted(missing)}')
    return shares


def naturalisation_ratios(origins: dict, year: str) -> tuple[dict, dict]:
    """Migration background per origin divided by citizenship per origin, at state level.

    Returns (ratio per BAMF origin group, provenance). A ratio of 2.0 means the
    origin-based population is twice the size of the passport-based population.
    """
    path = ROOT / 'inputs/mikrozensus-12211-0502-geburtsland-bw.csv'
    if not path.is_file():
        raise SystemExit(f'State-level Mikrozensus origin table not found: {path}')
    mh = {}
    for r in csv.DictReader(path.open(encoding='utf-8')):
        if r['year'] != year:
            continue
        v = r['value_thousand'].strip()
        if v.isdigit():
            mh[r['origin']] = int(v) * 1000
    az = {c: sum(d[c] or 0 for d in origins['districts']) for c in origins['columns']}

    ratios, provenance = {}, {}
    for group, column in ((g, c) for c, g in ORIGIN_COLUMNS.items()):
        label = MIKROZENSUS_ORIGIN.get(group)
        if label and label in mh and az.get(column):
            ratios[group] = mh[label] / az[column]
            provenance[group] = {'basis': 'published_for_this_origin',
                                 'migration_background_persons': mh[label],
                                 'citizenship_persons': az[column]}
    non_eu = sum((d['europe'] or 0) - (d['eu_states'] or 0) for d in origins['districts'])
    if 'Sonstiges Europa' in mh and non_eu:
        fallback = mh['Sonstiges Europa'] / non_eu
        for group in FALLBACK_RATIO_GROUPS:
            if group in ORIGIN_COLUMNS.values() and group not in ratios:
                ratios[group] = fallback
                provenance[group] = {'basis': 'fallback_non_eu_europe_aggregate',
                                     'migration_background_persons': mh['Sonstiges Europa'],
                                     'citizenship_persons': non_eu}
    missing = set(ORIGIN_COLUMNS.values()) - set(ratios)
    if missing:
        raise SystemExit(f'No naturalisation ratio available for: {sorted(missing)}')
    return ratios, provenance


def state_total(atlas: dict) -> tuple[int, int, str]:
    bw = atlas['bw']
    lo, hi = bw.get('value_lower'), bw.get('value_upper')
    if not (lo and hi):
        raise SystemExit(f'Published BW range not found in atlas["bw"]: {bw}')
    return int(lo), int(hi), bw.get('source_id', 'bamf_fb55')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=ROOT / 'docs/data/district-estimate.json')
    args = ap.parse_args()

    atlas = json.loads((ROOT / 'docs/data/atlas.json').read_text(encoding='utf-8'))
    origins = json.loads((ROOT / 'docs/data/district-origins-2024-12.json').read_text(encoding='utf-8'))
    migration = json.loads((ROOT / 'docs/data/district-migration-2024.json').read_text(encoding='utf-8'))
    shares = load_shares()
    t_low, t_high, total_source = state_total(atlas)

    population = {d['id']: d['population'] for d in atlas['districts']}
    mh = {d['id']: d['migration_background_thousand'] for d in migration['districts']}
    # Districts sharing one Mikrozensus region must not count that region twice.
    shared = {}
    for d in migration['districts']:
        if d['shared_region']:
            shared.setdefault(d['mikrozensus_region_code'], []).append(d['id'])
    mh_key = dict(mh)
    for ids in shared.values():
        pop = sum(population[i] for i in ids)
        for i in ids:
            mh_key[i] = mh[i] * population[i] / pop

    ratios, ratio_provenance = naturalisation_ratios(origins, migration['reference_period'])

    # Two keys per district: the raw citizenship key, and the same key with each origin
    # scaled by its own naturalisation-and-descendants factor.
    explained, corrected, rows = {}, {}, {}
    for r in origins['districts']:
        k = r['id']
        by_origin, by_origin_corrected = {}, {}
        for column, group in ORIGIN_COLUMNS.items():
            count = r.get(column) or 0
            share = shares[group]['share_percent'] / 100
            by_origin[group] = count * share
            by_origin_corrected[group] = count * ratios[group] * share
        explained[k] = sum(by_origin.values())
        corrected[k] = sum(by_origin_corrected.values())
        rows[k] = {'id': k, 'name': r['name'], 'population': population[k],
                   'explained_by_citizenship': round(explained[k]),
                   'explained_with_naturalisation': round(corrected[k]),
                   'by_origin': {g: round(v) for g, v in by_origin.items()},
                   'by_origin_with_naturalisation': {g: round(v) for g, v in by_origin_corrected.items()}}

    sum_e = sum(explained.values())
    sum_c = sum(corrected.values())
    sum_mh = sum(mh_key.values())

    def variant(name: str, total: int) -> dict:
        """Scale an explained part to the published total, distributing what it misses."""
        base = explained if name == 'citizenship' else corrected
        base_sum = sum_e if name == 'citizenship' else sum_c
        residual = total - base_sum
        out = {}
        for k in rows:
            if name == 'citizenship':
                # Residual follows the citizenship pattern itself.
                out[k] = total * base[k] / base_sum
            else:
                # Residual is the origin groups with no district figures at all; it
                # follows population with migration background.
                out[k] = base[k] + residual * mh_key[k] / sum_mh
        return out

    variants = {
        name: {'low': variant(name, t_low), 'high': variant(name, t_high)}
        for name in ('citizenship', 'migration_background')
    }

    districts = []
    for k, base in sorted(rows.items()):
        values = {}
        for name, band in variants.items():
            lo, hi = band['low'][k], band['high'][k]
            values[name] = {
                'persons_low': round(lo), 'persons_high': round(hi),
                'percent_low': round(100 * lo / base['population'], 2),
                'percent_high': round(100 * hi / base['population'], 2),
            }
        all_lo = min(v['persons_low'] for v in values.values())
        all_hi = max(v['persons_high'] for v in values.values())
        districts.append({
            **base,
            'variants': values,
            'combined_low_persons': all_lo,
            'combined_high_persons': all_hi,
            'combined_low_percent': round(100 * all_lo / base['population'], 2),
            'combined_high_percent': round(100 * all_hi / base['population'], 2),
        })

    for d in districts:
        if not 0 < d['combined_low_percent'] <= d['combined_high_percent'] < 60:
            raise ValueError(f'Implausible estimate for {d["name"]}: {d}')
    for name, band in variants.items():
        for edge, total in (('low', t_low), ('high', t_high)):
            s = sum(band[edge].values())
            if abs(s - total) > 1:
                raise ValueError(f'{name}/{edge} sums to {s}, expected {total}')

    data = {
        'type': 'modelled_district_muslim_population',
        'schema_version': '1.0',
        'is_model_not_measurement': True,
        'headline': 'Modellrechnung, keine amtliche Messung der Religionszugehörigkeit.',
        'method': ('Veröffentlichte Landessumme, verteilt nach Herkunftsschlüssel: '
                   'ausländische Bevölkerung je Staatsangehörigkeit multipliziert mit dem '
                   'bundesweiten muslimischen Anteil dieser Herkunftsgruppe.'),
        'state_total': {'persons_low': t_low, 'persons_high': t_high,
                        'reference_period': '2025', 'source_id': total_source},
        'origin_source': {'source': origins['source'], 'table': origins['source_table'],
                          'reference_period': origins['reference_period'],
                          'measurement': origins['measurement']},
        'share_source': {'source': 'BAMF Forschungsbericht 55, Tabelle 2',
                         'reference_period': '2019/2020',
                         'excluded': 'Fünf abweichende Werte aus Tabelle 1, Spalte E.'},
        'migration_source': {'source': migration['source'],
                             'reference_period': migration['reference_period']},
        'origin_groups_used': {c: {'group': g, 'share_percent': shares[g]['share_percent']}
                               for c, g in ORIGIN_COLUMNS.items()},
        'origin_groups_not_available_per_district': sorted(set(shares) - set(ORIGIN_COLUMNS.values())),
        'naturalisation_ratios': {g: {'ratio': round(v, 3), **ratio_provenance[g]}
                                  for g, v in sorted(ratios.items())},
        'coverage': {
            'explained_by_citizenship_persons': round(sum_e),
            'explained_with_naturalisation_persons': round(sum_c),
            'share_of_published_low_percent': round(100 * sum_e / t_low, 1),
            'share_of_published_high_percent': round(100 * sum_e / t_high, 1),
            'corrected_share_of_published_low_percent': round(100 * sum_c / t_low, 1),
            'corrected_share_of_published_high_percent': round(100 * sum_c / t_high, 1),
            'note': ('Die Staatsangehörigkeitsdaten erklären nur diesen Teil der '
                     'veröffentlichten Landessumme. Der Rest entfällt auf Eingebürgerte, '
                     'in Deutschland geborene Nachkommen und Herkunftsgruppen ohne '
                     'Kreisangabe. Genau dieser Rest wird in den beiden Varianten '
                     'unterschiedlich verteilt.'),
        },
        'variants': {
            'citizenship': ('Nur Staatsangehörigkeit. Der nicht erklärte Rest wird wie die '
                            'Staatsangehörigkeitsdaten selbst verteilt.'),
            'migration_background': ('Jede Herkunftsgruppe wird mit ihrem eigenen Faktor aus '
                                     'Migrationshintergrund je Herkunft geteilt durch '
                                     'Staatsangehörige derselben Herkunft hochgerechnet. Der '
                                     'verbleibende Rest wird nach Bevölkerung mit '
                                     'Migrationshintergrund verteilt.'),
        },
        'limitations': [
            'Keine amtliche Religionsstatistik auf Kreisebene; dies ist eine Modellrechnung.',
            'Die muslimischen Anteile je Herkunftsgruppe sind bundesweite Werte von 2019/2020. '
            'Auch der BAMF-Bericht selbst rechnet seine Werte für 2025 mit diesen Anteilen; '
            'neuere liegen nicht vor. Das ist die größte Fehlerquelle des Ergebnisses.',
            'Staatsangehörigkeit ist nicht Herkunft: Eingebürgerte fehlen in der Herkunftsquelle.',
            'Nur 8 der 18 veröffentlichten Herkunftsgruppen haben eine Entsprechung je Kreis.',
            'Die Bezugszeiten der Bausteine unterscheiden sich (2025, 31.12.2024, 2024, 2019/2020).',
            'Der Mikrozensus ist eine Stichprobe; Rastatt und Baden-Baden teilen eine Region.',
        ],
        'districts': districts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'Explained by citizenship only:      {round(sum_e):>9,} '
          f'({100*sum_e/t_high:.0f}-{100*sum_e/t_low:.0f}% of published)'.replace(',', '.'))
    print(f'Explained with naturalisation:     {round(sum_c):>9,} '
          f'({100*sum_c/t_high:.0f}-{100*sum_c/t_low:.0f}% of published)'.replace(',', '.'))
    print('Ratios:', ', '.join(f'{g} {v:.2f}' for g, v in sorted(ratios.items())))
    ranked = sorted(districts, key=lambda d: -d['combined_high_percent'])
    print(f"\n{'Kreis':<32}{'citizenship %':>16}{'migration %':>16}")
    for d in ranked[:8]:
        c, m = d['variants']['citizenship'], d['variants']['migration_background']
        print(f"  {d['name']:<30}{c['percent_low']:>7.1f}-{c['percent_high']:<7.1f}"
              f"{m['percent_low']:>8.1f}-{m['percent_high']:<7.1f}")


if __name__ == '__main__':
    main()

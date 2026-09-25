#!/usr/bin/env python3
"""Age pyramid for Baden-Württemberg 2025 by sex and immigration history.

Source: Statistisches Landesamt Baden-Württemberg, "Bevölkerung in Baden-Württemberg
2025 nach Altersgruppen, Geschlecht und Einwanderungsgeschichte" and "... nach
Einwanderungsgeschichte" (Mikrozensus).

A DIFFERENT CLASSIFICATION FROM THE REST OF THE ATLAS. Since 2023 the Mikrozensus
reports "Einwanderungsgeschichte" instead of "Migrationshintergrund", and the two are
not the same:

  * mit Einwanderungsgeschichte      the person or BOTH parents immigrated since 1950
  * mit einseitiger Einwanderungsgeschichte   ONE parent immigrated
  * ohne Einwanderungsgeschichte     neither

The district-level figures elsewhere in this atlas use "Migrationshintergrund" from
tables 12211-0502/0503/0504. The two must not be added together or compared as if they
were the same measure; this file therefore stays a separate state-level view and is
labelled as such. For orientation: the two immigration-history categories together come
to roughly the same magnitude as the migration-background figure, but the definitions
still differ.

Nothing here enters the modelled Muslim figures. Immigration history is not a religious
indicator, and this is a state total with no district detail.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ('Statistisches Landesamt Baden-Württemberg, Mikrozensus 2025, '
          '"Bevölkerung in Baden-Württemberg 2025 nach Altersgruppen, Geschlecht und '
          'Einwanderungsgeschichte"')
SOURCE_URL = 'https://www.statistik-bw.de/'
CATEGORIES = {
    'ohne Einwanderungsgeschichte': 'without',
    'Mit einseitiger Einwanderungsgeschichte': 'one_parent',
    'mit einseitiger Einwanderungsgeschichte': 'one_parent',
    'mit Einwanderungsgeschichte': 'with',
}
LABELS = {'without': 'ohne Einwanderungsgeschichte',
          'one_parent': 'mit einseitiger Einwanderungsgeschichte',
          'with': 'mit Einwanderungsgeschichte'}
YOUNG_GROUPS = ['0–4', '5–9', '10–14', '15–19', '20–24']


def value(token: str):
    token = (token or '').strip()
    return None if token in {'', '/', '.', '-', '–', 'x'} else int(token)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path,
                    default=ROOT / 'inputs/stala-bw-2025-einwanderungsgeschichte.csv')
    ap.add_argument('--output', type=Path,
                    default=ROOT / 'docs/data/state-age-pyramid-2025.json')
    args = ap.parse_args()

    rows = list(csv.DictReader(args.input.open(encoding='utf-8')))
    totals, cells, ages = {}, {}, []
    for r in rows:
        key = CATEGORIES.get(r['category'])
        if key is None:
            raise ValueError(f'Unknown category: {r["category"]!r}')
        if r['series'] == 'total':
            totals[key] = value(r['value_thousand'])
        else:
            cells[(r['age_group'], r['sex'], key)] = value(r['value_thousand'])
            if r['age_group'] not in ages:
                ages.append(r['age_group'])

    missing = set(LABELS) - set(totals)
    if missing:
        raise ValueError(f'Missing state totals for: {sorted(missing)}')

    pyramid, suppressed = [], []
    for age in ages:
        row = {'age_group': age}
        for sex in ('Männlich', 'Weiblich'):
            row[sex] = {}
            for key in LABELS:
                v = cells.get((age, sex, key))
                row[sex][key] = v
                if v is None:
                    suppressed.append({'age_group': age, 'sex': sex, 'category': LABELS[key]})
        pyramid.append(row)

    def covered(key):
        return sum(v for (a, s, k), v in cells.items() if k == key and v is not None)

    grand = sum(t for t in totals.values() if t is not None)
    age_sum = sum(v for v in cells.values() if v is not None)

    # Share of under-25s within each category, over the published cells only.
    young = {}
    for key in LABELS:
        total_cells = covered(key)
        y = sum(v for (a, s, k), v in cells.items()
                if k == key and a in YOUNG_GROUPS and v is not None)
        young[key] = round(100 * y / total_cells, 1) if total_cells else None

    if not (0 < young['with'] < 80) or not (0 < young['without'] < 80):
        raise ValueError(f'Implausible under-25 shares: {young}')
    if young['without'] >= young['with']:
        raise ValueError('Expected the immigration-history population to be younger; '
                         f'got {young}')

    data = {
        'type': 'state_age_pyramid_by_immigration_history',
        'schema_version': '1.0',
        'reference_period': '2025',
        'geography': 'Baden-Württemberg',
        'source': SOURCE,
        'source_url': SOURCE_URL,
        'unit_note': 'Angaben in Tausend.',
        'survey_note': 'Mikrozensus, Stichprobenerhebung mit Zufallsfehler.',
        'classification_note': (
            'Einwanderungsgeschichte ist NICHT dasselbe wie Migrationshintergrund. '
            '„mit Einwanderungsgeschichte" heißt: die Person oder beide Elternteile sind '
            'seit 1950 eingewandert; „einseitig" heißt: ein Elternteil. Die Kreiswerte '
            'im übrigen Atlas verwenden den Migrationshintergrund und dürfen mit diesen '
            'Zahlen nicht vermischt werden.'),
        'not_a_religion_dataset': (
            'Einwanderungsgeschichte ist keine Religionszugehörigkeit. Diese Zahlen gehen '
            'nicht in die Modellrechnung ein.'),
        'state_totals_thousand': {LABELS[k]: v for k, v in totals.items()},
        'state_total_thousand': grand,
        'age_table_sum_thousand': age_sum,
        'age_groups': ages,
        'under_25_share_percent': {LABELS[k]: v for k, v in young.items()},
        'suppressed_cells': suppressed,
        'pyramid': pyramid,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    view = {
        'meta': {k: data[k] for k in ('reference_period', 'geography', 'source',
                                      'survey_note', 'classification_note',
                                      'not_a_religion_dataset', 'unit_note')},
        'labels': LABELS,
        'age_groups': ages,
        'under_25': {LABELS[k]: v for k, v in young.items()},
        'totals': {LABELS[k]: v for k, v in totals.items()},
        'pyramid': pyramid,
    }
    args.output.with_name('pyramid-data.js').write_text(
        'window.ATLAS_PYRAMID=' + json.dumps(view, ensure_ascii=False,
                                             separators=(',', ':')) + ';\n', encoding='utf-8')

    print(f'{len(ages)} age groups, {grand:,} thousand people.'.replace(',', '.'))
    print('Under 25: ' + ', '.join(f'{LABELS[k]} {young[k]} %' for k in LABELS))
    print(f'Suppressed cells: {len(suppressed)}')


if __name__ == '__main__':
    main()

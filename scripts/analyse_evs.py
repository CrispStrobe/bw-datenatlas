#!/usr/bin/env python3
"""Rebuild selected German aggregates from licensed local EVS/Joint SAV files.

Raw files stay private. Install requirements-evs.txt and provide both SAV paths.
ZA7505 is the recent joint wave, not the historical IVS trend file.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def estimate(values, weights, valid_codes, selected_codes):
    """Valid response denominator; missing codes and nonpositive weights excluded."""
    if not set(selected_codes) <= set(valid_codes):
        raise ValueError('Selected codes must be valid response codes')
    if len(values) != len(weights):
        raise ValueError('Response/weight lengths differ')
    pairs = [(v, w) for v, w in zip(values, weights)
             if v in valid_codes and math.isfinite(w) and w > 0]
    denominator = math.fsum(w for _, w in pairs)
    if not denominator:
        raise ValueError('No valid weighted responses')
    numerator = math.fsum(w for v, w in pairs if v in selected_codes)
    return {'value': 100 * numerator / denominator,
            'valid_n': len(pairs), 'weighted_valid_n': denominator}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--evs-sav', type=Path, required=True)
    ap.add_argument('--joint-sav', type=Path, required=True)
    args = ap.parse_args()
    import pyreadstat
    spec_path = ROOT / 'inputs/evs-analysis-spec.json'
    spec = json.loads(spec_path.read_text())
    items = spec['items']
    sources = {}
    for key, path, columns, country, weight in [
        ('evs', args.evs_sav, ['country', 'gweight', 'version'] +
         sorted({r['variable'] for r in items}), 'country', 'gweight'),
        ('joint', args.joint_sav, ['cntry', 'study', 'gwght', 'version'] +
         sorted({r['joint_variable'] for r in items if 'joint_variable' in r}),
         'cntry', 'gwght')]:
        frame, meta = pyreadstat.read_sav(str(path), usecols=columns, user_missing=True)
        frame = frame[frame[country] == spec['country']]
        if key == 'joint':
            frame = frame[frame.study == spec['joint_study']]
        if len(frame) != 2170:
            raise ValueError(f'{key}: expected 2170 German EVS cases, got {len(frame)}')
        if not all(str(v).split()[0] in {'5.0.0', '5-0-0'} for v in frame.version.unique()):
            raise ValueError(f'{key}: unexpected source version')
        sources[key] = (frame, weight)
    result = []
    for r in items:
        frame, weight = sources['evs']
        calculated = estimate(frame[r['variable']], frame[weight],
                              r['valid_codes'], r['selected_codes'])
        # Shared harmonised variables must reproduce the source estimates;
        # Germany's WVS sample (study=2) must never enter the EVS denominator.
        if 'joint_variable' in r:
            joint, jw = sources['joint']
            check = estimate(joint[r['joint_variable']], joint[jw],
                             r['joint_valid_codes'], r['joint_selected_codes'])
            if calculated['valid_n'] != check['valid_n'] or not math.isclose(
                    calculated['value'], check['value'], abs_tol=1e-8):
                raise ValueError(f"Source/joint mismatch: {r['variable']}")
            calculated = check
        metadata = {k: v for k, v in r.items() if k not in {
            'variable', 'valid_codes', 'selected_codes', 'joint_variable',
            'joint_valid_codes', 'joint_selected_codes'}}
        result.append({**metadata, **calculated})
    # Finish validation before touching public aggregate outputs.
    target = ROOT / 'inputs/evs-items.csv'
    with target.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(result[0]))
        writer.writeheader(); writer.writerows(result)
    provenance = {
        'analysis': 'Weighted valid-response shares; Germany EVS only',
        'spec_sha256': hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        'sources': [
            {'file': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
             'doi': doi, 'version': '5.0.0'} for p, doi in [
                (args.evs_sav, '10.4232/1.13897'),
                (args.joint_sav, '10.4232/1.14320')]],
        'software': {'pyreadstat': pyreadstat.__version__},
        'country_code': spec['country'], 'joint_study_code': spec['joint_study'],
        'sample_n': 2170, 'items': len(result),
        'common_core_crosscheck': 'All selected common items match ZA7500 and ZA7505',
        'not_included': 'German WVS cases, matrix samples, historical IVS trend'}
    (ROOT / 'inputs/evs-analysis-provenance.json').write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + '\n')
    print(f'{len(result)} selected estimates; both source files cross-checked')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Fail if the build reads an input that is not committed.

The workflow rebuilds every model file and refuses the push when the result differs from
what the repository holds. That gate can only be met if CI reads the same inputs the
local build read — and it silently cannot when a new input file has been written but not
committed. That is what happened with the second-source file: the published data was
built with it, the repository did not contain it, and CI produced a different file with
no indication why.

Run before committing rebuilt data.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Every file the data build reads, by the scripts that CI runs.
READ_BY_THE_BUILD = [
    'inputs/institutions-town.json',
    'inputs/postcodes-bw.json',
    'inputs/landtag-affiliation-corroboration.json',
    'inputs/igmg-landtag-15-362.json',
]


def main() -> int:
    missing, dirty = [], []
    for name in READ_BY_THE_BUILD:
        path = ROOT / name
        if not path.is_file():
            continue
        tracked = subprocess.run(['git', 'ls-files', '--error-unmatch', name],
                                 cwd=ROOT, capture_output=True).returncode == 0
        if not tracked:
            missing.append(name)
            continue
        changed = subprocess.run(['git', 'diff', '--quiet', '--', name], cwd=ROOT).returncode
        staged = subprocess.run(['git', 'diff', '--cached', '--quiet', '--', name],
                                cwd=ROOT).returncode
        if changed and not staged:
            dirty.append(name)

    for name in missing:
        print(f'  not committed at all: {name}')
    for name in dirty:
        print(f'  changed but not staged: {name}')
    if missing or dirty:
        print('\nCI rebuilds from the repository. An input it cannot see produces a '
              'different file and the reproducibility gate fails without saying why.')
        return 1
    print(f'All {len(READ_BY_THE_BUILD)} build inputs are committed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

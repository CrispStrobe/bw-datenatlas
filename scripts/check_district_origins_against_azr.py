#!/usr/bin/env python3
"""Check the district origin figures against the federal register, country by country.

The model distributes a published state total across districts using nationality counts
from the state's own report, A I 4-j. Nothing checked those counts. The Federal
Statistical Office publishes the same register — the Ausländerzentralregister — per
district, and where the two overlap they must broadly agree.

They will not agree exactly, and should not: the state report is dated 31 December 2024
and the federal file 31 December 2025, so a year of arrivals and departures lies between
them. Ukraine and Syria in particular move fast. What this checks is whether any district
diverges so far that one of the two is describing something else — a misparsed column, a
district matched to the wrong row, a units error.

The federal file names only five countries; the state report names twenty-five, which is
why the model uses the state report and not this one. Five is enough to catch a
systematic fault.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'docs/data/district-origins-2024-12.json'
FEDERAL = ROOT / 'docs/data/district-azr-2025.json'
SHARED = ['turkey', 'ukraine', 'syria', 'romania', 'poland']
# A year apart, so movement is expected. These are the points at which a difference
# stops looking like a year and starts looking like a mistake.
TOLERANCE = {'turkey': 0.25, 'romania': 0.40, 'poland': 0.30,
             'syria': 0.60, 'ukraine': 0.80}


# Matched on the official district key, never on the name. Both files carry the same
# five-digit AGS, and the names collide: Heilbronn and Karlsruhe each exist twice in
# Baden-Württemberg, once as a Stadtkreis and once as a Landkreis. The first version of
# this script normalised the names, collapsed each pair into one key, and compared the
# city against the rural district — which is exactly the "district matched to the wrong
# row" fault it was written to catch. It caught it in itself.


def main() -> int:
    state = {r['id']: r for r in json.loads(STATE.read_text('utf-8'))['districts']}
    federal = json.loads(FEDERAL.read_text('utf-8'))['districts']

    unmatched, flagged, compared = [], [], 0
    for row in federal:
        theirs = state.get(row['id'])
        if theirs is None:
            unmatched.append(row['name'])
            continue
        for country in SHARED:
            a, b = theirs.get(country), row.get(country)
            if not a or not b:
                continue
            compared += 1
            drift = abs(b - a) / a
            if drift > TOLERANCE[country]:
                flagged.append({'district': row['name'], 'country': country,
                                'state_2024': a, 'federal_2025': b,
                                'drift': round(drift, 3)})

    print(f'{compared} Vergleiche über {len(federal) - len(unmatched)} Kreise.')
    if unmatched:
        print(f'  {len(unmatched)} Kreise ohne Gegenstück: {unmatched[:6]}')
    for row in sorted(flagged, key=lambda r: -r['drift'])[:15]:
        print(f"  {row['district'][:24]:26s} {row['country']:8s} "
              f"{row['state_2024']:>8,.0f} → {row['federal_2025']:>8,.0f}  "
              f"{row['drift']*100:5.1f} %")
    print(f'\n{len(flagged)} von {compared} Vergleichen über der Toleranz.')
    # Unmatched districts are a fault in this script, not in the data: both files cover
    # the same 44 districts.
    if unmatched:
        print('Kreise ohne Gegenstück deuten auf einen Namensabgleich hin, der nicht '
              'trägt — nicht auf fehlende Daten.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

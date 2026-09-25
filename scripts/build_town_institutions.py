#!/usr/bin/env python3
"""Build the published institution directory from the town-level input.

This is the whole institution pipeline of the public repository. The harvesting,
address verification and geocoding happen elsewhere, in a private repository that holds
the street addresses; what arrives here is their result with the streets removed.

The separation is not about the licence. The directory stays ODbL, because OpenStreetMap
geocoding is in it and share-alike does not care which repository a file sits in. It is
about what one downloadable artefact makes easy. Six hundred institutions' own Impressum
pages and a single curated statewide address file are not the same object, and it is the
second that the Zentralrat der Muslime stopped publishing, citing attacks on mosques —
the Bundeskriminalamt counted 53 of those in 2025 (Bundestags-Drucksachen 21/5917,
21/2705).

So this atlas says: this institution exists, in this town, in this federation, and here
is the proof. The proof is a link. Following it shows the address, exactly as it did
before this project existed; what is not published here is the compiled list.

The coordinate of every point is its municipality's label point from the official
boundaries, recomputed here rather than trusted from the input, so that the published
file can be rebuilt byte for byte and a building coordinate cannot slip in.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from bw_geography import Municipalities  # noqa: E402

FORBIDDEN = ('street', 'postcode_of_building', 'lat_of_building')
# Defence in depth. The extract in the private repository redacts addresses out of the
# notes, and twice it did so incompletely — once for an entry's own street, once for a
# rival address quoted in a note about it. This build refuses rather than publishes.
LOOKS_LIKE_AN_ADDRESS = re.compile(
    r'\b[\wÄÖÜäöüß.\-]*\s?(?:stra(?:ss|ß)e|str\.|weg|platz|allee|gasse|ring)'
    r'\s?\d{1,4}\s?[a-zA-Z]?\b', re.I)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path, default=ROOT / 'inputs/institutions-town.json')
    ap.add_argument('--output', type=Path, default=ROOT / 'docs/data/institutions.json')
    args = ap.parse_args()

    doc = json.loads(args.input.read_text(encoding='utf-8'))
    municipalities = Municipalities()
    by_ags = {props['id']: props
              for *_, props in municipalities.prepared}

    rows = []
    for entry in doc['institutions']:
        for field in FORBIDDEN:
            if field in entry:
                raise SystemExit(f'{field} must not appear in the public input: '
                                 f'{entry.get("name")}')
        props = by_ags.get(entry.get('municipality_id'))
        if props is None:
            raise SystemExit(f'unknown municipality for {entry.get("name")}: '
                             f'{entry.get("municipality_id")}')
        row = dict(entry)
        # Recomputed, never copied: the input could carry anything, and this is the one
        # place that decides what coordinate is published.
        row['lon'] = round(props['label_point'][0], 5)
        row['lat'] = round(props['label_point'][1], 5)
        row['municipality'] = props['name']
        row['location_precision'] = 'municipality'
        row['geocode_source'] = 'municipality_label_point'
        row['has_published_coordinates'] = False
        for key, value in row.items():
            if key.endswith('_url') or key in ('website', 'facebook', 'instagram'):
                continue
            found = LOOKS_LIKE_AN_ADDRESS.search(str(value))
            if found:
                raise SystemExit(f'address survives in {key} of {row.get("name")}: '
                                 f'{found.group(0)!r}')
        rows.append(row)

    published = {k: v for k, v in doc.items() if k != 'institutions'}
    published['institutions'] = rows
    published['located'] = len(rows)
    args.output.write_text(json.dumps(published, ensure_ascii=False, indent=1) + '\n',
                           encoding='utf-8')
    # The page reads the JS copy, not the JSON, so a build that wrote only the JSON
    # would leave the previous data on the map. During the split this file still held
    # every street address after the JSON had been cleaned — the whole point of the
    # separation, undone by one file that nothing rebuilt.
    args.output.with_name('institution-data.js').write_text(
        'window.ATLAS_INSTITUTIONS=' + json.dumps(published, ensure_ascii=False,
                                                  separators=(',', ':')) + ';\n',
        encoding='utf-8')
    print(f'{len(rows)} Einrichtungen auf Ortsebene geschrieben (JSON und JS).')


if __name__ == '__main__':
    main()

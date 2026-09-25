#!/usr/bin/env python3
"""The postcodes of Baden-Württemberg, from GeoNames, cross-checked against OpenStreetMap.

The atlas had no postcode list and so could not check its own postcodes. Arithmetic does
not help: 68, 69, 88, 89 and 97 lie partly inside the state and partly outside — the same
trap as the bounding box that let twenty-three out-of-state institutions onto the map.

WHY GEONAMES AND NOT OPENSTREETMAP. The first version of this script read OpenStreetMap's
`boundary=postal_code` relations. GeoNames is better on both counts that matter here.

  Coverage. GeoNames lists 1396 place postcodes for the state against OpenStreetMap's
  1192, and is very nearly a superset of it. Two postcodes this atlas uses — 73726
  Esslingen and 89597 Munderkingen — exist in GeoNames and are simply missing from the
  OpenStreetMap relations.

  Licence. GeoNames publishes under CC BY 4.0, which has no share-alike. OpenStreetMap's
  ODbL does, and this project already carries that obligation through Nominatim
  geocoding; there is no reason to extend it to a file that need not bear it. The
  companion project radius-atlas states the rule this follows: do not relabel an
  ODbL-derived database as CC BY. So OpenStreetMap stays as a cross-check only, and is
  named as such.

TWO KINDS OF POSTCODE. Germany issues Großkunden postcodes to single large recipients —
GeoNames lists "10875 Mercedes-Benz. io GmbH" among them. They are valid for post and
useless for locating anything, so they are kept separately and never count as evidence
that an address exists.

A caution that applies to the result: a postcode's presence here means it exists. Its
absence is weaker evidence, and two postcodes in this atlas — 79011, a Freiburg PO box,
and 74875 — appear in neither register.
"""
from __future__ import annotations
import argparse
import io
import json
import re
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache/geonames-de-postcodes.txt'
OSM_CACHE = ROOT / '.cache/osm-postcodes-bw.json'
OUTPUT = ROOT / 'inputs/postcodes-bw.json'
GEONAMES = 'https://download.geonames.org/export/zip/DE.zip'
STATE = 'Baden-Württemberg'
# A "place" whose name is a company is a Großkunden postcode, not a locality.
COMPANY = re.compile(r'\b(GmbH|AG|KG|mbH|e\.\s?V\.|SE|Bank|Versicherung|Verlag|Postfach)\b',
                     re.I)


def geonames_rows() -> list[list[str]]:
    if not (CACHE.is_file() and CACHE.stat().st_size > 10000):
        with urllib.request.urlopen(urllib.request.Request(
                GEONAMES, headers={'User-Agent': 'BW-Datenatlas/0.1'}), timeout=180) as r:
            archive = zipfile.ZipFile(io.BytesIO(r.read()))
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_bytes(archive.read('DE.txt'))
    return [line.rstrip('\n').split('\t')
            for line in CACHE.read_text(encoding='utf-8').splitlines() if line.strip()]


def osm_postcodes() -> set[str]:
    """Only to say, per postcode, whether OpenStreetMap maps an area for it."""
    if not OSM_CACHE.is_file():
        return set()
    return {(e.get('tags') or {}).get('postal_code')
            for e in json.loads(OSM_CACHE.read_text(encoding='utf-8')).get('elements', [])
            if (e.get('tags') or {}).get('postal_code')}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=OUTPUT)
    args = ap.parse_args()

    mapped = osm_postcodes()
    places: dict[str, dict] = {}
    bulk: dict[str, dict] = {}
    for row in geonames_rows():
        if len(row) < 11 or row[3] != STATE:
            continue
        code, name = row[1], row[2]
        target = bulk if COMPANY.search(name) else places
        entry = target.setdefault(code, {'postcode': code, 'places': [], 'districts': []})
        if name not in entry['places']:
            entry['places'].append(name)
        district = row[7]
        if district and district not in entry['districts']:
            entry['districts'].append(district)
        try:
            entry.setdefault('lat', round(float(row[9]), 5))
            entry.setdefault('lon', round(float(row[10]), 5))
        except (ValueError, IndexError):
            pass
    for code, entry in places.items():
        entry['mapped_in_openstreetmap'] = code in mapped

    doc = {
        'type': 'postcode_areas_of_baden_wuerttemberg',
        'schema_version': '2.0',
        'source': 'GeoNames, Postleitzahlendatei DE',
        'source_url': GEONAMES,
        'licence': 'GeoNames, CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/',
        'attribution': '© GeoNames, CC BY 4.0. Auswahl, Filterung und Trennung von '
                       'Großkunden-Postleitzahlen sind Bearbeitungen dieses Atlas.',
        'cross_check': ('Zu jeder Postleitzahl ist vermerkt, ob OpenStreetMap ein Gebiet '
                        'dafür führt (Relation boundary=postal_code, ODbL). Das ist nur '
                        'eine Gegenprobe; die Liste selbst stammt nicht daraus und wird '
                        'nicht als ODbL-Datenbank weitergegeben.'),
        'method': ('Alle Zeilen der GeoNames-Datei mit Bundesland „Baden-Württemberg“. '
                   'Zeilen, deren Ortsname ein Unternehmen ist, sind '
                   'Großkunden-Postleitzahlen und stehen getrennt.'),
        'caveat': ('Vorhandensein beweist, dass es die Postleitzahl gibt. Fehlen beweist '
                   'nicht, dass es sie nicht gibt.'),
        'count': len(places),
        'count_bulk_recipients': len(bulk),
        'postcodes': [places[c] for c in sorted(places)],
        'bulk_recipient_postcodes': [bulk[c] for c in sorted(bulk)],
    }
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                           encoding='utf-8')
    print(f'{len(places)} Postleitzahlen in Baden-Württemberg '
          f'({sum(1 for e in places.values() if e["mapped_in_openstreetmap"])} auch in '
          f'OpenStreetMap), {len(bulk)} Großkunden-Postleitzahlen getrennt.')


if __name__ == '__main__':
    main()

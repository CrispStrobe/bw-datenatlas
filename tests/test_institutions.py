#!/usr/bin/env python3
"""What the published institution directory must satisfy in this repository.

This atlas publishes the directory at town level: which institution exists, in which
municipality, in which federation, and with which sources. The street addresses live in
a separate, private repository and are deliberately absent here. The tests therefore ask
two kinds of question — that nothing which belongs to the private side has leaked, and
that everything published is sourced and correctly placed.
"""
from __future__ import annotations
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from bw_geography import Municipalities  # noqa: E402

LOOKS_LIKE_AN_ADDRESS = re.compile(
    r'\b[\wÄÖÜäöüß.\-]*\s?(?:stra(?:ss|ß)e|str\.|weg|platz|allee|gasse|ring)'
    r'\s?\d{1,4}\s?[a-zA-Z]?\b', re.I)

ALLOWED = {
    'organisation', 'name', 'city', 'postcode', 'municipality', 'municipality_id',
    'lat', 'lon', 'location_precision', 'geocode_source', 'has_published_coordinates',
    'source', 'source_url', 'source_kind', 'second_source_url', 'second_source_kind',
    'website', 'website_from', 'facebook', 'instagram', 'openstreetmap_url',
    'self_published_note', 'operator', 'denomination', 'regional_association',
    'claimed_affiliation', 'from_curated_file',
    'affiliation_source_url', 'affiliation_note',
    'affiliation_restated_url', 'affiliation_restated_note',
    'state_characterisation_url', 'state_characterisation_note', 'why_no_address',
}


class TestPublishedDirectory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads((ROOT / 'docs/data/institutions.json').read_text('utf-8'))
        cls.rows = cls.doc['institutions']
        cls.municipalities = Municipalities()
        cls.postcodes = {p['postcode'] for p in json.loads(
            (ROOT / 'inputs/postcodes-bw.json').read_text('utf-8'))['postcodes']}

    def test_no_street_field_anywhere(self):
        for row in self.rows:
            self.assertNotIn('street', row, f'{row["name"]} carries a street')

    def test_no_address_in_free_text(self):
        """A note may explain an address dispute; it may not restate the address.

        Two slipped through while this split was being built — an entry's own street in
        one note, and a rival directory's address quoted in another. Both were caught
        here rather than in review.
        """
        for row in self.rows:
            for key, value in row.items():
                if key.endswith('_url') or key in ('website', 'facebook', 'instagram'):
                    continue
                found = LOOKS_LIKE_AN_ADDRESS.search(str(value))
                self.assertIsNone(found, f'address in {key} of {row["name"]}: '
                                         f'{found.group(0) if found else ""!r}')

    def test_only_allowed_fields(self):
        for row in self.rows:
            self.assertTrue(set(row) <= ALLOWED,
                            f'unexpected field: {set(row) - ALLOWED}')

    def test_every_entry_has_a_source(self):
        for row in self.rows:
            self.assertTrue(row.get('source_url'), f'{row["name"]} has no source')

    def test_every_point_is_its_municipality_label_point(self):
        """The published coordinate must be the town's, never a building's."""
        by_ags = {props['id']: props for *_, props in self.municipalities.prepared}
        for row in self.rows:
            props = by_ags.get(row.get('municipality_id'))
            self.assertIsNotNone(props, f'{row["name"]} has no municipality')
            self.assertAlmostEqual(row['lon'], round(props['label_point'][0], 5), places=5)
            self.assertAlmostEqual(row['lat'], round(props['label_point'][1], 5), places=5)
            self.assertEqual(row.get('location_precision'), 'municipality')

    def test_every_point_lies_in_baden_wuerttemberg(self):
        for row in self.rows:
            self.assertIsNotNone(self.municipalities.at(row['lon'], row['lat']),
                                 f'{row["name"]} is outside the state')

    def test_postcodes_are_real_or_explained(self):
        """A postcode that no register knows is a data error worth failing on.

        Two are tolerated by name because they are known and documented: 79011 is a
        Freiburg PO box rather than a street postcode, and 74875 appears in neither
        GeoNames nor OpenStreetMap.
        """
        known_exceptions = {'79011', '74875'}
        for row in self.rows:
            code = row.get('postcode')
            if not code or code in known_exceptions:
                continue
            self.assertIn(code, self.postcodes,
                          f'{row["name"]}: postcode {code} is in no register')

    def test_no_personal_data(self):
        blob = ' '.join(str(v) for row in self.rows for k, v in row.items()
                        if not (k.endswith('_url') or k in ('website', 'facebook',
                                                            'instagram')))
        for pattern in (r'ansprechpartner', r'@gmx', r'@web\.de', r'@gmail',
                        r'\btelefon\b', r'\bmobil\b', r'privatanschrift', r'\bc/o\b'):
            self.assertIsNone(re.search(pattern, blob, re.I),
                              f'personal data pattern {pattern} found')

    def test_an_affiliation_claim_carries_its_claimant(self):
        for row in self.rows:
            if row.get('affiliation_note'):
                self.assertTrue(row.get('affiliation_source_url'),
                                f'{row["name"]} claims an affiliation without a source')
            if row.get('state_characterisation_note'):
                self.assertTrue(row.get('state_characterisation_url'),
                                f'{row["name"]} quotes an authority without a source')


if __name__ == '__main__':
    unittest.main()

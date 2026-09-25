"""Offline consistency tests, not a validation of the source estimates."""
import csv
import hashlib
import io
import json
from pathlib import Path
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
A = json.loads((ROOT/'docs/data/atlas.json').read_text(encoding='utf-8'))
OBS = json.loads((ROOT/'docs/data/research-observations.json').read_text(encoding='utf-8'))
BY_ID = {r['observation_id']: r for r in OBS}

class DataTests(unittest.TestCase):
    def test_input_snapshot_hash(self):
        with zipfile.ZipFile(ROOT/'inputs/research-v3.zip') as z:
            data = z.read('muslime_bw_daten.json')
        self.assertEqual(hashlib.sha256(data).hexdigest(), A['input_sha256'])

    def test_input_observations_unchanged(self):
        with zipfile.ZipFile(ROOT/'inputs/research-v3.zip') as z:
            original = json.loads(z.read('muslime_bw_daten.json'))
        self.assertEqual(original['observations'], OBS)

    def test_observation_counts_and_ids(self):
        self.assertEqual(len(OBS), 6367)
        self.assertEqual(len(BY_ID), 6367)
        self.assertEqual(len(A['datasets']), 40)
        self.assertEqual(sum(d['observation_count'] for d in A['datasets']), len(OBS))

    def test_districts_unique_44(self):
        self.assertEqual(len(A['districts']), 44)
        self.assertEqual(len({r['id'] for r in A['districts']}), 44)
        self.assertTrue(all(len(r['id']) == 5 and r['id'].startswith('08') for r in A['districts']))

    def test_district_input_values_and_derived_percentages(self):
        for d in A['districts']:
            values = [BY_ID[i]['value'] for i in d['source_ids']]
            self.assertEqual(values, [d['population'], d['foreign'], d['german']])
            self.assertEqual(d['population'], d['foreign']+d['german'])
            self.assertAlmostEqual(d['foreign_pct'], 100*d['foreign']/d['population'])
            self.assertEqual(d['reference_period'], '2024-11-30')

    def test_district_sums_match_published_state(self):
        state_rows = {r['indicator']: r['value'] for r in OBS if r['dataset_id']=='bw_population_2024' and r['geo_id']=='DE08'}
        self.assertEqual(sum(r['population'] for r in A['districts']), state_rows['population_total'])
        self.assertEqual(sum(r['foreign'] for r in A['districts']), state_rows['foreign_citizens'])

    def test_no_local_religion_observations(self):
        self.assertTrue(all(d['muslim_count'] is None and d['muslim_pct'] is None for d in A['districts']))
        self.assertTrue(all('muslim_count' not in m or m['muslim_count'] is None for m in A['municipalities']))

    def test_municipalities_unique_1101(self):
        self.assertEqual(len(A['municipalities']), 1101)
        self.assertEqual(len({m['geo_id'] for m in A['municipalities']}), 1101)
        self.assertEqual({m['district_code'] for m in A['municipalities']}, {d['id'] for d in A['districts']})

    def test_municipality_sums_and_dates(self):
        self.assertEqual(sum(m['population_total'] for m in A['municipalities']), 11241334)
        for m in A['municipalities']:
            self.assertEqual(m['population_total'], m['population_male']+m['population_female'])
            self.assertEqual(m['reference_period'], '2024-06-30')

    def test_official_keys_not_invented_before_crosswalk(self):
        self.assertEqual(sum(m['official_municipality_code'] is not None for m in A['municipalities']), 1)
        self.assertEqual(next(m for m in A['municipalities'] if m['official_municipality_code'])['official_municipality_code'], '08111000')

    def test_bw_estimate_is_published_range_not_point(self):
        self.assertIsNone(A['bw']['value'])
        self.assertEqual([A['bw']['value_lower'], A['bw']['value_upper']], [1133000,1197000])
        self.assertEqual([A['bw_pct']['value_lower'], A['bw_pct']['value_upper']], [10.1,10.7])
        self.assertIn('2019_spatial_weights_applied_to_2025', A['bw']['quality_flags'])
        self.assertIn('private_main_residence_households', A['bw_pct']['quality_flags'])

    def test_national_origins_are_national_not_bw(self):
        self.assertEqual(len(A['origins_de_2025']), 18)
        self.assertTrue(all(o['geo_id']=='DE' and o['reference_period']=='2025' for o in A['origins_de_2025']))
        self.assertTrue(all(o['dataset_id']=='bamf_fb55_origin_model_2025' for o in A['origins_de_2025']))
        self.assertTrue(all('Tabelle 2' in o['source_locator'] for o in A['origins_de_2025']))

    def test_origin_shares_have_explicit_denominator(self):
        for o in A['origins_de_2025']:
            self.assertAlmostEqual(o['share_of_published_de_total'], 100*o['value']/A['de_total']['value'])
            self.assertEqual(o['share_provenance'], 'derived')
            self.assertEqual(o['share_denominator_observation_id'], A['de_total']['observation_id'])

    def test_fourteen_state_units_not_sixteen_invented_estimates(self):
        self.assertEqual(len(A['states']), 14)
        names = [s['name'] for s in A['states']]
        self.assertTrue(any('Bremen' in n and 'Hamburg' in n for n in names))
        self.assertTrue(any('Brandenburg' in n and 'Mecklenburg' in n for n in names))

    def test_source_audit_comparison(self):
        rows = A['source_audit']['parameter_comparison']
        self.assertEqual(len(rows), 18)
        self.assertEqual(sum(r['table1_differs_from_original_mld'] for r in rows), 5)
        self.assertTrue(all(r['table2_matches_original_mld'] for r in rows))
        self.assertFalse(A['source_audit']['online_fb55_identity_verified'])

    def test_sources_and_observation_references_exist(self):
        self.assertTrue(all(o['source_id'] in A['sources'] for o in A['origins_de_2025']))
        for d in A['districts']:
            self.assertTrue(all(i in BY_ID for i in d['source_ids']))
        self.assertTrue(A['sources']['stala_monat_2020']['url'].endswith('Beitrag20_04_01.pdf'))

    def test_nationality_subsets_kept_separate(self):
        self.assertEqual(sum(r['reference_period']=='2024-12-31' for r in A['nationalities_bw']),25)
        self.assertEqual(sum(r['reference_period']=='2025' for r in A['nationalities_bw']),4)
        self.assertTrue(all('exact_azr_reference_day_unconfirmed' in r['quality_flags'] for r in A['nationalities_bw'] if r['reference_period']=='2025'))
        self.assertTrue(all('not_religion' in r['quality_flags'] for r in A['nationalities_bw']))

    def test_2026_flows_are_not_stock(self):
        months = [r for r in A['flows_bw'] if r['reference_period'].startswith('2026-') and r['reference_period_type']=='month']
        self.assertEqual(len(months),8)
        self.assertEqual(sum(r['value'] for r in months),5403)
        self.assertTrue(all('flow_not_stock' in r['quality_flags'] for r in months))

    def test_csv_view_matches_json(self):
        with (ROOT/'docs/data/districts-2024-11.csv').open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),44)
        self.assertEqual([int(r['population']) for r in rows], [d['population'] for d in A['districts']])

    def test_no_remote_browser_libraries_or_trackers(self):
        html=(ROOT/'docs/index.html').read_text(encoding='utf-8')
        self.assertNotIn('<script src="https:', html)
        self.assertNotIn('<script src="http:', html)
        js=(ROOT/'docs/assets/app.js').read_text(encoding='utf-8')
        self.assertNotIn('fetch(\'http', js)
        self.assertIn("fetch('data/research-observations.json')", js)

if __name__=='__main__': unittest.main(verbosity=2)

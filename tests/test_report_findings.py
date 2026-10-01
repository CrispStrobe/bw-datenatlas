import copy
import json
from pathlib import Path
import unittest
from scripts.prepare_report_findings import validate

ROOT = Path(__file__).resolve().parents[1]


class PublicReportFindings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads((ROOT / 'docs/data/report-findings.json').read_text())
        cls.reports = {r['id']: r for r in cls.doc['reports']}

    def test_partitions_match_public_totals(self):
        validate(self.doc)
        for key, total in [('rias_bw_2025', 335), ('pmk_bw_islamfeindlich', 220),
                           ('ofek_bw_2024_25', 164)]:
            self.assertEqual(sum(i['value'] for i in self.reports[key]['items']), total)
        broken = copy.deepcopy(self.doc)
        broken['reports'][0]['items'][0]['value'] += 1
        with self.assertRaises(ValueError):
            validate(broken)

    def test_separate_measures_and_reference_periods(self):
        self.assertEqual([i['value'] for i in self.reports['pmk_bw_antisemitic']['items']], [668, 590, 575])
        self.assertEqual(self.reports['leuchtlinie_bw_2024']['items'][0]['value'], 19)
        ofek = self.reports['ofek_bw_2024_25']
        self.assertEqual(ofek['period'], 'Oktober 2024 – September 2025')
        self.assertIn('160 aus Baden-Württemberg', ofek['note'])
        self.assertIn('Beratungsfälle, nicht einzelne Vorfälle', ofek['note'])
        self.assertEqual([i['value'] for i in ofek['items']], [37, 105, 19, 3])

    def test_uem_inventory_does_not_claim_all_full_texts_reviewed(self):
        studies = self.doc['uem_studies']
        self.assertEqual(len(studies), 16)
        full = [s for s in studies if s['review_status'] == 'Separater öffentlicher Bericht geprüft']
        self.assertEqual(len(full), 3)
        self.assertIn('nicht repräsentativ', self.reports['uem_overview']['note'])
        self.assertFalse(any(r['id'] == 'uem_media' for r in self.doc['reports']))

    def test_source_and_built_files_agree(self):
        source = json.loads((ROOT / 'inputs/report-findings.json').read_text())
        built = copy.deepcopy(self.doc)
        built.pop('rights')
        built['schema_version'] = source['schema_version']
        for report in built['reports']:
            for published_source in report['sources']:
                published_source.pop('source_rights')
        for study in built['uem_studies']:
            study.pop('source_rights')
        self.assertEqual(built, source)
        self.assertIn('window.ATLAS_REPORT_FINDINGS', (ROOT / 'docs/data/report-findings-data.js').read_text())

    def test_downloads_do_not_relicense_third_party_material(self):
        survey = json.loads((ROOT / 'docs/data/survey-items.json').read_text())
        for doc in (self.doc, survey):
            rights = doc['rights']
            self.assertIsNone(rights['license'])
            self.assertEqual(rights['license_status'], 'no_blanket_open_license')
            self.assertEqual(rights['atlas_material']['license'], 'MIT')
            self.assertFalse(rights['third_party_material']['relicensed_by_atlas'])
        sources = [i for b in survey['blocks'] for i in b['items']]
        sources += [s for r in self.doc['reports'] for s in r['sources']]
        sources += self.doc['uem_studies']
        for source in sources:
            self.assertFalse(source['source_rights']['relicensed_by_atlas'])
            self.assertEqual(source['source_rights']['license_status'], 'not_recorded_in_export')

    def test_ekd_and_fra_use_the_published_subsamples(self):
        survey = json.loads((ROOT / 'docs/data/survey-items.json').read_text())
        blocks = {b['block']: b for b in survey['blocks']}
        b = blocks['ekd2020_muslim_rights']
        self.assertEqual([i['value'] for i in b['items']], [67, 68, 60])
        self.assertEqual([i['base_n'] for i in b['items']], [742, 641, 877])
        self.assertTrue(all(i['field_period'] == 'Mai–Juni 2020' for i in b['items']))
        self.assertIn('mittlere Kategorie', blocks['ekd2020_antisemitic_influence']['note'])
        fra = blocks['fra2017_de_discrimination']
        self.assertEqual([i['value'] for i in fra['items']], [18, 33, 50, 65])
        self.assertIn('nicht alle Musliminnen', fra['note'])
        self.assertIn('Diskriminierungsrisiko', fra['note'])

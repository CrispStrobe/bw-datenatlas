"""Offline consistency tests, not a validation of the source estimates."""
import csv
import hashlib
import io
import json
import re
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

    def test_hero_tiles_match_the_census_file(self):
        """Die Kopfzahlen sind von Hand gesetzt; das hier hält sie an der Quelle fest.

        Sie stehen als Text im HTML, weil sie vor jedem Skript sichtbar sein sollen.
        Genau deshalb können sie unbemerkt von der Datei abweichen, aus der sie stammen
        — der Test rechnet sie nach, statt sie zu wiederholen.
        """
        z = json.loads((ROOT/'docs/data/municipal-religion-2022.json')
                       .read_text(encoding='utf-8'))['state_total']
        html = (ROOT/'docs/index.html').read_text(encoding='utf-8')
        kacheln = re.findall(r'<article class="kpi[^"]*">(.*?)</article>', html, re.S)
        self.assertEqual(len(kacheln), 4)
        def gesetzt(stichwort):
            k = [x for x in kacheln if stichwort in x]
            self.assertEqual(len(k), 1, stichwort)
            return k[0]
        for stichwort, anteil, absolut in (
                ('katholische', 'catholic_pct', 'catholic'),
                ('Evangelische', 'evangelical_pct', 'evangelical'),
                ('Sonstige', 'other_none_unstated_pct', 'other_none_unstated')):
            kachel = gesetzt(stichwort)
            self.assertIn(f'{z[anteil]:.1f}'.replace('.', ','), kachel)
            self.assertIn(f'{z[absolut]/1e6:.2f}'.replace('.', ',') + ' Mio.', kachel)
        # Die drei gezählten Anteile sind die ganze Bevölkerung; wäre das nicht so,
        # stünde neben ihnen eine vierte, ungenannte Gruppe.
        self.assertAlmostEqual(z['catholic_pct'] + z['evangelical_pct']
                               + z['other_none_unstated_pct'], 100, places=1)
        # Und die Schätzung liegt in der Restkategorie, nicht daneben: die Kachel sagt
        # das, und die Zahl erlaubt es auch.
        self.assertIn('enthalten', gesetzt('Sonstige'))
        self.assertLess(10.7, z['other_none_unstated_pct'])

    def test_fundamentalism_block_keeps_its_comparison_and_its_limits(self):
        """Ein Fundamentalismusbalken ohne Vergleichsgruppe wäre eine Anklage.

        Die Studie hat Christen mitbefragt, und genau das macht ihre Zahlen lesbar:
        3 und 4 Prozent neben 30 und 44. Fällt die Vergleichsgruppe weg, bleibt eine
        Grafik über eine Minderheit allein — deshalb steht sie hier als Bedingung.
        """
        d = json.loads((ROOT/'docs/data/survey-items.json').read_text(encoding='utf-8'))
        b = [x for x in d['blocks'] if x['block'] == 'fundamentalismus_sciics']
        self.assertEqual(len(b), 1)
        b = b[0]
        etiketten = ' | '.join(i['label'] for i in b['items'])
        self.assertIn('Katholiken', etiketten)
        self.assertIn('Protestanten', etiketten)
        self.assertIn('Muslime', etiketten)
        # Und die Einschränkung, die den Unterschied zwischen dieser Studie und einer
        # Aussage über „die Muslime in Deutschland" ausmacht.
        self.assertIn('keine Stichprobe der Muslime in Deutschland', b['note'])
        self.assertIn('nicht symmetrisch', b['note'])
        self.assertTrue(all(i['unit'] == 'percent' and 0 <= i['value'] <= 100
                            for i in b['items']))

    def test_konid_blocks_keep_all_four_groups(self):
        """Dieselbe Frage an vier Gruppen — das ist der ganze Wert dieser Erhebung.

        Der KONID-Survey stellt jede der drei Aussagen allen vor: Katholiken,
        Landeskirchen, Freikirchen, Muslimen. Bliebe eine Gruppe weg, wäre aus einem
        Vergleich eine Behauptung über die verbliebenen geworden.
        """
        d = json.loads((ROOT/'docs/data/survey-items.json').read_text(encoding='utf-8'))
        bloecke = [b for b in d['blocks'] if b['block'].startswith('konid_')]
        self.assertEqual(len(bloecke), 3)
        for b in bloecke:
            self.assertEqual([i['label'] for i in b['items']],
                             ['Römisch-katholisch', 'Landeskirchlich evangelisch',
                              'Evangelische Freikirchen', 'Muslimisch'])
            self.assertIn('Minderheiten', b['note'])
            self.assertIn('1,6 Prozent', b['note'])
        # Die Reihenfolge der drei Aussagen steigert sich im Bericht, und die Werte
        # steigern sich nicht mit: Vorrang vor der Verfassung bejahen mehr Freikirchliche
        # als Muslime. Wer nur den Gewaltsatz zitiert, zitiert nicht diese Studie.
        wert = {b['block']: {i['label']: i['value'] for i in b['items']}
                for b in bloecke}
        self.assertGreater(wert['konid_verfassung']['Evangelische Freikirchen'],
                           wert['konid_verfassung']['Muslimisch'])

    def test_zensus2011_religion_is_complete_and_adds_up(self):
        """Die einzige Zählung orthodoxer Christen, die es für dieses Land gibt.

        Sie kommt aus 44 einzeln ausgelesenen PDF-Bänden, und dabei kann viel
        danebengehen. Drei Prüfungen: alle Kreise da, die Kategorien summieren sich
        auf die Einwohnerzahl, und der Landeswert stimmt mit der Summe der Kreise
        überein.
        """
        d = json.loads((ROOT/'docs/data/zensus2011-religion.json').read_text(encoding='utf-8'))
        self.assertEqual(len(d['districts']), 44)
        self.assertEqual(len({x['ags'] for x in d['districts']}), 44)
        felder = list(d['categories'])
        # Was die Geheimhaltung weggenommen hat, steht hier namentlich. Der Datensatz
        # ist abgeschlossen — er kann sich nicht mehr ändern —, also darf der Test
        # exakt sein statt nachsichtig: fällt später ein Wert weg oder kommt einer
        # hinzu, ist die Auslesung kaputt und nicht die Statistik.
        gesperrt = {f: sorted(x['ags'] for x in d['districts'] if x[f] is None)
                    for f in felder}
        self.assertEqual(gesperrt['orthodox'], [])
        self.assertEqual(gesperrt['protestant_free'], ['08211'])   # Baden-Baden
        self.assertGreater(len(gesperrt['jewish']), 30)
        for f in ('roman_catholic', 'protestant', 'other_public_law', 'none'):
            self.assertEqual(gesperrt[f], [], f)
        # Wo nichts gesperrt ist, ergeben die Kreise das Land. Geheimhaltung rundet
        # jeden Einzelwert, ein Promille Abstand ist normal.
        for f in felder:
            summe = sum(x[f] for x in d['districts'] if x[f] is not None)
            if gesperrt[f]:
                self.assertLess(summe, d['state_total'][f], f)
            else:
                self.assertAlmostEqual(summe / d['state_total'][f], 1, places=2, msg=f)
        # Baden-Württemberg lag 2011 über dem Bund — das ist der Grund, warum diese
        # Ebene in diesem Atlas steht, und es soll auffallen, wenn es kippt.
        self.assertGreater(d['state_total']['orthodox'] / sum(
            d['state_total'][f] for f in felder),
            d['germany_total']['orthodox'] / sum(d['germany_total'][f] for f in felder))
        self.assertIn('Körperschaft des öffentlichen Rechts', d['membership_not_belief'])
        self.assertIn('Körperschaft', d['muslims_are_not_a_category_here'])

    def test_zensus2011_csv_matches_the_published_json(self):
        with (ROOT/'inputs/zensus2011-religion-kreise.csv').open(encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        d = json.loads((ROOT/'docs/data/zensus2011-religion.json').read_text(encoding='utf-8'))
        self.assertEqual([r['ags'] for r in rows], [x['ags'] for x in d['districts']])
        for r, x in zip(rows, d['districts']):
            self.assertEqual(int(r['orthodox']), x['orthodox'])
            self.assertEqual(float(r['orthodox_pct']), x['orthodox_pct'])

    def test_zensus2011_citizenship_cross_table(self):
        """Der Satz „Einwanderungskirchen" hängt an dieser einen Kreuztabelle.

        Sie ist zeilenweise aus 44 PDF-Bänden gelesen, und wo die Geheimhaltung zu
        oft zugegriffen hat, darf keine Zahl daraus werden. Beides steht hier fest:
        der Abstand, den die Karte zeigt, und die Lücken, die sie offenlässt.
        """
        d = json.loads((ROOT/'docs/data/zensus2011-religion.json').read_text(encoding='utf-8'))
        c = d['by_citizenship']
        anteil = lambda f: 100 * c[f]['foreign'] / c[f]['total']
        # Orthodox weit über, evangelisch weit unter dem Landesdurchschnitt — das ist
        # die Aussage der Grafik, und sie soll auffallen, wenn sie kippt.
        self.assertGreater(anteil('orthodox'), 50)
        self.assertLess(anteil('protestant'), 5)
        self.assertLess(anteil('roman_catholic'), 15)
        # Zwei Kategorien sind nicht auswertbar, und die Grafik zeigt sie als Lücke.
        # Fiele diese Sperre weg, stünden dort plötzlich Zahlen auf drei Kreisen.
        self.assertGreaterEqual(c['jewish']['foreign_districts_suppressed'], 40)
        self.assertGreaterEqual(c['protestant_free']['foreign_districts_suppressed'], 40)
        for f in ('orthodox', 'roman_catholic'):
            self.assertEqual(c[f]['foreign_districts_suppressed'], 0, f)
            # Die Untergliederung nach Herkunftsgruppen ist viel häufiger gesperrt
            # als die Ausländerzahl selbst; sie ergibt deshalb weniger und nie mehr.
            teile = sum(c[f][k] for k in ('foreign_eu27', 'foreign_other_europe',
                                          'foreign_rest_of_world', 'foreign_unclear'))
            self.assertLessEqual(teile, c[f]['foreign'], f)
            self.assertGreater(teile / c[f]['foreign'], 0.9, f)
            # Und die Kreuztabelle zählt dieselben Menschen wie die Haupttabelle.
            self.assertAlmostEqual(c[f]['total'] / d['state_total'][f], 1, places=3)
        self.assertIn('Pass, nicht die Herkunft', d['what_citizenship_shows'])

if __name__=='__main__': unittest.main(verbosity=2)

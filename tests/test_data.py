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

    def test_zensus2011_age_bounds_survive_the_secrecy(self):
        """Die Altersaussage muss auch am ungünstigen Rand der Sperre noch gelten.

        Bei den orthodoxen Kirchen fehlt die Klasse 65 und älter in 23 von 44
        Kreisen. Der gezählte Anteil ist deshalb zu niedrig, und die Obergrenze —
        alle nicht zugeordneten Personen wären über 65 — ist die Probe: liegt die
        noch deutlich unter dem evangelischen Wert, trägt der Satz in der
        Überschrift.
        """
        d = json.loads((ROOT/'docs/data/zensus2011-religion.json').read_text(encoding='utf-8'))
        a = d['by_age']
        for f, e in a.items():
            if not e['total']:
                continue
            self.assertLessEqual(e['a65_plus_pct_low'], e['a65_plus_pct_high'], f)
            # Die Geheimhaltung rundet jeden Einzelwert, und die Quelle sagt
            # selbst, dass Teilsummen deshalb von der Gesamtzahl abweichen
            # können — bei den Katholiken um 140 von 3,9 Millionen nach oben.
            self.assertLess(abs(e['assigned'] + e['unassigned'] - e['total'])
                            / e['total'], 0.001, f)
        for f in ('roman_catholic', 'protestant', 'none'):
            self.assertEqual(a[f]['unassigned'], 0, f)
            self.assertEqual(a[f]['a65_plus_pct_low'], a[f]['a65_plus_pct_high'], f)
        self.assertLess(a['orthodox']['a65_plus_pct_high'],
                        a['protestant']['a65_plus_pct_low'] / 1.8)
        self.assertLess(a['orthodox']['a65_plus_pct_high'], 12.5)

    def test_state_survey_blocks_are_about_immigration_not_religion(self):
        """Zwei Blöcke aus dem Landesbericht fragen nach Zuwanderern, nicht nach Religion.

        Das ist genau die Verwechslung, gegen die dieser Atlas gebaut ist, also muss
        sie an den Blöcken stehen — samt dem Wortlaut, mit dem die Erhebung den
        Begriff erklärt hat.
        """
        d = json.loads((ROOT/'docs/data/survey-items.json').read_text(encoding='utf-8'))
        bloecke = {b['block']: b for b in d['blocks']}
        for name in ('bw_integration_bewertung', 'bw_integration_erwartung'):
            b = bloecke[name]
            self.assertIn('Zuwanderer', b['note'])
            self.assertTrue(all(i['base_n'] == 1587 for i in b['items']), name)
            self.assertTrue(all(i['study'] == 'Integration unter Druck? 2019'
                                for i in b['items']), name)
        self.assertIn('nicht Religion, sondern Einwanderung',
                      bloecke['bw_integration_bewertung']['note'])
        # Die Antwortkategorien einer Frage ergeben zusammen höchstens 100 Prozent;
        # der Rest sind die, die nicht geantwortet haben.
        werte = {i['label']: i['value']
                 for i in bloecke['bw_integration_bewertung']['items']}
        for ort in ('Im Land', 'Am Wohnort'):
            summe = sum(v for k, v in werte.items() if k.startswith(ort))
            self.assertLessEqual(summe, 100, ort)
            self.assertGreater(summe, 80, ort)
        # Und der Befund, der den Block trägt: am eigenen Wohnort fällt das Urteil
        # besser aus als über das Land.
        self.assertGreater(werte['Am Wohnort: sehr gut gelungen']
                           + werte['Am Wohnort: gut gelungen'],
                           werte['Im Land: sehr gut gelungen']
                           + werte['Im Land: gut gelungen'])

    def test_every_survey_block_says_which_area_it_covers(self):
        """Ein Wert aus sechs Ländern darf sich nicht wie einer über dieses Land lesen.

        Bei zehn Blöcken sieht man das dem Titel nicht mehr an, also trägt jeder
        Block sein Gebiet — im Auswahlfeld als Gruppe, im Kopf als erste Angabe.
        """
        d = json.loads((ROOT/'docs/data/survey-items.json').read_text(encoding='utf-8'))
        raeume = d['scope_order']
        for b in d['blocks']:
            self.assertIn(b['scope'], raeume, b['block'])
        # Und die Reihenfolge folgt den Gebieten, Landesbezug zuerst.
        rang = [raeume.index(b['scope']) for b in d['blocks']]
        self.assertEqual(rang, sorted(rang))
        self.assertEqual(d['blocks'][0]['scope'], 'Baden-Württemberg')

    def test_religion_change_joins_and_adds_up(self):
        """Zwei Zählungen, elf Jahre auseinander, auf demselben Gebietsstand.

        Die Aussage steht und fällt damit, dass beide Jahre dieselben Gemeinden
        meinen. Beide Blätter derselben Veröffentlichung tragen dieselben 1.101
        Schlüssel; hier wird geprüft, dass die Umrechnung vom Regionalschlüssel auf
        den amtlichen Gemeindeschlüssel jede davon trifft.
        """
        d = json.loads((ROOT/'docs/data/religion-change-2011-2022.json')
                       .read_text(encoding='utf-8'))
        m = d['municipalities']
        self.assertEqual(len(m), 1101)
        g = json.loads((ROOT/'docs/data/geometry.json').read_text(encoding='utf-8'))
        schluessel = {c['ags'] for c in g['crosswalk']}
        self.assertEqual(schluessel - set(m), set())
        for ags, z in m.items():
            self.assertEqual(ags, z['regional_key'][:5] + z['regional_key'][-3:])
            self.assertAlmostEqual(
                z['both_churches_change'],
                z['both_churches_pct_2022'] - z['both_churches_pct_2011'], places=0)
        # Der Landesbefund, an dem die Karte hängt.
        st = d['state_total']
        self.assertAlmostEqual(st['both_churches_pct_2022'], 55.8, places=1)
        self.assertLess(st['both_churches_change'], -12)
        # Und die Kennzeichnung, die die Statistischen Ämter verlangen.
        self.assertIn('Eigenständige Berechnung', d['own_calculation'])
        self.assertIn('Kirchenaustritte', d['what_it_does_not_say'])

    def test_source_archives_separate_absence_from_failure(self):
        """„Nicht archiviert" und „Abfrage fehlgeschlagen" sind nicht dasselbe.

        Der erste Lauf meldete null von siebenundsechzig, weil archive.org
        durchgehend mit 429 antwortete und ein except das in „kein Schnappschuss"
        übersetzt hat — ein Ausfall der Messung, der wie ein Messergebnis aussah.
        Die Datei muss beides auseinanderhalten, und sie darf nicht veröffentlicht
        werden, solange nur Fehlschläge darinstehen.
        """
        d = json.loads((ROOT/'docs/data/source-archives.json').read_text(encoding='utf-8'))
        self.assertEqual(d['count'],
                         len(d['archives']) + len(d['without_snapshot']))
        self.assertEqual(d['with_snapshot'], len(d['archives']))
        fehlgeschlagen = [x for x in d['without_snapshot'] if x.get('lookup_failed')]
        self.assertEqual(fehlgeschlagen, [], 'Abfragen fehlgeschlagen, nicht leer')
        # Ein Lauf, der fast nichts findet, ist eher gedrosselt als aufschlussreich.
        self.assertGreater(d['with_snapshot'] / d['count'], 0.5)
        for url, a in d['archives'].items():
            self.assertTrue(a['url'].startswith('https://web.archive.org/web/'))
            self.assertRegex(a['captured'], r'^\d{4}-\d{2}-\d{2}$')
        self.assertIn('Abgefragt, nicht archiviert', d['not_an_archiving_run'])

    def test_cohesion_block_carries_the_reports_own_caveat(self):
        """Der niedrigste Wert der Studie ist der, den sie selbst einschränkt.

        Der Religionsmonitor 2026 misst für muslimische Befragte 46 Punkte und
        schreibt ausdrücklich dazu, das dürfe „keineswegs mit einer grundsätzlich
        geringeren Bereitschaft zu gesellschaftlichem Engagement und Solidarität
        gleichgesetzt werden". Wer die Zahl ohne diesen Satz zeigt, zeigt etwas
        anderes als die Studie.
        """
        d = json.loads((ROOT/'docs/data/survey-items.json').read_text(encoding='utf-8'))
        b = [x for x in d['blocks'] if x['block'] == 'rm2026_zusammenhalt'][0]
        self.assertIn('keineswegs', b['note'])
        self.assertIn('kein Prozentwert', b['note'])
        werte = {i['label']: i['value'] for i in b['items']}
        self.assertEqual(werte['Muslimisch'], 46)
        self.assertEqual(werte['Evangelisch'], 55)
        # Ein Index ist keine Quote; die Einheit entscheidet über die Beschriftung.
        self.assertTrue(all(i['unit'] == 'index' for i in b['items']))
        self.assertTrue(all(i['base_n'] == 5231 for i in b['items']))

    def test_checked_and_not_used_gives_a_reason_and_a_date(self):
        """Eine Absage ohne Grund ist keine Auskunft, und ohne Datum altert sie still.

        Eine Tabelle, die heute mit HTTP 400 antwortet, kann nächstes Jahr antworten;
        eine Studie kann einen Ergänzungsband bekommen. Wer das nachliest, muss
        wissen, wann geprüft wurde.
        """
        d = json.loads((ROOT/'docs/data/checked-not-used.json').read_text(encoding='utf-8'))
        self.assertGreaterEqual(d['count'], 4)
        for e in d['entries']:
            self.assertTrue(e['quelle'])
            self.assertGreater(len(e['warum_nicht']), 60, e['quelle'])
            self.assertRegex(e['geprueft_am'], r'^\d{4}-\d{2}-\d{2}$')
        # Die KMU 6 ist mit dem Satz abgelehnt, den sie selbst über sich schreibt.
        kmu = [e for e in d['entries'] if 'KMU 6' in e['quelle']]
        self.assertEqual(len(kmu), 1)
        self.assertIn('zu wenige in der Stichprobe', kmu[0]['warum_nicht'])
        # Abgelehnt ist eine Frage, nicht die Quelle: dieselbe Studie trägt zwei
        # Blöcke im Befragungsteil. Stünde sie hier pauschal als unbrauchbar,
        # widerspräche der Atlas sich selbst.
        umfragen = json.loads(
            (ROOT/'docs/data/survey-items.json').read_text(encoding='utf-8'))
        aus_kmu = [b for b in umfragen['blocks']
                   if any('KMU 6' in i['study'] for i in b['items'])]
        self.assertTrue(aus_kmu, 'KMU 6 wird nirgends verwendet')
        self.assertIn('nicht eine Quelle', kmu[0]['warum_nicht'])

    def test_bosch_and_evs_keep_methods_and_question_wording_separate(self):
        d = json.loads((ROOT/'docs/data/survey-items.json').read_text())
        blocks = {b['block']: b for b in d['blocks']}
        bw = blocks['bosch2025_index_bw']
        self.assertEqual([i['value'] for i in bw['items']], [68, 62, 74, 58, 44, 35])
        self.assertTrue(all(i['unit'] == 'index' and i['base_n'] is None
                            for i in bw['items']))
        self.assertIn('2018', bw['note'])
        self.assertIn('Methodeneffekte', bw['note'])
        neighbours = blocks['bosch2025_nachbarn']
        self.assertEqual([i['value'] for i in neighbours['items']], [19, 30, 50])
        # The repeated general religion proxy is not a group-specific rejection.
        self.assertIn('keine drei gemessenen Gruppenurteile', neighbours['note'])
        self.assertEqual([i['value'] for i in blocks['bosch2025_religion']['items']],
                         [22, 24, 50])
        self.assertIn('bleiben im Nenner', blocks['bosch2025_religion']['note'])
        evs = blocks['evs2017_nachbarn']
        self.assertEqual([i['value'] for i in evs['items']], [1.7, 4.3, 13.8])
        self.assertTrue(all(i['base_n'] == 2170 and i['question_ref']
                            and 'valid_n' not in i and 'weighted_valid_n' not in i
                            and i['source_kind'] == 'published_table' for i in evs['items']))
        self.assertIn('keine direkten Niveauvergleiche', evs['note'])
        for i in evs['items']:
            self.assertIn('access.gesis.org/dbk/65190#page=', i['source_url'])
            self.assertEqual(i['field_period'], '2017–2018')

    def test_evs_public_tables_keep_rounding_and_source_denominators(self):
        d = json.loads((ROOT/'docs/data/survey-items.json').read_text())
        blocks = {b['block']: b for b in d['blocks']}
        religion = blocks['evs2017_religion']['items']
        self.assertEqual([i['value'] for i in religion], [54.6, 63.4, 37.7])
        beliefs = blocks['evs2017_gottesvorstellungen']['items']
        self.assertAlmostEqual(sum(i['value'] for i in beliefs), 100, places=8)
        self.assertEqual([i['value'] for i in beliefs], [23.5, 40.3, 13.5, 22.7])
        evs_items = [i for b in d['blocks'] if b['block'].startswith('evs2017_') for i in b['items']]
        self.assertEqual(len(evs_items), 17)
        self.assertTrue(all('valid_n' not in i and 'weighted_valid_n' not in i for i in evs_items))
        self.assertIn('Ungewichtete gültige Fallzahlen', blocks['evs2017_gottesvorstellungen']['note'])

    def test_panel_attitudes_keep_randomised_wording_and_unknown_item_counts(self):
        d = json.loads((ROOT/'docs/data/survey-items.json').read_text())
        blocks = {b['block']: b for b in d['blocks']}
        compare = blocks['rm2023_zuschreibungen']
        self.assertEqual([i['value'] for i in compare['items']],
                         [66, 58, 57, 45, 75, 65, 74, 56])
        self.assertIn('zufällig auf zwei Befragtengruppen', compare['note'])
        self.assertIn('keine Eigenschaften', compare['note'])
        self.assertIn('1.912', compare['note'])
        for i in compare['items']:
            self.assertIsNone(i['base_n'])
            self.assertEqual(i['field_period'], 'Juni–Juli 2022')
            self.assertIn('Nichtmuslimische', i['population'])
            self.assertIn('Online-Access-Panel', i['population'])
            self.assertIsNone(i['question_ref'])
        counter = blocks['rm2023_differenzierung']
        # Rounded category sums are retained, not normalised to 100 or silently
        # replaced by a number derived from unpublished unrounded responses.
        self.assertEqual([i['value'] for i in counter['items']], [83, 85, 60, 69])
        self.assertIn('keine Diskriminierungserfahrungen', counter['note'])
        self.assertIn('gerundeter Kategorien', counter['note'])

    def test_religionsmonitor_figures_keep_distinct_items_and_missing_values(self):
        d = json.loads((ROOT/'docs/data/survey-items.json').read_text())
        blocks = {b['block']: b for b in d['blocks']}
        dogma = blocks['rm2013_dogmatismus']
        self.assertEqual({i['label']: i['value'] for i in dogma['items']},
                         {'Katholisch': 12, 'Evangelisch': 11, 'Muslimisch': 39})
        self.assertNotIn('Konfessionslos', [i['label'] for i in dogma['items']])
        rules = blocks['rm2017_regeln']
        self.assertEqual(next(i['value'] for i in rules['items']
                              if i['label'] == 'Sunniten'), 40)
        self.assertTrue(all(i['base_n'] is None for i in rules['items']))
        self.assertIn('überschneiden', rules['note'])
        self.assertIn('Oktober', dogma['items'][0]['field_period'])

    def test_religionsmonitor_cohesion_separates_dimensions_and_wave_samples(self):
        d = json.loads((ROOT/'docs/data/survey-items.json').read_text())
        blocks = {b['block']: b for b in d['blocks']}
        connection = blocks['rm2026_detail_verbundenheit']
        common_good = blocks['rm2026_detail_gemeinwohl']
        high = 'Muslimisch · Religiosität hoch'
        self.assertEqual(next(i['value'] for i in connection['items'] if i['label'] == high), 28)
        self.assertEqual(next(i['value'] for i in common_good['items'] if i['label'] == high), 52)
        self.assertTrue(all(i['unit'] == 'index' and i['base_n'] is None
                            for i in connection['items']))
        history = blocks['rm2026_history']['items']
        self.assertEqual([(i['label'], i['value'], i['base_n']) for i in history],
                         [('2017', 54, 4968), ('2020', 55, 3010),
                          ('2023', 46, 5004), ('2026', 51, 5231)])
        dimensions = blocks['rm2026_dimensions']
        self.assertIn('abweichend 67', dimensions['note'])

    def test_religionsmonitor_download_inventory_distinguishes_reviews(self):
        d = json.loads((ROOT/'inputs/religionsmonitor-publications.json').read_text())
        self.assertFalse(d['catalog_failures'])
        self.assertGreaterEqual(len(d['publications']), 40)
        self.assertTrue(all(p['status'] == 'downloaded' and len(p['sha256']) == 64
                            for p in d['publications']))
        reviewed = [p for p in d['publications'] if p['review_status'] != 'not_reviewed']
        self.assertGreaterEqual(len(reviewed), 6)
        self.assertTrue(all(p['reviewed_pages'] and p['used_blocks'] for p in reviewed))
        self.assertEqual(d, json.loads((ROOT/'docs/data/religionsmonitor-publications.json').read_text()))

    def test_solidarity_and_conspiracy_keep_population_and_fieldwork_distinct(self):
        d = json.loads((ROOT/'docs/data/survey-items.json').read_text())
        blocks = {b['block']: b for b in d['blocks']}
        syria = blocks['rm2023_hilfe_syrien']['items']
        ukraine = blocks['rm2023_hilfe_ukraine']['items']
        self.assertEqual([i['value'] for i in syria], [73, 88, 67, 73])
        self.assertEqual([i['value'] for i in ukraine], [82, 72, 76, 79])
        self.assertTrue(all(i['base_n'] is None for i in syria + ukraine))
        international = blocks['rm2023_verschwoerung_anfaellig']['items']
        self.assertEqual([i['base_n'] for i in international],
                         [4363, 1051, 1045, 1065, 1046, 1046, 1041])
        self.assertNotIn('Internetzugang', international[0]['population'])
        self.assertTrue(all('Internetzugang' in i['population'] for i in international[1:]))
        self.assertTrue(all(i['field_period'] == 'Juni bis Juli 2022' for i in international))
        religiosity = blocks['rm2023_verschwoerung_religioes']
        self.assertEqual([i['value'] for i in religiosity['items']], [13, 18, 21])
        self.assertIn('nicht den Anteil', religiosity['note'])
        self.assertIn('Teil der ersten', religiosity['note'])

    def test_islam_special_analysis_keeps_two_surveys_and_explicit_zero(self):
        d = json.loads((ROOT/'docs/data/survey-items.json').read_text())
        blocks = {b['block']: b for b in d['blocks']}
        muslim = blocks['rm2015_freizeit_muslime']['items']
        nonmuslim = blocks['rm2015_freizeit_nichtmuslime']['items']
        self.assertEqual([i['value'] for i in muslim], [8, 30, 29, 24, 8])
        self.assertEqual([i['value'] for i in nonmuslim], [63, 33, 3, 1, 0])
        self.assertTrue(all(i['base_n'] == 322 and '2012' in i['field_period'] for i in muslim))
        self.assertTrue(all(i['base_n'] == 937 and '2014' in i['field_period'] for i in nonmuslim))
        comparison = blocks['rm2015_islamwahrnehmung_vergleich']['items']
        self.assertEqual([i['base_n'] for i in comparison], [1683, 937, 1683, 937])

    def test_europe_survey_distinguishes_generations_and_work_denominators(self):
        d = json.loads((ROOT/'docs/data/survey-items.json').read_text())
        blocks = {b['block']: b for b in d['blocks']}
        language = blocks['rm2017_europa_sprache']
        self.assertEqual([i['value'] for i in language['items'][:3]], [23, 73, 46])
        self.assertIn('keine Messung heutiger Sprachkenntnisse', language['note'])
        self.assertTrue(all(i['base_n'] is None for i in language['items']))
        unemployment = blocks['rm2017_europa_arbeitslos']
        self.assertEqual([i['value'] for i in unemployment['items'][:2]], [5, 7])
        self.assertIn('keine amtliche Arbeitslosenquote', unemployment['note'])
        self.assertTrue(all('16 bis 65' in i['population'] and 'Ausbildung' in i['population']
                            for i in unemployment['items']))
        self.assertIn('Fluchtmigration', language['note'])

    def test_pandemic_derived_totals_preserve_rounding_and_source_discrepancies(self):
        d = json.loads((ROOT/'docs/data/survey-items.json').read_text())
        self.assertTrue(all(not i['question_ref'] or
                            not i['question_ref'].startswith(('Abbildung ', 'Tabelle '))
                            for b in d['blocks'] for i in b['items']))
        blocks = {b['block']: b for b in d['blocks']}
        domains = blocks['rm2023_pandemie_bereiche']
        self.assertEqual([i['value'] for i in domains['items']], [90, 85, 81, 74, 48, 29])
        self.assertIn('abweichend 30', domains['note'])
        groups = blocks['rm2023_pandemie_religion']
        self.assertIn('4.338', groups['note'])
        self.assertTrue(all(i['base_n'] is None for i in groups['items']))
        narratives = blocks['rm2023_pandemie_deutung']
        self.assertEqual([i['value'] for i in narratives['items']], [20, 10])
        self.assertIn('nicht dieselbe Messung', narratives['note'])

if __name__=='__main__': unittest.main(verbosity=2)

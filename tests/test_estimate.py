#!/usr/bin/env python3
"""Checks on the modelled district and municipal estimates.

These guard the properties that make the model defensible: it never invents a total,
it never uses a parameter the source review blocked, and it never presents a value
outside its own stated uncertainty.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / 'docs/data' / name).read_text(encoding='utf-8'))


class TestParameters(unittest.TestCase):
    def setUp(self):
        self.params = json.loads(
            (ROOT / 'inputs/muslim-shares-fb55-table2.json').read_text(encoding='utf-8'))

    def test_all_eighteen_origin_groups_present(self):
        self.assertEqual(len(self.params['origin_groups']), 18)

    def test_no_blocked_parameter_is_shipped(self):
        for g in self.params['origin_groups']:
            self.assertNotIn('no_automatic_parameter_use', g.get('quality_flags') or [],
                             f'{g["origin_group"]} is blocked and must not be usable')

    def test_shares_are_percentages(self):
        for g in self.params['origin_groups']:
            self.assertTrue(0 < g['share_percent'] <= 100, g)

    def test_table_one_values_are_not_used(self):
        """The five transposed Table 1 cells must not appear as Table 2 values."""
        shares = {g['origin_group']: g['share_percent'] for g in self.params['origin_groups']}
        self.assertAlmostEqual(shares['Irak'], 37.4, places=1)
        self.assertAlmostEqual(shares['Syrien'], 86.5, places=1)


class TestDistrictEstimate(unittest.TestCase):
    def setUp(self):
        self.data = load('district-estimate.json')
        self.districts = self.data['districts']

    def test_declares_itself_a_model(self):
        self.assertTrue(self.data['is_model_not_measurement'])

    def test_all_districts_present(self):
        self.assertEqual(len(self.districts), 44)
        self.assertEqual(len({d['id'] for d in self.districts}), 44)

    def test_each_variant_sums_to_the_published_total(self):
        low = self.data['state_total']['persons_low']
        high = self.data['state_total']['persons_high']
        for name in ('citizenship', 'migration_background'):
            s_low = sum(d['variants'][name]['persons_low'] for d in self.districts)
            s_high = sum(d['variants'][name]['persons_high'] for d in self.districts)
            self.assertAlmostEqual(s_low, low, delta=50, msg=name)
            self.assertAlmostEqual(s_high, high, delta=50, msg=name)

    def test_combined_band_contains_every_variant(self):
        for d in self.districts:
            for v in d['variants'].values():
                self.assertGreaterEqual(v['persons_low'], d['combined_low_persons'])
                self.assertLessEqual(v['persons_high'], d['combined_high_persons'])

    def test_naturalisation_ratios_are_at_least_one(self):
        """A ratio below 1 would mean fewer people of an origin than passports of it."""
        for group, r in self.data['naturalisation_ratios'].items():
            self.assertGreaterEqual(r['ratio'], 1.0, group)
            self.assertLess(r['ratio'], 4.0, group)

    def test_fallback_ratios_are_declared(self):
        for group, r in self.data['naturalisation_ratios'].items():
            self.assertIn(r['basis'], {'published_for_this_origin',
                                       'fallback_non_eu_europe_aggregate'}, group)

    def test_coverage_is_reported_and_incomplete(self):
        c = self.data['coverage']
        self.assertLess(c['share_of_published_low_percent'], 100)
        self.assertGreater(c['corrected_share_of_published_low_percent'],
                           c['share_of_published_low_percent'])

    def test_limitations_are_not_empty(self):
        self.assertGreaterEqual(len(self.data['limitations']), 5)


class TestMunicipalEstimate(unittest.TestCase):
    def setUp(self):
        self.data = load('municipal-estimate.json')
        self.rows = self.data['municipalities']
        self.district = load('district-estimate.json')

    def test_declares_itself_a_downscale(self):
        self.assertTrue(self.data['is_model_not_measurement'])
        self.assertTrue(self.data['is_downscale_of_district_model'])

    def test_all_municipalities_present(self):
        self.assertEqual(len(self.rows), 1101)
        self.assertEqual(len({m['geo_id'] for m in self.rows}), 1101)

    def test_central_value_lies_inside_its_band(self):
        for m in self.rows:
            if m['percent_central'] is None:
                continue
            self.assertLessEqual(m['percent_low'], m['percent_central'], m['name'])
            self.assertLessEqual(m['percent_central'], m['percent_high'], m['name'])

    def test_central_values_sum_to_the_published_midpoint(self):
        total = self.district['state_total']
        midpoint = (total['persons_low'] + total['persons_high']) / 2
        self.assertAlmostEqual(sum(m['persons_central'] for m in self.rows),
                               midpoint, delta=2000)

    def test_remainder_follows_immigration_history_not_headcount(self):
        """Origins without municipal data must not be spread evenly by population."""
        keys = {m['remainder_key'] for m in self.rows}
        self.assertEqual(keys, {'immigration_history'},
                         'the remainder fell back to population somewhere')

    def test_origin_pattern_never_carries_the_whole_district(self):
        """Origins with no municipal data must not follow the Turkish pattern."""
        for m in self.rows:
            self.assertLess(m['grid_fraction_of_district'], 1.0, m['name'])
            self.assertGreater(m['grid_fraction_of_district'], 0.0, m['name'])

    def test_states_which_origins_are_missing(self):
        missing = self.data['grid_source']['countries_not_in_this_grid']
        for country in ('Syrien', 'Afghanistan', 'Irak', 'Kosovo'):
            self.assertIn(country, missing)

    def test_inherits_district_limitations(self):
        for limitation in self.district['limitations']:
            self.assertIn(limitation, self.data['limitations'])


class TestSocioeconomicContext(unittest.TestCase):
    def setUp(self):
        self.data = load('district-socioeconomics-2024.json')

    def test_all_districts_present(self):
        self.assertEqual(len(self.data['districts']), 44)

    def test_declares_it_is_not_part_of_the_religion_model(self):
        self.assertIn('nicht in die Modellrechnung', self.data['not_used_for_religion_model'])

    def test_no_unemployment_rate_is_derived(self):
        self.assertIn('Erwerbslosenquote wird nicht gebildet', self.data['no_unemployment_rate'])
        for d in self.data['districts']:
            for key in ('with_migration_background', 'without_migration_background'):
                self.assertNotIn('unemployment_rate', d[key])

    def test_shares_are_plausible(self):
        for d in self.data['districts']:
            for key in ('with_migration_background', 'without_migration_background'):
                s = d[key]['employed_share_percent']
                if s is not None:
                    self.assertTrue(20 < s < 90, f'{d["name"]}: {s}')

    def test_suppressed_education_is_flagged_not_guessed(self):
        for d in self.data['districts']:
            for key in ('with_migration_background', 'without_migration_background'):
                block = d[key]
                if block['education_incomplete']:
                    self.assertIn(None, block['education_thousand'].values())


class TestAgeStructure(unittest.TestCase):
    def setUp(self):
        self.data = load('district-age-2024.json')

    def test_all_districts_present(self):
        self.assertEqual(len(self.data['districts']), 44)

    def test_it_is_not_sold_as_a_muslim_age_structure(self):
        self.assertIn('nicht die der modellierten muslimischen Bevölkerung',
                      self.data['not_a_muslim_age_structure'])

    def test_shares_are_withheld_when_coverage_is_poor(self):
        """A share built from half the age groups must not be published."""
        floor = self.data['minimum_coverage_for_shares_percent']
        for d in self.data['districts']:
            for key in ('with_migration_background', 'without_migration_background'):
                block = d[key]
                if block['shares_reportable']:
                    self.assertTrue(block['complete'] or
                                    (block['coverage_of_total_percent'] or 0) >= floor,
                                    f'{d["name"]}/{key}')
                else:
                    self.assertIsNone(block['under_25_share_of_covered_percent'], f'{d["name"]}/{key}')

    def test_suppressed_groups_stay_none(self):
        for d in self.data['districts']:
            for key in ('total', 'with_migration_background'):
                for name in d[key]['suppressed_groups']:
                    self.assertIsNone(d[key]['age_groups_thousand'][name])

    def test_migration_background_is_younger(self):
        """The documented contrast: a sanity check, not a claim about Muslims."""
        pairs = [(d['with_migration_background']['under_25_share_of_covered_percent'],
                  d['without_migration_background']['under_25_share_of_covered_percent'])
                 for d in self.data['districts']]
        pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
        self.assertGreater(len(pairs), 20)
        self.assertTrue(all(a > b for a, b in pairs))


class TestGenerations(unittest.TestCase):
    def setUp(self):
        self.data = load('district-generations-2024.json')
        self.estimate = load('district-estimate.json')

    def test_all_districts_present(self):
        self.assertEqual(len(self.data['districts']), 44)

    def test_migration_background_never_below_foreign_citizens(self):
        """The invisible group cannot be negative; that would break the correction."""
        for d in self.data['districts']:
            self.assertGreater(d['invisible_to_citizenship_persons'], 0, d['name'])

    def test_second_generation_is_a_large_part_of_the_invisible_group(self):
        shares = [d['second_generation_share_of_invisible_percent'] for d in self.data['districts']
                  if d['second_generation_share_of_invisible_percent'] is not None]
        self.assertGreater(len(shares), 30)
        for s in shares:
            self.assertTrue(30 < s < 100, s)

    def test_it_independently_supports_the_naturalisation_correction(self):
        """The model's uplift must not exceed what the invisible population allows.

        The correction multiplies citizenship counts by roughly 1.8 overall. The
        Mikrozensus says the population with migration background is about 1.95 times
        the foreign population, so the model's uplift has to sit below that.
        """
        coverage = self.estimate['coverage']
        uplift = (coverage['explained_with_naturalisation_persons']
                  / coverage['explained_by_citizenship_persons'])
        mh = sum(d['migration_background_thousand'] for d in self.data['districts']
                 if not d['shared_region'])
        mh += next(d['migration_background_thousand'] for d in self.data['districts']
                   if d['shared_region'])
        foreign = sum(d['foreign_citizens_persons'] for d in self.data['districts']
                      if not d['shared_region'])
        foreign += next(d['foreign_citizens_persons'] for d in self.data['districts']
                        if d['shared_region'])
        observed = mh * 1000 / foreign
        self.assertGreater(uplift, 1.0)
        self.assertLess(uplift, observed,
                        f'model uplift {uplift:.2f} exceeds the observed {observed:.2f}')

    def test_marital_status_is_context_only(self):
        self.assertIn('kein Merkmal der Religionszugehörigkeit',
                      self.data['not_used_for_religion_model'])

    def test_suppressed_marital_categories_stay_none(self):
        for d in self.data['districts']:
            shares = d['marital_status_share_percent'] or {}
            for k, v in d['marital_status_thousand'].items():
                if v is None:
                    self.assertIsNone(shares.get(k), f'{d["name"]}/{k}')


class TestCensusUpperBound(unittest.TestCase):
    def setUp(self):
        self.data = load('municipal-religion-bound.json')

    def test_every_municipality_is_checked(self):
        self.assertEqual(self.data['municipalities_checked'], 1101)

    def test_no_modelled_value_exceeds_what_the_census_allows(self):
        self.assertEqual(self.data['central_violations'], 0)
        self.assertEqual(self.data['upper_bound_violations'], 0)

    def test_the_residual_is_not_presented_as_a_muslim_share(self):
        self.assertIn('nicht als Muslimanteil gelesen', self.data['not_a_muslim_share'])
        self.assertIn('Islam ist keine eigene Kategorie', self.data['what_the_census_publishes'])

    def test_bound_actually_constrains_somewhere(self):
        """A ceiling that never binds anywhere would not be worth publishing."""
        headroom = [m['headroom_points'] for m in self.data['municipalities']
                    if m['headroom_points'] is not None]
        self.assertTrue(any(h < 10 for h in headroom))


class TestTimeseries(unittest.TestCase):
    def setUp(self):
        self.data = load('district-timeseries.json')

    def test_all_districts_and_years(self):
        self.assertEqual(len(self.data['districts']), 44)
        self.assertEqual(self.data['years'], ['2021', '2022', '2023', '2024', '2025'])

    def test_the_model_is_not_projected_backwards(self):
        self.assertIn('nicht in die Vergangenheit', self.data['no_modelled_backcast'])

    def test_sampling_caveat_is_stated(self):
        self.assertIn('Zufallsfehler', self.data['sampling_note'])

    def test_shares_are_plausible_in_every_year(self):
        for d in self.data['districts']:
            for year, v in d['series'].items():
                s = v['share_percent']
                if s is not None:
                    self.assertTrue(5 < s < 80, f'{d["name"]} {year}: {s}')


class TestModelIndependence(unittest.TestCase):
    def test_socioeconomics_do_not_feed_the_estimate(self):
        """Education and employment must never become predictors of religion."""
        source = (ROOT / 'scripts/build_estimate.py').read_text(encoding='utf-8')
        municipal = (ROOT / 'scripts/build_municipal_estimate.py').read_text(encoding='utf-8')
        for text in (source, municipal):
            self.assertNotIn('socioeconomics', text)
            self.assertNotIn('education', text)
            self.assertNotIn('employed', text)


class TestStateAgePyramid(unittest.TestCase):
    def setUp(self):
        self.data = load('state-age-pyramid-2025.json')

    def test_all_age_groups_present(self):
        self.assertEqual(len(self.data['pyramid']), 18)

    def test_classification_difference_is_stated(self):
        self.assertIn('NICHT dasselbe wie Migrationshintergrund',
                      self.data['classification_note'])

    def test_it_is_not_part_of_the_religion_model(self):
        self.assertIn('nicht in die Modellrechnung', self.data['not_a_religion_dataset'])

    def test_suppressed_cells_stay_none(self):
        for row in self.data['pyramid']:
            for sex in ('Männlich', 'Weiblich'):
                for key, v in row[sex].items():
                    if v is None:
                        self.assertIn({'age_group': row['age_group'], 'sex': sex,
                                       'category': {'without': 'ohne Einwanderungsgeschichte',
                                                    'one_parent': 'mit einseitiger Einwanderungsgeschichte',
                                                    'with': 'mit Einwanderungsgeschichte'}[key]},
                                      self.data['suppressed_cells'])

    def test_immigration_history_population_is_younger(self):
        u = self.data['under_25_share_percent']
        self.assertGreater(u['mit Einwanderungsgeschichte'], u['ohne Einwanderungsgeschichte'])

    def test_totals_are_not_mixed_with_migration_background(self):
        """The pyramid must not be built from the migration-background files."""
        src = (ROOT / 'scripts/prepare_state_age_pyramid.py').read_text(encoding='utf-8')
        self.assertNotIn('district-migration', src)
        self.assertNotIn('12211-0503', src)


class TestDataBases(unittest.TestCase):
    """The site must say what kind of source each figure rests on."""

    def setUp(self):
        self.data = load('bases.json')

    def test_every_entry_declares_its_kind(self):
        kinds = set(self.data['kinds'])
        self.assertTrue(self.data['entries'])
        for e in self.data['entries']:
            self.assertIn(e['kind'], kinds, e['measure'])
            self.assertTrue(e['reference'], e['measure'])
            self.assertTrue(e['used_for'], e['measure'])

    def test_both_foreign_counts_are_shown_and_reconciled(self):
        f = self.data['two_foreign_counts']
        self.assertNotEqual(f['fortschreibung_persons'], f['register_persons'])
        self.assertEqual(f['difference_persons'],
                         f['register_persons'] - f['fortschreibung_persons'])
        self.assertIn('methodischer und zeitlicher Unterschiede', f['explanation'])

    def test_the_two_counts_match_the_actual_data(self):
        atlas = load('atlas.json')
        origins = load('district-origins-2024-12.json')
        self.assertEqual(self.data['two_foreign_counts']['fortschreibung_persons'],
                         sum(d['foreign'] for d in atlas['districts']))
        self.assertEqual(self.data['two_foreign_counts']['register_persons'],
                         sum(d['foreign_total'] for d in origins['districts']))

    def test_denominator_difference_is_stated(self):
        self.assertIn('Hauptwohnsitzhaushalte', self.data['denominator_note'])
        self.assertIn('Fortschreibung', self.data['denominator_note'])

    def test_federal_cross_check_is_honest_about_its_limits(self):
        fx = self.data['federal_cross_check']
        self.assertLess(abs(fx['population_difference_percent']), 1.0)
        self.assertIn('NICHT ablesen', fx['what_it_cannot_show'])

    def test_the_model_is_labelled_as_a_model(self):
        model = [e for e in self.data['entries'] if e['kind'] == 'model']
        self.assertGreaterEqual(len(model), 2)

    def test_register_and_sample_are_distinguished(self):
        kinds = {e['kind'] for e in self.data['entries']}
        for expected in ('register', 'fortschreibung', 'sample', 'census', 'model'):
            self.assertIn(expected, kinds)


class TestExternalReferences(unittest.TestCase):
    """Independent estimates that are not model inputs."""

    def setUp(self):
        self.data = load('external-references.json')

    def test_spatial_ordering_agrees_with_the_published_map(self):
        self.assertGreaterEqual(self.data['kartenseite']['spearman_rank_correlation'], 0.8)

    def test_level_difference_is_explained_by_national_growth(self):
        k = self.data['kartenseite']
        self.assertTrue(1.1 < k['median_level_factor'] < 2.2)
        self.assertAlmostEqual(k['median_level_factor'],
                               k['expected_factor_from_national_growth'], delta=0.5)

    def test_stuttgart_is_consistent_with_the_city_estimate(self):
        s = self.data['stuttgart']
        self.assertGreater(s['modelled_percent'], s['percent'])
        self.assertLess(s['growth_factor_2017_to_2025'], 2.0)

    def test_the_limits_of_these_checks_are_stated(self):
        limits = ' '.join(self.data['what_this_does_not_show'])
        self.assertIn('18 Herkunftsländer', limits)
        self.assertIn('Melderegister', limits)


class TestGridAggregation(unittest.TestCase):
    """The assignment of grid cells to municipalities, tested against an official table."""

    def setUp(self):
        self.data = load('grid-aggregation-check.json')

    def test_all_municipalities_compared(self):
        self.assertEqual(self.data['municipalities_compared'], 1101)

    def test_aggregation_recovers_the_published_population(self):
        self.assertGreater(self.data['median_coverage'], 0.97)

    def test_residual_share_matches_the_published_table(self):
        self.assertLess(self.data['median_absolute_share_difference_points'], 1.0)

    def test_outliers_are_few_and_small(self):
        """Disagreement should be confined to places where census noise dominates."""
        self.assertLessEqual(self.data['municipalities_outside_share_tolerance'], 20)
        outliers = [m for m in self.data['municipalities']
                    if m['share_difference_points'] is not None
                    and abs(m['share_difference_points']) > self.data['share_tolerance_points']]
        small = [m for m in outliers if m['published_population'] < 10000]
        self.assertEqual(len(small), len(outliers),
                         'a large municipality disagrees; that would not be census noise')

    def test_known_source_differences_are_documented(self):
        joined = ' '.join(self.data['known_differences'])
        self.assertIn('163 Gemeinden', joined)
        self.assertIn('Cell-Key', joined)


class TestMunicipalDemography(unittest.TestCase):
    def setUp(self):
        self.data = load('municipal-demography-2022.json')

    def test_all_municipalities_present(self):
        self.assertEqual(len(self.data['municipalities']), 1101)

    def test_census_is_more_complete_than_the_sample(self):
        """The point of using the census here is that it has almost no gaps."""
        complete = [m for m in self.data['municipalities'] if m['age_complete']]
        self.assertGreater(len(complete), 1090)

    def test_suppressed_cells_stay_missing(self):
        for m in self.data['municipalities']:
            if not m['age_complete']:
                self.assertIn(None, m['age_groups'].values())

    def test_it_is_not_part_of_the_religion_model(self):
        self.assertIn('nicht in die Modellrechnung', self.data['not_a_religion_dataset'])
        src = (ROOT / 'scripts/build_estimate.py').read_text(encoding='utf-8')
        self.assertNotIn('municipal-demography', src)

    def test_census_revision_is_reported(self):
        lo, hi = self.data['census_revision_range_percent']
        self.assertLess(lo, 0)
        self.assertGreater(hi, 0)

    def test_licence_is_named(self):
        self.assertIn('Datenlizenz Deutschland', self.data['licence'])


# Die Prüfungen des Einrichtungsverzeichnisses stehen in
# tests/test_institutions.py. Dieses Repository veröffentlicht das Verzeichnis
# auf Ortsebene; die Prüfungen auf Anschriftenebene — Abstände zwischen
# Einrichtungen, Dubletten aus OpenStreetMap — gehören dorthin, wo die
# Anschriften liegen, und das ist nicht dieses Repository.



class TestAttribution(unittest.TestCase):
    """Every source the pipeline reads must be credited on the page.

    Several of these sources permit reuse only with attribution, so an uncredited
    source is a licence problem, not a cosmetic one.
    """

    def setUp(self):
        self.page = (ROOT / 'docs/index.html').read_text(encoding='utf-8')
        self.licences = (ROOT / 'DATA_LICENSES.md').read_text(encoding='utf-8')
        self.scripts = {p.name: p.read_text(encoding='utf-8')
                        for p in (ROOT / 'scripts').glob('*.py')}

    def test_every_genesis_table_used_is_credited(self):
        import re
        used = set()
        for text in self.scripts.values():
            used |= set(re.findall(r'12211-\d{4}', text))
        self.assertTrue(used, 'expected the pipeline to use GENESIS tables')
        for code in sorted(used):
            self.assertIn(code, self.page, f'{code} is used but not credited on the page')
            self.assertIn(code, self.licences, f'{code} is used but missing from DATA_LICENSES.md')

    def test_census_and_register_sources_are_credited(self):
        for needle in ('Zensus 2022', 'A I 4 - j/24', 'VG250'):
            self.assertIn(needle, self.page, needle)
            self.assertIn(needle, self.licences, needle)

    def test_attribution_required_notices_are_present(self):
        self.assertIn('Statistische Ämter des Bundes und der Länder', self.page)
        self.assertIn('mit Quellenangabe gestattet', self.page)
        self.assertIn('dl-de/by-2-0', self.page)

    def test_licence_table_names_what_each_source_is_used_for(self):
        start = self.page.index('Daten, Quellen und Lizenzen')
        table = self.page[start:self.page.index('</table>', start)]
        self.assertIn('Wofür verwendet', table)


if __name__ == '__main__':
    unittest.main()

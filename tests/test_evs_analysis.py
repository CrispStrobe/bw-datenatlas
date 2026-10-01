import unittest
from scripts.analyse_evs import estimate


class WeightedResponses(unittest.TestCase):
    def test_valid_count_is_not_weight_sum_and_missing_is_excluded(self):
        result = estimate([1, 2, -1, 1, 1], [1, 3, 50, 0, float('nan')], [1, 2], [1])
        self.assertEqual(result, {'value': 25, 'valid_n': 2, 'weighted_valid_n': 4})

    def test_uncertain_belief_is_a_valid_answer_not_missing(self):
        result = estimate([1, 3, -1], [1, 1, 100], [1, 2, 3, 4], [3])
        self.assertEqual(result['value'], 50)
        self.assertEqual(result['valid_n'], 2)

    def test_zero_denominator_cannot_become_zero_percent(self):
        with self.assertRaisesRegex(ValueError, 'No valid'):
            estimate([-1, -2], [1, 1], [1, 2], [1])

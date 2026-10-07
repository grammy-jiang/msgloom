import unittest

from topic01_validation.metrics import FractionMetric, expected_calibration_error, match_spans, reliability_bins
from topic01_validation.models import Span


class MetricTests(unittest.TestCase):
    def test_fraction_metric_explicit_zero_denominator(self):
        self.assertIsNone(FractionMetric(0, 0).value)

    def test_span_matching_one_to_one(self):
        result = match_spans([Span(0, 10), Span(20, 30)], [Span(0, 10), Span(21, 30)])
        self.assertEqual(result.precision.numerator, 2)
        self.assertEqual(result.recall.numerator, 2)

    def test_span_matching_never_reuses_one_prediction_for_two_gold_spans(self):
        result = match_spans([Span(0, 10), Span(0, 10)], [Span(0, 10)])
        self.assertEqual(len(result.matched_pairs), 1)
        self.assertEqual(len({pi for _, pi in result.matched_pairs}), len(result.matched_pairs))
        self.assertEqual(len({gi for gi, _ in result.matched_pairs}), len(result.matched_pairs))

    def test_span_matching_never_reuses_one_gold_for_duplicate_predictions(self):
        result = match_spans([Span(0, 10)], [Span(0, 10), Span(0, 10)])
        self.assertEqual(len(result.matched_pairs), 1)
        self.assertEqual(len({pi for _, pi in result.matched_pairs}), len(result.matched_pairs))
        self.assertEqual(len({gi for gi, _ in result.matched_pairs}), len(result.matched_pairs))

    def test_reliability_bins_have_counts(self):
        rows = reliability_bins([(0.1, False), (0.9, True)], bins=5)
        self.assertEqual(sum(r["count"] for r in rows), 2)

    def test_ece_is_zero_for_perfect_extreme_predictions(self):
        self.assertAlmostEqual(expected_calibration_error([(0.0, False), (1.0, True)], bins=2), 0.0)


if __name__ == "__main__":
    unittest.main()

import unittest

from topic01_validation.uncertainty import choose_threshold, evaluate_example, generate_examples


class UncertaintyTests(unittest.TestCase):
    def test_generation_is_deterministic(self):
        self.assertEqual(generate_examples(seed=7, count_per_family=3), generate_examples(seed=7, count_per_family=3))

    def test_threshold_calibration_returns_a_candidate(self):
        examples = generate_examples(seed=17, count_per_family=5)
        threshold, rows = choose_threshold(examples)
        self.assertTrue(0.6 <= threshold <= 0.95)
        self.assertTrue(rows)

    def test_ambiguous_exact_abstains(self):
        example = next(x for x in generate_examples(seed=11, count_per_family=2) if x.family == "ambiguous_exact")
        result = evaluate_example(example, threshold=0.80)
        self.assertTrue(result.resolution.abstained)

    def test_exact_unique_accepts_correct_source(self):
        example = next(x for x in generate_examples(seed=11, count_per_family=2) if x.family == "exact_unique")
        result = evaluate_example(example, threshold=0.80)
        self.assertFalse(result.resolution.abstained)
        self.assertTrue(result.accepted_correct)

    def test_calibration_and_holdout_templates_and_content_are_disjoint(self):
        cal = generate_examples(seed=20260915, count_per_family=10, variant="calibration")
        hold = generate_examples(seed=20260916, count_per_family=10, variant="holdout")
        self.assertFalse({x.template_family for x in cal} & {x.template_family for x in hold})
        self.assertFalse({x.content_key for x in cal} & {x.content_key for x in hold})



if __name__ == "__main__":
    unittest.main()

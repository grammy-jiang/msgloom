import unittest

from topic01_validation.fixtures import canonical_cases
from topic01_validation.models import Span, validate_cases


class SpanTests(unittest.TestCase):
    def test_iou(self):
        self.assertAlmostEqual(Span(0, 5).iou(Span(2, 7)), 3 / 7)

    def test_invalid_span(self):
        with self.assertRaises(ValueError):
            Span(5, 4)


class FixtureContractTests(unittest.TestCase):
    def test_all_canonical_cases_validate(self):
        validate_cases(canonical_cases())

    def test_case_ids_unique(self):
        ids = [c.case_id for c in canonical_cases()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_ambiguous_boilerplate_has_two_valid_sources(self):
        case = next(c for c in canonical_cases() if c.case_id == "boilerplate-collision")
        self.assertTrue(case.quotes[0].ambiguous)
        self.assertEqual({x.message_id for x in case.quotes[0].source_candidates}, {"boiler-a", "boiler-b"})

    def test_multiple_parent_gold_retains_both_parents(self):
        case = next(c for c in canonical_cases() if c.case_id == "multiple-parents")
        self.assertEqual(set(case.relations[0].target_ids), {"multi-a", "multi-b"})
        self.assertEqual(len(case.quotes), 2)
        self.assertTrue(all(not q.ambiguous for q in case.quotes))
        self.assertEqual([{x.message_id for x in q.source_candidates} for q in case.quotes], [{"multi-a"}, {"multi-b"}])

    def test_deadline_is_explicit_decision_relevant_gold(self):
        case = next(c for c in canonical_cases() if c.case_id == "late-parent-arrival")
        deadlines = [s for s in case.spans if s.kind == "deadline"]
        self.assertEqual([s.text for s in deadlines], ["Deadline: Friday."])


if __name__ == "__main__":
    unittest.main()

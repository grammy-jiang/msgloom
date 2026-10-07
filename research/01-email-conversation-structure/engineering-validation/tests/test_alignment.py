import unittest

from topic01_validation.alignment import best_match, candidate_matches, resolve_candidates
from topic01_validation.extraction import extract_body
from topic01_validation.fixtures import canonical_cases


class AlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {c.case_id: c for c in canonical_cases()}

    def test_exact_quote_maps_to_source(self):
        case = self.cases["late-parent-arrival"]
        gold = case.quotes[0]
        quote_text = gold.occurrence_span.extract(case.message(gold.message_id).expected_text)
        match = best_match(quote_text, case.message("late-parent").expected_text, source_message_id="late-parent")
        self.assertIsNotNone(match)
        self.assertTrue(match.exact)
        self.assertEqual(match.source_message_id, "late-parent")
        self.assertIn("Condition: Legal must sign off.", match.matched_text)

    def test_short_edit_is_fuzzy_not_exact(self):
        case = self.cases["short-edited-quote"]
        gold = case.quotes[0]
        quote_text = gold.occurrence_span.extract(case.message("edit-reply").expected_text)
        match = best_match(quote_text, case.message("edit-source").expected_text, source_message_id="edit-source")
        self.assertIsNotNone(match)
        self.assertFalse(match.exact)
        self.assertGreater(match.score, 0.80)

    def test_boilerplate_collision_abstains(self):
        case = self.cases["boilerplate-collision"]
        gold = case.quotes[0]
        quote_text = gold.occurrence_span.extract(case.message("boiler-reply").expected_text)
        sources = {m.message_id: m.expected_text for m in case.messages if m.message_id != "boiler-reply"}
        matches = candidate_matches(quote_text, sources)
        resolution = resolve_candidates(matches)
        self.assertTrue(resolution.abstained)
        self.assertEqual(resolution.reason, "ambiguous_candidates")
        self.assertEqual({m.source_message_id for m in resolution.candidates[:2]}, {"boiler-a", "boiler-b"})

    def test_dissimilar_source_below_threshold(self):
        match = best_match("Approve Alpha today.", "Completely unrelated weather forecast.", source_message_id="x", min_score=0.75)
        self.assertIsNone(match)


if __name__ == "__main__":
    unittest.main()

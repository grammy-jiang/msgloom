import unittest

from topic01_validation.fixtures import canonical_cases
from topic01_validation.replay import replay


class AdversarialMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {c.case_id: c for c in canonical_cases()}

    def test_duplicate_message_id_exposes_unsafe_unique_mapping(self):
        case = self.cases["duplicate-message-id"]
        finals = [replay(case, order).final for order in case.replay_orders]
        # The intentionally simple baseline uses a one-value map and is therefore
        # arrival-order-sensitive. This failure is a benchmark feature, not an
        # expected product behavior.
        self.assertNotEqual(finals[0], finals[1])
        relation = case.relations[0]
        self.assertTrue(relation.ambiguous)
        self.assertEqual(set(relation.target_ids), {"dup-a", "dup-b"})

    def test_ambiguity_preserving_duplicate_id_baseline_is_order_invariant(self):
        case = self.cases["duplicate-message-id"]
        finals = [replay(case, order, preserve_id_ambiguity=True).final for order in case.replay_orders]
        self.assertEqual(finals[0], finals[1])
        self.assertEqual(finals[1], finals[2])
        final = {a.relation_id: a for a in replay(case, case.replay_orders[0], preserve_id_ambiguity=True).snapshots[-1].assessments}
        parent = final["parent:dup-reply"]
        self.assertEqual(parent.status, "ambiguous")
        self.assertEqual(set(parent.targets), {"dup-a", "dup-b"})

    def test_header_vs_quote_source_remain_different_relations(self):
        case = self.cases["header-vs-quote-source-conflict"]
        result = replay(case, case.replay_orders[0])
        final = {a.relation_id: a for a in result.snapshots[-1].assessments}
        self.assertEqual(final["parent:conflict-reply"].targets, ("conflict-parent",))
        quote = [a for a in final.values() if a.kind == "quote_source" and a.message_id == "conflict-reply"]
        self.assertTrue(any(a.targets == ("conflict-quoted",) for a in quote))

    def test_same_subject_does_not_create_parent_relation(self):
        case = self.cases["same-subject-unrelated"]
        result = replay(case, case.replay_orders[0])
        self.assertFalse(any(a.kind == "reply_parent" for a in result.snapshots[-1].assessments))

    def test_changed_subject_retains_explicit_parent(self):
        case = self.cases["changed-subject-reply"]
        result = replay(case, case.replay_orders[0])
        final = {a.relation_id: a for a in result.snapshots[-1].assessments}
        self.assertEqual(final["parent:changed-subject-reply"].targets, ("changed-subject-root",))

    def test_truncated_references_does_not_replace_in_reply_to_parent(self):
        case = self.cases["truncated-references"]
        result = replay(case, case.replay_orders[0])
        final = {a.relation_id: a for a in result.snapshots[-1].assessments}
        self.assertEqual(final["parent:tr-reply"].targets, ("tr-mid",))

    def test_headerless_source_does_not_satisfy_unrelated_missing_parent_header(self):
        case = self.cases["headerless-source-and-missing-parent"]
        result = replay(case, case.replay_orders[0])
        final = {a.relation_id: a for a in result.snapshots[-1].assessments}
        parent = final["parent:headerless-reply"]
        self.assertEqual(parent.status, "missing")
        self.assertEqual(parent.targets, ("MISSING:<unknown-parent@synthetic.invalid>",))
        quote = [a for a in final.values() if a.kind == "quote_source" and a.message_id == "headerless-reply"]
        self.assertTrue(any(a.targets == ("headerless-source",) for a in quote))


if __name__ == "__main__":
    unittest.main()

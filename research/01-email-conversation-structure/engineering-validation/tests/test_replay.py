import unittest

from topic01_validation.fixtures import canonical_cases
from topic01_validation.replay import replay, replay_metrics


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {c.case_id: c for c in canonical_cases()}

    def test_late_parent_changes_parent_assessment(self):
        case = self.cases["late-parent-arrival"]
        result = replay(case, ("late-reply", "late-parent"))
        first = {a.relation_id: a for a in result.snapshots[0].assessments}
        final = {a.relation_id: a for a in result.snapshots[-1].assessments}
        self.assertEqual(first["parent:late-reply"].status, "missing")
        self.assertEqual(final["parent:late-reply"].status, "resolved")
        self.assertEqual(final["parent:late-reply"].targets, ("late-parent",))

    def test_final_state_is_arrival_order_invariant_for_late_parent_case(self):
        case = self.cases["late-parent-arrival"]
        results = [replay(case, order) for order in case.replay_orders]
        metrics = replay_metrics(results)
        self.assertEqual(metrics["final_state_agreement"], 1.0)
        self.assertGreaterEqual(metrics["relations_changed"], 1)
        self.assertEqual(metrics["relations_removed_before_final"], 0)

    def test_sibling_order_does_not_create_sibling_parent_relation(self):
        case = self.cases["sibling-branches"]
        for order in case.replay_orders:
            final = {a.relation_id: a for a in replay(case, order).snapshots[-1].assessments}
            self.assertEqual(final["parent:branch-left"].targets, ("branch-root",))
            self.assertEqual(final["parent:branch-right"].targets, ("branch-root",))

    def test_multiple_parents_are_not_collapsed(self):
        case = self.cases["multiple-parents"]
        result = replay(case, ("multi-a", "multi-b", "multi-reply"))
        final = {a.relation_id: a for a in result.snapshots[-1].assessments}
        self.assertEqual(set(final["parent:multi-reply"].targets), {"multi-a", "multi-b"})

    def test_truncated_references_has_separate_indirect_ancestry(self):
        case = self.cases["truncated-references"]
        result = replay(case, case.replay_orders[0], preserve_id_ambiguity=True)
        final = {a.relation_id: a for a in result.snapshots[-1].assessments}
        self.assertEqual(final["parent:tr-reply"].targets, ("tr-mid",))
        self.assertEqual(final["ancestry:tr-reply"].targets, ("tr-root",))

    def test_replay_metrics_detect_relation_removed_before_final(self):
        from topic01_validation.replay import Assessment, Snapshot, ReplayResult, replay_metrics
        first = Snapshot(1, "a", ("a",), (Assessment("parent:a", "a", "reply_parent", "resolved", ("x",), 1.0, "test"),))
        final = Snapshot(2, "b", ("a", "b"), ())
        metrics = replay_metrics((ReplayResult(("a", "b"), (first, final)),))
        self.assertEqual(metrics["relations_removed_before_final"], 1)



if __name__ == "__main__":
    unittest.main()

import tempfile
from pathlib import Path
import unittest

from topic01_validation.experiments import run_all


class ExperimentTests(unittest.TestCase):
    def test_full_synthetic_run_has_all_four_gaps(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "fixtures").mkdir()
            result = run_all(root)
        self.assertEqual(result["overall_status"], "EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC_WITH_IDENTIFIED_BASELINE_FAILURES")
        for key in ("E1", "E2", "E3", "E4"):
            self.assertEqual(result[key]["status"], "EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC")
        self.assertFalse(result["production_data_used"])
        self.assertFalse(result["external_network_used"])

    def test_markerless_failure_remains_visible(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / "fixtures").mkdir()
            result = run_all(root)
        recall = result["E2"]["quote_detection"]["recall"]["value"]
        self.assertLess(recall, 1.0)
        self.assertTrue(any("markerless" in x.lower() for x in result["E2"]["identified_failure_modes"]))

    def test_reuse_augmented_comparator_uses_past_context_and_keeps_negative_control(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / "fixtures").mkdir()
            result = run_all(root)
        augmented = result["E2"]["reuse_augmented_quote_detection"]
        fps = {(x["case_id"], x["message_id"]) for x in augmented["false_positive_messages"]}
        self.assertIn(("boilerplate-reuse-not-quotation", "reuse-boiler-new"), fps)
        self.assertNotIn(("markerless-copy", "markerless-source"), fps)
        self.assertNotIn(("forwarded-message-block", "forward-source"), fps)


    def test_lossy_extractor_breaks_independent_gold_metrics(self):
        from dataclasses import replace
        from unittest.mock import patch
        import topic01_validation.experiments as exp
        real_extract = exp.extract_body

        def lossy(raw):
            body = real_extract(raw)
            return replace(body, text=body.text.replace("\nDeadline: Friday.", ""))

        with patch.object(exp, "extract_body", lossy):
            result = exp.run_e2()
        self.assertLess(result["extraction_exact_body_match"]["value"], 1.0)
        self.assertLess(result["decision_condition_deadline_preservation"]["value"], 1.0)

    def test_strict_augmented_end_to_end_counts_false_accepted_predictions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / "fixtures").mkdir()
            result = run_all(root)
        strict = result["E2"]["arrival_time_reuse_augmented_end_to_end"]
        self.assertGreater(strict["false_accepted_attributions"], 0)
        self.assertGreater(strict["accepted_attribution_error"]["value"], 0.0)
        self.assertTrue(any(row["error_kind"] == "unmatched_predicted_occurrence" for row in strict["prediction_results"]))

    def test_e3_safe_identifier_comparator_and_occurrence_metrics_are_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / "fixtures").mkdir()
            result = run_all(root)
        unsafe = result["E3"]["unsafe_single_id_baseline"]
        safe = result["E3"]["ambiguity_preserving_id_baseline"]
        self.assertLess(unsafe["mean_final_state_agreement_multi_order_cases"], 1.0)
        self.assertEqual(safe["mean_final_state_agreement_multi_order_cases"], 1.0)
        self.assertEqual(safe["parent_relation_precision"]["value"], 1.0)
        self.assertEqual(safe["parent_relation_recall"]["value"], 1.0)
        self.assertEqual(safe["ancestry_precision"]["value"], 1.0)
        self.assertEqual(safe["ancestry_recall"]["value"], 1.0)
        # Occurrence-specific scoring must expose the composite/markerless/forwarded
        # detector gaps rather than letting one source decision satisfy a whole message.
        self.assertLess(safe["quote_occurrence_recall"]["value"], 1.0)
        self.assertLess(safe["quote_source_policy_recall_all_gold"]["value"], 1.0)

    def test_e3_dropped_inline_occurrence_reduces_occurrence_and_policy_recall(self):
        from dataclasses import replace
        from unittest.mock import patch
        import topic01_validation.experiments as exp
        real_replay = exp.replay
        baseline = exp.run_e3()["ambiguity_preserving_id_baseline"]

        def drop_one(case, order, **kwargs):
            result = real_replay(case, order, **kwargs)
            if case.case_id != "interleaved-inline-reply":
                return result
            snapshots = []
            for snap in result.snapshots:
                quotes = [a for a in snap.assessments if a.kind == "quote_source" and a.message_id == "inline-reply"]
                remove_id = max((a.relation_id for a in quotes), default=None)
                assessments = tuple(a for a in snap.assessments if a.relation_id != remove_id)
                snapshots.append(replace(snap, assessments=assessments))
            return replace(result, snapshots=tuple(snapshots))

        with patch.object(exp, "replay", drop_one):
            mutated = exp.run_e3()["ambiguity_preserving_id_baseline"]
        self.assertLess(mutated["quote_occurrence_recall"]["value"], baseline["quote_occurrence_recall"]["value"] )
        self.assertLess(mutated["quote_source_policy_recall_all_gold"]["value"], baseline["quote_source_policy_recall_all_gold"]["value"] )

    def test_e3_unexpected_parent_and_ancestry_predictions_reduce_precision(self):
        from dataclasses import replace
        from unittest.mock import patch
        import topic01_validation.experiments as exp
        from topic01_validation.replay import Assessment
        real_replay = exp.replay
        baseline = exp.run_e3()["ambiguity_preserving_id_baseline"]

        def add_unexpected(case, order, **kwargs):
            result = real_replay(case, order, **kwargs)
            if case.case_id != "same-subject-unrelated":
                return result
            snaps = list(result.snapshots)
            last = snaps[-1]
            extra = (
                Assessment("parent:unexpected", "same-subject-a", "reply_parent", "resolved", ("same-subject-b",), 1.0, "injected-test"),
                Assessment("ancestry:unexpected", "same-subject-a", "ancestry", "resolved", ("same-subject-b",), 1.0, "injected-test"),
            )
            snaps[-1] = replace(last, assessments=last.assessments + extra)
            return replace(result, snapshots=tuple(snaps))

        with patch.object(exp, "replay", add_unexpected):
            mutated = exp.run_e3()["ambiguity_preserving_id_baseline"]
        self.assertLess(mutated["parent_relation_precision"]["value"], baseline["parent_relation_precision"]["value"] )
        self.assertEqual(mutated["parent_relation_recall"], baseline["parent_relation_recall"] )
        self.assertLess(mutated["ancestry_precision"]["value"], baseline["ancestry_precision"]["value"] )
        self.assertEqual(mutated["ancestry_recall"], baseline["ancestry_recall"] )

    def test_e4_run_records_disjoint_template_holdout(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / "fixtures").mkdir()
            result = run_all(root)
        e4 = result["E4"]
        self.assertEqual(e4["content_overlap_count"], 0)
        self.assertFalse(set(e4["calibration_template_families"]) & set(e4["test_template_families"]))



if __name__ == "__main__":
    unittest.main()

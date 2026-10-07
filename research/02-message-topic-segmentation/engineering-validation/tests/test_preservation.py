import unittest
from topic02_validation.assignment import predict_case
from topic02_validation.fixtures import canonical_cases
from topic02_validation.preservation import decision_preservation,predicted_decision_membership
from topic02_validation.units import unitize

class PreservationTests(unittest.TestCase):
    def test_inventory_exposes_category_denominators_and_ambiguous_exclusion(self):
        m=predicted_decision_membership(canonical_cases(),lambda c:predict_case(c,mode='set_valued',context_mode='span_only'))
        inv=m['annotation_inventory'];self.assertEqual(inv['total']['annotated_spans'],21);self.assertEqual(inv['total']['scored_required_spans'],20);self.assertEqual(inv['total']['scored_required_memberships'],24);self.assertEqual(inv['total']['excluded_ambiguous_spans'],1)
        self.assertEqual(inv['by_kind']['deadline']['annotated_spans'],8);self.assertEqual(inv['by_kind']['deadline']['excluded_ambiguous_spans'],1)
    def test_inventory_denies_source_complete_semantic_coverage(self):
        m=predicted_decision_membership(canonical_cases(),lambda c:predict_case(c,mode='set_valued',context_mode='span_only'))
        self.assertIn('not a source-complete semantic inventory',m['annotation_inventory']['annotation_scope_warning'])
        self.assertIn('Gold-span-conditioned',m['claim_boundary'])
    def test_local_window_false_scope_counted_by_category(self):
        m=predicted_decision_membership(canonical_cases(),lambda c:predict_case(c,mode='set_valued',context_mode='local_window'))
        self.assertEqual(m['false_positive'],12)
        self.assertGreater(m['by_kind']['condition']['false_positive'],0)
        self.assertGreater(m['by_kind']['deadline']['false_positive'],0)
    def test_oracle_sentence_scope_false_positives_remain_visible(self):
        m=decision_preservation(canonical_cases(),lambda t:unitize(t,'sentence'))
        self.assertEqual(m['false_positive'],5);self.assertEqual(m['false_negative'],0)

if __name__=='__main__':unittest.main()

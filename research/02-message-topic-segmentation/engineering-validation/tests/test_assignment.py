import unittest
from topic02_validation.fixtures import canonical_cases
from topic02_validation.assignment import predict,predict_case
from topic02_validation.metrics import assignment_metrics,pair_prf

class AssignmentTests(unittest.TestCase):
    def test_set_valued_keeps_joint_membership(self):
        c=next(x for x in canonical_cases() if x.case_id=='overlap-shared-span');p=predict(c,c.span('shared'),mode='set_valued')
        self.assertEqual(set(p.topic_ids),{'ATLAS','BETA'})
    def test_single_label_cannot_keep_both_joint_memberships(self):
        c=next(x for x in canonical_cases() if x.case_id=='overlap-shared-span');p=predict(c,c.span('shared'),mode='single_label')
        self.assertLess(len(p.topic_ids),2)
    def test_ambiguous_common_text_abstains(self):
        c=next(x for x in canonical_cases() if x.case_id=='context-correction');p=predict(c,c.span('ref'),mode='set_valued')
        self.assertEqual(p.status,'abstained')
    def test_set_valued_improves_overlap_recall(self):
        cases=canonical_cases();single=assignment_metrics(cases,lambda c:predict_case(c,mode='single_label'));multi=assignment_metrics(cases,lambda c:predict_case(c,mode='set_valued'))
        self.assertGreater(multi['overlap_only_membership']['recall']['value'],single['overlap_only_membership']['recall']['value'])
    def test_local_context_false_memberships_are_in_precision_denominator(self):
        cases=canonical_cases();m=assignment_metrics(cases,lambda c:predict_case(c,mode='set_valued',context_mode='local_window'))
        self.assertGreater(m['membership_micro']['false_positive'],0);self.assertLess(m['membership_micro']['precision']['value'],1.0)
    def test_pair_prf_counts_extra_prediction(self):
        m=pair_prf({('c','s','A')},{('c','s','A'),('c','s','B')});self.assertEqual(m['false_positive'],1);self.assertEqual(m['precision']['denominator'],2)

if __name__=='__main__':unittest.main()

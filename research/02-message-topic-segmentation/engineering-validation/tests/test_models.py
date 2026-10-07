import inspect
import unittest
from topic02_validation import fixtures
from topic02_validation.fixtures import canonical_cases
from topic02_validation.models import MembershipGold, Span

class GoldContractTests(unittest.TestCase):
    def test_all_cases_validate_and_unique(self):
        cases=canonical_cases(); self.assertEqual(len(cases),18); self.assertEqual(len({c.case_id for c in cases}),18)
        for c in cases:c.validate()
    def test_gold_fixture_module_does_not_import_tested_components(self):
        src=inspect.getsource(fixtures)
        for forbidden in ('from .units','from .assignment','from .representation','from .preservation','extract_body'):
            self.assertNotIn(forbidden,src)
    def test_joint_membership_is_not_ambiguity(self):
        c=next(x for x in canonical_cases() if x.case_id=='overlap-shared-span');m=c.memberships[0]
        self.assertEqual(set(m.required_topics),{'ATLAS','BETA'});self.assertFalse(m.ambiguous)
    def test_ambiguous_membership_is_not_joint(self):
        c=next(x for x in canonical_cases() if x.case_id=='ambiguous-reference');m=c.memberships[0]
        self.assertFalse(m.required_topics);self.assertTrue(m.ambiguous);self.assertTrue(m.abstention_allowed)
    def test_noncontiguous_object_has_multiple_components(self):
        c=next(x for x in canonical_cases() if x.case_id=='noncontiguous-aba');o=c.topic_objects[0]
        self.assertEqual(o.topic_id,'ATLAS');self.assertEqual(o.span_ids,('a1','a2'))
    def test_span_iou(self):
        self.assertAlmostEqual(Span(0,10).iou(Span(5,15)),5/15)

if __name__=='__main__':unittest.main()

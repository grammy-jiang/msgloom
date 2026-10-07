import unittest
from topic02_validation.fixtures import canonical_cases
from topic02_validation.units import unitize,best_cover
from topic02_validation.preservation import topic_component_ceiling,decision_preservation

class UnitTests(unittest.TestCase):
    def test_sentence_unit_broadens_two_clause_message(self):
        c=next(x for x in canonical_cases() if x.case_id=='clause-split-two-matters');g=c.span('atlas-clause').span
        hull,exact=best_cover(g,unitize(c.text,'sentence'));self.assertFalse(exact);self.assertGreater(hull.end,g.end)
    def test_clause_partition_exposes_internal_boundaries(self):
        c=next(x for x in canonical_cases() if x.case_id=='clause-split-two-matters');u=unitize(c.text,'clause')
        self.assertGreaterEqual(len(u),4);self.assertTrue(any('Legal signs off' in x.text for x in u));self.assertTrue(any('postpone Beta' in x.text for x in u))
    def test_sentence_has_wrong_topic_scope_false_positives(self):
        cases=canonical_cases();m=decision_preservation(cases,lambda t:unitize(t,'sentence'))
        self.assertGreater(m['false_positive'],0);self.assertEqual(m['false_negative'],0)
    def test_clause_oracle_improves_scope_precision_on_frozen_cases(self):
        cases=canonical_cases();sent=decision_preservation(cases,lambda t:unitize(t,'sentence'));cl=decision_preservation(cases,lambda t:unitize(t,'clause'))
        self.assertGreater(cl['precision']['value'],sent['precision']['value'])
    def test_component_ceiling_is_not_claimed_perfect(self):
        m=topic_component_ceiling(canonical_cases(),lambda t:unitize(t,'clause'))
        self.assertLess(m['exact_topic_component_spans']['value'],1.0);self.assertGreater(m['exact_topic_component_spans']['value'],0.5)

if __name__=='__main__':unittest.main()

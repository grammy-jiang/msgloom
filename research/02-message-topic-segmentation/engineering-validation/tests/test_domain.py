import unittest
from topic02_validation.domain import evaluate_styles,style_strata
from topic02_validation.fixtures import canonical_cases

class DomainStyleTests(unittest.TestCase):
    def test_style_strata_are_declared_and_synthetic(self):
        s=style_strata(canonical_cases());self.assertIn('structured_list_table',s);self.assertIn('quoted_history',s);self.assertIn('context_dependent',s)
    def test_structured_style_exposes_lower_membership_recall(self):
        r=evaluate_styles(canonical_cases())['strata']
        self.assertLess(r['structured_list_table']['set_valued_span_only_membership']['recall']['value'],r['plain_prose']['set_valued_span_only_membership']['recall']['value'])
    def test_claim_boundary_denies_production_accuracy(self):
        r=evaluate_styles(canonical_cases());self.assertIn('do not estimate production-domain accuracy',r['claim_boundary'])

if __name__=='__main__':unittest.main()

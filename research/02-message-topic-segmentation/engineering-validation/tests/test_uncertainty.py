import unittest
from topic02_validation.uncertainty import generate_examples,choose_threshold,evaluate

class UncertaintyTests(unittest.TestCase):
    def test_calibration_holdout_templates_and_content_disjoint(self):
        a=generate_examples(seed=1,count_per_family=10,variant='calibration');b=generate_examples(seed=2,count_per_family=10,variant='holdout')
        self.assertFalse({x.template_family for x in a}&{x.template_family for x in b});self.assertFalse({x.content_key for x in a}&{x.content_key for x in b})
    def test_no_all_abstain_threshold_can_satisfy_coverage_floor(self):
        cal=generate_examples(seed=20260915,count_per_family=40,variant='calibration');s=choose_threshold(cal,max_error=.05,min_coverage=.4)
        self.assertFalse(s['target_met']);self.assertIsNone(s['selected_threshold']);self.assertIsNotNone(s['fallback_threshold'])
    def test_fallback_exposes_near_collision_errors(self):
        cal=generate_examples(seed=20260915,count_per_family=40,variant='calibration');test=generate_examples(seed=20260916,count_per_family=40,variant='holdout');s=choose_threshold(cal);th=s['fallback_threshold'];rows=[evaluate(x,threshold=th) for x in test];near=[x for x in rows if x.example.family=='near_collision'];self.assertTrue(all(not x.correct for x in near));self.assertTrue(all(not x.abstained for x in near))

if __name__=='__main__':unittest.main()

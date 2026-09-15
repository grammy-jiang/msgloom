import tempfile
from pathlib import Path
import unittest
from datetime import datetime as RealDateTime, timezone
from unittest.mock import patch
import topic02_validation.experiments as experiments
from topic02_validation.experiments import run_all,write_results

class ExperimentIntegrationTests(unittest.TestCase):
    def test_run_has_ev1_through_ev7_and_review_is_separate(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'fixtures').mkdir();r=run_all(root)
        self.assertEqual(set(k for k in r if k.startswith('EV')), {f'EV{i}' for i in range(1,8)})
        self.assertTrue(r['experiment_execution_status'].startswith('EXPERIMENT_EXECUTION_COMPLETE'))
        self.assertEqual(r['independent_review_status'],'PENDING_INDEPENDENT_REVIEW')
        self.assertFalse(r['production_data_used']);self.assertFalse(r['external_network_used'])
    def test_finished_timestamp_is_recorded_after_all_ev_calls(self):
        timeline=[]
        times=iter([
            RealDateTime(2026,9,15,1,2,3,tzinfo=timezone.utc),
            RealDateTime(2026,9,15,1,2,4,tzinfo=timezone.utc),
        ])
        class FakeDateTime:
            @classmethod
            def now(cls,tz):
                label='clock:start' if not timeline else 'clock:finish'
                timeline.append(label)
                return next(times)
        def ev(name,value):
            def inner(*args,**kwargs):
                timeline.append(name)
                return {'name':value}
            return inner
        with tempfile.TemporaryDirectory() as td,              patch.object(experiments,'datetime',FakeDateTime),              patch.object(experiments,'run_ev1',side_effect=ev('EV1',1)),              patch.object(experiments,'run_ev2',side_effect=ev('EV2',2)),              patch.object(experiments,'run_ev3',side_effect=ev('EV3',3)),              patch.object(experiments,'run_ev4',side_effect=ev('EV4',4)),              patch.object(experiments,'run_ev5',side_effect=ev('EV5',5)),              patch.object(experiments,'run_ev6',side_effect=ev('EV6',6)),              patch.object(experiments,'run_ev7',side_effect=ev('EV7',7)):
            r=experiments.run_all(Path(td))
        self.assertEqual(timeline,['clock:start','EV1','EV2','EV3','EV4','EV5','EV6','EV7','clock:finish'])
        self.assertLess(r['started_at_utc'],r['finished_at_utc'])
        self.assertEqual(r['EV7'],{'name':7})

    def test_ev3_distinguishes_gold_conditioned_from_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'fixtures').mkdir();r=run_all(root)
        self.assertIn('gold_span_conditioned_membership',r['EV3']);self.assertIn('end_to_end_unit_membership',r['EV3'])
        self.assertGreater(r['EV3']['end_to_end_unit_membership']['clause:set_valued']['false_positive_predicted_topic_spans'],0)
    def test_ev6_failure_is_not_hidden_by_all_abstain(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'fixtures').mkdir();r=run_all(root)
        self.assertFalse(r['EV6']['target_met']);self.assertIsNone(r['EV6']['selection']['selected_threshold']);self.assertGreater(r['EV6']['test_coverage']['value'],0);self.assertGreater(r['EV6']['test_accepted_error']['value'],.05)
    def test_write_results_reproduces_machine_status_without_granting_review(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'fixtures').mkdir();r=run_all(root);write_results(root,r)
            text=(root/'RESULTS.md').read_text();metrics=(root/'results/metrics.json').read_text()
        self.assertIn('PENDING_INDEPENDENT_REVIEW',text);self.assertIn('PENDING_INDEPENDENT_REVIEW',metrics)

if __name__=='__main__':unittest.main()

from dataclasses import fields,replace
import unittest
from unittest.mock import patch
import topic02_validation.replay as replay_mod
from topic02_validation.fixtures import canonical_cases
from topic02_validation.replay import PredictionSpan,PredictionCase,ContextInput,replay_case,evaluate_replay,predict_step,prediction_input,prediction_case

class ReplayTests(unittest.TestCase):
    def test_prediction_span_contains_no_semantic_gold_labels(self):
        self.assertEqual([f.name for f in fields(PredictionSpan)],['span_id','span','text'])
    def test_prediction_case_contains_no_gold_or_context_fields(self):
        self.assertEqual([f.name for f in fields(PredictionCase)],['case_id','text','topics','spans'])
        forbidden={'memberships','topic_objects','context_steps','context_texts','tags','expected_span_topic_sets','expected_abstentions'}
        self.assertFalse(forbidden & {f.name for f in fields(PredictionCase)})
    def test_context_input_contains_only_current_materialized_context(self):
        self.assertEqual([f.name for f in fields(ContextInput)],['step_id','available_contexts'])
        c=next(x for x in canonical_cases() if x.case_id=='context-correction')
        self.assertEqual(prediction_input(c,c.context_steps[0]).available_contexts,())
        self.assertEqual([x[0] for x in prediction_input(c,c.context_steps[1]).available_contexts],['ctx1'])
        self.assertEqual([x[0] for x in prediction_input(c,c.context_steps[2]).available_contexts],['ctx1','ctx2'])
    def test_prediction_case_ignores_case_gold_and_span_kind_origin_changes(self):
        for c in canonical_cases():
            p=prediction_case(c)
            stripped_spans=tuple(replace(s,origin='authored',kind='topic_evidence') for s in c.spans)
            changed=replace(c,spans=stripped_spans,memberships=(),topic_objects=(),context_steps=(),context_texts=())
            # Context is intentionally outside PredictionCase; semantic kind/origin are dropped.
            self.assertEqual(p,prediction_case(changed))
    def test_no_context_abstains(self):
        c=next(x for x in canonical_cases() if x.case_id=='ambiguous-reference');r=replay_case(c);p={x.span_id:x for x in r.steps[0].predictions};self.assertEqual(p['amb'].status,'abstained');self.assertEqual(p['deadline'].status,'abstained')
    def test_context_arrival_resolves_only_after_available(self):
        c=next(x for x in canonical_cases() if x.case_id=='ambiguous-reference');r=replay_case(c);p={x.span_id:x for x in r.steps[1].predictions};self.assertEqual(p['amb'].topic_ids,('ATLAS',))
    def test_correction_changes_only_ambiguous_span_and_keeps_neighbor(self):
        c=next(x for x in canonical_cases() if x.case_id=='context-correction');r=replay_case(c);ref=[];neighbor=[]
        for step in r.steps:
            p={x.span_id:x for x in step.predictions};ref.append(p['ref'].topic_ids if p['ref'].status=='resolved' else ());neighbor.append(p['neighbor'].topic_ids)
        self.assertEqual(ref,[(),('ATLAS',),('BETA',)]);self.assertEqual(neighbor,[('NORTH',),('NORTH',),('NORTH',)])
    def test_prediction_inputs_ignore_hidden_expected_gold_fields(self):
        for c in canonical_cases():
            pc=prediction_case(c)
            for step in c.context_steps:
                mutated=replace(step,expected_span_topic_sets=(),expected_abstentions=())
                self.assertEqual(prediction_input(c,step),prediction_input(c,mutated))
                self.assertEqual(predict_step(pc,prediction_input(c,step)).predictions,predict_step(pc,prediction_input(c,mutated)).predictions)
    def test_replay_call_site_passes_only_sanitized_prediction_objects(self):
        c=next(x for x in canonical_cases() if x.case_id=='context-correction')
        original=replay_mod.predict_step
        seen=[]
        def guard(pcase, step):
            self.assertIsInstance(pcase,PredictionCase)
            self.assertIsInstance(step,ContextInput)
            self.assertEqual([f.name for f in fields(type(pcase))],['case_id','text','topics','spans'])
            self.assertEqual([f.name for f in fields(type(step))],['step_id','available_contexts'])
            forbidden={'memberships','topic_objects','context_steps','context_texts','tags','expected_span_topic_sets','expected_abstentions'}
            self.assertFalse(any(hasattr(pcase,x) for x in forbidden))
            self.assertFalse(any(hasattr(step,x) for x in forbidden))
            for sp in pcase.spans:
                self.assertIsInstance(sp,PredictionSpan)
                self.assertEqual([f.name for f in fields(type(sp))],['span_id','span','text'])
                self.assertFalse(hasattr(sp,'kind'));self.assertFalse(hasattr(sp,'origin'))
            seen.append((pcase,step))
            return original(pcase,step)
        with patch.object(replay_mod,'predict_step',side_effect=guard):
            r=replay_mod.replay_case(c)
        self.assertEqual(len(seen),3)
        self.assertEqual([x[1].step_id for x in seen],['no-context','initial-context','corrected-context'])
        self.assertEqual([tuple(cid for cid,_ in x[1].available_contexts) for x in seen],[(),('ctx1',),('ctx1','ctx2')])
        self.assertEqual([x.step_id for x in r.steps],['no-context','initial-context','corrected-context'])

    def test_replay_metrics(self):
        m=evaluate_replay(canonical_cases());self.assertEqual(m['step_exact']['value'],1.0);self.assertEqual(m['correction_success']['value'],1.0)
    def test_first_step_result_cannot_contain_later_context_id(self):
        c=next(x for x in canonical_cases() if x.case_id=='context-correction');r=replay_case(c);self.assertEqual(r.steps[0].available_context_ids,());self.assertEqual(r.steps[1].available_context_ids,('ctx1',));self.assertEqual(r.steps[2].available_context_ids,('ctx1','ctx2'))

if __name__=='__main__':unittest.main()

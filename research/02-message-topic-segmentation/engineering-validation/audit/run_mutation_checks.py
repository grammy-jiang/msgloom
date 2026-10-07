from __future__ import annotations
from pathlib import Path
import json, os, shutil, subprocess, tempfile

ROOT=Path('research/02-message-topic-segmentation/engineering-validation').resolve()
SRC=ROOT/'src/topic02_validation'
TESTS=ROOT/'tests'
MUTATIONS=[
    {
      'name':'allow_one_prediction_to_match_multiple_gold_spans',
      'file':'end_to_end.py','old':'if gi in used_g or pi in used_p: continue','new':'if gi in used_g: continue',
      'test':'test_end_to_end.EndToEndTests.test_greedy_match_never_reuses_prediction',
    },
    {
      'name':'allow_one_gold_span_to_match_multiple_predictions',
      'file':'end_to_end.py','old':'if gi in used_g or pi in used_p: continue','new':'if pi in used_p: continue',
      'test':'test_end_to_end.EndToEndTests.test_greedy_match_never_reuses_gold',
    },
    {
      'name':'hide_false_positive_membership_from_precision_denominator',
      'file':'metrics.py','old':'precision = Fraction(tp, len(predicted))','new':'precision = Fraction(tp, len(gold))',
      'test':'test_assignment.AssignmentTests.test_pair_prf_counts_extra_prediction',
    },
    {
      'name':'leak_future_context_texts_into_prediction_input',
      'file':'replay.py',
      'old':'tuple((cid, cmap[cid]) for cid in step_gold.available_context_ids),',
      'new':'tuple(case_gold.context_texts),',
      'test':'test_replay.ReplayTests.test_context_input_contains_only_current_materialized_context',
    },
    {
      'name':'pass_gold_evidence_span_kind_origin_to_predictor',
      'file':'replay.py',
      'old':'tuple(PredictionSpan(s.span_id, s.span, s.text) for s in case_gold.spans),',
      'new':'tuple(case_gold.spans),',
      'test':'test_replay.ReplayTests.test_prediction_case_ignores_case_gold_and_span_kind_origin_changes',
    },
    {
      'name':'collapse_all_assignment_ids_to_constant',
      'file':'representation.py','old':'aid = f"assign:{case.case_id}:{m.span_id}"','new':'aid = "assign:constant"',
      'test':'test_representation.RepresentationTests.test_from_gold_matches_independent_fixture_fields',
    },
    {
      'name':'erase_span_origin_and_kind_during_gold_conversion',
      'file':'representation.py',
      'old':'return TopicRepresentation(case.case_id, case.text, case.topics, case.spans, tuple(assignments), case.topic_objects)',
      'new':'return TopicRepresentation(case.case_id, case.text, case.topics, tuple(EvidenceSpan(x.span_id, x.span, x.text) for x in case.spans), tuple(assignments), case.topic_objects)',
      'test':'test_representation.RepresentationTests.test_from_gold_matches_independent_fixture_fields',
    },

    {
      'name':'bypass_prediction_case_sanitizer_at_replay_call_site',
      'file':'replay.py','old':'pcase = prediction_case(case)','new':'pcase = case',
      'test':'test_replay.ReplayTests.test_replay_call_site_passes_only_sanitized_prediction_objects',
    },
    {
      'name':'expose_gold_context_steps_on_prediction_case',
      'file':'replay.py',
      'old':'    spans: tuple[PredictionSpan, ...]',
      'new':'    spans: tuple[PredictionSpan, ...]\n    context_steps: tuple = ()',
      'test':'test_replay.ReplayTests.test_prediction_case_contains_no_gold_or_context_fields',
    },
    {
      'name':'drop_ambiguous_abstention_permission',
      'file':'representation.py',
      'old':'tuple(tuple(sorted(x)) for x in m.alternative_topic_sets),\n                m.abstention_allowed,',
      'new':'tuple(tuple(sorted(x)) for x in m.alternative_topic_sets),\n                False,',
      'test':'test_representation.RepresentationTests.test_abstention_permission_changes_canonical_representation',
    },
    {
      'name':'strip_all_but_first_alternative_set',
      'file':'representation.py',
      'old':'tuple(tuple(sorted(x)) for x in m.alternative_topic_sets),',
      'new':'(tuple(sorted(m.alternative_topic_sets[0])),),',
      'test':'test_representation.RepresentationTests.test_from_gold_matches_independent_fixture_fields',
    },
    {
      'name':'collapse_topic_objects_to_first_component',
      'file':'representation.py',
      'old':'return TopicRepresentation(case.case_id, case.text, case.topics, case.spans, tuple(assignments), case.topic_objects)',
      'new':'return TopicRepresentation(case.case_id, case.text, case.topics, case.spans, tuple(assignments), tuple(TopicObjectGold(x.topic_id, x.span_ids[:1]) for x in case.topic_objects))',
      'test':'test_representation.RepresentationTests.test_from_gold_matches_independent_fixture_fields',
    },
    {
      'name':'remove_coverage_floor_from_threshold_selection',
      'file':'uncertainty.py','old':"r['accepted_error']<=max_error and r['coverage']>=min_coverage",'new':"r['accepted_error']<=max_error",
      'test':'test_uncertainty.UncertaintyTests.test_no_all_abstain_threshold_can_satisfy_coverage_floor',
    },
]
rows=[]
for mutation in MUTATIONS:
    with tempfile.TemporaryDirectory(prefix='topic02-mutant-') as td:
        td=Path(td);pkg=td/'topic02_validation';shutil.copytree(SRC,pkg)
        target=pkg/mutation['file'];text=target.read_text()
        if mutation['old'] not in text:
            raise RuntimeError(f"target text not found for {mutation['name']}")
        target.write_text(text.replace(mutation['old'],mutation['new'],1))
        env=os.environ.copy();env['PYTHONPATH']=str(td)
        cmd=['python3','-m','unittest',mutation['test']]
        proc=subprocess.run(cmd,cwd=TESTS,env=env,text=True,capture_output=True)
        killed=proc.returncode!=0
        rows.append({
            'mutation':mutation['name'],'file':mutation['file'],'target_test':mutation['test'],
            'killed':killed,'test_exit_code':proc.returncode,
            'stdout_tail':proc.stdout[-800:],'stderr_tail':proc.stderr[-1200:],
        })
status='PASS' if all(r['killed'] for r in rows) else 'FAIL'
print(json.dumps({'status':status,'mutation_count':len(rows),'rows':rows},indent=2))
raise SystemExit(0 if status=='PASS' else 1)

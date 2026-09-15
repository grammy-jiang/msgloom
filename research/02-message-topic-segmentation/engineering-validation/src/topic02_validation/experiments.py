"""Reproducible Topic 02 EV1-EV7 synthetic engineering experiments."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import platform
import sys
from typing import Any

from .assignment import predict_case
from .domain import evaluate_styles
from .fixtures import canonical_cases, write_fixture_corpus
from .end_to_end import evaluate_unit_assignment
from .metrics import assignment_metrics, expected_calibration_error, reliability_bins, topic_object_ceiling
from .preservation import decision_preservation, predicted_decision_membership, topic_component_ceiling
from .representation import round_trip
from .replay import evaluate_replay
from .uncertainty import choose_threshold, evaluate, generate_examples
from .units import unitize

EXECUTION_STATUS = "EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC_WITH_IDENTIFIED_FAILURES"
REVIEW_STATUS = "PENDING_INDEPENDENT_REVIEW"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_ev1(root: Path) -> dict[str, Any]:
    cases=canonical_cases();manifest=write_fixture_corpus(root/'fixtures')
    roundtrip=0
    for case in cases:
        decoded=round_trip(case)
        roundtrip += int(decoded.case_id==case.case_id)
    memberships=[m for c in cases for m in c.memberships]
    objects=[o for c in cases for o in c.topic_objects]
    return {
        'status':'EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC',
        'case_count':len(cases),
        'topic_definition_count':sum(len(c.topics) for c in cases),
        'evidence_span_count':sum(len(c.spans) for c in cases),
        'membership_row_count':len(memberships),
        'topic_object_count':len(objects),
        'noncontiguous_topic_object_count':sum(len(o.span_ids)>1 for o in objects),
        'joint_membership_span_count':sum(len(m.required_topics)>1 for m in memberships),
        'ambiguous_membership_row_count':sum(m.ambiguous for m in memberships),
        'roundtrip_cases':{'numerator':roundtrip,'denominator':len(cases),'value':roundtrip/len(cases)},
        'fixture_manifest_sha256':_sha(root/'fixtures/MANIFEST.json'),
        'gold_independence':manifest['gold_independence'],
        'claim_boundary':'Demonstrates lossless research-harness representation of the authored synthetic gold. It does not approve a production schema.',
    }


def _unit_metrics(cases) -> dict[str,Any]:
    result={}
    for kind in ['sentence','clause','edu_like','hybrid']:
        unitizer=lambda t,k=kind:unitize(t,k)
        result[kind]={
            'topic_component_ceiling':topic_component_ceiling(cases,unitizer),
            'topic_object_ceiling':topic_object_ceiling(cases,unitizer),
            'decision_scope_projection':decision_preservation(cases,unitizer),
        }
    return result


def run_ev2() -> dict[str,Any]:
    metrics=_unit_metrics(canonical_cases())
    return {
        'status':'EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC',
        'unit_metrics':metrics,
        'identified_findings':[
            'Sentence-only units preserve all decision-bearing gold Topics in the current synthetic corpus but broaden scope into wrong neighboring Topics in five projected memberships.',
            'Clause/EDU-like/hybrid deterministic partitions remove those five sentence-level scope false positives in this synthetic corpus, while exact Topic-component boundary representability remains below 1.0.',
            'Unit representational ceiling and learned unit prediction are separate tasks; no learned unit model is evaluated here.',
        ],
        'claim_boundary':'Oracle representational-ceiling stress test over independently authored synthetic spans; not a production segmentation benchmark.',
    }


def run_ev3() -> dict[str,Any]:
    cases=canonical_cases();comparators={};end_to_end={}
    for mode in ['single_label','set_valued']:
        for context in ['span_only','local_window']:
            name=f'{mode}:{context}'
            comparators[name]=assignment_metrics(cases,lambda c,m=mode,x=context:predict_case(c,mode=m,context_mode=x))
    for unit in ['sentence','clause','edu_like','hybrid']:
        for mode in ['single_label','set_valued']:
            end_to_end[f'{unit}:{mode}']=evaluate_unit_assignment(cases,unit_kind=unit,mode=mode)
    return {
        'status':'EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC',
        'gold_span_conditioned_membership':comparators,
        'end_to_end_unit_membership':end_to_end,
        'identified_findings':[
            'The single-label span-only comparator cannot preserve all joint memberships; overlap-only membership recall is lower than the set-valued comparator.',
            'Naive local-window set-valued context raises recall but introduces many false memberships, demonstrating scope broadening from neighboring matters.',
            'Ambiguous current evidence is scored separately from joint membership; the comparator abstains rather than forcing one of the acceptable alternatives.',
        ],
        'claim_boundary':'Transparent lexical comparators use fixture-supplied gold Topic definitions/counts as controlled oracle inputs. They are not automatic Topic discovery, a trained Topic model, or a production accuracy estimate.',
    }


def run_ev4() -> dict[str,Any]:
    cases=canonical_cases();oracle={};predicted={}
    for kind in ['sentence','clause','edu_like','hybrid']:
        oracle[kind]=decision_preservation(cases,lambda t,k=kind:unitize(t,k))
    for context in ['span_only','local_window']:
        predicted[f'set_valued:{context}']=predicted_decision_membership(cases,lambda c,x=context:predict_case(c,mode='set_valued',context_mode=x))
    return {
        'status':'EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC',
        'oracle_unit_scope':oracle,
        'predicted_decision_membership':predicted,
        'identified_findings':[
            'Sentence-level oracle projection creates wrong-Topic scope broadening even when decision-bearing source text is not omitted.',
            'Local-window assignment can add false decision-bearing Topic memberships; those predictions are included in precision denominators rather than discarded as unmatched extras.',
        ],
        'claim_boundary':'Synthetic decision/condition/exception/deadline/evidence scope diagnostic. It does not estimate natural workplace-email loss prevalence.',
    }


def run_ev5() -> dict[str,Any]:
    return {
        'status':'EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC',
        **evaluate_replay(canonical_cases()),
        'future_context_used':False,
        'semantic_response_scope_evaluated':False,
        'topic04_handoff':'Semantic response/agreement scope is not evaluated here.',
    }


def run_ev6() -> dict[str,Any]:
    calibration=generate_examples(seed=20260915,count_per_family=40,variant='calibration')
    test=generate_examples(seed=20260916,count_per_family=40,variant='holdout')
    cal_keys={x.content_key for x in calibration};test_keys={x.content_key for x in test}
    cal_templates=sorted({x.template_family for x in calibration});test_templates=sorted({x.template_family for x in test})
    if cal_keys & test_keys: raise RuntimeError('calibration/test content overlap')
    if set(cal_templates)&set(test_templates): raise RuntimeError('calibration/test template-family overlap')
    selection=choose_threshold(calibration,max_error=.05,min_coverage=.40)
    threshold=selection['selected_threshold'] if selection['selected_threshold'] is not None else selection['fallback_threshold']
    evaluated=[evaluate(x,threshold=threshold) for x in test]
    accepted=[x for x in evaluated if not x.abstained];wrong=[x for x in accepted if not x.correct]
    by_family={}
    for fam in sorted({x.example.family for x in evaluated}):
        rows=[x for x in evaluated if x.example.family==fam];acc=[x for x in rows if not x.abstained];bad=[x for x in acc if not x.correct]
        by_family[fam]={'count':len(rows),'accepted':len(acc),'abstained':len(rows)-len(acc),'wrong_accepted':len(bad),'coverage':len(acc)/len(rows),'accepted_error':len(bad)/len(acc) if acc else 0.0}
    reliability=[(x.confidence,x.correct) for x in accepted]
    return {
        'status':'EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC',
        'calibration_examples':len(calibration),'test_examples':len(test),
        'calibration_template_families':cal_templates,'test_template_families':test_templates,
        'content_overlap_count':len(cal_keys&test_keys),
        'selection':selection,'evaluated_threshold':threshold,
        'test_coverage':{'numerator':len(accepted),'denominator':len(evaluated),'value':len(accepted)/len(evaluated)},
        'test_accepted_error':{'numerator':len(wrong),'denominator':len(accepted),'value':len(wrong)/len(accepted) if accepted else None},
        'reliability_bins':reliability_bins(reliability,5),
        'accepted_prediction_ece':expected_calibration_error(reliability,5),
        'by_family':by_family,
        'target_met':selection['target_met'],
        'identified_failure_modes':[
            'No tested threshold simultaneously satisfies accepted-error <= 5% and coverage >= 40% on the calibration distribution.',
            'The fallback useful-coverage threshold predicts both matters for every near-collision example where the second matter is only background context, yielding systematic false joint membership.',
            'All-abstain thresholds are not accepted as a successful calibration solution because they violate the explicit coverage floor.',
        ],
        'topic10_handoff':'General calibration/selective-prediction method selection remains Topic 10; Topic 02 records the assignment-specific failure and plumbing only.',
        'claim_boundary':'Disjoint authored synthetic calibration/holdout diagnostic only; no production calibration claim.',
    }


def run_ev7() -> dict[str,Any]:
    return evaluate_styles(canonical_cases())


def run_all(root: Path) -> dict[str,Any]:
    started=datetime.now(timezone.utc)
    ev1=run_ev1(root)
    ev2=run_ev2()
    ev3=run_ev3()
    ev4=run_ev4()
    ev5=run_ev5()
    ev6=run_ev6()
    ev7=run_ev7()
    finished=datetime.now(timezone.utc)
    return {
        'run_schema':'topic02-engineering-run-v1',
        'experiment_execution_status':EXECUTION_STATUS,
        'independent_review_status':REVIEW_STATUS,
        'started_at_utc':started.isoformat(),
        'finished_at_utc':finished.isoformat(),
        'python':sys.version,'platform':platform.platform(),
        'production_data_used':False,'external_network_used':False,
        'scope':'Topic 02 EV1-EV7 synthetic engineering validation after Academic Round 2',
        'EV1':ev1,'EV2':ev2,'EV3':ev3,'EV4':ev4,
        'EV5':ev5,'EV6':ev6,'EV7':ev7,
    }


def _deterministic_view(result: dict[str,Any]) -> dict[str,Any]:
    return {k:v for k,v in result.items() if k not in {'started_at_utc','finished_at_utc','python','platform'}}


def write_results(root: Path, result: dict[str,Any]) -> None:
    results=root/'results';audit=root/'audit';results.mkdir(parents=True,exist_ok=True);audit.mkdir(parents=True,exist_ok=True)
    (results/'experiment-run.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    deterministic=_deterministic_view(result)
    (results/'metrics.json').write_text(json.dumps(deterministic,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    ev2=result['EV2'];ev3=result['EV3'];ev4=result['EV4'];ev6=result['EV6'];ev7=result['EV7']
    sspan=ev3['gold_span_conditioned_membership']['single_label:span_only'];mspan=ev3['gold_span_conditioned_membership']['set_valued:span_only'];mlocal=ev3['gold_span_conditioned_membership']['set_valued:local_window']
    md=f'''# Topic 02 engineering-validation results\n\n## Status\n\n- Experiment execution: **{result['experiment_execution_status']}**\n- Independent review: **{result['independent_review_status']}**\n\nNo production mailbox data or external network access was used by the experiment runner. These are synthetic/adversarial engineering results only.\n\n## EV1 — Lossless representation\n\n- Cases: **{result['EV1']['case_count']}**; evidence spans: **{result['EV1']['evidence_span_count']}**; membership rows: **{result['EV1']['membership_row_count']}**.\n- Non-contiguous Topic objects: **{result['EV1']['noncontiguous_topic_object_count']}**; joint-membership spans: **{result['EV1']['joint_membership_span_count']}**; ambiguous rows: **{result['EV1']['ambiguous_membership_row_count']}**.\n- Canonical representation round trips: **{result['EV1']['roundtrip_cases']['numerator']}/{result['EV1']['roundtrip_cases']['denominator']}**.\n\nThis validates the research representation contract only, not a production schema. Topic identities/counts are fixture-supplied controlled gold, not automatically discovered.\n\n## EV2 — Unit representational ceiling\n\n| Unit | Exact Topic components | Extra scope chars | Decision-scope precision |\n| --- | ---: | ---: | ---: |\n'''
    for kind in ['sentence','clause','edu_like','hybrid']:
        row=ev2['unit_metrics'][kind];md+=f"| {kind} | {row['topic_component_ceiling']['exact_topic_component_spans']['value']:.3f} | {row['topic_component_ceiling']['total_extra_scope_chars']} | {row['decision_scope_projection']['precision']['value']:.3f} |\n"
    md+=f'''\nSentence-level projection has full decision-scope recall in the frozen synthetic corpus but **{ev2['unit_metrics']['sentence']['decision_scope_projection']['false_positive']} wrong-Topic scope false positives**. Clause/EDU-like/hybrid remove those false positives here, but exact character-boundary representability remains below 1.0.\n\n## EV3 — Set-valued Topic assignment\n\n### Gold-span-conditioned membership diagnostic\n\n- Single-label span-only membership P/R: **{sspan['membership_micro']['precision']['value']:.3f}/{sspan['membership_micro']['recall']['value']:.3f}**; overlap recall **{sspan['overlap_only_membership']['recall']['value']:.3f}**.\n- Set-valued span-only membership P/R: **{mspan['membership_micro']['precision']['value']:.3f}/{mspan['membership_micro']['recall']['value']:.3f}**; overlap recall **{mspan['overlap_only_membership']['recall']['value']:.3f}**.\n- Set-valued local-window P/R: **{mlocal['membership_micro']['precision']['value']:.3f}/{mlocal['membership_micro']['recall']['value']:.3f}**.\n\nSet-valued output materially improves overlap recall. Naive local context obtains high recall by adding many false memberships; those errors remain in the denominator. These numbers are explicitly **gold-span-conditioned** and are not end-to-end span scores.\n\n### Deterministic unit + membership end-to-end baseline\n\n- Sentence + set-valued IoU>=0.5 P/R: **{ev3['end_to_end_unit_membership']['sentence:set_valued']['membership_span_iou50_precision']['value']:.3f}/{ev3['end_to_end_unit_membership']['sentence:set_valued']['membership_span_iou50_recall']['value']:.3f}**; exact-boundary recall **{ev3['end_to_end_unit_membership']['sentence:set_valued']['exact_boundary_match_recall']['value']:.3f}**.\n- Clause + set-valued IoU>=0.5 P/R: **{ev3['end_to_end_unit_membership']['clause:set_valued']['membership_span_iou50_precision']['value']:.3f}/{ev3['end_to_end_unit_membership']['clause:set_valued']['membership_span_iou50_recall']['value']:.3f}**; exact-boundary recall **{ev3['end_to_end_unit_membership']['clause:set_valued']['exact_boundary_match_recall']['value']:.3f}**.\n- Clause + set-valued exact non-contiguous Topic objects: **{ev3['end_to_end_unit_membership']['clause:set_valued']['exact_noncontiguous_topic_objects']['value']:.3f}**.\n\nExtra predicted Topic spans and missed gold spans are included in these end-to-end denominators.\n\n## EV4 — Decision-bearing preservation\n\n- Sentence oracle scope P/R: **{ev4['oracle_unit_scope']['sentence']['precision']['value']:.3f}/{ev4['oracle_unit_scope']['sentence']['recall']['value']:.3f}**.\n- Clause oracle scope P/R: **{ev4['oracle_unit_scope']['clause']['precision']['value']:.3f}/{ev4['oracle_unit_scope']['clause']['recall']['value']:.3f}**.\n- Set-valued span-only predicted decision membership P/R: **{ev4['predicted_decision_membership']['set_valued:span_only']['precision']['value']:.3f}/{ev4['predicted_decision_membership']['set_valued:span_only']['recall']['value']:.3f}**.\n- Set-valued local-window predicted decision membership P/R: **{ev4['predicted_decision_membership']['set_valued:local_window']['precision']['value']:.3f}/{ev4['predicted_decision_membership']['set_valued:local_window']['recall']['value']:.3f}**.\n- Scored required decision-bearing spans/memberships: **{ev4['predicted_decision_membership']['set_valued:span_only']['annotation_inventory']['total']['scored_required_spans']}/{ev4['predicted_decision_membership']['set_valued:span_only']['annotation_inventory']['total']['scored_required_memberships']}**; ambiguous decision-bearing spans excluded from required-membership scoring: **{ev4['predicted_decision_membership']['set_valued:span_only']['annotation_inventory']['total']['excluded_ambiguous_spans']}**.\n\n| Decision kind | Annotated spans | Scored required spans | Required memberships | Span-only P/R | Local-window P/R |\n| --- | ---: | ---: | ---: | ---: | ---: |\n{''.join(f"| {kind} | {inv['annotated_spans']} | {inv['scored_required_spans']} | {inv['scored_required_memberships']} | {ev4['predicted_decision_membership']['set_valued:span_only']['by_kind'][kind]['precision']['value'] if ev4['predicted_decision_membership']['set_valued:span_only']['by_kind'][kind]['precision']['value'] is not None else 'N/A'}/{ev4['predicted_decision_membership']['set_valued:span_only']['by_kind'][kind]['recall']['value'] if ev4['predicted_decision_membership']['set_valued:span_only']['by_kind'][kind]['recall']['value'] is not None else 'N/A'} | {ev4['predicted_decision_membership']['set_valued:local_window']['by_kind'][kind]['precision']['value'] if ev4['predicted_decision_membership']['set_valued:local_window']['by_kind'][kind]['precision']['value'] is not None else 'N/A'}/{ev4['predicted_decision_membership']['set_valued:local_window']['by_kind'][kind]['recall']['value'] if ev4['predicted_decision_membership']['set_valued:local_window']['by_kind'][kind]['recall']['value'] is not None else 'N/A'} |\n" for kind,inv in ev4['predicted_decision_membership']['set_valued:span_only']['annotation_inventory']['by_kind'].items())}\n\nThese are **selected independently authored synthetic decision-bearing annotations**, not a source-complete semantic inventory. Predicted decision membership is gold-span-conditioned and does not measure decision-span detection.\n\n## EV5 — Incremental context/correction\n\n- Step exact: **{result['EV5']['step_exact']['numerator']}/{result['EV5']['step_exact']['denominator']}**.\n- Expected abstention: **{result['EV5']['expected_abstention']['numerator']}/{result['EV5']['expected_abstention']['denominator']}**.\n- Correction success: **{result['EV5']['correction_success']['numerator']}/{result['EV5']['correction_success']['denominator']}**.\n- Future context used: **{str(result['EV5']['future_context_used']).lower()}**.\n\nSemantic response/agreement scope is deliberately not evaluated and remains Topic 04.\n\n## EV6 — Assignment uncertainty/abstention\n\n- Calibration/test examples: **{ev6['calibration_examples']}/{ev6['test_examples']}**, with disjoint template families and **{ev6['content_overlap_count']}** exact content overlap.\n- Target: accepted error <= {ev6['selection']['target_max_accepted_error']:.2f} with coverage >= {ev6['selection']['target_min_coverage']:.2f}.\n- Target met: **{ev6['target_met']}**.\n- Fallback useful-coverage threshold: **{ev6['evaluated_threshold']}**.\n- Holdout coverage/error: **{ev6['test_coverage']['value']:.3f}/{ev6['test_accepted_error']['value']:.3f}**.\n\nThe simple baseline **fails** the joint error/coverage target. An all-abstain threshold is not accepted as success.\n\n## EV7 — Synthetic workplace-style stratification\n\nThis is not production-domain validation. Per-style results are recorded in `results/metrics.json`. The strata include plain prose, multi-clause sentences, structured list/table content, quoted history, context-dependent references, and overlap/non-contiguous cases.\n\n## Supporting artifact audit\n\n`audit/SUPPORTING_ARTIFACT_AUDIT.md` records G1-E/G2-E1/G6-E1/G6-E2. Missing external annotation/scorer details remain explicit unknowns and are not guessed.\n\n## Deferred\n\nProduction representativeness, G10/Topic 03, semantic response scope/Topic 04, general calibration methodology/Topic 10, conditional external-method reproduction, and Raspberry Pi performance remain deferred as documented in `DEFERRED.md`.\n'''
    (root/'RESULTS.md').write_text(md)
    support_audit=root/'audit/SUPPORTING_ARTIFACT_AUDIT.md'
    manifest={
        'metrics_path':str((results/'metrics.json').relative_to(root)),
        'metrics_sha256':_sha(results/'metrics.json'),
        'experiment_run_sha256':_sha(results/'experiment-run.json'),
        'fixture_manifest_sha256':_sha(root/'fixtures/MANIFEST.json'),
        'supporting_artifact_audit_sha256':_sha(support_audit) if support_audit.exists() else None,
        'source_files':{},'test_files':{},
    }
    for p in sorted((root/'src/topic02_validation').glob('*.py')):manifest['source_files'][str(p.relative_to(root))]=_sha(p)
    for p in sorted((root/'tests').glob('test_*.py')):manifest['test_files'][str(p.relative_to(root))]=_sha(p)
    (audit/'experiment-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


def main() -> int:
    root=Path(__file__).resolve().parents[2]
    result=run_all(root);write_results(root,result)
    print(json.dumps({'experiment_execution_status':result['experiment_execution_status'],'independent_review_status':result['independent_review_status'],'metrics':str(root/'results/metrics.json')},indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())

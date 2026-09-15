"""Incremental context/correction diagnostic for EV5.

Prediction inputs are structurally separated from evaluation gold. `PredictionCase`
contains only case text, supplied Topic definitions, and prediction-only spans.
`ContextInput` contains only the step identifier and currently materialized
`(context_id, text)` pairs. Gold expected assignments/abstentions are consumed
only by `evaluate_replay`.
"""
from __future__ import annotations
from dataclasses import dataclass
import re
from .assignment import AssignmentPrediction, predict
from .models import BenchmarkCase, ContextStepGold, Span, TopicDefinition


@dataclass(frozen=True)
class PredictionSpan:
    span_id: str
    span: Span
    text: str


@dataclass(frozen=True)
class PredictionCase:
    """All and only message/Topic information available to EV5 prediction.

    Deliberately excludes memberships, Topic-object gold, context-step gold,
    tags, span semantic kind/origin labels, and all context text.
    """
    case_id: str
    text: str
    topics: tuple[TopicDefinition, ...]
    spans: tuple[PredictionSpan, ...]


@dataclass(frozen=True)
class ContextInput:
    step_id: str
    available_contexts: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class StepResult:
    case_id: str
    step_id: str
    available_context_ids: tuple[str, ...]
    predictions: tuple[AssignmentPrediction, ...]


@dataclass(frozen=True)
class ReplayResult:
    case_id: str
    steps: tuple[StepResult, ...]


def prediction_case(case_gold: BenchmarkCase) -> PredictionCase:
    """Drop all evaluation-only case fields before prediction."""
    return PredictionCase(
        case_gold.case_id,
        case_gold.text,
        case_gold.topics,
        tuple(PredictionSpan(s.span_id, s.span, s.text) for s in case_gold.spans),
    )


def prediction_input(case_gold: BenchmarkCase, step_gold: ContextStepGold) -> ContextInput:
    """Materialize only contexts available at this evaluation step."""
    cmap = dict(case_gold.context_texts)
    return ContextInput(
        step_gold.step_id,
        tuple((cid, cmap[cid]) for cid in step_gold.available_context_ids),
    )


def _last_context_override(case: PredictionCase, context_text: str) -> str | None:
    m = re.search(r"(?i)refers to\s+([A-Za-z0-9_-]+)", context_text)
    if m:
        token = m.group(1).lower()
        for topic in case.topics:
            if topic.topic_id.lower() == token or token in {x.lower() for x in topic.signature_terms}:
                return topic.topic_id
    words = set(re.findall(r"[A-Za-z0-9]+", context_text.lower()))
    hits=[]
    all_terms={t.topic_id:{x.lower() for x in t.signature_terms} for t in case.topics}
    for topic in case.topics:
        others=set().union(*(v for k,v in all_terms.items() if k!=topic.topic_id))
        if words & (all_terms[topic.topic_id]-others): hits.append(topic.topic_id)
    return hits[0] if len(hits)==1 else None


def predict_step(case: PredictionCase, step: ContextInput) -> StepResult:
    """Predict from message text, supplied Topic definitions and available context only."""
    available=[text for _, text in step.available_contexts]
    last=available[-1] if available else ""
    override=_last_context_override(case,last) if last else None
    preds=[]
    for span in case.spans:
        base=predict(case,span,mode="set_valued",context_mode="span_only")
        if override and base.status=="abstained":
            preds.append(AssignmentPrediction(span.span_id,(override,),"resolved",base.scores,"context_override_on_unresolved_span"))
        else:
            preds.append(base)
    return StepResult(case.case_id,step.step_id,tuple(cid for cid,_ in step.available_contexts),tuple(preds))


def replay_case(case: BenchmarkCase) -> ReplayResult:
    pcase = prediction_case(case)
    return ReplayResult(case.case_id,tuple(predict_step(pcase,prediction_input(case, step)) for step in case.context_steps))


def evaluate_replay(cases: tuple[BenchmarkCase,...]) -> dict:
    step_total=step_exact=0
    abst_total=abst_correct=0
    transitions=corrections=0
    rows=[]
    for case in cases:
        if not case.context_steps: continue
        result=replay_case(case)
        previous: dict[str, tuple[str,...] | None]={}
        for step_gold,step_result in zip(case.context_steps,result.steps):
            pred={p.span_id:(p.topic_ids if p.status=="resolved" else None) for p in step_result.predictions}
            expected={sid:tuple(sorted(tids)) for sid,tids in step_gold.expected_span_topic_sets}
            expected_abst=set(step_gold.expected_abstentions)
            exact=True
            for sid,tids in expected.items():
                ok=pred.get(sid)==tids; exact &= ok
                if sid in previous and previous[sid] is not None and previous[sid]!=tids:
                    transitions+=1; corrections+=int(ok)
                previous[sid]=pred.get(sid)
            for sid in expected_abst:
                abst_total+=1; ok=pred.get(sid) is None; abst_correct+=int(ok); exact &= ok
                if sid in previous and previous[sid] is not None: transitions+=1
                previous[sid]=pred.get(sid)
            step_total+=1;step_exact+=int(exact)
            rows.append({'case_id':case.case_id,'step_id':step_gold.step_id,'available_context_ids':list(step_result.available_context_ids),'expected':{**{k:list(v) for k,v in expected.items()},**{k:'ABSTAIN' for k in expected_abst}},'predicted':{k:(list(v) if v else 'ABSTAIN') for k,v in pred.items() if k in set(expected)|expected_abst},'exact':exact})
    from .metrics import Fraction
    return {
        'step_exact':Fraction(step_exact,step_total).to_dict(),
        'expected_abstention':Fraction(abst_correct,abst_total).to_dict(),
        'correction_success':Fraction(corrections,transitions).to_dict(),
        'rows':rows,
        'prediction_input_contract':'PredictionCase(case_id,text,topics,PredictionSpan[id,span,text]) plus ContextInput(step_id, available_contexts) only; memberships, Topic objects, semantic span kind/origin, context-step gold, future context collections, and expected assignments/abstentions are outside predictor inputs.',
        'claim_boundary':'Controlled context-step diagnostic only; no production coreference/semantic-response accuracy claim.'
    }

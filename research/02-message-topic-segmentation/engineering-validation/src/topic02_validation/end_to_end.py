"""End-to-end deterministic unit + Topic membership comparators for EV2/EV3.

Unlike assignment.py's gold-span-conditioned diagnostic, these comparators start
from deterministic predicted units and therefore include extra/missing predicted
spans in the evaluation denominators.
"""
from __future__ import annotations
from dataclasses import dataclass
from .assignment import predict
from .models import BenchmarkCase, EvidenceSpan, Span
from .units import unitize
from .metrics import Fraction


@dataclass(frozen=True)
class PredictedTopicSpan:
    prediction_id: str
    span: Span
    topic_id: str
    text: str


def predict_topic_spans(case: BenchmarkCase, *, unit_kind: str, mode: str = "set_valued", threshold: float = 0.34) -> tuple[PredictedTopicSpan,...]:
    out=[]
    for index,unit in enumerate(unitize(case.text,unit_kind)):
        synthetic=EvidenceSpan(f"pred:{unit_kind}:{index}",unit.span,unit.text)
        p=predict(case,synthetic,mode=mode,context_mode="span_only",threshold=threshold)
        if p.status!='resolved':
            continue
        for tid in p.topic_ids:
            out.append(PredictedTopicSpan(f"{synthetic.span_id}:{tid}",unit.span,tid,unit.text))
    return tuple(out)


def gold_topic_spans(case: BenchmarkCase) -> tuple[PredictedTopicSpan,...]:
    out=[]
    seen=set()
    for obj in case.topic_objects:
        for sid in obj.span_ids:
            key=(sid,obj.topic_id)
            if key in seen: continue
            seen.add(key)
            span=case.span(sid)
            out.append(PredictedTopicSpan(f"gold:{sid}:{obj.topic_id}",span.span,obj.topic_id,span.text))
    return tuple(out)


def _greedy_match(gold: tuple[PredictedTopicSpan,...], pred: tuple[PredictedTopicSpan,...], *, min_iou: float) -> list[tuple[int,int,float]]:
    candidates=[]
    for gi,g in enumerate(gold):
        for pi,p in enumerate(pred):
            if g.topic_id!=p.topic_id: continue
            iou=g.span.iou(p.span)
            if iou>=min_iou:
                candidates.append((iou,gi,pi))
    candidates.sort(key=lambda x:(-x[0],x[1],x[2]))
    used_g=set();used_p=set();matches=[]
    for iou,gi,pi in candidates:
        if gi in used_g or pi in used_p: continue
        used_g.add(gi);used_p.add(pi);matches.append((gi,pi,iou))
    return matches


def evaluate_unit_assignment(cases: tuple[BenchmarkCase,...], *, unit_kind: str, mode: str = "set_valued", min_iou: float = 0.5) -> dict:
    gold_total=pred_total=matched_total=exact_total=0
    complete_objects=complete_objects_exact=0
    noncont_total=noncont_exact=0
    rows=[]
    for case in cases:
        gold=gold_topic_spans(case);pred=predict_topic_spans(case,unit_kind=unit_kind,mode=mode)
        matches=_greedy_match(gold,pred,min_iou=min_iou)
        gold_total+=len(gold);pred_total+=len(pred);matched_total+=len(matches)
        exact_total+=sum(gold[gi].span==pred[pi].span for gi,pi,_ in matches)
        matched_gold={(gold[gi].topic_id,gold[gi].span.start,gold[gi].span.end) for gi,_,_ in matches}
        matched_pred={(pred[pi].topic_id,pred[pi].span.start,pred[pi].span.end) for _,pi,_ in matches}
        for obj in case.topic_objects:
            complete_objects+=1
            if len(obj.span_ids)>1:noncont_total+=1
            gold_set={(obj.topic_id,case.span(sid).span.start,case.span(sid).span.end) for sid in obj.span_ids}
            pred_set={(x.topic_id,x.span.start,x.span.end) for x in pred if x.topic_id==obj.topic_id}
            ok=pred_set==gold_set
            complete_objects_exact+=int(ok)
            if len(obj.span_ids)>1:noncont_exact+=int(ok)
        rows.append({
            'case_id':case.case_id,'gold_count':len(gold),'predicted_count':len(pred),
            'matched_iou50':len(matches),'exact_boundary_matches':sum(gold[gi].span==pred[pi].span for gi,pi,_ in matches),
            'false_positive_predictions':len(pred)-len(matches),'false_negative_gold':len(gold)-len(matches),
            'matches':[{'gold_id':gold[gi].prediction_id,'prediction_id':pred[pi].prediction_id,'iou':iou,'exact':gold[gi].span==pred[pi].span} for gi,pi,iou in matches],
        })
    precision=Fraction(matched_total,pred_total);recall=Fraction(matched_total,gold_total)
    p=precision.value or 0.0;r=recall.value or 0.0
    return {
        'unit_kind':unit_kind,'mode':mode,'min_iou':min_iou,
        'membership_span_iou50_precision':precision.to_dict(),
        'membership_span_iou50_recall':recall.to_dict(),
        'membership_span_iou50_f1':2*p*r/(p+r) if p+r else 0.0,
        'exact_boundary_match_recall':Fraction(exact_total,gold_total).to_dict(),
        'false_positive_predicted_topic_spans':pred_total-matched_total,
        'false_negative_gold_topic_spans':gold_total-matched_total,
        'exact_complete_topic_objects':Fraction(complete_objects_exact,complete_objects).to_dict(),
        'exact_noncontiguous_topic_objects':Fraction(noncont_exact,noncont_total).to_dict(),
        'rows':rows,
        'claim_boundary':'Deterministic unit + lexical assignment baseline. Unlike gold-span-conditioned membership, extra/missing predicted spans enter denominators.',
    }

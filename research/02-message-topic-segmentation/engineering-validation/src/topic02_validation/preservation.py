"""Decision-bearing preservation diagnostics for EV4.

The synthetic decision-bearing annotations are deliberately selected stress
labels, not a source-complete semantic inventory. Metrics expose both category
populations and exclusions so aggregate scores cannot be read as natural
prevalence or complete source coverage.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Iterable
from .models import BenchmarkCase, Span
from .units import best_cover
from .metrics import Fraction, pair_prf

DECISION_KINDS = {
    "condition", "exception", "deadline", "approval_constraint",
    "decision", "supporting_evidence",
}


def project_topic_objects(case: BenchmarkCase, unitizer) -> dict[str, tuple[Span, ...]]:
    units = unitizer(case.text)
    projected: dict[str, list[Span]] = {}
    for obj in case.topic_objects:
        rows = projected.setdefault(obj.topic_id, [])
        for sid in obj.span_ids:
            hull, _ = best_cover(case.span(sid).span, units)
            if hull is not None and hull not in rows:
                rows.append(hull)
    return {k: tuple(sorted(v)) for k, v in projected.items()}


def _inventory(cases: Iterable[BenchmarkCase]) -> dict:
    by_kind: dict[str, dict[str, int]] = defaultdict(lambda: {"annotated_spans":0,"scored_required_spans":0,"scored_required_memberships":0,"excluded_ambiguous_spans":0,"excluded_unassigned_spans":0})
    total={"annotated_spans":0,"scored_required_spans":0,"scored_required_memberships":0,"excluded_ambiguous_spans":0,"excluded_unassigned_spans":0}
    for case in cases:
        memberships={m.span_id:m for m in case.memberships}
        for span in case.spans:
            if span.kind not in DECISION_KINDS: continue
            row=by_kind[span.kind];row["annotated_spans"]+=1;total["annotated_spans"]+=1
            m=memberships.get(span.span_id)
            if m and m.required_topics:
                row["scored_required_spans"]+=1;total["scored_required_spans"]+=1
                row["scored_required_memberships"]+=len(m.required_topics);total["scored_required_memberships"]+=len(m.required_topics)
            elif m and m.alternative_topic_sets:
                row["excluded_ambiguous_spans"]+=1;total["excluded_ambiguous_spans"]+=1
            else:
                row["excluded_unassigned_spans"]+=1;total["excluded_unassigned_spans"]+=1
    return {"total":total,"by_kind":dict(sorted(by_kind.items())),"annotation_scope_warning":"Selected independently authored stress annotations only; other semantically important phrases may intentionally be unlabeled. These denominators are not a source-complete semantic inventory."}


def _kind_metrics(gold_by_kind, pred_by_kind, exact_by_kind, span_total_by_kind) -> dict:
    kinds=sorted(set(gold_by_kind)|set(pred_by_kind)|set(span_total_by_kind))
    out={}
    for kind in kinds:
        prf=pair_prf(gold_by_kind.get(kind,set()),pred_by_kind.get(kind,set()))
        prf["exact_span_topic_scope"]=Fraction(exact_by_kind.get(kind,0),span_total_by_kind.get(kind,0)).to_dict()
        out[kind]=prf
    return out


def decision_preservation(cases: Iterable[BenchmarkCase], unitizer) -> dict:
    cases=tuple(cases)
    gold_pairs: set[tuple[str, str, str]] = set();pred_pairs: set[tuple[str, str, str]] = set()
    gold_kind=defaultdict(set);pred_kind=defaultdict(set);exact_kind=defaultdict(int);span_kind=defaultdict(int)
    rows=[];total_spans=exact_spans=0
    for case in cases:
        projected=project_topic_objects(case,unitizer);memberships={m.span_id:m for m in case.memberships}
        for span in case.spans:
            if span.kind not in DECISION_KINDS: continue
            m=memberships.get(span.span_id)
            if not m or not m.required_topics:
                rows.append({"case_id":case.case_id,"span_id":span.span_id,"kind":span.kind,"scored":False,"exclusion":"ambiguous" if m and m.alternative_topic_sets else "unassigned"})
                continue
            total_spans+=1;span_kind[span.kind]+=1
            predicted_topics={tid for tid,pspans in projected.items() if any(p.start<=span.span.start and p.end>=span.span.end for p in pspans)}
            for tid in m.required_topics:
                key=(case.case_id,span.span_id,tid);gold_pairs.add(key);gold_kind[span.kind].add(key)
            for tid in predicted_topics:
                key=(case.case_id,span.span_id,tid);pred_pairs.add(key);pred_kind[span.kind].add(key)
            exact=predicted_topics==set(m.required_topics);exact_spans+=int(exact);exact_kind[span.kind]+=int(exact)
            rows.append({"case_id":case.case_id,"span_id":span.span_id,"kind":span.kind,"scored":True,"gold_topics":list(m.required_topics),"predicted_topics":sorted(predicted_topics),"exact_topic_scope":exact})
    metrics=pair_prf(gold_pairs,pred_pairs)
    metrics.update({
        "exact_decision_span_topic_scope":Fraction(exact_spans,total_spans).to_dict(),
        "annotation_inventory":_inventory(cases),
        "by_kind":_kind_metrics(gold_kind,pred_kind,exact_kind,span_kind),
        "rows":rows,
        "claim_boundary":"Oracle unit-projection score on selected synthetic decision-bearing annotations. It is not source-complete semantic preservation or production loss prevalence.",
    })
    return metrics


def topic_component_ceiling(cases: Iterable[BenchmarkCase], unitizer) -> dict:
    total=exact=0;extra=missing=0;rows=[]
    for case in cases:
        units=unitizer(case.text);eligible={(obj.topic_id,sid) for obj in case.topic_objects for sid in obj.span_ids}
        for topic_id,sid in sorted(eligible):
            total+=1;gold=case.span(sid);hull,ok=best_cover(gold.span,units);exact+=int(ok)
            if hull is None:ex=0;miss=gold.span.length
            else:ov=hull.overlap(gold.span);ex=hull.length-ov;miss=gold.span.length-ov
            extra+=ex;missing+=miss
            rows.append({"case_id":case.case_id,"topic_id":topic_id,"span_id":sid,"gold":gold.span.to_dict(),"cover":hull.to_dict() if hull else None,"exact":ok,"extra_chars":ex,"missing_chars":miss})
    return {"exact_topic_component_spans":Fraction(exact,total).to_dict(),"total_extra_scope_chars":extra,"total_missing_chars":missing,"rows":rows}


def predicted_decision_membership(cases: Iterable[BenchmarkCase], predictor) -> dict:
    """Gold-span-conditioned Topic membership on selected decision-bearing spans."""
    cases=tuple(cases)
    gold_pairs:set[tuple[str,str,str]]=set();pred_pairs:set[tuple[str,str,str]]=set()
    gold_kind=defaultdict(set);pred_kind=defaultdict(set);exact_kind=defaultdict(int);span_kind=defaultdict(int)
    exact_total=exact_count=0;rows=[]
    for case in cases:
        preds={p.span_id:p for p in predictor(case)};memberships={m.span_id:m for m in case.memberships}
        for span in case.spans:
            if span.kind not in DECISION_KINDS:continue
            m=memberships.get(span.span_id)
            if not m or not m.required_topics:
                rows.append({"case_id":case.case_id,"span_id":span.span_id,"kind":span.kind,"scored":False,"exclusion":"ambiguous" if m and m.alternative_topic_sets else "unassigned"})
                continue
            exact_total+=1;span_kind[span.kind]+=1
            for tid in m.required_topics:
                key=(case.case_id,span.span_id,tid);gold_pairs.add(key);gold_kind[span.kind].add(key)
            p=preds.get(span.span_id);predicted=set(p.topic_ids) if p is not None and p.status=='resolved' else set()
            for tid in predicted:
                key=(case.case_id,span.span_id,tid);pred_pairs.add(key);pred_kind[span.kind].add(key)
            exact=predicted==set(m.required_topics);exact_count+=int(exact);exact_kind[span.kind]+=int(exact)
            rows.append({'case_id':case.case_id,'span_id':span.span_id,'kind':span.kind,'scored':True,'gold_topics':list(m.required_topics),'predicted_topics':sorted(predicted),'exact':exact})
    out=pair_prf(gold_pairs,pred_pairs)
    out.update({
        'exact_decision_span_membership':Fraction(exact_count,exact_total).to_dict(),
        'annotation_inventory':_inventory(cases),
        'by_kind':_kind_metrics(gold_kind,pred_kind,exact_kind,span_kind),
        'rows':rows,
        'claim_boundary':'Gold-span-conditioned assignment diagnostic over selected synthetic decision-bearing annotations; not decision-span detection and not source-complete semantic preservation.',
    })
    return out

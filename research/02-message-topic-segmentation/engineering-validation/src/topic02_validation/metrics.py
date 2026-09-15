"""Metrics with explicit denominators for Topic 02 validation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from .models import BenchmarkCase, Span
from .units import Unit, best_cover


@dataclass(frozen=True)
class Fraction:
    numerator: int
    denominator: int

    @property
    def value(self) -> float | None:
        return self.numerator / self.denominator if self.denominator else None

    def to_dict(self) -> dict[str, int | float | None]:
        return {"numerator": self.numerator, "denominator": self.denominator, "value": self.value}


def span_ceiling(cases: Iterable[BenchmarkCase], unitizer) -> dict:
    total = exact = 0
    broadening = omitted = 0
    by_kind: dict[str, list[int]] = {}
    rows = []
    for case in cases:
        units = unitizer(case.text)
        for gold in case.spans:
            total += 1
            hull, ok = best_cover(gold.span, units)
            exact += int(ok)
            if hull is None:
                omitted += gold.span.length
                extra = 0
                miss = gold.span.length
            else:
                overlap = hull.overlap(gold.span)
                extra = hull.length - overlap
                miss = gold.span.length - overlap
                broadening += extra
                omitted += miss
            stats = by_kind.setdefault(gold.kind, [0, 0])
            stats[0] += int(ok); stats[1] += 1
            rows.append({
                "case_id": case.case_id, "span_id": gold.span_id, "kind": gold.kind,
                "gold": gold.span.to_dict(), "cover": hull.to_dict() if hull else None,
                "exact": ok, "extra_chars": extra, "missing_chars": miss,
            })
    return {
        "exact_span_representability": Fraction(exact, total).to_dict(),
        "total_extra_scope_chars": broadening,
        "total_missing_chars": omitted,
        "by_kind": {k: Fraction(v[0], v[1]).to_dict() for k, v in sorted(by_kind.items())},
        "rows": rows,
    }


def topic_object_ceiling(cases: Iterable[BenchmarkCase], unitizer) -> dict:
    total = exact = noncont_total = noncont_exact = 0
    rows = []
    for case in cases:
        units = unitizer(case.text)
        for obj in case.topic_objects:
            total += 1
            exact_spans = []
            for sid in obj.span_ids:
                gold = case.span(sid)
                _, ok = best_cover(gold.span, units)
                exact_spans.append(ok)
            obj_exact = all(exact_spans)
            exact += int(obj_exact)
            if len(obj.span_ids) > 1:
                noncont_total += 1; noncont_exact += int(obj_exact)
            rows.append({"case_id": case.case_id, "topic_id": obj.topic_id, "span_ids": list(obj.span_ids), "exact": obj_exact, "component_exact": exact_spans})
    return {
        "exact_topic_object_representability": Fraction(exact, total).to_dict(),
        "exact_noncontiguous_topic_objects": Fraction(noncont_exact, noncont_total).to_dict(),
        "rows": rows,
    }


def pair_prf(gold: set[tuple[str, str]], predicted: set[tuple[str, str]]) -> dict:
    tp = len(gold & predicted)
    precision = Fraction(tp, len(predicted))
    recall = Fraction(tp, len(gold))
    p = precision.value or 0.0; r = recall.value or 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {
        "true_positive": tp,
        "false_positive": len(predicted - gold),
        "false_negative": len(gold - predicted),
        "precision": precision.to_dict(),
        "recall": recall.to_dict(),
        "f1": f1,
    }


def assignment_metrics(cases: Iterable[BenchmarkCase], predictor) -> dict:
    gold_pairs: set[tuple[str, str, str]] = set()
    pred_pairs: set[tuple[str, str, str]] = set()
    overlap_gold: set[tuple[str, str, str]] = set()
    overlap_pred: set[tuple[str, str, str]] = set()
    ambiguous_total = ambiguous_abstain = ambiguous_forced = 0
    object_total = object_exact = noncont_total = noncont_exact = 0
    message_total = message_exact = 0
    rows = []

    for case in cases:
        preds = {p.span_id: p for p in predictor(case)}
        membership = {m.span_id: m for m in case.memberships}
        for m in case.memberships:
            p = preds.get(m.span_id)
            if m.required_topics:
                for tid in m.required_topics:
                    gold_pairs.add((case.case_id, m.span_id, tid))
                    if len(m.required_topics) > 1:
                        overlap_gold.add((case.case_id, m.span_id, tid))
                if p and p.status == "resolved":
                    for tid in p.topic_ids:
                        pred_pairs.add((case.case_id, m.span_id, tid))
                        if len(m.required_topics) > 1:
                            overlap_pred.add((case.case_id, m.span_id, tid))
            elif m.alternative_topic_sets:
                ambiguous_total += 1
                if not p or p.status == "abstained":
                    ambiguous_abstain += 1
                else:
                    ambiguous_forced += 1
                    # A forced assertion on genuinely ambiguous current evidence is
                    # counted as a false-positive membership in end-to-end PRF.
                    for tid in p.topic_ids:
                        pred_pairs.add((case.case_id, m.span_id, tid))
            rows.append({
                "case_id": case.case_id,
                "span_id": m.span_id,
                "gold_required": list(m.required_topics),
                "gold_alternatives": [list(x) for x in m.alternative_topic_sets],
                "prediction": list(p.topic_ids) if p and p.status == "resolved" else [],
                "status": p.status if p else "missing_prediction",
            })

        eligible_ids = {sid for obj in case.topic_objects for sid in obj.span_ids}
        for obj in case.topic_objects:
            object_total += 1
            if len(obj.span_ids) > 1:
                noncont_total += 1
            predicted_spans = {
                sid for sid in eligible_ids
                if (p := preds.get(sid)) is not None and p.status == "resolved" and obj.topic_id in p.topic_ids
            }
            ok = predicted_spans == set(obj.span_ids)
            object_exact += int(ok)
            if len(obj.span_ids) > 1:
                noncont_exact += int(ok)

        gold_message_topics = {o.topic_id for o in case.topic_objects}
        # Message-set evaluation only uses object-eligible spans, not nested
        # condition/deadline annotations, so it remains a distinct output task.
        predicted_message_topics = {
            tid for sid in eligible_ids
            for tid in (preds[sid].topic_ids if sid in preds and preds[sid].status == "resolved" else ())
        }
        message_total += 1
        message_exact += int(predicted_message_topics == gold_message_topics)

    return {
        "membership_micro": pair_prf({(c,s,t) for c,s,t in gold_pairs}, {(c,s,t) for c,s,t in pred_pairs}),
        "overlap_only_membership": pair_prf({(c,s,t) for c,s,t in overlap_gold}, {(c,s,t) for c,s,t in overlap_pred}),
        "ambiguous_abstention": Fraction(ambiguous_abstain, ambiguous_total).to_dict(),
        "ambiguous_forced_assignment": Fraction(ambiguous_forced, ambiguous_total).to_dict(),
        "exact_topic_objects": Fraction(object_exact, object_total).to_dict(),
        "exact_noncontiguous_topic_objects": Fraction(noncont_exact, noncont_total).to_dict(),
        "whole_message_topic_set_exact": Fraction(message_exact, message_total).to_dict(),
        "rows": rows,
    }


def reliability_bins(rows: list[tuple[float,bool]], bins: int = 5) -> list[dict]:
    out=[]
    for i in range(bins):
        lo=i/bins;hi=(i+1)/bins
        bucket=[x for x in rows if (lo <= x[0] < hi) or (i==bins-1 and x[0]==1.0)]
        if not bucket:
            out.append({'bin':i,'lower':lo,'upper':hi,'count':0,'mean_confidence':None,'accuracy':None});continue
        out.append({'bin':i,'lower':lo,'upper':hi,'count':len(bucket),'mean_confidence':sum(x[0] for x in bucket)/len(bucket),'accuracy':sum(int(x[1]) for x in bucket)/len(bucket)})
    return out


def expected_calibration_error(rows: list[tuple[float,bool]], bins: int = 5) -> float | None:
    if not rows:return None
    ece=0.0
    for b in reliability_bins(rows,bins):
        if not b['count']:continue
        ece += (b['count']/len(rows))*abs(b['mean_confidence']-b['accuracy'])
    return ece

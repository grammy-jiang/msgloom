"""Transparent lexical assignment comparators for EV3/EV5.

These baselines are diagnostic only. They use fixture-supplied Topic descriptors
as controlled inputs and do not claim production Topic accuracy.
"""
from __future__ import annotations
from dataclasses import dataclass
import re
from .models import BenchmarkCase, EvidenceSpan, TopicDefinition


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9]+", text.lower()))


@dataclass(frozen=True)
class AssignmentPrediction:
    span_id: str
    topic_ids: tuple[str, ...]
    status: str  # resolved | abstained
    scores: tuple[tuple[str, float], ...]
    mode: str

    def __post_init__(self) -> None:
        if self.status not in {"resolved", "abstained"}:
            raise ValueError(self.status)
        if self.status == "resolved" and not self.topic_ids:
            raise ValueError("resolved prediction needs topics")
        if self.status == "abstained" and self.topic_ids:
            raise ValueError("abstained prediction cannot assert topics")


def topic_score(text: str, topic: TopicDefinition) -> float:
    terms = {x.lower() for x in topic.signature_terms if x.strip()}
    if not terms:
        return 0.0
    tok = _tokens(text)
    return len(tok & terms) / len(terms)


def span_context(case: BenchmarkCase, span: EvidenceSpan, radius: int = 45, extra_context: str = "") -> str:
    start = max(0, span.span.start - radius)
    end = min(len(case.text), span.span.end + radius)
    text = case.text[start:end]
    if extra_context:
        text += "\n" + extra_context
    return text


def predict(
    case: BenchmarkCase,
    span: EvidenceSpan,
    *,
    mode: str = "set_valued",
    context_mode: str = "span_only",
    extra_context: str = "",
    threshold: float = 0.34,
) -> AssignmentPrediction:
    if context_mode == "span_only":
        evidence = span.text + ("\n" + extra_context if extra_context else "")
    elif context_mode == "local_window":
        evidence = span_context(case, span, extra_context=extra_context)
    else:
        raise KeyError(context_mode)
    scores = tuple(sorted(((t.topic_id, topic_score(evidence, t)) for t in case.topics), key=lambda x: (-x[1], x[0])))
    eligible = [tid for tid, score in scores if score >= threshold]
    if not eligible:
        return AssignmentPrediction(span.span_id, (), "abstained", scores, f"{mode}:{context_mode}")

    # Ambiguity guard: shared generic terms (for example "approval limit") do
    # not justify choosing among several concrete matters. Multiple labels are
    # asserted only when the evidence contains an exclusive cue for every
    # selected matter; one exclusive cue can reduce the candidate set to one.
    if len(eligible) > 1:
        tok = _tokens(evidence)
        term_sets = {t.topic_id: {x.lower() for x in t.signature_terms} for t in case.topics}
        exclusive_hit = {}
        for tid in eligible:
            others = set().union(*(terms for oid, terms in term_sets.items() if oid != tid))
            exclusive = term_sets[tid] - others
            exclusive_hit[tid] = bool(tok & exclusive)
        hit_topics = [tid for tid in eligible if exclusive_hit[tid]]
        if len(hit_topics) == 1:
            eligible = hit_topics
        elif len(hit_topics) != len(eligible):
            return AssignmentPrediction(span.span_id, (), "abstained", scores, f"{mode}:{context_mode}")

    if mode == "single_label":
        if len(eligible) > 1 and len(scores) > 1 and abs(scores[0][1] - scores[1][1]) < 1e-12:
            return AssignmentPrediction(span.span_id, (), "abstained", scores, f"{mode}:{context_mode}")
        eligible = eligible[:1]
    elif mode != "set_valued":
        raise KeyError(mode)
    return AssignmentPrediction(span.span_id, tuple(sorted(eligible)), "resolved", scores, f"{mode}:{context_mode}")


def predict_case(
    case: BenchmarkCase,
    *,
    mode: str = "set_valued",
    context_mode: str = "span_only",
    extra_context: str = "",
    threshold: float = 0.34,
) -> tuple[AssignmentPrediction, ...]:
    return tuple(predict(case, s, mode=mode, context_mode=context_mode, extra_context=extra_context, threshold=threshold) for s in case.spans)

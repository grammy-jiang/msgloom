"""Bounded synthetic workplace-style stratification for EV7.

This is not production-domain validation. It partitions independently authored
fixtures by format/semantic stressor and reports the same diagnostic baseline per
stratum so domain/style-sensitive failures remain visible.
"""
from __future__ import annotations
from collections import defaultdict
from .models import BenchmarkCase
from .assignment import predict_case
from .metrics import assignment_metrics
from .preservation import decision_preservation, topic_component_ceiling
from .units import unitize

STYLE_CASES: dict[str, frozenset[str]] = {
    "plain_prose": frozenset({
        "single-topic-deadline","two-topics-contiguous","noncontiguous-aba",
        "overlap-shared-span","condition-scope","exception-scope",
        "shared-supporting-evidence","shared-plus-specific",
        "same-term-different-matters","irrelevant-chatter",
        "shared-evidence-separate-decision","noncontiguous-with-overlap",
    }),
    "multi_clause_sentence": frozenset({"clause-split-two-matters","condition-scope","exception-scope","shared-plus-specific"}),
    "structured_list_table": frozenset({"heading-list-scope","table-rows"}),
    "quoted_history": frozenset({"quoted-vs-authored"}),
    "context_dependent": frozenset({"ambiguous-reference","context-correction"}),
    "overlap_or_noncontiguous": frozenset({"noncontiguous-aba","overlap-shared-span","shared-supporting-evidence","shared-plus-specific","shared-evidence-separate-decision","noncontiguous-with-overlap"}),
}


def style_strata(cases: tuple[BenchmarkCase,...]) -> dict[str, tuple[BenchmarkCase,...]]:
    by_id={c.case_id:c for c in cases}
    return {name:tuple(by_id[x] for x in sorted(ids)) for name,ids in STYLE_CASES.items()}


def evaluate_styles(cases: tuple[BenchmarkCase,...]) -> dict:
    rows={}
    for style,subset in style_strata(cases).items():
        assign=assignment_metrics(subset,lambda c:predict_case(c,mode="set_valued",context_mode="span_only"))
        sentence_scope=decision_preservation(subset,lambda t:unitize(t,"sentence"))
        clause_scope=decision_preservation(subset,lambda t:unitize(t,"clause"))
        clause_ceiling=topic_component_ceiling(subset,lambda t:unitize(t,"clause"))
        rows[style]={
            "case_count":len(subset),
            "case_ids":[c.case_id for c in subset],
            "set_valued_span_only_membership":{k:v for k,v in assign["membership_micro"].items() if k!="rows"},
            "set_valued_overlap_recall":assign["overlap_only_membership"]["recall"],
            "set_valued_exact_topic_objects":assign["exact_topic_objects"],
            "sentence_decision_scope_precision":sentence_scope["precision"],
            "clause_decision_scope_precision":clause_scope["precision"],
            "clause_exact_topic_component_spans":clause_ceiling["exact_topic_component_spans"],
        }
    return {
        "status":"SYNTHETIC_STYLE_STRATIFICATION_COMPLETE",
        "strata":rows,
        "claim_boundary":"Synthetic workplace-style stress strata only. They expose format/context sensitivity but do not estimate production-domain accuracy, prevalence, or representativeness.",
    }

"""Probe-backed field evaluation behind the public Mail predicate evaluator."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import StrEnum
from typing import cast

from .rule_evaluation import MailRuleFact, MailRuleFacts, MailRuleRequiredData
from .rule_regex import (
    MailRegexEngine,
    MailRegexEvaluationError,
    MailRegexSyntaxError,
)

_BODY_FIELDS = frozenset(
    {
        "body_contains",
        "body_regex",
        "body_or_subject_contains",
        "body_or_subject_regex",
    }
)
_HEADER_FIELDS = frozenset({"header_contains", "header_regex"})
_ITEM_CLASS_FIELDS = frozenset(
    {"item_class_exact", "item_class_contains", "item_class_regex"}
)
_SPECIAL_CLASS_FIELDS = frozenset(
    {
        "is_meeting_request",
        "is_meeting_response",
        "is_non_delivery_report",
        "is_read_receipt",
    }
)
_MEETING_RESPONSES = frozenset(
    {
        "ipm.schedule.meeting.resp.pos",
        "ipm.schedule.meeting.resp.tent",
        "ipm.schedule.meeting.resp.neg",
    }
)


def evaluate_probe_field(
    field: str,
    configured: object,
    facts: MailRuleFacts,
    engine: MailRegexEngine,
):
    """Return a MailPredicateResult for probe-backed fields, else None."""

    if field in _BODY_FIELDS:
        return _body_field(field, cast(tuple[str, ...], configured), facts, engine)
    if field in _HEADER_FIELDS:
        return _header_field(field, cast(tuple[str, ...], configured), facts, engine)
    if field == "sensitivity":
        return _scalar_or(
            MailRuleFact.SENSITIVITY,
            facts.sensitivity,
            _enum_values(configured),
            facts,
            required=MailRuleRequiredData.EXTENDED_PROPERTIES,
            mode="exact",
            engine=engine,
        )
    if field in {"message_size_min_kb", "message_size_max_kb"}:
        return _size_field(field, cast(int, configured), facts)
    if field in _ITEM_CLASS_FIELDS:
        mode = field.removeprefix("item_class_")
        return _scalar_or(
            MailRuleFact.ITEM_CLASS,
            facts.item_class,
            cast(tuple[str, ...], configured),
            facts,
            required=MailRuleRequiredData.EXTENDED_PROPERTIES,
            mode=mode,
            engine=engine,
        )
    if field in _SPECIAL_CLASS_FIELDS:
        return _special_class_field(field, cast(bool, configured), facts)
    return None


def _body_field(
    field: str,
    configured: tuple[str, ...],
    facts: MailRuleFacts,
    engine: MailRegexEngine,
):
    regex = field.endswith("_regex")
    if field.startswith("body_or_subject_"):
        alternatives = []
        for value in configured:
            subject = _one_text(
                fact=MailRuleFact.SUBJECT,
                source=facts.subject,
                configured=value,
                facts=facts,
                required=MailRuleRequiredData.METADATA,
                mode="regex" if regex else "contains",
                engine=engine,
            )
            body = _one_text(
                fact=MailRuleFact.BODY,
                source=facts.body,
                configured=value,
                facts=facts,
                required=MailRuleRequiredData.BODY,
                mode="regex" if regex else "contains",
                engine=engine,
            )
            alternatives.append(_or((subject, body)))
        return _or(alternatives)

    return _scalar_or(
        MailRuleFact.BODY,
        facts.body,
        configured,
        facts,
        required=MailRuleRequiredData.BODY,
        mode="regex" if regex else "contains",
        engine=engine,
    )


def _header_field(
    field: str,
    configured: tuple[str, ...],
    facts: MailRuleFacts,
    engine: MailRegexEngine,
):
    if MailRuleFact.HEADERS not in facts.available_facts:
        return _unknown(MailRuleRequiredData.HEADERS)
    mode = "regex" if field.endswith("_regex") else "contains"
    per_value = []
    for value in configured:
        per_value.append(
            _or(
                _match_text(header, value, mode=mode, engine=engine)
                for header in facts.headers
            )
        )
    return _or(per_value)


def _size_field(field: str, configured_kib: int, facts: MailRuleFacts):
    if MailRuleFact.MESSAGE_SIZE_BYTES not in facts.available_facts:
        return _unknown(MailRuleRequiredData.EXTENDED_PROPERTIES)
    size = facts.message_size_bytes
    if size is None:
        return _false()
    boundary = configured_kib * 1024
    return _truth(size >= boundary if field.endswith("min_kb") else size <= boundary)


def _special_class_field(field: str, configured: bool, facts: MailRuleFacts):
    if MailRuleFact.ITEM_CLASS not in facts.available_facts:
        return _unknown(MailRuleRequiredData.EXTENDED_PROPERTIES)
    item_class = facts.item_class
    classified = False if item_class is None else _classify(field, item_class)
    return _truth(classified is configured)


def _classify(field: str, item_class: str) -> bool:
    folded = item_class.casefold()
    if field == "is_meeting_request":
        return folded == "ipm.schedule.meeting.request"
    if field == "is_meeting_response":
        return folded in _MEETING_RESPONSES
    if field == "is_non_delivery_report":
        return folded.startswith("report.") and folded.endswith(".ndr")
    return (
        folded.startswith("report.") and folded.endswith(".ipnrn")
    ) or folded == "ipm.note.receipt.smime"


def _scalar_or(
    fact: MailRuleFact,
    source: str | None,
    configured: tuple[str, ...],
    facts: MailRuleFacts,
    *,
    required: MailRuleRequiredData,
    mode: str,
    engine: MailRegexEngine,
):
    if fact not in facts.available_facts:
        return _unknown(required)
    return _or(
        _match_text(source, value, mode=mode, engine=engine) for value in configured
    )


def _one_text(
    *,
    fact: MailRuleFact,
    source: str | None,
    configured: str,
    facts: MailRuleFacts,
    required: MailRuleRequiredData,
    mode: str,
    engine: MailRegexEngine,
):
    if fact not in facts.available_facts:
        return _unknown(required)
    return _match_text(source, configured, mode=mode, engine=engine)


def _match_text(
    source: str | None,
    configured: str,
    *,
    mode: str,
    engine: MailRegexEngine,
):
    if source is None:
        return _false()
    if mode == "regex":
        try:
            compiled = engine.compile(configured)
            return _truth(engine.search(compiled, source))
        except (MailRegexSyntaxError, MailRegexEvaluationError):
            return _unknown(reason="regex_evaluation_failed")
    source_folded = source.casefold()
    configured_folded = configured.casefold()
    if mode == "exact":
        return _truth(source_folded == configured_folded)
    return _truth(configured_folded in source_folded)


def _enum_values(value: object) -> tuple[str, ...]:
    return tuple(cast(StrEnum, item).value for item in cast(Sequence[object], value))


def _truth(value: bool):
    from .rule_predicates import MailPredicateResult, MailTruth

    return MailPredicateResult(MailTruth.TRUE if value else MailTruth.FALSE)


def _false():
    from .rule_predicates import MailPredicateResult, MailTruth

    return MailPredicateResult(MailTruth.FALSE)


def _unknown(
    required: MailRuleRequiredData | None = None,
    *,
    reason: str | None = None,
):
    from .rule_predicates import MailPredicateResult, MailTruth

    return MailPredicateResult(
        MailTruth.UNKNOWN,
        required_data=frozenset() if required is None else frozenset({required}),
        reason_codes=() if reason is None else (reason,),
    )


def _or(results: Iterable):
    from .rule_predicates import MailPredicateResult, MailTruth

    collected = tuple(results)
    if any(result.truth is MailTruth.TRUE for result in collected):
        return MailPredicateResult(MailTruth.TRUE)
    unknowns = [result for result in collected if result.truth is MailTruth.UNKNOWN]
    if unknowns:
        return MailPredicateResult(
            MailTruth.UNKNOWN,
            required_data=frozenset().union(
                *(result.required_data for result in unknowns)
            ),
            reason_codes=tuple(
                dict.fromkeys(
                    reason for result in unknowns for reason in result.reason_codes
                )
            ),
        )
    return MailPredicateResult(MailTruth.FALSE)

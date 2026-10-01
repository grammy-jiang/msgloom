"""Pure tri-state predicate evaluation for Outlook Mail rules."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import cast

from .rule_config import MailRulePredicates
from .rule_evaluation import (
    MailRecipientFact,
    MailRuleFact,
    MailRuleFacts,
    MailRuleRequiredData,
)
from .rule_regex import (
    MailRegexEngine,
    MailRegexEvaluationError,
    MailRegexSyntaxError,
)


class MailTruth(StrEnum):
    """Three-valued predicate truth."""

    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MailPredicateResult:
    """One predicate/block truth plus repairable data needs and bounded reasons."""

    truth: MailTruth
    required_data: frozenset[MailRuleRequiredData] = frozenset()
    reason_codes: tuple[str, ...] = ()


def evaluate_predicate_block(
    predicates: MailRulePredicates,
    facts: MailRuleFacts,
    *,
    regex_engine: MailRegexEngine,
) -> MailPredicateResult:
    """Evaluate one flat AND block without Scrapy/provider side effects."""

    results: list[MailPredicateResult] = []
    for field in sorted(predicates.model_fields_set):
        value = getattr(predicates, field)
        results.append(_evaluate_field(field, value, facts, regex_engine))
    return _and_results(results)


_PROBE_GROUPS: dict[str, MailRuleRequiredData] = {
    "body_contains": MailRuleRequiredData.BODY,
    "body_regex": MailRuleRequiredData.BODY,
    "body_or_subject_contains": MailRuleRequiredData.BODY,
    "body_or_subject_regex": MailRuleRequiredData.BODY,
    "header_contains": MailRuleRequiredData.HEADERS,
    "header_regex": MailRuleRequiredData.HEADERS,
    "sensitivity": MailRuleRequiredData.EXTENDED_PROPERTIES,
    "message_size_min_kb": MailRuleRequiredData.EXTENDED_PROPERTIES,
    "message_size_max_kb": MailRuleRequiredData.EXTENDED_PROPERTIES,
    "item_class_exact": MailRuleRequiredData.EXTENDED_PROPERTIES,
    "item_class_contains": MailRuleRequiredData.EXTENDED_PROPERTIES,
    "item_class_regex": MailRuleRequiredData.EXTENDED_PROPERTIES,
    "is_meeting_request": MailRuleRequiredData.EXTENDED_PROPERTIES,
    "is_meeting_response": MailRuleRequiredData.EXTENDED_PROPERTIES,
    "is_non_delivery_report": MailRuleRequiredData.EXTENDED_PROPERTIES,
    "is_read_receipt": MailRuleRequiredData.EXTENDED_PROPERTIES,
}

_RECIPIENT_FACTS: dict[str, MailRuleFact] = {
    "from": MailRuleFact.FROM_RECIPIENT,
    "sender": MailRuleFact.SENDER_RECIPIENT,
    "to": MailRuleFact.TO_RECIPIENTS,
    "cc": MailRuleFact.CC_RECIPIENTS,
    "bcc": MailRuleFact.BCC_RECIPIENTS,
    "reply_to": MailRuleFact.REPLY_TO_RECIPIENTS,
}

# fmt: off
_DATETIME_FIELDS: dict[str, tuple[MailRuleFact, str, str]] = {
    "received_after": (MailRuleFact.RECEIVED_DATE_TIME, "received_date_time", "after"),
    "received_before": (MailRuleFact.RECEIVED_DATE_TIME, "received_date_time", "before"),
    "sent_after": (MailRuleFact.SENT_DATE_TIME, "sent_date_time", "after"),
    "sent_before": (MailRuleFact.SENT_DATE_TIME, "sent_date_time", "before"),
    "created_after": (MailRuleFact.CREATED_DATE_TIME, "created_date_time", "after"),
    "created_before": (MailRuleFact.CREATED_DATE_TIME, "created_date_time", "before"),
}
# fmt: on


def _evaluate_field(
    field: str,
    configured: object,
    facts: MailRuleFacts,
    engine: MailRegexEngine,
) -> MailPredicateResult:
    if field in _PROBE_GROUPS:
        return _unknown(required=_PROBE_GROUPS[field])

    if field in {"subject_exact", "subject_contains", "subject_regex"}:
        mode = field.removeprefix("subject_")
        return _text_field(
            fact=MailRuleFact.SUBJECT,
            source=facts.subject,
            configured=cast(tuple[str, ...], configured),
            mode=mode,
            facts=facts,
            engine=engine,
        )

    recipient = _recipient_field(field, configured, facts, engine)
    if recipient is not None:
        return recipient

    if field == "categories":
        return _category_field(cast(tuple[str, ...], configured), facts)
    if field == "importance":
        return _enum_field(
            MailRuleFact.IMPORTANCE,
            facts.importance,
            _enum_values(configured),
            facts,
        )
    if field == "inference_classification":
        return _enum_field(
            MailRuleFact.INFERENCE_CLASSIFICATION,
            facts.inference_classification,
            _enum_values(configured),
            facts,
        )
    if field == "followup_status":
        return _enum_field(
            MailRuleFact.FOLLOWUP_STATUS,
            _normalize_followup(facts.followup_status),
            _enum_values(configured),
            facts,
        )

    if field == "has_attachments":
        return _boolean_field(
            MailRuleFact.HAS_ATTACHMENTS,
            facts.has_attachments,
            cast(bool, configured),
            facts,
        )
    if field == "is_read":
        return _boolean_field(
            MailRuleFact.IS_READ,
            facts.is_read,
            cast(bool, configured),
            facts,
        )
    if field == "is_draft":
        return _boolean_field(
            MailRuleFact.IS_DRAFT,
            facts.is_draft,
            cast(bool, configured),
            facts,
        )

    if field in _DATETIME_FIELDS:
        fact, attr, comparison = _DATETIME_FIELDS[field]
        return _datetime_field(
            fact,
            cast(str | None, getattr(facts, attr)),
            cast(datetime, configured),
            comparison,
            facts,
        )

    raise ValueError(f"unsupported Mail predicate field: {field}")


def _recipient_field(
    field: str,
    configured: object,
    facts: MailRuleFacts,
    engine: MailRegexEngine,
) -> MailPredicateResult | None:
    specs: dict[str, tuple[str, str]] = {
        "from_addresses": ("from", "address_exact"),
        "from_contains": ("from", "name_or_address_contains"),
        "from_address_contains": ("from", "address_contains"),
        "from_address_regex": ("from", "address_regex"),
        "sender_addresses": ("sender", "address_exact"),
        "sender_contains": ("sender", "name_or_address_contains"),
        "sender_address_contains": ("sender", "address_contains"),
        "sender_address_regex": ("sender", "address_regex"),
        "to_addresses": ("to", "address_exact"),
        "to_address_contains": ("to", "address_contains"),
        "to_address_regex": ("to", "address_regex"),
        "cc_addresses": ("cc", "address_exact"),
        "cc_address_contains": ("cc", "address_contains"),
        "cc_address_regex": ("cc", "address_regex"),
        "bcc_addresses": ("bcc", "address_exact"),
        "bcc_address_contains": ("bcc", "address_contains"),
        "bcc_address_regex": ("bcc", "address_regex"),
        "reply_to_addresses": ("reply_to", "address_exact"),
        "reply_to_address_contains": ("reply_to", "address_contains"),
        "reply_to_address_regex": ("reply_to", "address_regex"),
    }
    if field in specs:
        source_name, mode = specs[field]
        fact = _RECIPIENT_FACTS[source_name]
        source = _recipient_source(source_name, facts)
        return _recipient_list_match(
            fact,
            source,
            cast(tuple[str, ...], configured),
            mode,
            facts,
            engine,
        )

    if field in {
        "recipient_contains",
        "recipient_address_contains",
        "recipient_address_regex",
    }:
        needed = {MailRuleFact.TO_RECIPIENTS, MailRuleFact.CC_RECIPIENTS}
        if not needed.issubset(facts.available_facts):
            return _unknown(required=MailRuleRequiredData.METADATA)
        source = facts.to_recipients + facts.cc_recipients
        mode = {
            "recipient_contains": "name_or_address_contains",
            "recipient_address_contains": "address_contains",
            "recipient_address_regex": "address_regex",
        }[field]
        return _recipient_list_match(
            None,
            source,
            cast(tuple[str, ...], configured),
            mode,
            facts,
            engine,
        )
    return None


def _recipient_source(
    source_name: str,
    facts: MailRuleFacts,
) -> tuple[MailRecipientFact, ...]:
    if source_name == "from":
        return () if facts.from_recipient is None else (facts.from_recipient,)
    if source_name == "sender":
        return () if facts.sender_recipient is None else (facts.sender_recipient,)
    return cast(
        tuple[MailRecipientFact, ...],
        getattr(facts, f"{source_name}_recipients"),
    )


def _recipient_list_match(
    fact: MailRuleFact | None,
    recipients: tuple[MailRecipientFact, ...],
    configured: tuple[str, ...],
    mode: str,
    facts: MailRuleFacts,
    engine: MailRegexEngine,
) -> MailPredicateResult:
    if fact is not None and fact not in facts.available_facts:
        return _unknown(required=MailRuleRequiredData.METADATA)

    alternatives: list[MailPredicateResult] = []
    for configured_value in configured:
        matches: list[MailPredicateResult] = []
        for recipient in recipients:
            if mode == "address_exact":
                matches.append(
                    _literal_result(
                        recipient.address,
                        configured_value,
                        exact=True,
                    )
                )
            elif mode == "address_contains":
                matches.append(
                    _literal_result(recipient.address, configured_value, exact=False)
                )
            elif mode == "address_regex":
                matches.append(
                    _regex_result(recipient.address, configured_value, engine)
                )
            else:
                matches.append(
                    _or_results(
                        (
                            _literal_result(
                                recipient.name,
                                configured_value,
                                exact=False,
                            ),
                            _literal_result(
                                recipient.address,
                                configured_value,
                                exact=False,
                            ),
                        )
                    )
                )
        alternatives.append(_or_results(matches))
    return _or_results(alternatives)


def _category_field(
    configured: tuple[str, ...],
    facts: MailRuleFacts,
) -> MailPredicateResult:
    if MailRuleFact.CATEGORIES not in facts.available_facts:
        return _unknown(required=MailRuleRequiredData.METADATA)
    return _or_results(
        _literal_result(category, wanted, exact=True)
        for wanted in configured
        for category in facts.categories
    )


def _enum_field(
    fact: MailRuleFact,
    source: str | None,
    configured: tuple[str, ...],
    facts: MailRuleFacts,
) -> MailPredicateResult:
    if fact not in facts.available_facts:
        return _unknown(required=MailRuleRequiredData.METADATA)
    return _or_results(
        _literal_result(source, wanted, exact=True) for wanted in configured
    )


def _boolean_field(
    fact: MailRuleFact,
    source: bool | None,
    configured: bool,
    facts: MailRuleFacts,
) -> MailPredicateResult:
    if fact not in facts.available_facts:
        return _unknown(required=MailRuleRequiredData.METADATA)
    return _truth(source is configured)


def _datetime_field(
    fact: MailRuleFact,
    source: str | None,
    configured: datetime,
    comparison: str,
    facts: MailRuleFacts,
) -> MailPredicateResult:
    if fact not in facts.available_facts:
        return _unknown(required=MailRuleRequiredData.METADATA)
    if source is None:
        return _false()
    try:
        observed = datetime.fromisoformat(source)
    except ValueError:
        return _unknown(
            required=MailRuleRequiredData.METADATA,
            reason="metadata_fact_invalid",
        )
    if observed.tzinfo is None or observed.utcoffset() is None:
        return _unknown(
            required=MailRuleRequiredData.METADATA,
            reason="metadata_fact_invalid",
        )
    left = observed.astimezone(UTC)
    right = configured.astimezone(UTC)
    if comparison == "after":
        return _truth(left >= right)
    return _truth(left < right)


def _text_field(
    *,
    fact: MailRuleFact,
    source: str | None,
    configured: tuple[str, ...],
    mode: str,
    facts: MailRuleFacts,
    engine: MailRegexEngine,
) -> MailPredicateResult:
    if fact not in facts.available_facts:
        return _unknown(required=MailRuleRequiredData.METADATA)
    if mode == "regex":
        return _or_results(
            _regex_result(source, pattern, engine) for pattern in configured
        )
    exact = mode == "exact"
    return _or_results(
        _literal_result(source, wanted, exact=exact) for wanted in configured
    )


def _literal_result(
    source: str | None,
    configured: str,
    *,
    exact: bool,
) -> MailPredicateResult:
    if source is None:
        return _false()
    source_folded = source.casefold()
    configured_folded = configured.casefold()
    return _truth(
        source_folded == configured_folded
        if exact
        else configured_folded in source_folded
    )


def _regex_result(
    source: str | None,
    pattern: str,
    engine: MailRegexEngine,
) -> MailPredicateResult:
    if source is None:
        return _false()
    try:
        compiled = engine.compile(pattern)
        return _truth(engine.search(compiled, source))
    except (MailRegexSyntaxError, MailRegexEvaluationError):
        return _unknown(reason="regex_evaluation_failed")


def _enum_values(value: object) -> tuple[str, ...]:
    return tuple(cast(StrEnum, item).value for item in cast(Sequence[object], value))


def _normalize_followup(value: str | None) -> str | None:
    if value == "notFlagged":
        return "not_flagged"
    return value.casefold() if isinstance(value, str) else None


def _truth(value: bool) -> MailPredicateResult:
    return MailPredicateResult(MailTruth.TRUE if value else MailTruth.FALSE)


def _false() -> MailPredicateResult:
    return MailPredicateResult(MailTruth.FALSE)


def _unknown(
    *,
    required: MailRuleRequiredData | None = None,
    reason: str | None = None,
) -> MailPredicateResult:
    required_data = frozenset() if required is None else frozenset({required})
    reasons = () if reason is None else (reason,)
    return MailPredicateResult(
        MailTruth.UNKNOWN,
        required_data=required_data,
        reason_codes=reasons,
    )


def _or_results(results: Iterable[MailPredicateResult]) -> MailPredicateResult:
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
            reason_codes=_reason_union(unknowns),
        )
    return MailPredicateResult(MailTruth.FALSE)


def _and_results(results: Iterable[MailPredicateResult]) -> MailPredicateResult:
    collected = tuple(results)
    if any(result.truth is MailTruth.FALSE for result in collected):
        return MailPredicateResult(MailTruth.FALSE)
    unknowns = [result for result in collected if result.truth is MailTruth.UNKNOWN]
    if unknowns:
        return MailPredicateResult(
            MailTruth.UNKNOWN,
            required_data=frozenset().union(
                *(result.required_data for result in unknowns)
            ),
            reason_codes=_reason_union(unknowns),
        )
    return MailPredicateResult(MailTruth.TRUE)


def _reason_union(results: Iterable[MailPredicateResult]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(reason for result in results for reason in result.reason_codes)
    )

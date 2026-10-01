"""Bounded acquisition helpers for one Outlook Mail composite rule probe."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .rule_body import MailBodyUnavailable, logical_mail_body
from .rule_evaluation import (
    MailRuleFact,
    MailRuleFacts,
    MailRuleObservation,
    MailRuleProbeData,
    MailRuleProbeFailure,
    MailRuleProbeStatus,
    MailRuleRequiredData,
    mail_rule_facts_from_graph,
)

MAIL_RULE_PROBE_MAX_BYTES = 8 * 1024 * 1024

PIDTAG_SENSITIVITY = "Integer 0x0036"
PIDTAG_MESSAGE_SIZE = "Integer 0x0E08"
PIDTAG_MESSAGE_CLASS = "String 0x001A"

EXTENDED_PROPERTY_EXPAND = (
    "singleValueLegacyExtendedProperties("
    "$filter=id eq 'Integer 0x0036' or "
    "id eq 'Integer 0x0E08' or "
    "id eq 'String 0x001A')"
)

_METADATA_FIELDS = (
    "lastModifiedDateTime",
    "subject",
    "from",
    "sender",
    "toRecipients",
    "ccRecipients",
    "bccRecipients",
    "replyTo",
    "receivedDateTime",
    "sentDateTime",
    "createdDateTime",
    "importance",
    "categories",
    "hasAttachments",
    "isRead",
    "isDraft",
    "inferenceClassification",
    "flag",
    "bodyPreview",
)

_METADATA_FACTS = (
    MailRuleFact.LAST_MODIFIED_DATE_TIME,
    MailRuleFact.SUBJECT,
    MailRuleFact.FROM_RECIPIENT,
    MailRuleFact.SENDER_RECIPIENT,
    MailRuleFact.TO_RECIPIENTS,
    MailRuleFact.CC_RECIPIENTS,
    MailRuleFact.BCC_RECIPIENTS,
    MailRuleFact.REPLY_TO_RECIPIENTS,
    MailRuleFact.RECEIVED_DATE_TIME,
    MailRuleFact.SENT_DATE_TIME,
    MailRuleFact.CREATED_DATE_TIME,
    MailRuleFact.IMPORTANCE,
    MailRuleFact.CATEGORIES,
    MailRuleFact.HAS_ATTACHMENTS,
    MailRuleFact.IS_READ,
    MailRuleFact.IS_DRAFT,
    MailRuleFact.INFERENCE_CLASSIFICATION,
    MailRuleFact.FOLLOWUP_STATUS,
    MailRuleFact.BODY_PREVIEW,
)

_EXTENDED_FACTS = (
    MailRuleFact.SENSITIVITY,
    MailRuleFact.MESSAGE_SIZE_BYTES,
    MailRuleFact.ITEM_CLASS,
)

_SENSITIVITY = {
    "0": "normal",
    "1": "personal",
    "2": "private",
    "3": "confidential",
}


@dataclass(frozen=True, slots=True)
class OutlookMailRuleProbeResult:
    """Internal Spider output consumed by the Mail rule middleware."""

    observation: MailRuleObservation
    probe: MailRuleProbeData


def probe_select_fields(
    required_data: frozenset[MailRuleRequiredData],
) -> tuple[str, ...]:
    """Return deterministic unique Graph fields for one composite probe."""

    if not required_data:
        raise ValueError("Mail rule probe requires at least one data group")
    fields = ["id", "changeKey"]
    if MailRuleRequiredData.METADATA in required_data:
        fields.extend(_METADATA_FIELDS)
    if MailRuleRequiredData.BODY in required_data:
        fields.append("body")
    if MailRuleRequiredData.HEADERS in required_data:
        fields.append("internetMessageHeaders")
    return tuple(dict.fromkeys(fields))


def probe_expand(required_data: frozenset[MailRuleRequiredData]) -> str | None:
    """Return the one fixed extended-property expansion when required."""

    if MailRuleRequiredData.EXTENDED_PROPERTIES in required_data:
        return EXTENDED_PROPERTY_EXPAND
    return None


def parse_probe_payload(
    payload: dict[str, Any],
    *,
    observation: MailRuleObservation,
    required_data: frozenset[MailRuleRequiredData],
    evidence_id: str | None,
) -> MailRuleProbeData:
    """Parse one provider response into bounded partial facts."""

    if payload.get("id") != observation.message_id or not isinstance(
        payload.get("changeKey"), str
    ):
        return _failed_probe(
            evidence_id,
            MailRuleFact.CHANGE_KEY,
            "invalid_probe_identity",
        )

    metadata = mail_rule_facts_from_graph(payload)
    available = set(metadata.available_facts)
    available.add(MailRuleFact.CHANGE_KEY)
    facts = replace(
        metadata,
        change_key=payload["changeKey"],
        available_facts=frozenset(available),
    )
    failures: list[MailRuleProbeFailure] = []

    if MailRuleRequiredData.METADATA in required_data:
        failures.extend(
            _missing_failures(facts, _METADATA_FACTS, "probe_fact_unavailable")
        )

    if MailRuleRequiredData.BODY in required_data:
        facts, body_failure = _with_body(facts, payload.get("body"))
        if body_failure is not None:
            failures.append(body_failure)

    if MailRuleRequiredData.HEADERS in required_data:
        facts, header_failure = _with_headers(
            facts,
            payload.get("internetMessageHeaders"),
        )
        if header_failure is not None:
            failures.append(header_failure)

    if MailRuleRequiredData.EXTENDED_PROPERTIES in required_data:
        facts, extended_failures = _with_extended_properties(
            facts,
            payload.get("singleValueLegacyExtendedProperties"),
        )
        failures.extend(extended_failures)

    status = (
        MailRuleProbeStatus.COMPLETE
        if not failures
        else MailRuleProbeStatus.PARTIAL
        if facts.available_facts - {MailRuleFact.CHANGE_KEY}
        else MailRuleProbeStatus.FAILED
    )
    return MailRuleProbeData(
        status=status,
        facts=facts,
        evidence_id=evidence_id,
        failures=tuple(failures),
    )


def request_failure_probe(
    *,
    required_data: frozenset[MailRuleRequiredData],
    evidence_id: str | None,
) -> MailRuleProbeData:
    """Represent an exhausted provider request as bounded fact failures."""

    facts = _requested_facts(required_data)
    return MailRuleProbeData(
        status=MailRuleProbeStatus.FAILED,
        facts=MailRuleFacts(),
        evidence_id=evidence_id,
        failures=tuple(
            MailRuleProbeFailure(fact=fact, reason_code="probe_request_failed")
            for fact in facts
        ),
    )


def _requested_facts(
    required_data: frozenset[MailRuleRequiredData],
) -> tuple[MailRuleFact, ...]:
    result: list[MailRuleFact] = []
    if MailRuleRequiredData.METADATA in required_data:
        result.extend(_METADATA_FACTS)
    if MailRuleRequiredData.BODY in required_data:
        result.append(MailRuleFact.BODY)
    if MailRuleRequiredData.HEADERS in required_data:
        result.append(MailRuleFact.HEADERS)
    if MailRuleRequiredData.EXTENDED_PROPERTIES in required_data:
        result.extend(_EXTENDED_FACTS)
    return tuple(dict.fromkeys(result))


def _missing_failures(
    facts: MailRuleFacts,
    expected: tuple[MailRuleFact, ...],
    reason: str,
) -> tuple[MailRuleProbeFailure, ...]:
    return tuple(
        MailRuleProbeFailure(fact=fact, reason_code=reason)
        for fact in expected
        if fact not in facts.available_facts
    )


def _with_body(
    facts: MailRuleFacts,
    raw_body: object,
) -> tuple[MailRuleFacts, MailRuleProbeFailure | None]:
    try:
        body = logical_mail_body(raw_body)
    except MailBodyUnavailable as error:
        return facts, MailRuleProbeFailure(
            fact=MailRuleFact.BODY,
            reason_code=error.reason_code,
        )
    return (
        replace(
            facts,
            body=body,
            available_facts=facts.available_facts | {MailRuleFact.BODY},
        ),
        None,
    )


def _with_headers(
    facts: MailRuleFacts,
    raw_headers: object,
) -> tuple[MailRuleFacts, MailRuleProbeFailure | None]:
    if not isinstance(raw_headers, list):
        return facts, MailRuleProbeFailure(
            fact=MailRuleFact.HEADERS,
            reason_code="probe_fact_unavailable",
        )
    values: list[str] = []
    for header in raw_headers:
        if not isinstance(header, dict):
            return facts, MailRuleProbeFailure(
                fact=MailRuleFact.HEADERS,
                reason_code="invalid_probe_payload",
            )
        name = header.get("name")
        value = header.get("value")
        if not isinstance(name, str) or not isinstance(value, str):
            return facts, MailRuleProbeFailure(
                fact=MailRuleFact.HEADERS,
                reason_code="invalid_probe_payload",
            )
        values.append(f"{name}: {value}")
    return (
        replace(
            facts,
            headers=tuple(values),
            available_facts=facts.available_facts | {MailRuleFact.HEADERS},
        ),
        None,
    )


def _with_extended_properties(
    facts: MailRuleFacts,
    raw_properties: object,
) -> tuple[MailRuleFacts, tuple[MailRuleProbeFailure, ...]]:
    values: dict[str, object] = {}
    duplicate_ids: set[str] = set()
    if isinstance(raw_properties, list):
        for item in raw_properties:
            if not isinstance(item, dict):
                continue
            property_id = item.get("id")
            if not isinstance(property_id, str):
                continue
            if property_id in values:
                duplicate_ids.add(property_id)
            else:
                values[property_id] = item.get("value")

    available = set(facts.available_facts)
    failures: list[MailRuleProbeFailure] = []

    sensitivity = None
    if PIDTAG_SENSITIVITY not in duplicate_ids:
        raw = values.get(PIDTAG_SENSITIVITY)
        if isinstance(raw, str) and raw in _SENSITIVITY:
            sensitivity = _SENSITIVITY[raw]
            available.add(MailRuleFact.SENSITIVITY)
    if MailRuleFact.SENSITIVITY not in available:
        failures.append(
            MailRuleProbeFailure(
                fact=MailRuleFact.SENSITIVITY,
                reason_code="invalid_probe_payload",
            )
        )

    message_size = None
    if PIDTAG_MESSAGE_SIZE not in duplicate_ids:
        raw = values.get(PIDTAG_MESSAGE_SIZE)
        if isinstance(raw, str):
            try:
                candidate = int(raw, 10)
            except ValueError:
                candidate = -1
            if 0 <= candidate <= 2_147_483_647:
                message_size = candidate
                available.add(MailRuleFact.MESSAGE_SIZE_BYTES)
    if MailRuleFact.MESSAGE_SIZE_BYTES not in available:
        failures.append(
            MailRuleProbeFailure(
                fact=MailRuleFact.MESSAGE_SIZE_BYTES,
                reason_code="invalid_probe_payload",
            )
        )

    item_class = None
    if PIDTAG_MESSAGE_CLASS not in duplicate_ids:
        raw = values.get(PIDTAG_MESSAGE_CLASS)
        if isinstance(raw, str) and len(raw) <= 2_048:
            item_class = raw
            available.add(MailRuleFact.ITEM_CLASS)
    if MailRuleFact.ITEM_CLASS not in available:
        failures.append(
            MailRuleProbeFailure(
                fact=MailRuleFact.ITEM_CLASS,
                reason_code="invalid_probe_payload",
            )
        )

    return (
        replace(
            facts,
            sensitivity=sensitivity,
            message_size_bytes=message_size,
            item_class=item_class,
            available_facts=frozenset(available),
        ),
        tuple(failures),
    )


def _failed_probe(
    evidence_id: str | None,
    fact: MailRuleFact,
    reason: str,
) -> MailRuleProbeData:
    return MailRuleProbeData(
        status=MailRuleProbeStatus.FAILED,
        facts=MailRuleFacts(),
        evidence_id=evidence_id,
        failures=(MailRuleProbeFailure(fact=fact, reason_code=reason),),
    )


__all__ = [
    "EXTENDED_PROPERTY_EXPAND",
    "MAIL_RULE_PROBE_MAX_BYTES",
    "OutlookMailRuleProbeResult",
    "parse_probe_payload",
    "probe_expand",
    "probe_select_fields",
    "request_failure_probe",
]

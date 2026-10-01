"""Pure contracts and bounded source-fact projection for Outlook Mail rules."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from message_ingest.items.microsoft.outlook.email import OutlookMailItem

_SAFE_TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,96}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")

_MAX_SUBJECT_CHARS = 16_384
_MAX_RECIPIENT_PART_CHARS = 1_024
_MAX_RECIPIENTS = 256
_MAX_CATEGORIES = 128
_MAX_CATEGORY_CHARS = 1_024
_MAX_SCALAR_CHARS = 2_048
_MAX_BODY_PREVIEW_CHARS = 1_024


class MailRuleEvaluationState(StrEnum):
    """Lifecycle state returned by the deterministic rule evaluator."""

    FINAL = "final"
    NEEDS_DATA = "needs_data"
    UNRESOLVED = "unresolved"


class MailRuleDecisionOutcome(StrEnum):
    """Terminal decision classification used for audit and aggregate stats."""

    MATCHED = "matched"
    DEFAULT = "default"
    UNRESOLVED = "unresolved"


class MailRuleRequiredData(StrEnum):
    """Closed source-data groups that one composite probe may request."""

    METADATA = "metadata"
    BODY = "body"
    HEADERS = "headers"
    EXTENDED_PROPERTIES = "extended_properties"


class MailRuleProbeStatus(StrEnum):
    """Usability of one bounded rule-probe result."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class MailRuleFact(StrEnum):
    """Closed source-fact vocabulary consumed by Mail predicates."""

    CHANGE_KEY = "change_key"
    LAST_MODIFIED_DATE_TIME = "last_modified_date_time"
    SUBJECT = "subject"
    FROM_RECIPIENT = "from_recipient"
    SENDER_RECIPIENT = "sender_recipient"
    TO_RECIPIENTS = "to_recipients"
    CC_RECIPIENTS = "cc_recipients"
    BCC_RECIPIENTS = "bcc_recipients"
    REPLY_TO_RECIPIENTS = "reply_to_recipients"
    RECEIVED_DATE_TIME = "received_date_time"
    SENT_DATE_TIME = "sent_date_time"
    CREATED_DATE_TIME = "created_date_time"
    IMPORTANCE = "importance"
    CATEGORIES = "categories"
    HAS_ATTACHMENTS = "has_attachments"
    IS_READ = "is_read"
    IS_DRAFT = "is_draft"
    INFERENCE_CLASSIFICATION = "inference_classification"
    FOLLOWUP_STATUS = "followup_status"
    BODY_PREVIEW = "body_preview"
    BODY = "body"
    HEADERS = "headers"
    SENSITIVITY = "sensitivity"
    MESSAGE_SIZE_BYTES = "message_size_bytes"
    ITEM_CLASS = "item_class"


@dataclass(frozen=True, slots=True)
class MailRecipientFact:
    """One bounded Graph recipient without retaining provider dictionaries."""

    name: str | None = None
    address: str | None = None


@dataclass(frozen=True, slots=True)
class MailRuleFacts:
    """Bounded values plus explicit fact availability."""

    change_key: str | None = None
    last_modified_date_time: str | None = None
    subject: str | None = None
    from_recipient: MailRecipientFact | None = None
    sender_recipient: MailRecipientFact | None = None
    to_recipients: tuple[MailRecipientFact, ...] = ()
    cc_recipients: tuple[MailRecipientFact, ...] = ()
    bcc_recipients: tuple[MailRecipientFact, ...] = ()
    reply_to_recipients: tuple[MailRecipientFact, ...] = ()
    received_date_time: str | None = None
    sent_date_time: str | None = None
    created_date_time: str | None = None
    importance: str | None = None
    categories: tuple[str, ...] = ()
    has_attachments: bool | None = None
    is_read: bool | None = None
    is_draft: bool | None = None
    inference_classification: str | None = None
    followup_status: str | None = None
    body_preview: str | None = None
    body: str | None = None
    headers: tuple[str, ...] = ()
    sensitivity: str | None = None
    message_size_bytes: int | None = None
    item_class: str | None = None
    available_facts: frozenset[MailRuleFact] = frozenset()


@dataclass(frozen=True, slots=True)
class MailRuleObservation:
    """One bounded provider observation plus acquisition correlation."""

    message_id: str
    run_id: str | None
    evidence_id: str | None
    observation_kind: str
    facts: MailRuleFacts


@dataclass(frozen=True, slots=True)
class MailRuleProbeFailure:
    """One unavailable requested fact with a privacy-safe reason."""

    fact: MailRuleFact
    reason_code: str

    def __post_init__(self) -> None:
        _require_safe_token("reason_code", self.reason_code)


@dataclass(frozen=True, slots=True)
class MailRuleProbeData:
    """Bounded facts returned by one rule-probe acquisition."""

    status: MailRuleProbeStatus
    facts: MailRuleFacts
    evidence_id: str | None
    failures: tuple[MailRuleProbeFailure, ...] = ()

    def __post_init__(self) -> None:
        if self.status is MailRuleProbeStatus.COMPLETE:
            if self.failures:
                raise ValueError("complete rule probe carries no fact failures")
            return
        if not self.failures:
            raise ValueError("partial/failed rule probe requires fact failures")

    @property
    def reason_code(self) -> str | None:
        """Transitional single-reason view for existing observability."""

        return self.failures[0].reason_code if self.failures else None


@dataclass(frozen=True, slots=True)
class MailRuleEvaluation:
    """One bounded intermediate or terminal acquisition-policy result."""

    state: MailRuleEvaluationState
    selected_profile: str | None = None
    outcome: MailRuleDecisionOutcome | None = None
    required_data: frozenset[MailRuleRequiredData] = frozenset()
    ruleset_id: str | None = None
    ruleset_digest: str | None = None
    matched_rule_ids: tuple[str, ...] = ()
    stop_rule_id: str | None = None
    probe_used: bool = False
    fallback_used: bool = False
    reason_code: str | None = None

    def __post_init__(self) -> None:
        _validate_correlation_tokens(self)
        if (
            self.stop_rule_id is not None
            and self.stop_rule_id not in self.matched_rule_ids
        ):
            raise ValueError("stop rule must be one of the matched rules")

        if self.state is MailRuleEvaluationState.FINAL:
            self._validate_final()
            return
        if self.state is MailRuleEvaluationState.NEEDS_DATA:
            self._validate_needs_data()
            return
        self._validate_unresolved()

    def _validate_final(self) -> None:
        if self.selected_profile is None:
            raise ValueError("final rule evaluation requires an acquisition profile")
        if self.outcome not in {
            MailRuleDecisionOutcome.MATCHED,
            MailRuleDecisionOutcome.DEFAULT,
        }:
            raise ValueError("final rule evaluation requires a terminal outcome")
        if self.required_data or self.reason_code is not None or self.fallback_used:
            raise ValueError("final rule evaluation carries no pending/fallback state")

    def _validate_needs_data(self) -> None:
        if not self.required_data:
            raise ValueError("needs-data rule evaluation requires source data")
        if (
            self.selected_profile is not None
            or self.outcome is not None
            or self.reason_code is not None
            or self.stop_rule_id is not None
            or self.fallback_used
        ):
            raise ValueError("needs-data rule evaluation is not terminal")

    def _validate_unresolved(self) -> None:
        if self.selected_profile is None:
            raise ValueError("unresolved rule evaluation requires a fail-safe profile")
        if self.outcome is not MailRuleDecisionOutcome.UNRESOLVED:
            raise ValueError("unresolved rule evaluation requires unresolved outcome")
        if self.required_data:
            raise ValueError("unresolved rule evaluation carries no pending data")
        if not self.fallback_used or self.reason_code is None:
            raise ValueError("unresolved rule evaluation requires fallback and reason")


class MailRuleEvaluator(Protocol):
    """Pure deterministic evaluator consumed by the Scrapy adapter."""

    def evaluate(
        self,
        observation: MailRuleObservation,
        *,
        probe: MailRuleProbeData | None = None,
    ) -> MailRuleEvaluation:
        """Return one intermediate or terminal rule evaluation."""
        ...


def _require_safe_token(name: str, value: str) -> None:
    if _SAFE_TOKEN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a bounded log-safe token")


def _validate_correlation_tokens(evaluation: MailRuleEvaluation) -> None:
    for name, value in (
        ("selected_profile", evaluation.selected_profile),
        ("ruleset_id", evaluation.ruleset_id),
        ("stop_rule_id", evaluation.stop_rule_id),
        ("reason_code", evaluation.reason_code),
    ):
        if value is not None:
            _require_safe_token(name, value)
    for rule_id in evaluation.matched_rule_ids:
        _require_safe_token("matched_rule_id", rule_id)
    if (
        evaluation.ruleset_digest is not None
        and _SHA256.fullmatch(evaluation.ruleset_digest) is None
    ):
        raise ValueError("ruleset_digest must be lowercase SHA-256 hex")


def _bounded_nullable_string(
    raw: Mapping[str, object],
    key: str,
    maximum: int,
) -> tuple[str | None, bool]:
    if key not in raw:
        return None, False
    value = raw[key]
    if value is None:
        return None, True
    if isinstance(value, str) and len(value) <= maximum:
        return value, True
    return None, False


def _bounded_bool(
    raw: Mapping[str, object],
    key: str,
) -> tuple[bool | None, bool]:
    if key not in raw:
        return None, False
    value = raw[key]
    if isinstance(value, bool):
        return value, True
    return None, False


def _recipient_fact(raw: object) -> tuple[MailRecipientFact | None, bool]:
    if raw is None:
        return None, True
    if not isinstance(raw, Mapping):
        return None, False
    email = raw.get("emailAddress")
    if not isinstance(email, Mapping):
        return None, False
    name = email.get("name")
    address = email.get("address")
    if name is not None and (
        not isinstance(name, str) or len(name) > _MAX_RECIPIENT_PART_CHARS
    ):
        return None, False
    if address is not None and (
        not isinstance(address, str) or len(address) > _MAX_RECIPIENT_PART_CHARS
    ):
        return None, False
    return MailRecipientFact(name=name, address=address), True


def _recipient_list(
    raw: Mapping[str, object],
    key: str,
) -> tuple[tuple[MailRecipientFact, ...], bool]:
    if key not in raw:
        return (), False
    value = raw[key]
    if not isinstance(value, list):
        return (), False
    result: list[MailRecipientFact] = []
    for recipient in value:
        fact, valid = _recipient_fact(recipient)
        if not valid or fact is None:
            return (), False
        result.append(fact)
    return tuple(result), True


def _categories(raw: Mapping[str, object]) -> tuple[tuple[str, ...], bool]:
    if "categories" not in raw:
        return (), False
    value = raw["categories"]
    if not isinstance(value, list) or len(value) > _MAX_CATEGORIES:
        return (), False
    if any(
        not isinstance(item, str) or len(item) > _MAX_CATEGORY_CHARS for item in value
    ):
        return (), False
    return tuple(value), True


def _followup_status(raw: Mapping[str, object]) -> tuple[str | None, bool]:
    if "flag" not in raw:
        return None, False
    flag = raw["flag"]
    if not isinstance(flag, Mapping) or "flagStatus" not in flag:
        return None, False
    value = flag["flagStatus"]
    if value is None:
        return None, True
    if isinstance(value, str) and len(value) <= _MAX_SCALAR_CHARS:
        return value, True
    return None, False


def _discovery_facts(raw: Mapping[str, object]) -> MailRuleFacts:
    available: set[MailRuleFact] = set()

    def string(key: str, fact: MailRuleFact, maximum: int = _MAX_SCALAR_CHARS):
        value, valid = _bounded_nullable_string(raw, key, maximum)
        if valid:
            available.add(fact)
        return value

    def boolean(key: str, fact: MailRuleFact):
        value, valid = _bounded_bool(raw, key)
        if valid:
            available.add(fact)
        return value

    from_recipient, from_valid = (
        _recipient_fact(raw["from"]) if "from" in raw else (None, False)
    )
    sender_recipient, sender_valid = (
        _recipient_fact(raw["sender"]) if "sender" in raw else (None, False)
    )
    if from_valid:
        available.add(MailRuleFact.FROM_RECIPIENT)
    if sender_valid:
        available.add(MailRuleFact.SENDER_RECIPIENT)

    recipient_keys = (
        ("toRecipients", MailRuleFact.TO_RECIPIENTS),
        ("ccRecipients", MailRuleFact.CC_RECIPIENTS),
        ("bccRecipients", MailRuleFact.BCC_RECIPIENTS),
        ("replyTo", MailRuleFact.REPLY_TO_RECIPIENTS),
    )
    present_lists = [raw[key] for key, _fact in recipient_keys if key in raw]
    recipient_overflow = (
        sum(len(value) for value in present_lists if isinstance(value, list))
        > _MAX_RECIPIENTS
    )
    recipient_values: dict[MailRuleFact, tuple[MailRecipientFact, ...]] = {}
    for key, fact in recipient_keys:
        values, valid = _recipient_list(raw, key)
        if recipient_overflow:
            values, valid = (), False
        recipient_values[fact] = values
        if valid:
            available.add(fact)

    categories, categories_valid = _categories(raw)
    if categories_valid:
        available.add(MailRuleFact.CATEGORIES)
    followup, followup_valid = _followup_status(raw)
    if followup_valid:
        available.add(MailRuleFact.FOLLOWUP_STATUS)

    return MailRuleFacts(
        change_key=string("changeKey", MailRuleFact.CHANGE_KEY),
        last_modified_date_time=string(
            "lastModifiedDateTime", MailRuleFact.LAST_MODIFIED_DATE_TIME
        ),
        subject=string("subject", MailRuleFact.SUBJECT, _MAX_SUBJECT_CHARS),
        from_recipient=from_recipient,
        sender_recipient=sender_recipient,
        to_recipients=recipient_values[MailRuleFact.TO_RECIPIENTS],
        cc_recipients=recipient_values[MailRuleFact.CC_RECIPIENTS],
        bcc_recipients=recipient_values[MailRuleFact.BCC_RECIPIENTS],
        reply_to_recipients=recipient_values[MailRuleFact.REPLY_TO_RECIPIENTS],
        received_date_time=string("receivedDateTime", MailRuleFact.RECEIVED_DATE_TIME),
        sent_date_time=string("sentDateTime", MailRuleFact.SENT_DATE_TIME),
        created_date_time=string("createdDateTime", MailRuleFact.CREATED_DATE_TIME),
        importance=string("importance", MailRuleFact.IMPORTANCE),
        categories=categories,
        has_attachments=boolean("hasAttachments", MailRuleFact.HAS_ATTACHMENTS),
        is_read=boolean("isRead", MailRuleFact.IS_READ),
        is_draft=boolean("isDraft", MailRuleFact.IS_DRAFT),
        inference_classification=string(
            "inferenceClassification", MailRuleFact.INFERENCE_CLASSIFICATION
        ),
        followup_status=followup,
        body_preview=string(
            "bodyPreview", MailRuleFact.BODY_PREVIEW, _MAX_BODY_PREVIEW_CHARS
        ),
        available_facts=frozenset(available),
    )


def mail_rule_observation_from_item(item: OutlookMailItem) -> MailRuleObservation:
    """Project provider JSON into bounded rule facts without raw-payload retention."""

    return MailRuleObservation(
        message_id=item.message_id,
        run_id=item.run_id,
        evidence_id=item.evidence_id,
        observation_kind=item.observation_kind,
        facts=_discovery_facts(item.raw),
    )


__all__ = [
    "MailRecipientFact",
    "MailRuleDecisionOutcome",
    "MailRuleEvaluation",
    "MailRuleEvaluationState",
    "MailRuleEvaluator",
    "MailRuleFact",
    "MailRuleFacts",
    "MailRuleObservation",
    "MailRuleProbeData",
    "MailRuleProbeFailure",
    "MailRuleProbeStatus",
    "MailRuleRequiredData",
    "mail_rule_observation_from_item",
]

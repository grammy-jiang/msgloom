"""Pure contracts for Outlook Mail acquisition-rule evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from message_ingest.items.microsoft.outlook.email import OutlookMailItem

_SAFE_TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,96}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


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
    """Closed vocabulary of source data that evaluation may request."""

    BODY = "body"


class MailRuleProbeStatus(StrEnum):
    """Usability of one bounded rule-probe result."""

    COMPLETE = "complete"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class MailRuleObservation:
    """Bounded discovery facts used by rule evaluation without raw payload retention."""

    message_id: str
    run_id: str | None
    evidence_id: str | None
    observation_kind: str
    last_modified_date_time: str | None
    subject: str | None
    sender_address: str | None
    from_address: str | None
    to_addresses: tuple[str, ...]
    cc_addresses: tuple[str, ...]
    bcc_addresses: tuple[str, ...]
    importance: str | None
    categories: tuple[str, ...]
    has_attachments: bool | None
    body_preview: str | None


@dataclass(frozen=True, slots=True)
class MailRuleProbeData:
    """Bounded source data returned by one acquisition-rule probe."""

    status: MailRuleProbeStatus
    body: str | None
    last_modified_date_time: str | None
    evidence_id: str | None
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if self.reason_code is not None:
            _require_safe_token("reason_code", self.reason_code)
        if self.status is MailRuleProbeStatus.COMPLETE:
            if not isinstance(self.body, str) or self.reason_code is not None:
                raise ValueError(
                    "complete rule probe requires body and no failure reason"
                )
            return
        if self.body is not None or self.reason_code is None:
            raise ValueError("failed rule probe requires only a bounded failure reason")


@dataclass(frozen=True, slots=True)
class MailRuleEvaluation:
    """One bounded intermediate or terminal acquisition-policy result."""

    state: MailRuleEvaluationState
    selected_profile: str | None = None
    outcome: MailRuleDecisionOutcome | None = None
    required_data: MailRuleRequiredData | None = None
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
            if self.selected_profile is None:
                raise ValueError(
                    "final rule evaluation requires an acquisition profile"
                )
            if self.outcome not in {
                MailRuleDecisionOutcome.MATCHED,
                MailRuleDecisionOutcome.DEFAULT,
            }:
                raise ValueError("final rule evaluation requires a terminal outcome")
            if (
                self.required_data is not None
                or self.reason_code is not None
                or self.fallback_used
            ):
                raise ValueError(
                    "final rule evaluation carries no pending/fallback state"
                )
            return

        if self.state is MailRuleEvaluationState.NEEDS_DATA:
            if self.required_data is not MailRuleRequiredData.BODY:
                raise ValueError("needs-data rule evaluation requires body data")
            if (
                self.selected_profile is not None
                or self.outcome is not None
                or self.reason_code is not None
                or self.stop_rule_id is not None
                or self.fallback_used
            ):
                raise ValueError("needs-data rule evaluation is not terminal")
            return

        if self.selected_profile is None:
            raise ValueError("unresolved rule evaluation requires a fail-safe profile")
        if self.outcome is not MailRuleDecisionOutcome.UNRESOLVED:
            raise ValueError("unresolved rule evaluation requires unresolved outcome")
        if self.required_data is not None:
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


def _recipient_addresses(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    values: list[str] = []
    for recipient in raw:
        if not isinstance(recipient, dict):
            continue
        email = recipient.get("emailAddress")
        if not isinstance(email, dict):
            continue
        address = email.get("address")
        if isinstance(address, str):
            values.append(address)
    return tuple(values)


def _string_tuple(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(value for value in raw if isinstance(value, str))


def mail_rule_observation_from_item(item: OutlookMailItem) -> MailRuleObservation:
    """Project one provider observation into the bounded future RuleEngine input."""

    return MailRuleObservation(
        message_id=item.message_id,
        run_id=item.run_id,
        evidence_id=item.evidence_id,
        observation_kind=item.observation_kind,
        last_modified_date_time=(
            value
            if isinstance((value := item.raw.get("lastModifiedDateTime")), str)
            else None
        ),
        subject=item.subject,
        sender_address=item.sender_address,
        from_address=item.from_address,
        to_addresses=_recipient_addresses(item.raw.get("toRecipients")),
        cc_addresses=_recipient_addresses(item.raw.get("ccRecipients")),
        bcc_addresses=_recipient_addresses(item.raw.get("bccRecipients")),
        importance=item.importance,
        categories=_string_tuple(item.raw.get("categories")),
        has_attachments=item.has_attachments,
        body_preview=item.body_preview,
    )


__all__ = [
    "MailRuleDecisionOutcome",
    "MailRuleEvaluation",
    "MailRuleEvaluationState",
    "MailRuleEvaluator",
    "MailRuleObservation",
    "MailRuleProbeData",
    "MailRuleProbeStatus",
    "MailRuleRequiredData",
    "mail_rule_observation_from_item",
]

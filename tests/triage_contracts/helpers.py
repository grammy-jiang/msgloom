"""Synthetic helpers for triage contract tests."""

from __future__ import annotations

from datetime import UTC, datetime

from msgloom.contracts import VersionRef
from msgloom.preparation import (
    FilteringDecision,
    FilteringDisposition,
    PreparedParty,
    PreparedRecord,
    PreparedSourceType,
)
from msgloom.triage import (
    EvidenceKind,
    Priority,
    RuleOutcome,
    TopicAllocation,
    TopicCandidate,
    TriageEvidence,
)


def ref(kind: str, identity: str, version: str = "1") -> VersionRef:
    """Build one synthetic exact version reference."""
    return VersionRef(kind=kind, identity=identity, version=version)


def prepared(
    identity: str,
    *,
    subject: str = "Synthetic work",
    body: str = "Please review the synthetic work.",
    sender: str = "sender@example.invalid",
    filtering: FilteringDisposition = FilteringDisposition.INCLUDED,
) -> PreparedRecord:
    """Build a minimal prepared record with no private provider data."""
    return PreparedRecord(
        source=ref("source", identity),
        source_type=PreparedSourceType.OUTLOOK_EMAIL,
        sender=PreparedParty(identity=sender),
        author=None,
        recipients=(),
        source_time=datetime(2026, 9, 29, 8, 0, tzinfo=UTC),
        subject=subject,
        body=body,
        relationships=(),
        attachments=(),
        parsed_contents=(),
        limitations=(),
        source_mappings=(),
        filtering=FilteringDecision(disposition=filtering),
    )


def empty_outcome(source: VersionRef) -> RuleOutcome:
    """Build an outcome with no deterministic matches."""
    return RuleOutcome(
        source_ref=source,
        matches=(),
        excluded=False,
        required_priority=None,
        minimum_priority=None,
        guidance=(),
        review_items=(),
    )


def evidence(
    source: VersionRef, text: str = "Synthetic source statement"
) -> TriageEvidence:
    """Build grounded synthetic evidence."""
    return TriageEvidence(
        kind=EvidenceKind.SOURCE_STATEMENT,
        source_ref=source,
        statement=text,
    )


def topic(
    key: str,
    sources: tuple[VersionRef, ...],
    *,
    priority: Priority = Priority.NORMAL,
    rule_matches: tuple[VersionRef, ...] = (),
    title: str = "Synthetic topic",
) -> TopicCandidate:
    """Build one bounded candidate topic."""
    return TopicCandidate(
        allocation_key=key,
        title=title,
        source_refs=sources,
        rule_matches=rule_matches,
        priority=priority,
        reason="Synthetic reason",
    )


def allocation(
    key: str,
    topic_identity: str,
    assessment_identity: str,
) -> TopicAllocation:
    """Build trusted application-issued topic and assessment identities."""
    return TopicAllocation(
        allocation_key=key,
        topic_ref=ref("topic", topic_identity),
        assessment_ref=ref("topic-assessment", assessment_identity),
    )

"""Build and validate immutable report semantics before rendering."""

from __future__ import annotations

from itertools import chain
from urllib.parse import urlsplit

from msgloom.contracts import Limitation
from msgloom.triage import EvidenceKind, TopicAssessment, TriageEvidence

from .models import ReportOverviewItem, ReportSelectionPlan, ReportTopic


class ReportBuildError(ValueError):
    """Classify incomplete or unsafe report content without leaking source data."""


def build_topics(
    topics: tuple[TopicAssessment, ...],
    plan: ReportSelectionPlan,
) -> tuple[ReportTopic, ...]:
    """Copy every essential field and source identity into report topics."""
    links = {item.source_ref: item for item in plan.source_links}
    for link in plan.source_links:
        parsed = urlsplit(link.url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ReportBuildError("source link is not a safe http/https URL")
    result = []
    for topic in topics:
        evidence = _evidence(topic)
        source_set = set(topic.source_refs)
        if any(item.source_ref not in source_set for item in evidence):
            raise ReportBuildError("topic evidence references an unselected source")
        topic_links = tuple(links[x] for x in topic.source_refs if x in links)
        result.append(
            ReportTopic(
                topic_ref=topic.topic_ref,
                assessment_ref=topic.assessment_ref,
                title=topic.title,
                source_refs=topic.source_refs,
                priority=topic.priority,
                reason=topic.reason,
                developments=topic.developments,
                actions=topic.actions,
                deadlines=topic.deadlines,
                risks=topic.risks,
                evidence=evidence,
                limitations=topic.limitations,
                source_links=topic_links,
            )
        )
    return tuple(result)


def build_overview(topics: tuple[ReportTopic, ...]) -> tuple[ReportOverviewItem, ...]:
    """Build identity-bound overview entries without self-reported coverage."""
    return tuple(
        ReportOverviewItem(
            topic_ref=item.topic_ref,
            assessment_ref=item.assessment_ref,
            title=item.title,
            priority=item.priority,
            developments=tuple(x.text for x in item.developments),
            actions=tuple(x.text for x in item.actions),
            deadlines=tuple(x.original_wording for x in item.deadlines),
            risks=tuple(x.text for x in item.risks),
        )
        for item in topics
    )


def validate_semantic_coverage(
    topics: tuple[ReportTopic, ...],
    overview: tuple[ReportOverviewItem, ...],
) -> None:
    """Compare exact identities and essential content, never item counts alone."""
    overview_by = {(x.topic_ref, x.assessment_ref): x for x in overview}
    expected = {(x.topic_ref, x.assessment_ref) for x in topics}
    if set(overview_by) != expected:
        raise ReportBuildError("report overview topic identity coverage failed")
    for topic in topics:
        item = overview_by[(topic.topic_ref, topic.assessment_ref)]
        if item.actions != tuple(x.text for x in topic.actions):
            raise ReportBuildError("report overview action coverage failed")
        if item.deadlines != tuple(x.original_wording for x in topic.deadlines):
            raise ReportBuildError("report overview deadline coverage failed")
        if item.risks != tuple(x.text for x in topic.risks):
            raise ReportBuildError("report overview risk coverage failed")
        if item.developments != tuple(x.text for x in topic.developments):
            raise ReportBuildError("report overview development coverage failed")


def report_limitations(
    topics: tuple[ReportTopic, ...],
    plan: ReportSelectionPlan,
    upstream: tuple[Limitation, ...] = (),
) -> tuple[Limitation, ...]:
    """Collect explicit source limitations and pending-work warnings."""
    values = list(upstream)
    values.extend(chain.from_iterable(item.limitations for item in topics))
    values.extend(
        Limitation(code="pending_newer_assessment", detail=item.detail)
        for item in plan.pending_warnings
    )
    return tuple(values)


def _evidence(topic: TopicAssessment) -> tuple[TriageEvidence, ...]:
    values: list[TriageEvidence] = []
    for item in topic.developments:
        values.extend(item.evidence)
    for item in topic.actions:
        values.extend(item.evidence)
    for item in topic.deadlines:
        values.extend(item.evidence)
    for item in topic.risks:
        values.extend(item.evidence)
    unique: list[TriageEvidence] = []
    for item in values:
        if item not in unique:
            unique.append(item)
    if any(
        item.kind not in {EvidenceKind.SOURCE_STATEMENT, EvidenceKind.INTERPRETATION}
        for item in unique
    ):
        raise ReportBuildError("report evidence kind is unsupported")
    return tuple(unique)

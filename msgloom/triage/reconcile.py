"""Validate and bind semantic triage output to trusted saved inputs."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ValidationError
from pydantic_core import PydanticSerializationError

from msgloom.contracts import VersionRef
from msgloom.preparation import PreparedRecord
from msgloom.preparation.filtering import (
    FilterConfig,
    FilterOutcome,
    FilterResult,
    apply_filters,
)

from .evidence import EvidenceGroundingError, validate_evidence
from .models import (
    Priority,
    PriorTopicAssessment,
    RelationshipStatus,
    SourceDisposition,
    SourceDispositionKind,
    TopicAllocation,
    TopicAssessment,
    TopicCandidate,
    TopicRelationship,
    TriageCandidate,
    TriageData,
    TriageEvidence,
    priority_rank,
)
from .rules import RuleOutcome, TriageRuleEvaluation, evaluate_rules


class TriageReconciliationError(ValueError):
    """Expose only a stable safe code for rejected semantic output."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def reconcile_triage(
    candidate: TriageCandidate,
    *,
    selected_records: tuple[PreparedRecord, ...],
    filter_config: FilterConfig,
    filter_results: tuple[FilterResult, ...],
    rule_evaluation: TriageRuleEvaluation,
    topic_allocations: tuple[TopicAllocation, ...],
    prior_assessments: tuple[PriorTopicAssessment, ...] = (),
) -> TriageData:
    """Bind candidate semantics to exact, revalidated persisted inputs."""
    candidate = _revalidate(candidate, TriageCandidate, "invalid-candidate-input")
    records_tuple = _revalidate_many(
        selected_records, PreparedRecord, "invalid-selected-input"
    )
    filter_config = _revalidate(
        filter_config, FilterConfig, "invalid-filter-configuration"
    )
    filter_results = _revalidate_many(
        filter_results, FilterResult, "invalid-filter-result"
    )
    rule_evaluation = _revalidate(
        rule_evaluation, TriageRuleEvaluation, "invalid-rule-evaluation"
    )
    topic_allocations = _revalidate_many(
        topic_allocations, TopicAllocation, "invalid-topic-allocation"
    )
    prior_assessments = _revalidate_many(
        prior_assessments, PriorTopicAssessment, "invalid-prior-assessment"
    )

    records = _unique_map(
        ((record.source, record) for record in records_tuple),
        "duplicate-selected-source",
    )
    filters = _validate_filter_binding(records, filter_config, filter_results)
    outcomes = _validate_rule_binding(records_tuple, records, rule_evaluation)
    allocations = _unique_map(
        ((item.allocation_key, item) for item in topic_allocations),
        "duplicate-topic-allocation",
    )
    topic_keys = tuple(topic.allocation_key for topic in candidate.topics)
    if len(topic_keys) != len(set(topic_keys)):
        raise TriageReconciliationError("duplicate-topic-allocation-key")
    if set(topic_keys) != set(allocations):
        raise TriageReconciliationError("topic-allocation-coverage-mismatch")
    priors = _unique_map(
        (((item.topic_ref, item.assessment_ref), item) for item in prior_assessments),
        "duplicate-prior-assessment",
    )
    _validate_disposition_uniqueness(candidate.dispositions)
    _validate_source_coverage(candidate, records)
    topics: list[TopicAssessment] = []
    relationships: list[TopicRelationship] = []
    for topic in candidate.topics:
        allocation = allocations[topic.allocation_key]
        _validate_topic(topic, records, filters, outcomes)
        relationship = _relationship(topic, allocation, records, priors)
        if relationship is not None:
            relationships.append(relationship)
        topics.append(_bind_topic(topic, allocation))
    _validate_dispositions(candidate.dispositions, records, filters, outcomes)
    try:
        data = TriageData(
            topics=tuple(topics),
            dispositions=candidate.dispositions,
            relationships=tuple(relationships),
        )
        return TriageData.model_validate_json(data.model_dump_json(), strict=True)
    except (ValidationError, ValueError, TypeError, PydanticSerializationError):
        raise TriageReconciliationError("invalid-reconciled-triage-data") from None


def _validate_filter_binding(
    records: dict[VersionRef, PreparedRecord],
    config: FilterConfig,
    results: tuple[FilterResult, ...],
) -> dict[VersionRef, FilterResult]:
    bound = _unique_map(
        ((result.input, result) for result in results),
        "duplicate-filter-result",
    )
    if set(bound) != set(records):
        raise TriageReconciliationError("filter-result-coverage-mismatch")
    for source, record in records.items():
        result = bound[source]
        if result.configuration_ref != config.reference:
            raise TriageReconciliationError("filter-configuration-mismatch")
        try:
            expected = apply_filters(record, config)
        except (ValidationError, ValueError, TypeError):
            raise TriageReconciliationError("invalid-filter-binding") from None
        if result != expected:
            raise TriageReconciliationError("filter-result-mismatch")
    return bound


def _validate_rule_binding(
    records_tuple: tuple[PreparedRecord, ...],
    records: dict[VersionRef, PreparedRecord],
    evaluation: TriageRuleEvaluation,
) -> dict[VersionRef, RuleOutcome]:
    outcomes = _unique_map(
        ((outcome.source_ref, outcome) for outcome in evaluation.outcomes),
        "duplicate-rule-outcome",
    )
    if set(outcomes) != set(records):
        raise TriageReconciliationError("rule-outcome-coverage-mismatch")
    try:
        expected = evaluate_rules(records_tuple, evaluation.config)
    except (ValidationError, ValueError, TypeError):
        raise TriageReconciliationError("invalid-rule-evaluation") from None
    if evaluation.outcomes != expected:
        raise TriageReconciliationError("rule-evaluation-mismatch")
    return outcomes


def _validate_source_coverage(
    candidate: TriageCandidate,
    records: dict[VersionRef, PreparedRecord],
) -> None:
    selected = set(records)
    topic_sources = {
        source for topic in candidate.topics for source in topic.source_refs
    }
    disposition_sources = {item.source_ref for item in candidate.dispositions}
    used = topic_sources | disposition_sources
    if not used <= selected:
        raise TriageReconciliationError("invented-source-reference")
    if used != selected:
        raise TriageReconciliationError("missing-source-coverage")
    if topic_sources & disposition_sources:
        raise TriageReconciliationError("source-has-topic-and-disposition")


def _validate_disposition_uniqueness(
    dispositions: tuple[SourceDisposition, ...],
) -> None:
    refs = tuple(item.source_ref for item in dispositions)
    if len(refs) != len(set(refs)):
        raise TriageReconciliationError("duplicate-source-disposition")


def _validate_topic(
    topic: TopicCandidate,
    records: dict[VersionRef, PreparedRecord],
    filters: dict[VersionRef, FilterResult],
    outcomes: dict[VersionRef, RuleOutcome],
) -> None:
    for source in topic.source_refs:
        record = records.get(source)
        outcome = outcomes.get(source)
        result = filters.get(source)
        if record is None or outcome is None or result is None:
            raise TriageReconciliationError("invented-source-reference")
        if result.outcome is FilterOutcome.EXCLUDED:
            raise TriageReconciliationError("excluded-source-mapped-to-topic")
        if result.outcome is FilterOutcome.CONFLICT:
            raise TriageReconciliationError("filter-conflict-mapped-to-topic")
        if outcome.excluded:
            raise TriageReconciliationError("excluded-source-mapped-to-topic")
        if outcome.review_items:
            raise TriageReconciliationError("rule-conflict-mapped-to-topic")
    expected_rules = {
        match.rule_ref
        for source in topic.source_refs
        for match in outcomes[source].matches
    }
    if set(topic.rule_matches) != expected_rules:
        raise TriageReconciliationError("topic-rule-match-mismatch")
    _validate_priority(topic, outcomes)
    allowed_sources = set(topic.source_refs)
    for item in _topic_evidence(topic):
        record = records.get(item.source_ref)
        if record is None:
            raise TriageReconciliationError("evidence-source-mismatch")
        _ground_evidence(item, record, allowed_sources)


def _validate_priority(
    topic: TopicCandidate,
    outcomes: dict[VersionRef, RuleOutcome],
) -> None:
    required = {
        outcomes[source].required_priority
        for source in topic.source_refs
        if outcomes[source].required_priority is not None
    }
    if len(required) > 1:
        raise TriageReconciliationError("topic-required-priority-conflict")
    if required and topic.priority != next(iter(required)):
        raise TriageReconciliationError("required-priority-violation")
    minimums: list[Priority] = []
    for source in topic.source_refs:
        minimum = outcomes[source].minimum_priority
        if minimum is not None:
            minimums.append(minimum)
    if minimums:
        strongest = max(minimums, key=priority_rank)
        if priority_rank(topic.priority) < priority_rank(strongest):
            raise TriageReconciliationError("minimum-priority-violation")


def _topic_evidence(topic: TopicCandidate) -> Iterable[TriageEvidence]:
    for development in topic.developments:
        yield from development.evidence
    for action in topic.actions:
        yield from action.evidence
    for deadline in topic.deadlines:
        yield from deadline.evidence
    for risk in topic.risks:
        yield from risk.evidence


def _validate_dispositions(
    dispositions: tuple[SourceDisposition, ...],
    records: dict[VersionRef, PreparedRecord],
    filters: dict[VersionRef, FilterResult],
    outcomes: dict[VersionRef, RuleOutcome],
) -> None:
    for disposition in dispositions:
        record = records[disposition.source_ref]
        result = filters[disposition.source_ref]
        outcome = outcomes[disposition.source_ref]
        for item in disposition.evidence:
            _ground_evidence(item, record, {disposition.source_ref})
        expected = _required_disposition(result, outcome)
        if expected is not None and disposition.kind is not expected:
            raise TriageReconciliationError("deterministic-disposition-violation")
        if expected is None and disposition.kind is SourceDispositionKind.EXCLUDED:
            raise TriageReconciliationError("unpermitted-excluded-disposition")
        if expected is None and (
            outcome.required_priority is not None
            or outcome.minimum_priority is not None
        ):
            raise TriageReconciliationError("required-priority-source-disposed")


def _required_disposition(
    result: FilterResult,
    outcome: RuleOutcome,
) -> SourceDispositionKind | None:
    if result.outcome is FilterOutcome.CONFLICT or outcome.review_items:
        return SourceDispositionKind.REVIEW_REQUIRED
    if result.outcome is FilterOutcome.EXCLUDED or outcome.excluded:
        return SourceDispositionKind.EXCLUDED
    return None


def _ground_evidence(
    item: TriageEvidence,
    record: PreparedRecord,
    allowed_primary_sources: set[VersionRef],
) -> None:
    """Translate mechanical evidence failures to the opaque public boundary."""
    try:
        validate_evidence(item, record, allowed_primary_sources)
    except EvidenceGroundingError as exc:
        raise TriageReconciliationError(exc.code) from None


def _relationship(
    topic: TopicCandidate,
    allocation: TopicAllocation,
    records: dict[VersionRef, PreparedRecord],
    priors: dict[tuple[VersionRef, VersionRef], PriorTopicAssessment],
) -> TopicRelationship | None:
    continuation = topic.continuation
    if continuation is None:
        return None
    key = (continuation.prior_topic_ref, continuation.prior_assessment_ref)
    prior = priors.get(key)
    if prior is None:
        raise TriageReconciliationError("invented-prior-topic")
    if allocation.assessment_ref == prior.assessment_ref:
        raise TriageReconciliationError("reused-prior-assessment-version")
    current_sources = set(topic.source_refs)
    prior_sources = set(prior.source_refs)
    for item in continuation.evidence:
        if item.source_ref in current_sources:
            _ground_evidence(item, records[item.source_ref], current_sources)
        elif item.source_ref not in prior_sources:
            raise TriageReconciliationError("continuation-evidence-source-mismatch")
    evidence_sources = {item.source_ref for item in continuation.evidence}
    if continuation.status is RelationshipStatus.CONFIRMED:
        if allocation.topic_ref != prior.topic_ref:
            raise TriageReconciliationError("confirmed-continuation-new-identity")
        if not (
            evidence_sources & current_sources and evidence_sources & prior_sources
        ):
            raise TriageReconciliationError("ungrounded-confirmed-continuation")
        linked_prior_evidence = tuple(
            item for item in continuation.evidence if item.source_ref in prior_sources
        )
        if any(item not in prior.evidence for item in linked_prior_evidence):
            raise TriageReconciliationError("ungrounded-confirmed-continuation")
    elif allocation.topic_ref == prior.topic_ref:
        raise TriageReconciliationError("uncertain-continuation-reused-identity")
    return TopicRelationship(
        current_topic_ref=allocation.topic_ref,
        current_assessment_ref=allocation.assessment_ref,
        prior_topic_ref=prior.topic_ref,
        prior_assessment_ref=prior.assessment_ref,
        status=continuation.status,
        reason=continuation.reason,
        evidence=continuation.evidence,
    )


def _bind_topic(
    topic: TopicCandidate,
    allocation: TopicAllocation,
) -> TopicAssessment:
    try:
        return TopicAssessment(
            topic_ref=allocation.topic_ref,
            assessment_ref=allocation.assessment_ref,
            title=topic.title,
            source_refs=topic.source_refs,
            rule_matches=topic.rule_matches,
            priority=topic.priority,
            reason=topic.reason,
            developments=topic.developments,
            actions=topic.actions,
            deadlines=topic.deadlines,
            risks=topic.risks,
            limitations=topic.limitations,
        )
    except (ValidationError, ValueError, TypeError):
        raise TriageReconciliationError("invalid-topic-candidate") from None


def _revalidate[T: BaseModel](value: object, model: type[T], code: str) -> T:
    if not isinstance(value, model):
        raise TriageReconciliationError(code)
    try:
        payload = value.model_dump_json(warnings="error")
        return model.model_validate_json(payload, strict=True)
    except (
        ValidationError,
        ValueError,
        TypeError,
        AttributeError,
        PydanticSerializationError,
    ):
        raise TriageReconciliationError(code) from None


def _revalidate_many[T: BaseModel](
    values: object,
    model: type[T],
    code: str,
) -> tuple[T, ...]:
    if not isinstance(values, tuple):
        raise TriageReconciliationError(code)
    return tuple(_revalidate(value, model, code) for value in values)


def _unique_map(items: Iterable[tuple[object, object]], code: str) -> dict:
    result: dict = {}
    for key, value in items:
        if key in result:
            raise TriageReconciliationError(code)
        result[key] = value
    return result

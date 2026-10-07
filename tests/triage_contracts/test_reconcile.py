"""Bound triage reconciliation and topic-identity regressions."""

from __future__ import annotations

import pytest

from msgloom.preparation import FilteringDisposition
from msgloom.preparation.filtering import (
    AddressNormalization,
    FilterConfig,
    FilterEffect,
    FilterRule,
    SubjectMatchMode,
    SubjectPattern,
    apply_filters,
)
from msgloom.triage import (
    PredicateKind,
    Priority,
    PriorTopicAssessment,
    RelationshipStatus,
    RuleEffect,
    RuleEffectKind,
    RulePredicate,
    SourceDisposition,
    SourceDispositionKind,
    TopicContinuation,
    TriageCandidate,
    TriageReconciliationError,
    TriageRule,
    TriageRuleConfig,
    evaluate_rule_set,
    reconcile_triage,
)

from .helpers import allocation, evidence, prepared, ref, topic


def _filter_config(*rules: FilterRule) -> FilterConfig:
    return FilterConfig(
        reference=ref("filter-config", "synthetic"),
        address_normalization=AddressNormalization.EXACT,
        rules=rules,
    )


def _rule_config(*rules: TriageRule) -> TriageRuleConfig:
    return TriageRuleConfig(version=ref("rule-set", "v1"), rules=rules)


def _inputs(records, rule_config: TriageRuleConfig | None = None):
    filter_config = _filter_config()
    return {
        "filter_config": filter_config,
        "filter_results": tuple(
            apply_filters(record, filter_config) for record in records
        ),
        "rule_evaluation": evaluate_rule_set(
            records, rule_config if rule_config is not None else _rule_config()
        ),
    }


def _required_rule(priority: Priority) -> TriageRule:
    return TriageRule(
        rule_ref=ref("triage-rule", "required"),
        predicates=(
            RulePredicate(
                kind=PredicateKind.SUBJECT_CONTAINS,
                text_value="Synthetic",
            ),
        ),
        effects=(
            RuleEffect(
                kind=RuleEffectKind.REQUIRED_PRIORITY,
                priority=priority,
            ),
        ),
    )


def test_exact_source_coverage_allows_several_topics_and_stable_identities() -> None:
    first = prepared("source-a", filtering=FilteringDisposition.PENDING)
    second = prepared("source-b", filtering=FilteringDisposition.PENDING)
    candidate = TriageCandidate(
        topics=(
            topic("a", (first.source,), title="Same display title"),
            topic("b", (second.source,), title="Same display title"),
        ),
        dispositions=(),
    )
    data = reconcile_triage(
        candidate,
        selected_records=(first, second),
        topic_allocations=(
            allocation("a", "topic-a", "assessment-a"),
            allocation("b", "topic-b", "assessment-b"),
        ),
        **_inputs((first, second)),
    )
    identities = {item.topic_ref.identity for item in data.topics}
    if identities != {"topic-a", "topic-b"}:
        pytest.fail("display title affected trusted topic identity")


@pytest.mark.parametrize(
    ("candidate", "records", "allocations", "code"),
    [
        (
            TriageCandidate(topics=(), dispositions=()),
            (prepared("source-a"),),
            (),
            "missing-source-coverage",
        ),
        (
            TriageCandidate(
                topics=(topic("a", (ref("source", "invented"),)),),
                dispositions=(),
            ),
            (prepared("source-a"),),
            (allocation("a", "topic-a", "assessment-a"),),
            "invented-source-reference",
        ),
    ],
)
def test_missing_and_invented_sources_fail(
    candidate,
    records,
    allocations,
    code: str,
) -> None:
    with pytest.raises(TriageReconciliationError, match=code):
        reconcile_triage(
            candidate,
            selected_records=records,
            topic_allocations=allocations,
            **_inputs(records),
        )


def test_duplicate_selected_source_and_disposition_fail() -> None:
    record = prepared("source-a")
    disposition = SourceDisposition(
        source_ref=record.source,
        kind=SourceDispositionKind.NO_REPORTABLE_CONTENT,
        reason="Synthetic disposition",
    )
    inputs = _inputs((record,))
    with pytest.raises(TriageReconciliationError, match="duplicate-selected-source"):
        reconcile_triage(
            TriageCandidate(topics=(), dispositions=(disposition,)),
            selected_records=(record, record),
            topic_allocations=(),
            **inputs,
        )
    with pytest.raises(TriageReconciliationError, match="duplicate-source-disposition"):
        reconcile_triage(
            TriageCandidate(topics=(), dispositions=(disposition, disposition)),
            selected_records=(record,),
            topic_allocations=(),
            **inputs,
        )


def test_required_and_minimum_priorities_cannot_be_overridden() -> None:
    record = prepared("source-a")
    rule = _required_rule(Priority.IMPORTANT)
    candidate = TriageCandidate(
        topics=(
            topic(
                "a",
                (record.source,),
                priority=Priority.NORMAL,
                rule_matches=(rule.rule_ref,),
            ),
        ),
        dispositions=(),
    )
    with pytest.raises(TriageReconciliationError, match="required-priority-violation"):
        reconcile_triage(
            candidate,
            selected_records=(record,),
            topic_allocations=(allocation("a", "topic-a", "assessment-a"),),
            **_inputs((record,), _rule_config(rule)),
        )


def test_real_filter_result_controls_pending_prepared_record() -> None:
    record = prepared("pending", filtering=FilteringDisposition.PENDING)
    candidate = TriageCandidate(
        topics=(topic("a", (record.source,)),),
        dispositions=(),
    )
    data = reconcile_triage(
        candidate,
        selected_records=(record,),
        topic_allocations=(allocation("a", "topic-a", "assessment-a"),),
        **_inputs((record,)),
    )
    if data.topics[0].source_refs != (record.source,):
        pytest.fail("accepted A2 filter result did not authorize selected source")

    legacy_excluded = prepared(
        "legacy-excluded", filtering=FilteringDisposition.EXCLUDED
    )
    accepted = reconcile_triage(
        TriageCandidate(
            topics=(topic("legacy", (legacy_excluded.source,)),),
            dispositions=(),
        ),
        selected_records=(legacy_excluded,),
        topic_allocations=(allocation("legacy", "topic-legacy", "assessment-legacy"),),
        **_inputs((legacy_excluded,)),
    )
    if accepted.topics[0].source_refs != (legacy_excluded.source,):
        pytest.fail("embedded prepared filtering overrode accepted A2 result")

    inputs = _inputs((record,))
    with pytest.raises(
        TriageReconciliationError, match="filter-result-coverage-mismatch"
    ):
        reconcile_triage(
            candidate,
            selected_records=(record,),
            filter_config=inputs["filter_config"],
            filter_results=(),
            rule_evaluation=inputs["rule_evaluation"],
            topic_allocations=(allocation("a", "topic-a", "assessment-a"),),
        )


def test_excluded_and_guidance_filter_results_cannot_be_semantically_overridden() -> (
    None
):
    record = prepared("source-a", filtering=FilteringDisposition.EXCLUDED)
    exclude = FilterRule(
        reference=ref("filter-rule", "exclude"),
        effect=FilterEffect.EXCLUDE,
        subject_patterns=(
            SubjectPattern(mode=SubjectMatchMode.CONTAINS, value="Synthetic"),
        ),
    )
    filter_config = _filter_config(exclude)
    excluded = apply_filters(record, filter_config)
    low_topic = topic("a", (record.source,), priority=Priority.LOW_VALUE)
    with pytest.raises(
        TriageReconciliationError, match="excluded-source-mapped-to-topic"
    ):
        reconcile_triage(
            TriageCandidate(topics=(low_topic,), dispositions=()),
            selected_records=(record,),
            filter_config=filter_config,
            filter_results=(excluded,),
            rule_evaluation=evaluate_rule_set((record,), _rule_config()),
            topic_allocations=(allocation("a", "topic-a", "assessment-a"),),
        )

    guidance = FilterRule(
        reference=ref("filter-rule", "guidance"),
        effect=FilterEffect.GUIDANCE,
        subject_patterns=(
            SubjectPattern(mode=SubjectMatchMode.CONTAINS, value="Synthetic"),
        ),
        guidance="Synthetic guidance",
    )
    guidance_config = _filter_config(guidance)
    disposition = SourceDisposition(
        source_ref=record.source,
        kind=SourceDispositionKind.EXCLUDED,
        reason="Model attempted exclusion",
    )
    with pytest.raises(
        TriageReconciliationError, match="unpermitted-excluded-disposition"
    ):
        reconcile_triage(
            TriageCandidate(topics=(), dispositions=(disposition,)),
            selected_records=(record,),
            filter_config=guidance_config,
            filter_results=(apply_filters(record, guidance_config),),
            rule_evaluation=evaluate_rule_set((record,), _rule_config()),
            topic_allocations=(),
        )


def test_rule_conflict_cannot_fall_back_to_low_value() -> None:
    record = prepared("conflict")
    rule = TriageRule(
        rule_ref=ref("triage-rule", "conflict"),
        predicates=(
            RulePredicate(kind=PredicateKind.SUBJECT_CONTAINS, text_value="Synthetic"),
        ),
        effects=(
            RuleEffect(
                kind=RuleEffectKind.REQUIRED_PRIORITY,
                priority=Priority.CRITICAL,
            ),
            RuleEffect(
                kind=RuleEffectKind.REQUIRED_PRIORITY,
                priority=Priority.NORMAL,
            ),
        ),
    )
    low_topic = topic(
        "c",
        (record.source,),
        priority=Priority.LOW_VALUE,
        rule_matches=(rule.rule_ref,),
    )
    with pytest.raises(
        TriageReconciliationError, match="rule-conflict-mapped-to-topic"
    ):
        reconcile_triage(
            TriageCandidate(topics=(low_topic,), dispositions=()),
            selected_records=(record,),
            topic_allocations=(allocation("c", "topic-c", "assessment-c"),),
            **_inputs((record,), _rule_config(rule)),
        )


def test_confirmed_continuation_uses_supplied_evidence_and_identity() -> None:
    current = prepared("current")
    prior_source = ref("source", "prior")
    prior_evidence = evidence(prior_source, "Prior synthetic statement")
    prior = PriorTopicAssessment(
        topic_ref=ref("topic", "stable-topic"),
        assessment_ref=ref("topic-assessment", "prior-assessment"),
        source_refs=(prior_source,),
        evidence=(prior_evidence,),
    )
    continuation = TopicContinuation(
        prior_topic_ref=prior.topic_ref,
        prior_assessment_ref=prior.assessment_ref,
        status=RelationshipStatus.CONFIRMED,
        reason="Synthetic supported continuation",
        evidence=(
            evidence(current.source, "Please review the synthetic work."),
            prior_evidence,
        ),
    )
    candidate_topic = topic("a", (current.source,)).model_copy(
        update={"continuation": continuation}
    )
    data = reconcile_triage(
        TriageCandidate(topics=(candidate_topic,), dispositions=()),
        selected_records=(current,),
        topic_allocations=(allocation("a", "stable-topic", "current-assessment"),),
        prior_assessments=(prior,),
        **_inputs((current,)),
    )
    if data.relationships[0].status is not RelationshipStatus.CONFIRMED:
        pytest.fail("supported continuation was not preserved as confirmed")


def test_unsupported_continuation_stays_uncertain_and_separate() -> None:
    current = prepared("current")
    prior_source = ref("source", "prior")
    prior = PriorTopicAssessment(
        topic_ref=ref("topic", "prior-topic"),
        assessment_ref=ref("topic-assessment", "prior-assessment"),
        source_refs=(prior_source,),
    )
    continuation = TopicContinuation(
        prior_topic_ref=prior.topic_ref,
        prior_assessment_ref=prior.assessment_ref,
        status=RelationshipStatus.UNCERTAIN,
        reason="Insufficient synthetic continuity evidence",
    )
    candidate_topic = topic("a", (current.source,)).model_copy(
        update={"continuation": continuation}
    )
    data = reconcile_triage(
        TriageCandidate(topics=(candidate_topic,), dispositions=()),
        selected_records=(current,),
        topic_allocations=(allocation("a", "new-topic", "current-assessment"),),
        prior_assessments=(prior,),
        **_inputs((current,)),
    )
    if data.topics[0].topic_ref == prior.topic_ref:
        pytest.fail("uncertain continuation collapsed into the prior topic")


def test_invented_prior_and_unsupplied_prior_evidence_fail_safely() -> None:
    current = prepared("current")
    prior_source = ref("source", "prior")
    continuation = TopicContinuation(
        prior_topic_ref=ref("topic", "prior-topic"),
        prior_assessment_ref=ref("topic-assessment", "prior-assessment"),
        status=RelationshipStatus.CONFIRMED,
        reason="Synthetic claimed continuation",
        evidence=(
            evidence(current.source, "Please review the synthetic work."),
            evidence(prior_source),
        ),
    )
    candidate_topic = topic("a", (current.source,)).model_copy(
        update={"continuation": continuation}
    )
    with pytest.raises(TriageReconciliationError, match="invented-prior-topic"):
        reconcile_triage(
            TriageCandidate(topics=(candidate_topic,), dispositions=()),
            selected_records=(current,),
            topic_allocations=(allocation("a", "prior-topic", "current-assessment"),),
            **_inputs((current,)),
        )

    prior = PriorTopicAssessment(
        topic_ref=continuation.prior_topic_ref,
        assessment_ref=continuation.prior_assessment_ref,
        source_refs=(prior_source,),
        evidence=(),
    )
    with pytest.raises(
        TriageReconciliationError, match="ungrounded-confirmed-continuation"
    ):
        reconcile_triage(
            TriageCandidate(topics=(candidate_topic,), dispositions=()),
            selected_records=(current,),
            topic_allocations=(allocation("a", "prior-topic", "current-assessment"),),
            prior_assessments=(prior,),
            **_inputs((current,)),
        )


def test_reconciliation_replay_and_boundary_errors_are_opaque() -> None:
    record = prepared("source-a")
    candidate = TriageCandidate(
        topics=(topic("a", (record.source,)),),
        dispositions=(),
    )
    kwargs = {
        "selected_records": (record,),
        "topic_allocations": (allocation("a", "stable-topic", "assessment-a"),),
        **_inputs((record,)),
    }
    first = reconcile_triage(candidate, **kwargs)
    second = reconcile_triage(candidate, **kwargs)
    if first != second:
        pytest.fail("explicit replay changed trusted topic identity decisions")

    secret = "PRIVATE-INVALID-PRIORITY-MUST-NOT-ECHO"
    invalid_topic = candidate.topics[0].model_copy(update={"priority": secret})
    invalid = candidate.model_copy(update={"topics": (invalid_topic,)})
    with pytest.raises(TriageReconciliationError) as caught:
        reconcile_triage(invalid, **kwargs)
    if secret in str(caught.value):
        pytest.fail("reconciliation error leaked bypassed candidate content")


def test_reused_prior_assessment_version_is_rejected() -> None:
    current = prepared("current")
    prior_source = ref("source", "prior")
    prior_evidence = evidence(prior_source)
    prior = PriorTopicAssessment(
        topic_ref=ref("topic", "stable-topic"),
        assessment_ref=ref("topic-assessment", "same-assessment"),
        source_refs=(prior_source,),
        evidence=(prior_evidence,),
    )
    continuation = TopicContinuation(
        prior_topic_ref=prior.topic_ref,
        prior_assessment_ref=prior.assessment_ref,
        status=RelationshipStatus.CONFIRMED,
        reason="Synthetic continuation",
        evidence=(
            evidence(current.source, "Please review the synthetic work."),
            prior_evidence,
        ),
    )
    candidate_topic = topic("a", (current.source,)).model_copy(
        update={"continuation": continuation}
    )
    with pytest.raises(
        TriageReconciliationError, match="reused-prior-assessment-version"
    ):
        reconcile_triage(
            TriageCandidate(topics=(candidate_topic,), dispositions=()),
            selected_records=(current,),
            topic_allocations=(allocation("a", "stable-topic", "same-assessment"),),
            prior_assessments=(prior,),
            **_inputs((current,)),
        )

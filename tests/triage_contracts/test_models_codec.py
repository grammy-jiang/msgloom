"""Structured triage and canonical codec regressions."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from msgloom.triage import (
    ActionOwner,
    Deadline,
    OwnerState,
    Priority,
    SourceDisposition,
    SourceDispositionKind,
    TopicAssessment,
    TriageAction,
    TriageData,
    TriageDataCodec,
)

from .helpers import evidence, ref


def _data() -> TriageData:
    source_a = ref("source", "source-a")
    source_b = ref("source", "source-b")
    topic_a = TopicAssessment(
        topic_ref=ref("topic", "topic-a"),
        assessment_ref=ref("topic-assessment", "assessment-a"),
        title="Display title A",
        source_refs=(source_a,),
        priority=Priority.CRITICAL,
        reason="Synthetic critical reason",
        actions=(
            TriageAction(
                text="Complete synthetic review",
                owner=ActionOwner(state=OwnerState.UNKNOWN),
                evidence=(evidence(source_a),),
            ),
        ),
        deadlines=(
            Deadline(
                original_wording="before the synthetic cutoff",
                interpreted_at=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
                timezone_basis="UTC from configured synthetic context",
                ambiguous=True,
                evidence=(evidence(source_a),),
            ),
        ),
    )
    topic_b = TopicAssessment(
        topic_ref=ref("topic", "topic-b"),
        assessment_ref=ref("topic-assessment", "assessment-b"),
        title="Display title B",
        source_refs=(source_b,),
        priority=Priority.NORMAL,
        reason="Synthetic normal reason",
    )
    return TriageData(topics=(topic_a, topic_b), dispositions=())


def test_owner_states_and_deadline_semantics_are_explicit() -> None:
    known = ActionOwner(state=OwnerState.KNOWN, value="Synthetic owner")
    unknown = ActionOwner(state=OwnerState.UNKNOWN)
    absent = ActionOwner(state=OwnerState.ABSENT)
    if known == unknown or unknown == absent:
        pytest.fail("owner known, unknown, and absent states collapsed")
    with pytest.raises(ValidationError):
        ActionOwner(state=OwnerState.UNKNOWN, value="invented")
    with pytest.raises(ValidationError):
        Deadline(
            original_wording="tomorrow",
            interpreted_at=datetime.fromisoformat("2026-09-30T09:00:00"),
            timezone_basis="unknown",
            ambiguous=True,
            evidence=(evidence(ref("source", "source-a")),),
        )


def test_structured_models_reject_coercion_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ActionOwner.model_validate(
            {"state": "known", "value": 123},
            strict=True,
        )
    with pytest.raises(ValidationError):
        SourceDisposition.model_validate(
            {
                "source_ref": {
                    "kind": "source",
                    "identity": "source-a",
                    "version": "1",
                },
                "kind": "no-reportable-content",
                "reason": "Synthetic reason",
                "extra": "forbidden",
            },
            strict=True,
        )


def test_codec_roundtrip_is_canonical_and_preserves_deadline_details() -> None:
    codec = TriageDataCodec()
    original = _data()
    payload = codec.encode(original)
    decoded = codec.decode(payload)
    if decoded != original:
        pytest.fail("canonical triage roundtrip changed semantic data")
    deadline = decoded.topics[0].deadlines[0]
    if deadline.original_wording != "before the synthetic cutoff":
        pytest.fail("original deadline wording was not preserved")
    if deadline.timezone_basis != "UTC from configured synthetic context":
        pytest.fail("deadline timezone basis was not preserved")
    if not deadline.ambiguous:
        pytest.fail("deadline ambiguity was not preserved")


def test_codec_revalidates_model_construct_and_model_copy_bypasses() -> None:
    codec = TriageDataCodec()
    valid = _data()
    constructed = TriageData.model_construct(
        schema_version="1",
        topics=({"not": "a topic"},),
        dispositions=(),
        relationships=(),
    )
    with pytest.raises(TypeError, match="triage@1 data failed validation"):
        codec.encode(constructed)
    invalid_topic = valid.topics[0].model_copy(
        update={"source_refs": ("not-a-version-ref",)}
    )
    copied = valid.model_copy(update={"topics": (invalid_topic,)})
    with pytest.raises(TypeError, match="triage@1 data failed validation"):
        codec.encode(copied)


def test_codec_errors_do_not_echo_source_values() -> None:
    secret = "SYNTHETIC-SOURCE-VALUE-MUST-NOT-LEAK"
    malformed = (
        '{"schema_version":"1","topics":[{"topic_ref":{"kind":"topic",'
        f'"identity":"{secret}","version":"1"}}],"dispositions":[]}}'
    ).encode()
    with pytest.raises(ValueError) as caught:
        TriageDataCodec().decode(malformed)
    if secret in str(caught.value):
        pytest.fail("codec validation error leaked a source value")


def test_low_value_is_a_real_priority_not_an_implicit_disposition() -> None:
    disposition = SourceDisposition(
        source_ref=ref("source", "source-a"),
        kind=SourceDispositionKind.NO_REPORTABLE_CONTENT,
        reason="Synthetic explicit disposition",
    )
    if disposition.kind.value == Priority.LOW_VALUE.value:
        pytest.fail("low-value priority collapsed into a source disposition")


def test_codec_is_compatible_with_semantic_data_registry_contract() -> None:
    from msgloom.persistence.semantic import SemanticDataRegistry

    registry = SemanticDataRegistry((TriageDataCodec(),))
    original = _data()
    encoded = registry.encode("triage-data:synthetic", "triage", "1", original)
    decoded = registry.decode(encoded.reference, encoded.payload)
    if decoded != original:
        pytest.fail("semantic registry roundtrip changed triage data")


def test_candidate_validator_returns_safe_error_without_source_echo() -> None:
    from msgloom.triage import (
        TriageCandidateValidationError,
        validate_triage_candidate,
    )

    secret = "SYNTHETIC-CANDIDATE-VALUE-MUST-NOT-LEAK"
    payload = (
        '{"schema_version":"1","topics":[{"allocation_key":"a",'
        f'"title":"{secret}","source_refs":[]}}],"dispositions":[]}}'
    )
    with pytest.raises(TriageCandidateValidationError) as caught:
        validate_triage_candidate(payload)
    if secret in str(caught.value):
        pytest.fail("candidate validation error leaked structured-output values")


def test_saved_semantic_models_reject_duplicate_source_coverage() -> None:
    source = ref("source", "source-a")
    with pytest.raises(ValidationError):
        TopicAssessment(
            topic_ref=ref("topic", "topic-a"),
            assessment_ref=ref("topic-assessment", "assessment-a"),
            title="Synthetic topic",
            source_refs=(source, source),
            priority=Priority.NORMAL,
            reason="Synthetic reason",
        )


def test_candidate_json_schema_is_closed_for_structured_output() -> None:
    from msgloom.triage import TriageCandidate

    schema = TriageCandidate.model_json_schema()
    if schema.get("additionalProperties") is not False:
        pytest.fail("candidate structured-output schema is not closed")
    if schema.get("type") != "object":
        pytest.fail("candidate structured-output schema is not an object")


def test_rule_evaluation_codec_binds_configuration_and_outcomes() -> None:
    from msgloom.triage import (
        PredicateKind,
        RuleEffect,
        RuleEffectKind,
        RulePredicate,
        TriageRule,
        TriageRuleConfig,
        TriageRuleEvaluationCodec,
        evaluate_rule_set,
    )

    from .helpers import prepared

    record = prepared("source-a")
    rule = TriageRule(
        rule_ref=ref("triage-rule", "critical"),
        predicates=(
            RulePredicate(kind=PredicateKind.SUBJECT_CONTAINS, text_value="Synthetic"),
        ),
        effects=(
            RuleEffect(
                kind=RuleEffectKind.REQUIRED_PRIORITY,
                priority=Priority.CRITICAL,
            ),
        ),
    )
    evaluation = evaluate_rule_set(
        (record,),
        TriageRuleConfig(version=ref("rule-set", "v1"), rules=(rule,)),
    )
    codec = TriageRuleEvaluationCodec()
    if codec.decode(codec.encode(evaluation)) != evaluation:
        pytest.fail("triage_rules@1 roundtrip changed deterministic evaluation")
    invalid = evaluation.model_copy(
        update={
            "outcomes": (
                evaluation.outcomes[0].model_copy(
                    update={"required_priority": Priority.NORMAL}
                ),
            )
        }
    )
    with pytest.raises(TypeError, match="triage_rules@1 data failed validation"):
        codec.encode(invalid)


def test_saved_confirmed_relationship_requires_contained_current_and_prior_evidence() -> (
    None
):
    from msgloom.triage import RelationshipStatus, TopicRelationship

    valid = _data()
    topic = valid.topics[0]
    invented_prior = ref("source", "prior")
    relationship = TopicRelationship(
        current_topic_ref=topic.topic_ref,
        current_assessment_ref=topic.assessment_ref,
        prior_topic_ref=topic.topic_ref,
        prior_assessment_ref=ref("topic-assessment", "prior"),
        status=RelationshipStatus.CONFIRMED,
        reason="Synthetic continuity",
        evidence=(evidence(invented_prior),),
    )
    with pytest.raises(ValidationError):
        TriageData(
            topics=valid.topics,
            dispositions=(),
            relationships=(relationship,),
        )


def test_confirmed_relationship_rejects_reused_assessment_version() -> None:
    from msgloom.triage import RelationshipStatus, TopicRelationship

    topic = _data().topics[0]
    with pytest.raises(ValidationError):
        TopicRelationship(
            current_topic_ref=topic.topic_ref,
            current_assessment_ref=topic.assessment_ref,
            prior_topic_ref=topic.topic_ref,
            prior_assessment_ref=topic.assessment_ref,
            status=RelationshipStatus.CONFIRMED,
            reason="Synthetic invalid continuity",
            evidence=(evidence(topic.source_refs[0]),),
        )

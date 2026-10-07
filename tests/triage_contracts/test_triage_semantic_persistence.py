"""Verify exact saved triage dependencies and same-source prompt replay."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ExternalEffectState,
    ResultRef,
    TerminalStatus,
)
from msgloom.persistence import Phase1Persistence
from msgloom.preparation.filtering import (
    AddressNormalization,
    FilterConfig,
    apply_filters,
)
from msgloom.triage import (
    Development,
    PriorTopicAssessment,
    RelationshipStatus,
    TopicContinuation,
    TriageCandidate,
    TriageData,
    TriageRuleConfig,
    evaluate_rule_set,
    reconcile_triage,
)
from tests.prepared_contract_fixtures import phase1_url, prepared_result
from tests.triage_contracts.helpers import allocation, evidence, prepared, ref, topic


def test_saved_rules_and_same_source_reassessment_retain_topic_after_restart(
    tmp_path: Path,
) -> None:
    """Prompt replay creates a new assessment and preserves the saved prior."""
    record = prepared("same-saved-source")
    if record.body is None:
        pytest.fail("synthetic source body is missing")
    supporting = evidence(record.source, record.body)
    candidate_topic = topic("a", (record.source,)).model_copy(
        update={
            "developments": (
                Development(text="Synthetic development", evidence=(supporting,)),
            )
        }
    )
    filters = FilterConfig(
        reference=ref("filter-config", "synthetic"),
        address_normalization=AddressNormalization.EXACT,
        rules=(),
    )
    filtered = apply_filters(record, filters)
    evaluated = evaluate_rule_set(
        (record,), TriageRuleConfig(version=ref("rule-set", "synthetic"), rules=())
    )
    original = reconcile_triage(
        TriageCandidate(topics=(candidate_topic,), dispositions=()),
        topic_allocations=(allocation("a", "stable-topic", "assessment-old"),),
        selected_records=(record,),
        filter_config=filters,
        filter_results=(filtered,),
        rule_evaluation=evaluated,
    )

    async def exercise() -> None:
        url = phase1_url(tmp_path / "phase1.sqlite3")
        store = await Phase1Persistence.open(url)
        dependencies: tuple[ResultRef, ...] = ()
        try:
            for kind, value in (
                ("prepared", record),
                ("filter_result", filtered),
                ("triage_rules", evaluated),
                ("triage", original),
            ):
                data_ref = store.semantic_reference(f"data-{kind}", kind, "1", value)
                result = replace(
                    prepared_result(data_ref, result_id=f"result-{kind}"),
                    kind=kind,
                    input_refs=dependencies,
                    source_versions=(record.source,),
                    rule_version=evaluated.config.version.version,
                    prompt_version="synthetic-prompt-v1" if kind == "triage" else None,
                )
                await store.append_result_with_data(result, value)
                dependencies = (ResultRef(result.result_id, kind, "1"),)
        finally:
            await store.close()

        reopened = await Phase1Persistence.open(url)
        try:
            old_result = await reopened.get_result("result-triage")
            if old_result is None or old_result.semantic_data_ref is None:
                pytest.fail("saved prior triage data is missing")
            saved = await reopened.load_semantic_data(old_result.semantic_data_ref)
            if not isinstance(saved, TriageData) or saved != original:
                pytest.fail("prior triage did not retain its typed exact value")
            old_topic = saved.topics[0]
            prior = PriorTopicAssessment(
                topic_ref=old_topic.topic_ref,
                assessment_ref=old_topic.assessment_ref,
                source_refs=old_topic.source_refs,
                evidence=old_topic.developments[0].evidence,
            )
            updated_topic = candidate_topic.model_copy(
                update={
                    "continuation": TopicContinuation(
                        prior_topic_ref=prior.topic_ref,
                        prior_assessment_ref=prior.assessment_ref,
                        status=RelationshipStatus.CONFIRMED,
                        reason="Explicit reassessment of the same saved source.",
                        evidence=(supporting,),
                    )
                }
            )
            updated = reconcile_triage(
                TriageCandidate(topics=(updated_topic,), dispositions=()),
                topic_allocations=(allocation("a", "stable-topic", "assessment-new"),),
                prior_assessments=(prior,),
                selected_records=(record,),
                filter_config=filters,
                filter_results=(filtered,),
                rule_evaluation=evaluated,
            )
            data_ref = reopened.semantic_reference(
                "data-replay", "triage", "1", updated
            )
            replay = replace(
                old_result,
                result_id="result-replay",
                execution=ExecutionIdentity("execution-replay"),
                attempt=AttemptIdentity("attempt-replay"),
                input_refs=dependencies,
                topic_versions=(updated.topics[0].assessment_ref,),
                prompt_version="synthetic-prompt-v2",
                semantic_data_ref=data_ref,
            )
            await reopened.append_result_with_data(replay, updated)
            if updated.topics[0].topic_ref != old_topic.topic_ref:
                pytest.fail("supported same-source replay changed topic identity")
            if updated.topics[0].assessment_ref == old_topic.assessment_ref:
                pytest.fail("prompt replay reused the prior assessment version")
            if await reopened.get_result("result-triage") != old_result:
                pytest.fail("prompt replay changed the saved prior result")
            token = await reopened.acquire_claim(
                "report:replayed-triage",
                ClaimKind.REPORT_BUILD,
                ExecutionIdentity("execution-report"),
                AttemptIdentity("attempt-report"),
                required_inputs=(ResultRef("result-replay", "triage", "1"),),
            )
            await reopened.finish_claim(
                token, TerminalStatus.COMPLETE, ExternalEffectState.NONE
            )
        finally:
            await reopened.close()

    asyncio.run(exercise())

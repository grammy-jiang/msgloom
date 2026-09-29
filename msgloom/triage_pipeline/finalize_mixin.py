"""Multipart reconciliation and terminal publication helpers for A3."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from msgloom.contracts import (
    AttemptIdentity,
    ClaimToken,
    ExternalEffectState,
    Failure,
    Limitation,
    OperationOutcome,
    OperationRequest,
    PhaseCapability,
    ResultRef,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence, StaleClaimError
from msgloom.triage import (
    SourceDisposition,
    SourceDispositionKind,
    TopicCandidate,
    TriageCandidate,
)
from msgloom.triage_input import TriageInputSnapshot
from msgloom.working_context import WorkingContextSnapshot, snapshot_ref

from .common import (
    RUN_STATE,
    cpu_bound,
    drain,
    ensure_acceptance_time,
    record_result,
    result_ref,
    stable_id,
)
from .models import TriageProducerConfig


class _TriageFinalizeMixin:
    """Combine only trusted allocation identities and publish final state."""

    _persistence: Phase1Persistence
    _config: TriageProducerConfig
    _runner: Any

    def _combine_candidates(
        self, candidates: list[TriageCandidate], snapshot: TriageInputSnapshot
    ) -> TriageCandidate:
        topics: dict[str, TopicCandidate] = {}
        dispositions: dict[VersionRef, SourceDisposition] = {}
        for candidate in candidates:
            for topic in candidate.topics:
                existing = topics.get(topic.allocation_key)
                if existing is None:
                    topics[topic.allocation_key] = topic
                    continue
                stable = (
                    existing.title,
                    existing.priority,
                    existing.reason,
                    existing.continuation,
                )
                incoming = (
                    topic.title,
                    topic.priority,
                    topic.reason,
                    topic.continuation,
                )
                if stable != incoming:
                    raise ValueError("multipart topic semantics conflict")
                topics[topic.allocation_key] = existing.model_copy(
                    update={
                        "source_refs": self._unique(
                            (*existing.source_refs, *topic.source_refs)
                        ),
                        "rule_matches": self._unique(
                            (*existing.rule_matches, *topic.rule_matches)
                        ),
                        "developments": self._unique(
                            (*existing.developments, *topic.developments)
                        ),
                        "actions": self._unique((*existing.actions, *topic.actions)),
                        "deadlines": self._unique(
                            (*existing.deadlines, *topic.deadlines)
                        ),
                        "risks": self._unique((*existing.risks, *topic.risks)),
                        "limitations": self._unique(
                            (*existing.limitations, *topic.limitations)
                        ),
                    }
                )
            for item in candidate.dispositions:
                existing = dispositions.get(item.source_ref)
                if existing is not None and existing != item:
                    raise ValueError("multipart source disposition conflicts")
                dispositions[item.source_ref] = item

        for held in snapshot.held:
            kind = (
                SourceDispositionKind.REVIEW_REQUIRED
                if any("conflict" in reason.value for reason in held.reasons)
                else SourceDispositionKind.EXCLUDED
            )
            deterministic = SourceDisposition(
                source_ref=held.source_ref,
                kind=kind,
                reason="Deterministic filtering or triage rules held this source",
            )
            existing = dispositions.get(held.source_ref)
            if existing is not None and existing != deterministic:
                raise ValueError("AI output conflicts with deterministic disposition")
            dispositions[held.source_ref] = deterministic

        return TriageCandidate(
            topics=tuple(topics[key] for key in sorted(topics)),
            dispositions=tuple(
                dispositions[key]
                for key in sorted(
                    dispositions,
                    key=lambda ref: (ref.kind, ref.identity, ref.version),
                )
            ),
        )

    @staticmethod
    def _unique(values):
        result = []
        for value in values:
            if value not in result:
                result.append(value)
        return tuple(result)

    async def _save_triage(
        self,
        request,
        attempt,
        claim,
        data,
        upstream,
        rule_ref,
        context_ref,
        input_ref,
        evidence_refs,
        context,
    ) -> ResultRef:
        result_id = stable_id(
            "triage",
            request.execution.value,
            self._config.versions.prompt.version,
            self._config.versions.model.version,
            input_ref.result_id,
            self._config.semantic_fingerprint(),
        )
        semantic = await cpu_bound(
            self._persistence.semantic_reference,
            f"{result_id}:data",
            "triage",
            "1",
            data,
        )
        lineage = (
            *(result_ref(item) for item in upstream),
            rule_ref,
            context_ref,
            input_ref,
            *evidence_refs,
        )
        source_versions = tuple(
            sorted(
                {source for topic in data.topics for source in topic.source_refs}
                | {item.source_ref for item in data.dispositions},
                key=lambda ref: (ref.kind, ref.identity, ref.version),
            )
        )
        result = self._stage(
            request,
            attempt,
            result_id,
            "triage",
            lineage,
            source_versions,
            semantic=semantic,
            working_context=snapshot_ref(context),
            topic_versions=tuple(topic.assessment_ref for topic in data.topics),
        )
        ensure_acceptance_time()
        await self._persistence.append_result_with_data(result, data, claim=claim)
        return record_result(result_ref(result))

    def _stage(
        self,
        request,
        attempt,
        result_id,
        kind,
        input_refs,
        source_versions,
        *,
        semantic,
        working_context=None,
        topic_versions=(),
        acceptable=True,
        status=TerminalStatus.COMPLETE,
    ) -> StageResult:
        run_state = RUN_STATE.get()
        prepared_versions = () if run_state is None else run_state.prepared_versions
        return StageResult(
            result_id=result_id,
            kind=kind,
            schema_version="1",
            execution=request.execution,
            attempt=attempt,
            input_refs=tuple(input_refs),
            source_versions=tuple(source_versions),
            prepared_versions=prepared_versions,
            topic_versions=tuple(topic_versions),
            configuration_version=self._config.configuration_version,
            code_version=self._config.code_version,
            status=status,
            acceptable=acceptable,
            rule_version=self._config.rule_config.version.version,
            prompt_version=self._config.versions.prompt.version,
            model_identifier=self._config.trusted_policy.models[
                self._config.versions.model
            ],
            working_context_version=working_context,
            semantic_data_ref=semantic,
        )

    def _part_attempt(self, request: OperationRequest, part_id: str) -> AttemptIdentity:
        return AttemptIdentity(
            stable_id(
                "ai-attempt",
                request.execution.value,
                part_id,
                self._config.versions.prompt.version,
                self._config.versions.model.version,
                self._config.versions.output_schema.version,
                self._config.configuration_version,
                self._config.semantic_fingerprint(),
            )
        )

    @staticmethod
    def _context_text(context: WorkingContextSnapshot) -> str:
        payload = {
            "configuration_ref": {
                "kind": context.configuration_ref.kind,
                "identity": context.configuration_ref.identity,
                "version": context.configuration_ref.version,
            },
            "capture_time": context.capture_time.isoformat(),
            "timezone": context.timezone,
            "snapshot_sha256": context.snapshot_sha256,
            "files": [
                {
                    "selection_id": item.selection_id,
                    "state": item.state.value,
                    "text": item.text,
                    "modified_at": (
                        None
                        if item.modified_at is None
                        else item.modified_at.isoformat()
                    ),
                    "limitations": [
                        {"code": value.code, "detail": value.detail}
                        for value in item.limitations
                    ],
                }
                for item in context.files
            ],
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    async def _cancel_claim(self, claim: ClaimToken) -> None:
        try:
            await drain(
                self._persistence.finish_claim(
                    claim, TerminalStatus.CANCELLED, ExternalEffectState.NONE
                )
            )
        except (StaleClaimError, asyncio.CancelledError):
            pass

    @staticmethod
    def _stale(
        request: OperationRequest, refs: tuple[ResultRef, ...] = ()
    ) -> OperationOutcome:
        return OperationOutcome(
            execution=request.execution,
            capability=PhaseCapability.TRIAGE,
            status=TerminalStatus.FAILED,
            result_refs=refs,
            failures=(Failure("stale_triage_claim", "triage ownership expired"),),
        )

    @staticmethod
    def _outcome(
        request: OperationRequest,
        status: TerminalStatus,
        *,
        refs: tuple[ResultRef, ...] = (),
        failure: Failure | None = None,
        limitation: Limitation | None = None,
    ) -> OperationOutcome:
        return OperationOutcome(
            execution=request.execution,
            capability=PhaseCapability.TRIAGE,
            status=status,
            result_refs=refs,
            failures=() if failure is None else (failure,),
            limitations=() if limitation is None else (limitation,),
            external_effect=ExternalEffectState.NONE,
        )

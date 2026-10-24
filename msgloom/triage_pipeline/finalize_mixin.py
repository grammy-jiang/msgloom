"""
Multipart reconciliation and terminal publication helpers for A3.

Terminal status (C0-17g): :meth:`_TriageFinalizeMixin._terminal_state`
decides the status of a finished run from its input snapshot. A
``triage_input@1`` snapshot keeps the unchanged rule: ``COMPLETE`` with
exactly the limitations the caller computed. A ``triage_input@2`` snapshot
is verified first. A missing, forged or invalid digest raises
:exc:`~msgloom.triage_pipeline.limitations.V2ProvenanceError` and nothing
is saved. If the verified snapshot is incomplete or holds a source, the
status is ``INCOMPLETE`` and the v2 limitations (with their original
provenance) are appended. Only a complete snapshot without a held source
gets ``COMPLETE``. :meth:`_TriageFinalizeMixin._save_triage_v2` applies
that decision and writes one new result. It never rewrites a saved result.
"""

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
from msgloom.triage_input.models_v2 import TriageInputSnapshot as V2Snapshot
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
from .limitations import (
    MAX_PROPAGATED_LIMITATIONS,
    KnownLimitationError,
    V2ProvenanceError,
    v2_input_limitations,
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
        limitations=(),
        status=TerminalStatus.COMPLETE,
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
            limitations=limitations,
            status=status,
        )
        ensure_acceptance_time()
        await self._persistence.append_result_with_data(result, data, claim=claim)
        return record_result(result_ref(result))

    @staticmethod
    def _terminal_state(
        snapshot: object,
        limitations: tuple[Limitation, ...] = (),
        expected_snapshot_sha256: str | None = None,
    ) -> tuple[TerminalStatus, tuple[Limitation, ...]]:
        """Return the terminal status and limitations for ``snapshot``.

        A v1 snapshot returns ``COMPLETE`` and ``limitations`` unchanged.
        Any other value must be a verified v2 snapshot, else
        :exc:`V2ProvenanceError` is raised.
        """
        if isinstance(snapshot, TriageInputSnapshot):
            return TerminalStatus.COMPLETE, limitations
        if not isinstance(snapshot, V2Snapshot):
            raise V2ProvenanceError("v2-provenance-missing")
        held = v2_input_limitations(snapshot, expected_snapshot_sha256)
        if not held:
            return TerminalStatus.COMPLETE, limitations
        merged = (*limitations, *(item for item in held if item not in limitations))
        if len(merged) > MAX_PROPAGATED_LIMITATIONS:
            raise KnownLimitationError("v2-limitation-overflow")
        return TerminalStatus.INCOMPLETE, merged

    async def _save_triage_v2(
        self,
        snapshot: object,
        request: OperationRequest,
        *args: Any,
        limitations: tuple[Limitation, ...] = (),
        expected_snapshot_sha256: str | None = None,
    ) -> OperationOutcome:
        """Save one triage result with a v2-aware terminal status.

        ``args`` are the arguments of :meth:`_save_triage` after
        ``request``. The provenance check runs before any write, so a
        forged snapshot saves nothing. The outcome status equals the saved
        result status.
        """
        status, merged = self._terminal_state(
            snapshot, limitations, expected_snapshot_sha256
        )
        final_ref = await self._save_triage(
            request, *args, limitations=merged, status=status
        )
        return self._outcome(request, status, refs=(final_ref,), limitations=merged)

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
        limitations=(),
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
            limitations=tuple(limitations),
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
        limitations: tuple[Limitation, ...] = (),
    ) -> OperationOutcome:
        return OperationOutcome(
            execution=request.execution,
            capability=PhaseCapability.TRIAGE,
            status=status,
            result_refs=refs,
            failures=() if failure is None else (failure,),
            limitations=(
                limitations if limitation is None else (*limitations, limitation)
            ),
            external_effect=ExternalEffectState.NONE,
        )

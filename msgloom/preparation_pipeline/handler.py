"""Finite awaited A2 preparation OperationHandler."""

from __future__ import annotations

import asyncio
import hashlib
import json

from msgloom.contracts import (
    ClaimKind,
    Failure,
    Limitation,
    OperationOutcome,
    OperationRequest,
    PhaseCapability,
    ResultRef,
    TerminalStatus,
)
from msgloom.persistence import (
    ClaimUnavailableError,
    Phase1Persistence,
    Phase1PersistenceError,
    StaleClaimError,
)
from msgloom.sources import (
    CollectedSelection,
    CollectedSelectionCodec,
    CollectedSourceReader,
)

from ._state import CapturedSelection, RunState
from .models import PreparationMode, PreparationPlan, SelectionPlan, revalidate_plan
from .record_steps import RecordSteps
from .stage_steps import StageSteps, _finish_uninterrupted


class PreparationHandler(RecordSteps, StageSteps):
    """Produce captured, parsed, filtered, and grouped A2 results."""

    def __init__(
        self,
        persistence: Phase1Persistence,
        reader: CollectedSourceReader,
        plan: PreparationPlan,
    ) -> None:
        self._persistence = persistence
        self._reader = reader
        self._plan = plan

    async def run(self, request: OperationRequest) -> OperationOutcome:
        """Run one already-admitted PREPARE request under a durable claim."""
        try:
            self._plan = revalidate_plan(self._plan)
        except (TypeError, ValueError):
            return self._outcome(
                request,
                TerminalStatus.BLOCKED,
                limitations=(
                    Limitation(
                        "invalid-preparation-plan",
                        "Trusted preparation configuration failed closed validation.",
                    ),
                ),
            )
        invalid = self._validate_request(request)
        if invalid is not None:
            return self._outcome(
                request, TerminalStatus.BLOCKED, limitations=(invalid,)
            )

        replay_error = await self._preflight_replay()
        if replay_error is not None:
            return self._outcome(
                request, TerminalStatus.BLOCKED, limitations=(replay_error,)
            )
        required = tuple(
            item.replay_result
            for item in self._plan.selections
            if item.replay_result is not None
        )
        try:
            token = await self._persistence.acquire_claim(
                self._claim_key(),
                ClaimKind.PREPARE,
                request.execution,
                self._plan.attempt,
                required_inputs=required,
                lease_seconds=self._plan.claim_lease_seconds,
            )
        except ClaimUnavailableError:
            return self._outcome(
                request,
                TerminalStatus.BLOCKED,
                limitations=(
                    Limitation(
                        "duplicate-preparation-claim",
                        "Equivalent preparation work already has a durable owner.",
                    ),
                ),
            )
        except Phase1PersistenceError:
            return self._outcome(
                request,
                TerminalStatus.FAILED,
                failures=(
                    Failure(
                        "preparation-claim-failed",
                        "Preparation claim admission failed safely.",
                    ),
                ),
            )

        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._plan.execution_timeout_seconds
        state = RunState([], [], token)
        terminal = TerminalStatus.FAILED
        try:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise TimeoutError
            async with asyncio.timeout(remaining):
                captured = await self._capture_all(request, state)
                prepared, prepared_refs, prepared_versions = await self._prepare_all(
                    request, captured, state
                )
                filter_results, filter_refs = await self._filter_all(
                    request,
                    prepared,
                    prepared_refs,
                    prepared_versions,
                    state,
                )
                await self._group_all(
                    request,
                    prepared,
                    prepared_refs,
                    prepared_versions,
                    filter_results,
                    filter_refs,
                    state,
                )
                terminal = (
                    TerminalStatus.INCOMPLETE
                    if state.limitations
                    else TerminalStatus.COMPLETE
                )
        except asyncio.CancelledError:
            await _finish_uninterrupted(
                self._persistence,
                token,
                TerminalStatus.CANCELLED,
                preserve_cancellation=True,
            )
            raise
        except TimeoutError:
            terminal = TerminalStatus.INCOMPLETE
            state.limitations.append(
                Limitation(
                    "preparation-timeout",
                    "Preparation exceeded its finite execution budget.",
                )
            )
        except StaleClaimError:
            terminal = TerminalStatus.FAILED
            state.limitations.append(
                Limitation(
                    "preparation-claim-lost",
                    "Preparation ownership expired or was replaced before publication.",
                )
            )
        except Exception as error:  # noqa: BLE001
            terminal = TerminalStatus.FAILED
            await _finish_uninterrupted(
                self._persistence, token, terminal, suppress_stale=True
            )
            return self._outcome(
                request,
                terminal,
                refs=tuple(state.refs),
                limitations=tuple(state.limitations),
                failures=(
                    Failure(
                        "preparation-failed",
                        f"Preparation failed with {type(error).__name__}.",
                    ),
                ),
            )

        owned = await _finish_uninterrupted(
            self._persistence, token, terminal, suppress_stale=True
        )
        if not owned:
            terminal = TerminalStatus.FAILED
            if not any(
                item.code == "preparation-claim-lost" for item in state.limitations
            ):
                state.limitations.append(
                    Limitation(
                        "preparation-claim-lost",
                        "Preparation ownership expired or was replaced before completion.",
                    )
                )
        return self._outcome(
            request,
            terminal,
            refs=tuple(state.refs),
            limitations=tuple(state.limitations),
        )

    async def _preflight_replay(self) -> Limitation | None:
        """Bound replay metadata before semantic payload or claim validation loads."""
        if self._plan.mode is not PreparationMode.REPLAY:
            return None
        total = 0
        for item in self._plan.selections:
            if item.replay_result is None:
                return Limitation(
                    "invalid-replay-plan",
                    "Replay selection is missing its exact durable result reference.",
                )
            result = await self._persistence.get_result(item.replay_result.result_id)
            if (
                result is None
                or result.kind != item.replay_result.kind
                or result.schema_version != item.replay_result.schema_version
                or not result.acceptable
                or result.semantic_data_ref is None
            ):
                return Limitation(
                    "invalid-replay-result",
                    "Replay selection does not reference acceptable durable semantic data.",
                )
            total += result.semantic_data_ref.byte_count
            if total > self._plan.max_total_selected_bytes:
                return Limitation(
                    "selection-budget-exceeded",
                    "Replay selection metadata exceeds the configured aggregate budget.",
                )
        return None

    def _validate_request(self, request: OperationRequest) -> Limitation | None:
        if request.capability is not PhaseCapability.PREPARE:
            return Limitation(
                "wrong-capability",
                "Preparation handler accepts only the PREPARE capability.",
            )
        expected = tuple(item.source for item in self._plan.selections)
        if request.target_inputs != expected:
            return Limitation(
                "target-mismatch",
                "Request targets do not match the trusted finite preparation plan.",
            )
        keys = tuple(key for key, _value in request.parameters)
        if len(keys) != len(set(keys)):
            return Limitation(
                "duplicate-parameter",
                "Preparation request contains duplicate parameter names.",
            )
        if request.parameters:
            return Limitation(
                "unsupported-parameter",
                "Preparation behavior is fixed by trusted configuration, not parameters.",
            )
        return None

    def _claim_key(self) -> str:
        work = self._plan.model_dump(mode="json", round_trip=True, warnings="error")
        work.pop("attempt")
        payload = json.dumps(
            work,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return "prepare:" + hashlib.sha256(payload).hexdigest()

    async def _capture_all(
        self,
        request: OperationRequest,
        state: RunState,
    ) -> tuple[CapturedSelection, ...]:
        captured: list[tuple[SelectionPlan, CollectedSelection, ResultRef | None]] = []
        for item in self._plan.selections:
            if self._plan.mode is PreparationMode.LIVE:
                selection = await self._reader.read_selection(item.source)
                encoded = await self._run_sync_owned(
                    CollectedSelectionCodec().encode, selection
                )
                payload_size = len(encoded) + self._selection_evidence_bytes(selection)
                result_ref = None
            else:
                if item.replay_result is None or item.replay_selection is None:
                    raise RuntimeError("validated replay plan lost exact references")
                result = await self._persistence.get_result(
                    item.replay_result.result_id
                )
                if (
                    result is None
                    or result.kind != item.replay_result.kind
                    or result.schema_version != item.replay_result.schema_version
                    or not result.acceptable
                    or result.semantic_data_ref is None
                ):
                    raise RuntimeError("replay selection result is not acceptable")
                value = await self._persistence.load_semantic_data(
                    result.semantic_data_ref
                )
                if not isinstance(value, CollectedSelection):
                    raise RuntimeError("replay semantic data has the wrong type")
                selection = value
                if (
                    selection.source != item.source
                    or selection.selection != item.replay_selection
                ):
                    raise RuntimeError("replay selection lineage does not match plan")
                payload_size = (
                    result.semantic_data_ref.byte_count
                    + self._selection_evidence_bytes(selection)
                )
                result_ref = item.replay_result
            state.selected_bytes += payload_size
            if state.selected_bytes > self._plan.max_total_selected_bytes:
                raise ValueError("aggregate selection exceeds configured bound")
            captured.append((item, selection, result_ref))

        values: list[CapturedSelection] = []
        for ordinal, (item, selection, result_ref) in enumerate(captured):
            if result_ref is None:
                result_ref = await self._save_value(
                    request,
                    state,
                    "collected_selection",
                    "1",
                    selection,
                    source_versions=(selection.source,),
                    input_refs=(),
                    tag=f"selection:{ordinal}:{selection.selection.version}",
                )
            values.append(CapturedSelection(item, selection, result_ref))
        return tuple(values)

    @staticmethod
    def _selection_evidence_bytes(selection: CollectedSelection) -> int:
        """Count unique declared saved evidence before any parser read."""
        record = selection.record
        references = [record.source_bytes]
        if record.body is not None:
            references.append(record.body.saved_bytes)
        references.extend(item.saved_bytes for item in record.alternate_bodies)
        references.extend(item.saved_bytes for item in record.attachments)
        unique = {
            (item.reference, item.sha256, item.byte_count): item.byte_count
            for item in references
            if item is not None
        }
        return sum(unique.values())

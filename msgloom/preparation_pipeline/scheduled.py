"""Finite scheduled intake and exact replay under existing PREPARE authority."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import TYPE_CHECKING

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExternalEffectState,
    Limitation,
    OperationOutcome,
    OperationRequest,
    ResultRef,
    TerminalStatus,
)
from msgloom.persistence import Phase1Persistence, StaleClaimError
from msgloom.sources import CollectedSelection, SavedSourceReaderConfig
from msgloom.sources.release_reader import ReleaseSourceReader

from .handler import PreparationHandler
from .intake import PreparationIntakeService
from .intake_models import IntakeScope, PreparationIntakeWorkset, workset_claim_key
from .models import PreparationMode, SelectionPlan

if TYPE_CHECKING:
    from msgloom.configuration.composition import PreparationOperationData


class ScheduledPreparationHandler:
    """
    Process targets sequentially with bounded work and awaited cleanup.

    Caller owns persistence. This handler owns its source reader. Existing
    pending work is considered before intake. Each pending failure consumes one
    budget unit; new intake still advances independently. Transition work stays
    pending because the reviewed completion API has no transition output proof.
    """

    def __init__(
        self,
        persistence: Phase1Persistence,
        source: SavedSourceReaderConfig,
        operation: PreparationOperationData,
        attempt: AttemptIdentity,
    ) -> None:
        self._persistence = persistence
        self._source = source
        self._operation = operation
        self._attempt = attempt

    async def run(self, request: OperationRequest) -> OperationOutcome:
        """Return one finite aggregate without creating an event loop."""
        reader = ReleaseSourceReader(self._source)
        outputs: list[ResultRef] = []
        pending = False
        try:
            targets = sorted(
                self._operation.intake_targets,
                key=lambda t: (t.source_id, t.stream, t.consumer_id),
            )
            if not targets:
                return OperationOutcome(
                    request.execution, request.capability, TerminalStatus.COMPLETE
                )
            catalog = await reader.catalog.catalog_identity()
            for target in targets:
                scope = IntakeScope(
                    catalog=catalog,
                    source_id=target.source_id,
                    stream=target.stream,
                    consumer_id=target.consumer_id,
                )
                try:
                    states = await self._persistence.list_preparation_intake_worksets(
                        scope,
                        limit=target.max_pending_worksets,
                    )
                    for state in states:
                        refs, accepted = await self._process(
                            state.workset,
                            reader,
                            request,
                        )
                        outputs.extend(refs)
                        pending |= not accepted
                    saved = await PreparationIntakeService(
                        self._persistence,
                        reader,
                    ).run(
                        scope,
                        execution=request.execution,
                        attempt=self._attempt,
                        configuration_version=self._operation.configuration_version,
                        code_version=self._operation.code_version,
                        limit=target.max_entries,
                        lease_seconds=self._operation.claim_lease_seconds,
                    )
                    if saved is not None:
                        if len(states) < target.max_pending_worksets:
                            refs, accepted = await self._process(
                                ResultRef(
                                    saved.result_id, saved.kind, saved.schema_version
                                ),
                                reader,
                                request,
                            )
                            outputs.extend(refs)
                            pending |= not accepted
                        else:
                            pending = True
                except asyncio.CancelledError:
                    raise
                except Exception:  # noqa: BLE001
                    # A failed target cannot fabricate progress for another.
                    # The Application outcome exposes a fixed safe limitation.
                    pending = True
        finally:
            await reader.close()
        return OperationOutcome(
            request.execution,
            request.capability,
            TerminalStatus.INCOMPLETE if pending else TerminalStatus.COMPLETE,
            result_refs=tuple(dict.fromkeys(outputs)),
            limitations=(
                Limitation(
                    "scheduled-work-pending", "Some scheduled work remains pending."
                ),
            )
            if pending
            else (),
        )

    async def _process(self, reference, reader, request):
        """Fence exact replay outputs with the separate workset claim."""
        saved = await self._persistence.get_result(reference.result_id)
        if saved is None or saved.semantic_data_ref is None:
            return (), False
        workset = await self._persistence.load_semantic_data(saved.semantic_data_ref)
        if not isinstance(workset, PreparationIntakeWorkset) or workset.transitions:
            return (), False
        claim = await self._persistence.acquire_claim(
            workset_claim_key(reference.result_id),
            ClaimKind.PREPARE,
            request.execution,
            self._attempt,
            required_inputs=(reference,),
            lease_seconds=self._operation.claim_lease_seconds,
        )
        status = TerminalStatus.FAILED
        try:
            plans = []
            for ref in workset.selection_refs:
                selected = await self._persistence.get_result(ref.result_id)
                if selected is None or selected.semantic_data_ref is None:
                    return (), False
                value = await self._persistence.load_semantic_data(
                    selected.semantic_data_ref,
                )
                if not isinstance(value, CollectedSelection):
                    return (), False
                plans.append(
                    SelectionPlan(
                        source=value.source,
                        replay_result=ref,
                        replay_selection=value.selection,
                    )
                )
            outputs = ()
            status = TerminalStatus.COMPLETE
            if plans:
                plan = self._operation.plan(
                    mode=PreparationMode.REPLAY,
                    attempt=self._attempt,
                    selections=tuple(plans),
                )
                outcome = await PreparationHandler(
                    self._persistence,
                    reader,
                    plan,
                ).run(replace(request, target_inputs=tuple(p.source for p in plans)))
                status, outputs = outcome.status, outcome.result_refs
            if status not in {TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE}:
                return outputs, False
            await self._persistence.finalize_preparation_intake_workset(
                reference.result_id,
                status,
                outputs,
                claim=claim,
            )
            return outputs, True
        except asyncio.CancelledError:
            status = TerminalStatus.CANCELLED
            raise
        finally:
            try:
                await self._persistence.finish_claim(
                    claim,
                    status,
                    ExternalEffectState.NONE,
                )
            except StaleClaimError:
                pass

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
    budget unit; new intake still advances independently. Each attempt reserves
    one durable discovery turn, so failures cannot monopolize later invocations.
    Transition work stays pending because the reviewed completion API has no
    transition output proof.
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
        incomplete = False
        budget = self._operation.execution_timeout_seconds
        try:
            targets = sorted(
                self._operation.intake_targets,
                key=lambda t: (t.source_id, t.stream, t.consumer_id),
            )
            if not targets:
                return OperationOutcome(
                    request.execution, request.capability, TerminalStatus.COMPLETE
                )
            async with asyncio.timeout(budget):
                catalog = await reader.catalog.catalog_identity()
            for target in targets:
                scope = IntakeScope(
                    catalog=catalog,
                    source_id=target.source_id,
                    stream=target.stream,
                    consumer_id=target.consumer_id,
                )
                try:
                    attempted = 0
                    for _ in range(target.max_pending_worksets):
                        async with asyncio.timeout(budget):
                            states = await self._persistence.select_preparation_intake_worksets(
                                scope, limit=1
                            )
                        if not states:
                            break
                        attempted += 1
                        refs, accepted, status = await self._bounded_process(
                            states[0].workset,
                            reader,
                            request,
                        )
                        outputs.extend(refs)
                        pending |= not accepted
                        incomplete |= status is TerminalStatus.INCOMPLETE
                    # Materialization receives its own finite budget, shorter
                    # than the intake claim lease. Cancellation drains accepted
                    # persistence operations before leaving this context.
                    async with asyncio.timeout(budget):
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
                    if saved is not None and attempted < target.max_pending_worksets:
                        # Fresh admission shares the same durable rotation.
                        # Selection grants no claim or completion authority.
                        async with asyncio.timeout(budget):
                            states = await self._persistence.select_preparation_intake_worksets(
                                scope, limit=1
                            )
                        if states:
                            refs, accepted, status = await self._bounded_process(
                                states[0].workset,
                                reader,
                                request,
                            )
                            outputs.extend(refs)
                            pending |= not accepted
                            incomplete |= status is TerminalStatus.INCOMPLETE
                    # A full processed page is not proof of an empty queue.
                    # This bounded read also includes newly admitted work.
                    async with asyncio.timeout(budget):
                        remaining = (
                            await self._persistence.list_preparation_intake_worksets(
                                scope,
                                limit=1,
                            )
                        )
                    pending |= bool(remaining)
                except asyncio.CancelledError:
                    raise
                except Exception:  # noqa: BLE001
                    pending = True
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            pending = True
        finally:
            await reader.close()
        limitations = []
        if pending:
            limitations.append(
                Limitation(
                    "scheduled-work-pending", "Some scheduled work remains pending."
                )
            )
        if incomplete:
            limitations.append(
                Limitation(
                    "scheduled-preparation-incomplete",
                    "Accepted preparation reported incomplete output.",
                )
            )
        return OperationOutcome(
            request.execution,
            request.capability,
            TerminalStatus.INCOMPLETE
            if pending or incomplete
            else TerminalStatus.COMPLETE,
            result_refs=tuple(dict.fromkeys(outputs)),
            limitations=tuple(limitations),
        )

    async def _bounded_process(self, reference, reader, request):
        """
        Charge one work unit for failure and bound the whole replay cut.

        All replay plans share this deadline, including finalization. Half the
        configured lease surplus is reserved for cancellation and claim cleanup.
        Awaited store and reader workers are drained; none are detached at exit.
        """
        execution = self._operation.execution_timeout_seconds
        margin = (self._operation.claim_lease_seconds - execution) / 2
        try:
            async with asyncio.timeout(execution + margin):
                return await self._process(reference, reader, request)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            return (), False, TerminalStatus.FAILED

    async def _process(self, reference, reader, request):
        """Fence exact replay outputs with the separate workset claim."""
        saved = await self._persistence.get_result(reference.result_id)
        if saved is None or saved.semantic_data_ref is None:
            return (), False, TerminalStatus.FAILED
        workset = await self._persistence.load_semantic_data(saved.semantic_data_ref)
        if not isinstance(workset, PreparationIntakeWorkset) or workset.transitions:
            return (), False, TerminalStatus.FAILED
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
                    return (), False, TerminalStatus.FAILED
                value = await self._persistence.load_semantic_data(
                    selected.semantic_data_ref,
                )
                if not isinstance(value, CollectedSelection):
                    return (), False, TerminalStatus.FAILED
                plans.append(
                    SelectionPlan(
                        source=value.source,
                        replay_result=ref,
                        replay_selection=value.selection,
                    )
                )
            outputs: list[ResultRef] = []
            status = TerminalStatus.COMPLETE
            # A source version can occur in several distinct release entries.
            # Split only at exact frozen-input boundaries; each accepted plan
            # contributes its whole disjoint manifest to the existing proof.
            batches: list[list[SelectionPlan]] = []
            for selection in plans:
                if (
                    not batches
                    or len(batches[-1]) >= self._operation.max_records
                    or selection.source in {p.source for p in batches[-1]}
                ):
                    batches.append([])
                batches[-1].append(selection)
            for selections in batches:
                plan = self._operation.plan(
                    mode=PreparationMode.REPLAY,
                    attempt=self._attempt,
                    selections=tuple(selections),
                )
                outcome = await PreparationHandler(
                    self._persistence,
                    reader,
                    plan,
                ).run(
                    replace(
                        request,
                        target_inputs=tuple(p.source for p in selections),
                    )
                )
                outputs.extend(outcome.result_refs)
                if outcome.status not in {
                    TerminalStatus.COMPLETE,
                    TerminalStatus.INCOMPLETE,
                }:
                    status = outcome.status
                    return tuple(outputs), False, status
                if outcome.status is TerminalStatus.INCOMPLETE:
                    status = TerminalStatus.INCOMPLETE
            await self._persistence.finalize_preparation_intake_workset(
                reference.result_id,
                status,
                tuple(outputs),
                claim=claim,
            )
            return tuple(outputs), True, status
        except asyncio.CancelledError:
            status = TerminalStatus.CANCELLED
            raise
        except Exception:
            status = TerminalStatus.FAILED
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

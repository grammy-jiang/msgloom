"""Finite release admission, ending before parser or producer execution."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Literal

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ClaimToken,
    ExecutionIdentity,
    ExternalEffectState,
    ResultRef,
    StageResult,
    TerminalStatus,
)
from msgloom.persistence import Phase1Persistence, StaleClaimError
from msgloom.preparation_pipeline.intake_codec import PreparationIntakeWorksetCodec
from msgloom.preparation_pipeline.intake_models import (
    MAX_INTAKE_ENTRIES,
    HeldIntakeEntry,
    IntakeAnchor,
    IntakeScope,
    IntakeSelection,
    IntakeTransition,
    PreparationIntakeWorkset,
)
from msgloom.sources.models import (
    CollectedSelection,
    SourceEvidenceLimitError,
    SourceReaderError,
    SourceReferenceError,
)
from msgloom.sources.release_reader import ReleaseSourceReader


class PreparationIntakeService:
    """
    Admit one bounded source/stream cut through the existing async store.

    The caller owns reader and persistence lifetimes. Accepted database work
    drains before cancellation propagates. Saved selections can outlive failed
    admission; retries verify and reuse their deterministic identities. Only
    finalization makes the workset, pending index, and cursor durable together.
    """

    def __init__(self, persistence: Phase1Persistence, reader: ReleaseSourceReader):
        self._persistence = persistence
        self._reader = reader

    async def run(
        self,
        scope: IntakeScope,
        *,
        execution: ExecutionIdentity,
        attempt: AttemptIdentity,
        configuration_version: str,
        code_version: str,
        limit: int = 100,
        lease_seconds: float = 300,
    ) -> StageResult | None:
        """Save one pending workset, or return ``None`` for an empty cut."""
        scope = IntakeScope.model_validate_json(scope.model_dump_json())
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("intake limit must be between 1 and 1000")
        for version in (configuration_version, code_version):
            if (
                not isinstance(version, str)
                or not version.strip()
                or len(version.encode()) > 2048
            ):
                raise ValueError("intake versions must be bounded non-empty text")
        claim = await self._persistence.acquire_claim(
            scope.claim_key(),
            ClaimKind.PREPARE_INTAKE,
            execution,
            attempt,
            lease_seconds=lease_seconds,
        )
        status = TerminalStatus.FAILED
        try:
            result = await self._admit(
                scope, claim, configuration_version, code_version, limit
            )
            status = TerminalStatus.COMPLETE
            return result
        except asyncio.CancelledError:
            status = TerminalStatus.CANCELLED
            raise
        finally:
            try:
                await self._persistence.finish_claim(
                    claim, status, ExternalEffectState.NONE
                )
            except StaleClaimError:
                # A superseded owner cannot alter the successor's history.
                pass

    async def _admit(self, scope, claim, configuration, code, limit):
        catalog = self._reader.catalog
        if await catalog.catalog_identity() != scope.catalog:
            raise SourceReferenceError("Intake catalog identity mismatch")
        previous = await self._persistence.get_preparation_intake_cursor(scope)
        if previous.last_release_entry_seq:
            anchor = await catalog.get_release_entry(previous.last_release_entry_seq)
            if (
                anchor is None
                or anchor.entry_digest != previous.last_release_entry_digest
                or anchor.source_id != scope.source_id
                or anchor.stream != scope.stream
                or anchor.catalog != scope.catalog
            ):
                raise SourceReferenceError("Intake cursor anchor mismatch")
        ceiling = await catalog.max_release_entry_seq(scope.source_id, scope.stream)
        if ceiling < previous.last_release_entry_seq:
            raise SourceReferenceError("Intake ledger moved behind cursor")
        page = await catalog.list_release_entries(
            scope.source_id,
            scope.stream,
            after_seq=previous.last_release_entry_seq,
            through_seq=ceiling,
            limit=limit,
        )
        if not page.entries:
            return None
        selections = []
        transitions = []
        held = []
        admitted = []
        workset = None
        for entry in page.entries:
            entry_held = []
            try:
                released = await self._reader.read_entry(entry.reference)
                mapped = [
                    _transition(entry.reference, item) for item in released.transitions
                ]
                mapped.extend(
                    IntakeTransition(
                        entry=entry.reference,
                        fact_id=fact.fact_id,
                        transition_kind="context_refresh",
                        resource_kind=fact.resource_kind,
                        resource_identity=fact.resource_identity,
                        scope_kind=fact.scope_kind or fact.resource_kind,
                        scope_identity=fact.scope_identity or fact.resource_identity,
                    )
                    for fact in released.facts
                    if fact.fact_kind == "control_context" and fact.role != "proof"
                )
                # Root context has no wider A1 scope. Its resource is the
                # refresh scope; never promote context to readable primary work.
                values = tuple(
                    value
                    for value in (
                        released.selection,
                        *released.components,
                    )
                    if value is not None
                )
                if not values and not mapped:
                    raise SourceReferenceError("Release has no intake disposition")
            except SourceReaderError as error:
                # Generic evidence errors cover missing files, ownership, and
                # invalid bytes. Only the typed limit error proves a narrower
                # reason; exception text is not a classification contract.
                reason = (
                    "byte_limit"
                    if isinstance(error, SourceEvidenceLimitError)
                    else "materialization_failed"
                )
                entry_held = [HeldIntakeEntry(entry=entry.reference, reason=reason)]
                values, mapped = (), []
            proposed = [
                IntakeSelection(
                    entry=entry.reference,
                    result=ResultRef(
                        _identity(
                            "selection",
                            [
                                scope.claim_key(),
                                entry.reference.model_dump(mode="json"),
                                entry.facts,
                                configuration,
                                code,
                                ordinal,
                            ],
                        ),
                        "collected_selection",
                        "1",
                    ),
                )
                for ordinal in range(len(values))
            ]
            # Preflight the exact complete candidate before selection writes.
            # Aggregate overflow ends this prefix. An entry that cannot fit
            # alone is held so the stable cursor can make durable progress.
            candidate, reason = _bounded_workset(
                scope,
                previous,
                configuration,
                code,
                [*admitted, entry],
                [*selections, *proposed],
                [*transitions, *mapped],
                [*held, *entry_held],
            )
            if candidate is None:
                if admitted:
                    break
                entry_held = [
                    HeldIntakeEntry(
                        entry=entry.reference, reason=reason or "byte_limit"
                    )
                ]
                values, proposed, mapped = (), [], []
                candidate, _ = _bounded_workset(
                    scope,
                    previous,
                    configuration,
                    code,
                    [entry],
                    [],
                    [],
                    entry_held,
                )
                if candidate is None:
                    raise SourceReferenceError("Held entry exceeds intake bounds")
            for item, value in zip(proposed, values, strict=True):
                await self._selection(
                    item.result.result_id, value, claim, configuration, code
                )
            selections.extend(proposed)
            transitions.extend(mapped)
            held.extend(entry_held)
            admitted.append(entry)
            workset = candidate
        if workset is None:
            raise SourceReferenceError("Intake cut has no bounded disposition")
        identity = _identity("workset", workset.model_dump(mode="json"))
        result = self._result(
            identity,
            "preparation_intake_workset",
            workset,
            claim,
            configuration,
            code,
            workset.selection_refs,
        )
        await self._persistence.finalize_preparation_intake(
            result, workset, claim=claim
        )
        return result

    def _result(self, identity, kind, value, claim, configuration, code, inputs=()):
        sources = (
            (value.source, value.selection)
            if isinstance(value, CollectedSelection)
            else ()
        )
        return StageResult(
            result_id=identity,
            kind=kind,
            schema_version="1",
            execution=claim.execution,
            attempt=claim.attempt,
            input_refs=inputs,
            source_versions=sources,
            prepared_versions=(),
            topic_versions=(),
            configuration_version=configuration,
            code_version=code,
            status=TerminalStatus.COMPLETE,
            acceptable=True,
            semantic_data_ref=self._persistence.semantic_reference(
                identity, kind, "1", value
            ),
        )

    async def _selection(self, identity, value, claim: ClaimToken, configuration, code):
        result = self._result(
            identity, "collected_selection", value, claim, configuration, code
        )
        prior = await self._persistence.get_result(identity)
        if prior is None:
            await self._persistence.append_result_with_data(result, value, claim=claim)
        else:
            if (
                not prior.acceptable
                or prior.kind != result.kind
                or prior.schema_version != "1"
                or prior.semantic_data_ref != result.semantic_data_ref
                or prior.configuration_version != configuration
                or prior.code_version != code
                or prior.source_versions != result.source_versions
                or prior.input_refs
            ):
                raise SourceReferenceError("Deterministic intake selection conflicts")
            if prior.semantic_data_ref is None:
                raise SourceReferenceError("Intake selection lacks saved data")
            await self._persistence.load_semantic_data(prior.semantic_data_ref)
        return ResultRef(identity, "collected_selection", "1")


def _bounded_workset(
    scope, previous, configuration, code, entries, selections, transitions, held
) -> tuple[
    PreparationIntakeWorkset | None,
    Literal["byte_limit", "query_limit"] | None,
]:
    """Validate count and canonical bytes without writing any disposition."""
    if max(len(selections), len(transitions)) > MAX_INTAKE_ENTRIES:
        return None, "query_limit"
    last = entries[-1]
    workset = PreparationIntakeWorkset(
        scope=scope,
        previous=previous,
        cutoff=IntakeAnchor(
            last_release_entry_seq=last.release_entry_seq,
            last_release_entry_digest=last.entry_digest,
        ),
        entries=tuple(entry.reference for entry in entries),
        selections=tuple(selections),
        transitions=tuple(transitions),
        held=tuple(held),
        configuration_version=configuration,
        code_version=code,
    )
    # Construction above checks the full structural contract. The codec adds
    # the encoded size bound, including JSON escaping and repeated references.
    try:
        PreparationIntakeWorksetCodec().encode(workset)
    except ValueError:
        return None, "byte_limit"
    return workset, None


def _identity(kind, value):
    """Hash canonical admission lineage without attempt-specific state."""
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "intake-" + kind + ":" + hashlib.sha256(data.encode()).hexdigest()


def _transition(entry, value):
    """Map exact provider reasons without widening scoped absence to deletion."""
    mapping: dict[
        str,
        Literal[
            "presence", "absence", "membership_removal", "deletion", "context_refresh"
        ],
    ] = {
        "snapshot_present": "presence",
        "inventory_present": "presence",
        "present": "presence",
        "observed_present": "presence",
        "reconciliation_seen": "presence",
        "snapshot_absent": "absence",
        "resync_absent": "absence",
        "not_in_complete_reconciliation": "absence",
        "not_in_complete_inventory": "absence",
        "not_in_complete_snapshot": "absence",
        "folder_membership_removed": "membership_removal",
        "folder_delta_removed": "membership_removal",
        "delta_removed": "membership_removal",
        "provider_deleted": "deletion",
    }
    kind = mapping.get(value.reason)
    if value.stream == "outlook_calendar":
        try:
            reason = json.loads(value.reason)
            calendar: dict[
                str, Literal["presence", "absence", "membership_removal"]
            ] = {
                "present": "presence",
                "removed": "membership_removal",
                # A reset proves absence only in this exact calendar window.
                "rebaseline_absence": "absence",
            }
            provider_kind = reason.get("kind")
            kind = (
                calendar.get(provider_kind) if isinstance(provider_kind, str) else None
            )
        except (ValueError, AttributeError):
            kind = None
    if kind is None:
        raise SourceReferenceError("Unsupported exact transition reason")
    return IntakeTransition(
        entry=entry,
        fact_id=value.fact_id,
        transition_kind=kind,
        resource_kind=value.resource_kind,
        resource_identity=value.resource_identity,
        scope_kind=value.scope_kind,
        scope_identity=value.scope_identity,
    )

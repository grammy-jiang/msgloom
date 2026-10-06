"""Explicit finite historical admission using the normal A2 workset owner."""

import asyncio
from dataclasses import asdict

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ExternalEffectState,
    ResultRef,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence, StaleClaimError
from msgloom.preparation_pipeline.intake import PreparationIntakeService, _identity
from msgloom.preparation_pipeline.intake_codec import PreparationIntakeWorksetCodec
from msgloom.preparation_pipeline.intake_models import (
    MAX_INTAKE_ENTRIES,
    IntakeAnchor,
    IntakeScope,
    PreparationIntakeWorkset,
)
from msgloom.sources.models import SourceReferenceError
from msgloom.sources.release_reader import ReleaseSourceReader


class HistoricalBaselineService:
    """
    Freeze operator-approved exact versions once for a new consumer scope.

    The caller supplies a bounded explicit version list and approval identity;
    no timestamp or discovery query expands that scope. Capture the release
    anchor before reading evidence so concurrent later releases remain future
    work. Evidence and selections are durable before the normal atomic workset
    commit. A failed attempt may leave reusable exact selections but no cursor.
    Reader and persistence lifetimes belong to the caller.
    """

    def __init__(self, persistence: Phase1Persistence, reader: ReleaseSourceReader):
        self._persistence = persistence
        self._reader = reader
        self._intake = PreparationIntakeService(persistence, reader)

    async def run(
        self,
        scope: IntakeScope,
        *,
        sources: tuple[VersionRef, ...],
        approval_id: str,
        execution: ExecutionIdentity,
        attempt: AttemptIdentity,
        configuration_version: str,
        code_version: str,
        lease_seconds: float = 300,
    ) -> StageResult:
        """Save one immutable starting workset; reject an initialized scope."""
        scope = IntakeScope.model_validate_json(scope.model_dump_json())
        if (
            not isinstance(sources, tuple)
            or not 1 <= len(sources) <= MAX_INTAKE_ENTRIES
            or len(set(sources)) != len(sources)
            or any(not isinstance(source, VersionRef) for source in sources)
        ):
            raise ValueError("baseline requires bounded unique exact sources")
        for value in (approval_id, configuration_version, code_version):
            if (
                not isinstance(value, str)
                or not value.strip()
                or len(value.encode()) > 2048
            ):
                raise ValueError("baseline approval and versions must be bounded text")
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
                scope, sources, approval_id, claim, configuration_version, code_version
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
                pass

    async def _admit(self, scope, sources, approval, claim, configuration, code):
        catalog = self._reader.catalog
        if await catalog.catalog_identity() != scope.catalog:
            raise SourceReferenceError("Baseline catalog identity mismatch")
        previous = await self._persistence.get_preparation_intake_cursor(scope)
        prior = await self._persistence.list_preparation_intake_worksets(
            scope, limit=1, pending_only=False
        )
        if previous.last_release_entry_seq or prior:
            raise ValueError("historical baseline already initialized")
        ceiling = await catalog.max_release_entry_seq(scope.source_id, scope.stream)
        cutoff = IntakeAnchor()
        if ceiling:
            entry = await catalog.get_release_entry(ceiling)
            if (
                entry is None
                or entry.catalog != scope.catalog
                or (entry.source_id, entry.stream) != (scope.source_id, scope.stream)
            ):
                raise SourceReferenceError("Baseline release anchor mismatch")
            cutoff = IntakeAnchor(
                last_release_entry_seq=ceiling,
                last_release_entry_digest=entry.entry_digest,
            )
        values = []
        for source in sources:
            value = await self._reader.read_baseline_selection(source)
            stream = {
                "outlook_email": "outlook_mail",
                "contact": "contacts",
            }.get(value.record.source_type.value, value.record.source_type.value)
            if (
                value.record.source_scope.identity != scope.source_id
                or stream != scope.stream
            ):
                raise SourceReferenceError("Baseline source is outside approved scope")
            values.append(value)
        refs = tuple(
            ResultRef(
                _identity(
                    "baseline-selection",
                    [
                        scope.claim_key(),
                        asdict(value.selection),
                        configuration,
                        code,
                    ],
                ),
                "collected_selection",
                "1",
            )
            for value in values
        )
        workset = PreparationIntakeWorkset(
            scope=scope,
            previous=previous,
            cutoff=cutoff,
            entries=(),
            configuration_version=configuration,
            code_version=code,
            baseline_approval=approval,
            baseline_sources=sources,
            baseline_selections=refs,
        )
        PreparationIntakeWorksetCodec().encode(workset)
        for ref, value in zip(refs, values, strict=True):
            await self._intake._selection(
                ref.result_id, value, claim, configuration, code
            )
        identity = _identity("baseline", workset.model_dump(mode="json"))
        result = self._intake._result(
            identity,
            "preparation_intake_workset",
            workset,
            claim,
            configuration,
            code,
            refs,
        )
        await self._persistence.finalize_preparation_intake(
            result, workset, claim=claim
        )
        return result

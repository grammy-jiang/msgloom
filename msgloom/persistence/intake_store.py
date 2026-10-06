"""
Atomic intake admission and pending completion in Phase1Store transactions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.engine import Connection, Engine

from msgloom.contracts import (
    ClaimKind,
    ClaimToken,
    ResultRef,
    ResultSchemaRegistry,
    StageResult,
    TerminalStatus,
)
from msgloom.persistence.claim_store import (
    claim_attempt,
    require_claim_publication,
    require_current_claim,
    require_unreconciled_claim,
)
from msgloom.persistence.codecs import decode_result_refs, encode_result_refs
from msgloom.persistence.errors import (
    DependencyNotReadyError,
    ImmutableRecordError,
    StaleClaimError,
    UnknownResultSchemaError,
)
from msgloom.persistence.intake_completion import (
    recheck_completion,
    validate_completion,
)
from msgloom.persistence.intake_records import (
    cursor_predicate,
    page_bounds,
    read_cursor,
    saved_result,
    scope_values,
    workset_ref,
    workset_state,
)
from msgloom.persistence.intake_scheduling import select_pending
from msgloom.persistence.records import (
    INTAKE_CURSORS,
    INTAKE_HELD_ENTRIES,
    INTAKE_WORKSETS,
    SCHEMA_METADATA,
)
from msgloom.persistence.result_store import append_stage_result
from msgloom.persistence.schema_store import LEGACY_TERMINAL_PREFIX
from msgloom.persistence.semantic import SemanticDataRegistry
from msgloom.persistence.semantic_store import append_semantic_data, load_semantic_data
from msgloom.preparation_pipeline.intake_models import (
    INTAKE_KIND,
    INTAKE_SCHEMA_VERSION,
    HeldIntakeEntry,
    IndexedHeldIntakeEntry,
    IntakeAnchor,
    IntakeScope,
    IntakeWorksetState,
    PreparationIntakeWorkset,
    workset_claim_key,
)
from msgloom.sources.handoff_models import ReleaseEntryRef


class PreparationIntakeStore(ABC):
    """
    Extend the existing neutral owner without opening a second SQLite layer.

    The concrete store supplies its strong writer transaction, registered
    schemas, and engine. All source assembly and saved-selection integrity
    reads precede writer ownership; final writes use metadata checks only.
    """

    engine: Engine
    registry: ResultSchemaRegistry
    semantic_registry: SemanticDataRegistry

    @abstractmethod
    def _write_transaction(self) -> AbstractContextManager[Connection]:
        """Use the caller's existing BEGIN IMMEDIATE transaction owner."""
        raise NotImplementedError

    def _require_schema(self, kind: str, schema_version: str) -> None:
        """Enforce the single concrete owner's registered result schemas."""
        if not self.registry.supports(kind, schema_version):
            raise UnknownResultSchemaError(
                f"unregistered result schema: {kind!r} version {schema_version!r}"
            )

    def get_preparation_intake_cursor(self, scope: IntakeScope) -> IntakeAnchor:
        """Read one stable consumer anchor without consulting A1."""
        with self.engine.connect() as connection:
            return read_cursor(connection, scope)

    def _prevalidate_intake_inputs(self, refs: tuple[ResultRef, ...]) -> None:
        """Validate saved payload integrity before taking writer ownership."""
        with self.engine.connect() as connection:
            for ref in refs:
                result = saved_result(connection, ref, self.registry)
                if result.semantic_data_ref is not None:
                    load_semantic_data(
                        connection,
                        result.semantic_data_ref,
                        self.semantic_registry,
                    )

    def finalize_preparation_intake(
        self,
        result: StageResult,
        workset: PreparationIntakeWorkset,
        *,
        claim: ClaimToken,
    ) -> None:
        """
        Save workset, pending/held indexes, and cursor in one fenced commit.

        The caller has already verified A1 anchors, frozen the complete entry
        cut, and saved its exact selections under the intake claim. There is no
        A1 reader, evidence callback, or provider mutation in this API. A
        failed write leaves the prior cursor and pending index unchanged.
        Finish the intake claim separately after this method succeeds.
        """
        self._require_schema(INTAKE_KIND, INTAKE_SCHEMA_VERSION)
        reference = result.semantic_data_ref
        if (
            result.kind != INTAKE_KIND
            or result.schema_version != INTAKE_SCHEMA_VERSION
            or reference is None
            or (reference.kind, reference.schema_version)
            != (INTAKE_KIND, INTAKE_SCHEMA_VERSION)
            or not result.acceptable
            or result.configuration_version != workset.configuration_version
            or result.code_version != workset.code_version
            or result.input_refs != workset.selection_refs
        ):
            raise ValueError("intake StageResult does not bind its exact workset")
        workset_claim_key(result.result_id)
        encoded = self.semantic_registry.encode_for_reference(reference, workset)
        if (
            claim.kind is not ClaimKind.PREPARE_INTAKE
            or claim.claim_key != workset.scope.claim_key()
            or result.execution != claim.execution
            or result.attempt != claim.attempt
        ):
            raise StaleClaimError("intake claim does not own this workset")
        self._prevalidate_intake_inputs(workset.selection_refs)
        with self._write_transaction() as connection:
            require_claim_publication(connection, claim, result, now=datetime.now(UTC))
            if read_cursor(connection, workset.scope) != workset.previous:
                raise StaleClaimError("preparation intake cursor changed")
            for ref in workset.selection_refs:
                saved_result(connection, ref, self.registry)
            append_semantic_data(connection, encoded)
            append_stage_result(connection, result, require_new=True)
            connection.execute(
                INTAKE_WORKSETS.insert().values(
                    result_id=result.result_id,
                    scope_key=workset.scope.claim_key(),
                    cutoff_release_entry_seq=workset.cutoff.last_release_entry_seq,
                    cutoff_release_entry_digest=workset.cutoff.last_release_entry_digest,
                    state="pending",
                    result_refs=encode_result_refs(()),
                )
            )
            for held in workset.held:
                connection.execute(
                    INTAKE_HELD_ENTRIES.insert().values(
                        result_id=result.result_id,
                        scope_key=workset.scope.claim_key(),
                        release_entry_seq=held.entry.release_entry_seq,
                        entry_digest=held.entry.entry_digest,
                        reason=held.reason,
                    )
                )
            position = {
                "last_release_entry_seq": workset.cutoff.last_release_entry_seq,
                "last_release_entry_digest": workset.cutoff.last_release_entry_digest,
            }
            if workset.previous.last_release_entry_seq == 0:
                connection.execute(
                    INTAKE_CURSORS.insert().values(
                        **scope_values(workset.scope),
                        **position,
                    )
                )
            else:
                connection.execute(
                    update(INTAKE_CURSORS)
                    .where(cursor_predicate(workset.scope))
                    .values(**position)
                )
            require_claim_publication(connection, claim, result, now=datetime.now(UTC))

    def list_preparation_intake_worksets(
        self,
        scope: IntakeScope,
        *,
        limit: int = 100,
        after_seq: int = 0,
        pending_only: bool = True,
    ) -> tuple[IntakeWorksetState, ...]:
        """Page pending or all worksets in monotonic admission order."""
        page_bounds(limit, after_seq)
        if type(pending_only) is not bool:
            raise ValueError("pending_only must be a boolean")
        table = INTAKE_WORKSETS
        query = select(table).where(
            table.c.scope_key == scope.claim_key(),
            table.c.cutoff_release_entry_seq > after_seq,
        )
        if pending_only:
            query = query.where(table.c.state == "pending")
        query = query.order_by(table.c.cutoff_release_entry_seq).limit(limit)
        with self.engine.connect() as connection:
            if (
                pending_only
                and connection.execute(
                    select(SCHEMA_METADATA.c.key)
                    .where(
                        SCHEMA_METADATA.c.key.startswith(LEGACY_TERMINAL_PREFIX),
                        SCHEMA_METADATA.c.value == scope.claim_key(),
                    )
                    .limit(1)
                ).first()
                is not None
            ):
                raise DependencyNotReadyError(
                    "preparation intake recovery-hold: legacy terminal history"
                )
            return tuple(
                workset_state(row) for row in connection.execute(query).mappings()
            )

    def select_preparation_intake_worksets(
        self,
        scope: IntakeScope,
        *,
        limit: int = 100,
    ) -> tuple[IntakeWorksetState, ...]:
        """
        Durably rotate bounded pending discovery independently of admission.

        The selection position commits before return, so failed processing or
        a restart cannot pin discovery to the oldest workset. Fixed cycle
        ceilings preserve turns despite continuing admissions. Selection grants
        no processing claim and changes no admission or completion state.
        Callers that may stop before attempting every selected item must use
        ``limit=1`` immediately before each attempt. Crashes leave all selected
        work pending for a later rotation.
        """
        page_bounds(limit, 0)
        scope_key = scope.claim_key()
        with self._write_transaction() as connection:
            return select_pending(connection, scope_key, limit)

    def list_preparation_intake_held_entries(
        self,
        scope: IntakeScope,
        *,
        limit: int = 100,
        after_seq: int = 0,
    ) -> tuple[IndexedHeldIntakeEntry, ...]:
        """
        Page exact held references for explicit repair without cursor rewind.
        """
        page_bounds(limit, after_seq)
        table = INTAKE_HELD_ENTRIES
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(table)
                .where(
                    table.c.scope_key == scope.claim_key(),
                    table.c.release_entry_seq > after_seq,
                )
                .order_by(table.c.release_entry_seq)
                .limit(limit)
            ).mappings()
            return tuple(
                IndexedHeldIntakeEntry(
                    workset=workset_ref(row["result_id"]),
                    disposition=HeldIntakeEntry(
                        entry=ReleaseEntryRef(
                            catalog=scope.catalog,
                            release_entry_seq=row["release_entry_seq"],
                            entry_digest=row["entry_digest"],
                        ),
                        reason=row["reason"],
                    ),
                )
                for row in rows
            )

    def finalize_preparation_intake_workset(
        self,
        result_id: str,
        status: TerminalStatus,
        result_refs: tuple[ResultRef, ...],
        *,
        claim: ClaimToken,
    ) -> None:
        """
        Mark accepted processing terminal under its exact live PREPARE claim.

        Acquire PREPARE at :func:`workset_claim_key` with the immutable workset
        as a required input before processing. Its finite lease must enclose
        processing and this final update. Existing plan claims remain separate.
        FAILED, CANCELLED, and BLOCKED attempts leave the index pending.
        Accepted plan outputs must cover every frozen selection with exact
        semantic lineage. Proof is loaded before this short writer transaction;
        only saved metadata and accepted plan attempts are rechecked inside it.
        """
        if status not in {TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE}:
            raise ValueError(
                "only accepted preparation outcomes can finish intake work"
            )
        if type(result_refs) is not tuple or len(result_refs) > 1024:
            raise ValueError("terminal result references must be bounded")
        if any(
            not isinstance(ref, ResultRef)
            or any(
                not part.strip() or len(part.encode()) > 2048
                for part in (ref.result_id, ref.kind, ref.schema_version)
            )
            for ref in result_refs
        ):
            raise ValueError("terminal result references must be bounded")
        if len(set(result_refs)) != len(result_refs):
            raise ValueError("duplicate terminal result references")
        ref = workset_ref(result_id)
        if claim.kind is not ClaimKind.PREPARE or claim.claim_key != workset_claim_key(
            result_id
        ):
            raise StaleClaimError("processing claim does not own this workset")
        values = {
            "state": "terminal",
            "terminal_status": status.value,
            "result_refs": encode_result_refs(result_refs),
            "terminal_claim_token": claim.token,
            "terminal_execution_id": claim.execution.value,
            "terminal_attempt_id": claim.attempt.value,
        }
        with self.engine.connect() as connection:
            self._require_terminal_history(connection, result_id, values)
            saved = saved_result(connection, ref, self.registry)
            if saved.semantic_data_ref is None:
                raise ValueError("intake workset lacks its semantic payload")
            workset = load_semantic_data(
                connection,
                saved.semantic_data_ref,
                self.semantic_registry,
            )
            if not isinstance(workset, PreparationIntakeWorkset):
                raise TypeError("intake workset has an invalid semantic payload")
            proof = validate_completion(
                connection,
                workset,
                result_refs,
                claim,
                status,
                self.registry,
                self.semantic_registry,
            )

        with self._write_transaction() as connection:
            self._require_processing_claim(connection, claim, ref)
            table = INTAKE_WORKSETS
            row = (
                connection.execute(
                    select(table).where(
                        table.c.result_id == result_id,
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ValueError("intake workset is not admitted")
            self._require_terminal_history(connection, result_id, values)
            recheck_completion(
                connection,
                saved,
                proof,
                workset,
                result_refs,
                status,
                self.registry,
            )
            if row["state"] == "terminal":
                if any(row[key] != value for key, value in values.items()):
                    raise ImmutableRecordError(
                        "terminal intake processing is immutable"
                    )
                return
            connection.execute(
                update(table).where(table.c.result_id == result_id).values(**values)
            )
            self._require_processing_claim(connection, claim, ref)
            self._require_terminal_history(connection, result_id, values)
            recheck_completion(
                connection,
                saved,
                proof,
                workset,
                result_refs,
                status,
                self.registry,
            )

    @staticmethod
    def _require_terminal_history(connection, result_id, values) -> None:
        """Keep historical dispositions immutable, including explicit holds."""
        hold = connection.execute(
            select(SCHEMA_METADATA.c.key).where(
                SCHEMA_METADATA.c.key == LEGACY_TERMINAL_PREFIX + result_id,
            )
        ).first()
        if hold is not None:
            raise DependencyNotReadyError(
                "legacy terminal requires recovery-hold resolution"
            )
        row = (
            connection.execute(
                select(INTAKE_WORKSETS).where(
                    INTAKE_WORKSETS.c.result_id == result_id,
                )
            )
            .mappings()
            .first()
        )
        if (
            row is not None
            and row["state"] == "terminal"
            and any(row[key] != value for key, value in values.items())
        ):
            raise ImmutableRecordError("terminal intake processing is immutable")

    @staticmethod
    def _require_processing_claim(
        connection: Connection,
        claim: ClaimToken,
        ref: ResultRef,
    ) -> None:
        current = require_current_claim(connection, claim, now=datetime.now(UTC))
        require_unreconciled_claim(connection, claim)
        attempt = claim_attempt(connection, claim)
        if attempt["finished_at"] is not None:
            raise StaleClaimError("terminal claim cannot finish pending intake")
        if ref not in decode_result_refs(current["required_inputs"]):
            raise StaleClaimError("processing claim lacks exact workset dependency")

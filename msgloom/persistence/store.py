"""Synchronous SQLAlchemy owner for provider-neutral Phase 1 tables."""

import os
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, delete, select, update
from sqlalchemy.engine import Connection, make_url

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ClaimToken,
    ExecutionIdentity,
    ExternalEffectState,
    OperationOutcome,
    ResultRef,
    ResultSchemaRegistry,
    SemanticDataRef,
    StageResult,
    TerminalStatus,
)
from msgloom.persistence.claim_store import (
    claim_attempt,
    claim_is_expired,
    require_claim_publication,
    require_current_claim,
    validate_lease_seconds,
)
from msgloom.persistence.codecs import encode_result_refs
from msgloom.persistence.errors import (
    ClaimUnavailableError,
    DependencyNotReadyError,
    ExternalEffectReconciliationRequired,
    ImmutableRecordError,
    SemanticDataReferenceError,
    StaleClaimError,
    UnknownResultSchemaError,
)
from msgloom.persistence.reconciliation import (
    ClaimInspection,
    ReconciliationRequest,
    ReconciliationResult,
)
from msgloom.persistence.reconciliation_store import inspect_claim, reconcile_effect
from msgloom.persistence.records import (
    CLAIM_ATTEMPTS,
    OPERATION_OUTCOMES,
    STAGE_RESULTS,
    WORK_CLAIMS,
    outcome_from_row,
    outcome_values,
    result_from_row,
)
from msgloom.persistence.result_store import append_stage_result
from msgloom.persistence.schema_store import initialize_schema
from msgloom.persistence.semantic import SemanticDataRegistry
from msgloom.persistence.semantic_store import append_semantic_data, load_semantic_data

_SAFE_RETRY_EFFECTS = frozenset(
    {
        ExternalEffectState.NONE,
        ExternalEffectState.NOT_STARTED,
        ExternalEffectState.REJECTED,
    }
)


class Phase1Store:
    """Own synchronous SQLite transactions for the neutral application schema."""

    def __init__(
        self,
        database_url: str,
        registry: ResultSchemaRegistry,
        semantic_registry: SemanticDataRegistry | None = None,
    ) -> None:
        url = make_url(database_url)
        if url.get_backend_name() != "sqlite":
            raise ValueError("Phase 1 persistence currently requires SQLite")
        if not url.database or url.database == ":memory:":
            raise ValueError("Phase 1 durable persistence requires a file database")

        path = Path(url.database)
        path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
        self.registry = registry
        self.semantic_registry = semantic_registry or SemanticDataRegistry.phase1()
        self.engine = create_engine(
            database_url,
            connect_args={"autocommit": True, "timeout": 30.0},
            pool_size=1,
            max_overflow=0,
            pool_timeout=30.0,
        )
        try:
            initialize_schema(self.engine)
            os.chmod(path, 0o600)
        except BaseException:
            self.engine.dispose()
            raise

    def close(self) -> None:
        """Dispose the engine after all awaited facade calls have drained."""
        self.engine.dispose()

    def semantic_reference(
        self,
        data_id: str,
        kind: str,
        schema_version: str,
        value: object,
    ) -> SemanticDataRef:
        """Build an integrity reference using the registered semantic codec."""
        return self.semantic_registry.reference(data_id, kind, schema_version, value)

    def append_result(
        self, result: StageResult, *, claim: ClaimToken | None = None
    ) -> None:
        """Append metadata-only results, optionally fenced by a live claim."""
        if result.semantic_data_ref is not None:
            raise SemanticDataReferenceError(
                "semantic result data must use append_result_with_data"
            )
        self._require_schema(result.kind, result.schema_version)
        needs_data = self.registry.requires_data(result.kind, result.schema_version)
        if result.acceptable and needs_data:
            raise SemanticDataReferenceError("acceptable result requires semantic data")
        with self._write_transaction() as connection:
            if claim is not None:
                require_claim_publication(
                    connection, claim, result, now=datetime.now(UTC)
                )
            append_stage_result(connection, result)
            if claim is not None:
                require_claim_publication(
                    connection, claim, result, now=datetime.now(UTC)
                )

    def append_result_with_data(
        self,
        result: StageResult,
        value: object,
        *,
        require_new: bool = False,
        claim: ClaimToken | None = None,
    ) -> None:
        """Atomically append a result/data pair, optionally requiring a new id."""
        self._require_schema(result.kind, result.schema_version)
        reference = result.semantic_data_ref
        if reference is None:
            raise SemanticDataReferenceError(
                "semantic result must declare semantic_data_ref"
            )
        if (
            reference.kind != result.kind
            or reference.schema_version != result.schema_version
        ):
            raise SemanticDataReferenceError(
                "semantic data kind/schema must match its stage result"
            )
        encoded = self.semantic_registry.encode_for_reference(reference, value)
        with self._write_transaction() as connection:
            if claim is not None:
                require_claim_publication(
                    connection, claim, result, now=datetime.now(UTC)
                )
            append_semantic_data(connection, encoded)
            append_stage_result(connection, result, require_new=require_new)
            if claim is not None:
                require_claim_publication(
                    connection, claim, result, now=datetime.now(UTC)
                )

    def load_semantic_data(self, reference: SemanticDataRef) -> object:
        """Load and validate one immutable semantic payload."""
        with self.engine.connect() as connection:
            return load_semantic_data(connection, reference, self.semantic_registry)

    def get_result(self, result_id: str) -> StageResult | None:
        """Load one result and enforce its registered semantic-data policy."""
        table = STAGE_RESULTS
        with self.engine.connect() as connection:
            row = (
                connection.execute(select(table).where(table.c.result_id == result_id))
                .mappings()
                .first()
            )
        if row is None:
            return None
        self._require_schema(row["kind"], row["schema_version"])
        result = result_from_row(row)
        needs_data = self.registry.requires_data(result.kind, result.schema_version)
        if result.acceptable and result.semantic_data_ref is None and needs_data:
            raise SemanticDataReferenceError("acceptable result lacks semantic data")
        return result

    def save_outcome(self, outcome: OperationOutcome) -> None:
        """Save one immutable terminal operation outcome."""
        table = OPERATION_OUTCOMES
        values = outcome_values(outcome)
        with self._write_transaction() as connection:
            existing = (
                connection.execute(
                    select(table).where(table.c.execution_id == outcome.execution.value)
                )
                .mappings()
                .first()
            )
            if existing is not None:
                if outcome_from_row(existing) != outcome:
                    raise ImmutableRecordError(
                        f"operation outcome {outcome.execution.value!r} is immutable"
                    )
                return
            connection.execute(table.insert().values(**values))

    def get_outcome(self, execution: ExecutionIdentity) -> OperationOutcome | None:
        """Load a terminal operation outcome."""
        table = OPERATION_OUTCOMES
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(table).where(table.c.execution_id == execution.value)
                )
                .mappings()
                .first()
            )
        return None if row is None else outcome_from_row(row)

    def acquire_claim(
        self,
        claim_key: str,
        kind: ClaimKind,
        execution: ExecutionIdentity,
        attempt: AttemptIdentity,
        required_inputs: tuple[ResultRef, ...],
        lease_seconds: float,
    ) -> ClaimToken:
        """Atomically validate dependencies and acquire or reclaim one scope."""
        if not claim_key.strip():
            raise ValueError("claim key must be non-empty")
        lease = validate_lease_seconds(lease_seconds)
        claims = WORK_CLAIMS
        attempts = CLAIM_ATTEMPTS

        with self._write_transaction() as connection:
            self._require_inputs(connection, required_inputs)
            now = datetime.now(UTC)
            expires = now + timedelta(seconds=lease)
            current = (
                connection.execute(
                    select(claims).where(claims.c.claim_key == claim_key)
                )
                .mappings()
                .first()
            )
            if current is not None:
                effect = ExternalEffectState(current["external_effect"])
                if effect not in _SAFE_RETRY_EFFECTS:
                    raise ExternalEffectReconciliationRequired(
                        "prior external effect requires reconciliation"
                    )
                if not claim_is_expired(current, now):
                    raise ClaimUnavailableError("durable claim is already held")
                connection.execute(
                    update(attempts)
                    .where(attempts.c.claim_token == current["claim_token"])
                    .values(
                        terminal_status=TerminalStatus.INCOMPLETE.value,
                        finished_at=_time(now),
                    )
                )
                connection.execute(
                    delete(claims).where(claims.c.claim_key == claim_key)
                )

            token = ClaimToken(
                claim_key=claim_key,
                token=uuid4().hex,
                kind=kind,
                execution=execution,
                attempt=attempt,
            )
            refs = encode_result_refs(required_inputs)
            connection.execute(
                claims.insert().values(
                    claim_key=claim_key,
                    claim_token=token.token,
                    claim_kind=kind.value,
                    execution_id=execution.value,
                    attempt_id=attempt.value,
                    required_inputs=refs,
                    claimed_at=_time(now),
                    expires_at=_time(expires),
                    external_effect=ExternalEffectState.NOT_STARTED.value,
                )
            )
            connection.execute(
                attempts.insert().values(
                    claim_token=token.token,
                    claim_key=claim_key,
                    claim_kind=kind.value,
                    execution_id=execution.value,
                    attempt_id=attempt.value,
                    started_at=_time(now),
                    external_effect=ExternalEffectState.NOT_STARTED.value,
                )
            )
            return token

    def mark_external_effect(
        self, token: ClaimToken, effect: ExternalEffectState
    ) -> None:
        """Persist effect state before or after a future external submission."""
        claims = WORK_CLAIMS
        attempts = CLAIM_ATTEMPTS
        with self._write_transaction() as connection:
            now = datetime.now(UTC)
            current = require_current_claim(
                connection, token, now=now, require_unexpired=False
            )
            if token.kind is not ClaimKind.REPORT_SUBMIT:
                raise ValueError(
                    "only report submission claims can have external effects"
                )
            if effect is ExternalEffectState.NONE:
                raise ValueError("report submission must classify its external effect")
            attempt = claim_attempt(connection, token)
            if attempt["finished_at"] is not None:
                raise ImmutableRecordError("terminal claim attempt is immutable")
            current_effect = ExternalEffectState(current["external_effect"])
            if claim_is_expired(current, now) and current_effect in _SAFE_RETRY_EFFECTS:
                raise StaleClaimError(
                    "expired claim cannot begin a new external effect"
                )
            connection.execute(
                update(claims)
                .where(claims.c.claim_token == token.token)
                .values(external_effect=effect.value)
            )
            connection.execute(
                update(attempts)
                .where(attempts.c.claim_token == token.token)
                .values(external_effect=effect.value)
            )

    def finish_claim(
        self,
        token: ClaimToken,
        status: TerminalStatus,
        effect: ExternalEffectState,
    ) -> None:
        """Finish an attempt and release only effects that are safe to retry."""
        claims = WORK_CLAIMS
        attempts = CLAIM_ATTEMPTS
        with self._write_transaction() as connection:
            now = datetime.now(UTC)
            current = require_current_claim(
                connection, token, now=now, require_unexpired=False
            )
            current_effect = ExternalEffectState(current["external_effect"])
            if claim_is_expired(current, now) and current_effect in _SAFE_RETRY_EFFECTS:
                raise StaleClaimError(
                    "expired claim cannot finish after ownership ended"
                )
            if (
                token.kind is ClaimKind.REPORT_SUBMIT
                and effect is ExternalEffectState.NONE
            ):
                raise ValueError("report submission must classify its external effect")
            if token.kind is not ClaimKind.REPORT_SUBMIT and effect not in {
                ExternalEffectState.NONE,
                ExternalEffectState.NOT_STARTED,
            }:
                raise ValueError("non-submission claims cannot record external effects")
            attempt = claim_attempt(connection, token)
            if attempt["finished_at"] is not None:
                if (
                    attempt["terminal_status"] == status.value
                    and attempt["external_effect"] == effect.value
                ):
                    return
                raise ImmutableRecordError("terminal claim attempt is immutable")
            connection.execute(
                update(attempts)
                .where(attempts.c.claim_token == token.token)
                .values(
                    terminal_status=status.value,
                    external_effect=effect.value,
                    finished_at=_time(now),
                )
            )
            if effect in _SAFE_RETRY_EFFECTS:
                connection.execute(
                    delete(claims).where(claims.c.claim_token == token.token)
                )
                return
            connection.execute(
                update(claims)
                .where(claims.c.claim_token == token.token)
                .values(external_effect=effect.value, expires_at=_time(now))
            )

    def reconcile_external_effect(
        self, request: ReconciliationRequest
    ) -> ReconciliationResult:
        """Atomically save reconciliation proof and update retry gating."""
        with self._write_transaction() as connection:
            return reconcile_effect(connection, request, self._require_inputs)

    def inspect_claim(
        self, claim_key: str, *, history_limit: int = 100
    ) -> ClaimInspection:
        """Read bounded current ownership and immutable claim history."""
        with self.engine.connect() as connection:
            return inspect_claim(connection, claim_key, history_limit)

    def _require_inputs(
        self, connection: Connection, refs: tuple[ResultRef, ...]
    ) -> None:
        table = STAGE_RESULTS
        for ref in refs:
            self._require_schema(ref.kind, ref.schema_version)
            row = (
                connection.execute(
                    select(table).where(table.c.result_id == ref.result_id)
                )
                .mappings()
                .first()
            )
            if row is None:
                raise DependencyNotReadyError("required stage result is not durable")
            if row["kind"] != ref.kind or row["schema_version"] != ref.schema_version:
                raise DependencyNotReadyError(
                    "required stage result version mismatches"
                )
            if not row["acceptable"]:
                raise DependencyNotReadyError(
                    "required stage result is not explicitly acceptable"
                )
            data_ref = result_from_row(row).semantic_data_ref
            needs_data = self.registry.requires_data(ref.kind, ref.schema_version)
            if data_ref is None and needs_data:
                raise DependencyNotReadyError("required result lacks semantic data")
            if data_ref is not None:
                if (
                    data_ref.kind != row["kind"]
                    or data_ref.schema_version != row["schema_version"]
                ):
                    raise DependencyNotReadyError(
                        "required semantic data schema mismatches its stage result"
                    )
                load_semantic_data(connection, data_ref, self.semantic_registry)

    def _require_schema(self, kind: str, schema_version: str) -> None:
        if not self.registry.supports(kind, schema_version):
            raise UnknownResultSchemaError(
                f"unregistered result schema: {kind!r} version {schema_version!r}"
            )

    @contextmanager
    def _write_transaction(self):
        with self.engine.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.exec_driver_sql("COMMIT")
            except BaseException:
                connection.exec_driver_sql("ROLLBACK")
                raise


def _time(value: datetime) -> str:
    return value.isoformat(timespec="microseconds")

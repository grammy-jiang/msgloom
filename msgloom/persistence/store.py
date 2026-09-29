"""Synchronous SQLAlchemy owner for provider-neutral Phase 1 tables."""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, delete, inspect, select, update
from sqlalchemy.engine import Connection, RowMapping, make_url

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ClaimToken,
    ExecutionIdentity,
    ExternalEffectState,
    OperationOutcome,
    ResultRef,
    ResultSchemaRegistry,
    StageResult,
    TerminalStatus,
)
from msgloom.persistence.codecs import encode_result_refs
from msgloom.persistence.errors import (
    ClaimUnavailableError,
    DependencyNotReadyError,
    ExternalEffectReconciliationRequired,
    ImmutableRecordError,
    IncompatibleSchemaError,
    StaleClaimError,
    UnknownResultSchemaError,
)
from msgloom.persistence.models import Phase1Base
from msgloom.persistence.records import (
    CLAIM_ATTEMPTS,
    OPERATION_OUTCOMES,
    SCHEMA_METADATA,
    STAGE_RESULTS,
    WORK_CLAIMS,
    outcome_from_row,
    outcome_values,
    result_from_row,
    result_values,
)

_SCHEMA_VERSION = "1"
_SAFE_RETRY_EFFECTS = frozenset(
    {
        ExternalEffectState.NONE,
        ExternalEffectState.NOT_STARTED,
        ExternalEffectState.REJECTED,
    }
)


class Phase1Store:
    """Own synchronous SQLite transactions for the neutral application schema."""

    def __init__(self, database_url: str, registry: ResultSchemaRegistry) -> None:
        url = make_url(database_url)
        if url.get_backend_name() != "sqlite":
            raise ValueError("Phase 1 persistence currently requires SQLite")
        if not url.database or url.database == ":memory:":
            raise ValueError("Phase 1 durable persistence requires a file database")

        path = Path(url.database)
        path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
        self.registry = registry
        self.engine = create_engine(
            database_url,
            connect_args={"autocommit": True, "timeout": 30.0},
            pool_size=1,
            max_overflow=0,
            pool_timeout=30.0,
        )
        try:
            self._initialize_schema()
            os.chmod(path, 0o600)
        except BaseException:
            self.engine.dispose()
            raise

    def close(self) -> None:
        """Dispose the engine after all awaited facade calls have drained."""
        self.engine.dispose()

    def append_result(self, result: StageResult) -> None:
        """Append one immutable result, allowing only identical replay."""
        self._require_schema(result.kind, result.schema_version)
        values = result_values(result)
        table = STAGE_RESULTS
        with self._write_transaction() as connection:
            existing = (
                connection.execute(
                    select(table).where(table.c.result_id == result.result_id)
                )
                .mappings()
                .first()
            )
            if existing is not None:
                if result_from_row(existing) != result:
                    raise ImmutableRecordError(
                        f"stage result {result.result_id!r} is immutable"
                    )
                return
            connection.execute(table.insert().values(**values))

    def get_result(self, result_id: str) -> StageResult | None:
        """Load one immutable result by identity."""
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
        return result_from_row(row)

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
        if lease_seconds < 0:
            raise ValueError("claim lease must be non-negative")
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=lease_seconds)
        claims = WORK_CLAIMS
        attempts = CLAIM_ATTEMPTS

        with self._write_transaction() as connection:
            self._require_inputs(connection, required_inputs)
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
                if _parse_time(current["expires_at"]) > now:
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
            self._require_current_claim(connection, token)
            if token.kind is not ClaimKind.REPORT_SUBMIT:
                raise ValueError(
                    "only report submission claims can have external effects"
                )
            if effect is ExternalEffectState.NONE:
                raise ValueError("report submission must classify its external effect")
            attempt = self._claim_attempt(connection, token)
            if attempt["finished_at"] is not None:
                raise ImmutableRecordError("terminal claim attempt is immutable")
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
        now = datetime.now(UTC)
        with self._write_transaction() as connection:
            self._require_current_claim(connection, token)
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
            attempt = self._claim_attempt(connection, token)
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

    def _require_current_claim(self, connection: Connection, token: ClaimToken) -> None:
        claims = WORK_CLAIMS
        current = (
            connection.execute(
                select(claims).where(claims.c.claim_key == token.claim_key)
            )
            .mappings()
            .first()
        )
        if current is None:
            raise StaleClaimError("claim attempt no longer owns this scope")
        if (
            current["claim_token"] != token.token
            or current["claim_kind"] != token.kind.value
            or current["execution_id"] != token.execution.value
            or current["attempt_id"] != token.attempt.value
        ):
            raise StaleClaimError("claim token metadata does not match current owner")

    def _claim_attempt(self, connection: Connection, token: ClaimToken) -> RowMapping:
        attempt = (
            connection.execute(
                select(CLAIM_ATTEMPTS).where(
                    CLAIM_ATTEMPTS.c.claim_token == token.token
                )
            )
            .mappings()
            .first()
        )
        if attempt is None:
            raise StaleClaimError("claim attempt history is missing")
        if (
            attempt["claim_key"] != token.claim_key
            or attempt["claim_kind"] != token.kind.value
            or attempt["execution_id"] != token.execution.value
            or attempt["attempt_id"] != token.attempt.value
        ):
            raise StaleClaimError("claim token metadata does not match attempt history")
        return attempt

    def _require_schema(self, kind: str, schema_version: str) -> None:
        if not self.registry.supports(kind, schema_version):
            raise UnknownResultSchemaError(
                f"unregistered result schema: {kind!r} version {schema_version!r}"
            )

    def _initialize_schema(self) -> None:
        expected = set(Phase1Base.metadata.tables)
        with self.engine.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                existing = {
                    name
                    for name in inspect(connection).get_table_names()
                    if name.startswith("phase1_")
                }
                if not existing:
                    Phase1Base.metadata.create_all(connection)
                    connection.execute(
                        SCHEMA_METADATA.insert().values(
                            key="schema_version", value=_SCHEMA_VERSION
                        )
                    )
                elif existing != expected:
                    raise IncompatibleSchemaError(
                        "neutral table set requires an explicit migration"
                    )
                else:
                    version = connection.execute(
                        select(SCHEMA_METADATA.c.value).where(
                            SCHEMA_METADATA.c.key == "schema_version"
                        )
                    ).scalar_one_or_none()
                    if version != _SCHEMA_VERSION:
                        raise IncompatibleSchemaError(
                            "neutral schema version requires an explicit migration"
                        )
                connection.exec_driver_sql("COMMIT")
            except BaseException:
                connection.exec_driver_sql("ROLLBACK")
                raise

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


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("stored claim time must be timezone-aware")
    return parsed

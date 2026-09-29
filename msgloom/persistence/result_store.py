"""Append-only SQL operation for immutable Phase 1 stage results."""

from sqlalchemy import select
from sqlalchemy.engine import Connection

from msgloom.contracts import StageResult
from msgloom.persistence.errors import ImmutableRecordError
from msgloom.persistence.records import STAGE_RESULTS, result_from_row, result_values


def append_stage_result(connection: Connection, result: StageResult) -> None:
    """Append a result idempotently or reject a conflicting historical rewrite."""
    values = result_values(result)
    existing = (
        connection.execute(
            select(STAGE_RESULTS).where(STAGE_RESULTS.c.result_id == result.result_id)
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
    connection.execute(STAGE_RESULTS.insert().values(**values))

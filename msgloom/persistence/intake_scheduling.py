"""Rotate bounded pending discovery inside the neutral writer transaction."""

import json

from sqlalchemy import func, select, update
from sqlalchemy.engine import Connection

from msgloom.persistence.errors import DependencyNotReadyError
from msgloom.persistence.intake_records import page_bounds, workset_state
from msgloom.persistence.records import INTAKE_WORKSETS, SCHEMA_METADATA
from msgloom.persistence.schema_store import LEGACY_TERMINAL_PREFIX
from msgloom.preparation_pipeline.intake_models import IntakeWorksetState

_ROTATION_PREFIX = "preparation_intake_rotation:"


def select_pending(
    connection: Connection, scope_key: str, limit: int
) -> tuple[IntakeWorksetState, ...]:
    """
    Reserve discovery turns, preserving pending work and processing ownership.

    The caller owns BEGIN IMMEDIATE and supplies a validated scope key and
    limit. A fixed ceiling closes each cycle even when admissions outpace
    processing. At most two bounded reads cover one wrap without duplicates.
    Position updates and selection decode share one rollback boundary.
    """
    metadata = SCHEMA_METADATA
    if (
        connection.execute(
            select(metadata.c.key)
            .where(
                metadata.c.key.startswith(LEGACY_TERMINAL_PREFIX),
                metadata.c.value == scope_key,
            )
            .limit(1)
        ).first()
        is not None
    ):
        raise DependencyNotReadyError(
            "preparation intake recovery-hold: legacy terminal history"
        )
    key = _ROTATION_PREFIX + scope_key
    stored = connection.execute(
        select(metadata.c.value).where(metadata.c.key == key)
    ).scalar_one_or_none()
    table = INTAKE_WORKSETS
    pending = (
        table.c.scope_key == scope_key,
        table.c.state == "pending",
    )
    ceiling_now = connection.execute(
        select(func.max(table.c.cutoff_release_entry_seq)).where(*pending)
    ).scalar_one()
    if ceiling_now is None:
        return ()
    position, ceiling = _position(stored, ceiling_now)
    query = select(table).where(*pending).order_by(table.c.cutoff_release_entry_seq)
    rows = list(
        connection.execute(
            query.where(
                table.c.cutoff_release_entry_seq > position,
                table.c.cutoff_release_entry_seq <= ceiling,
            ).limit(limit)
        ).mappings()
    )
    if len(rows) < limit:
        # Start a new finite cycle. Entries selected from the previous tail
        # already received their turn in this page and must not repeat here.
        ceiling = ceiling_now
        wrapped = query.where(
            table.c.result_id.not_in([row["result_id"] for row in rows])
        ).limit(limit - len(rows))
        rows.extend(connection.execute(wrapped).mappings())
    states = tuple(workset_state(row) for row in rows)
    value = json.dumps([rows[-1]["cutoff_release_entry_seq"], ceiling])
    if stored is None:
        connection.execute(metadata.insert().values(key=key, value=value))
    else:
        connection.execute(
            update(metadata).where(metadata.c.key == key).values(value=value)
        )
    return states


def _position(stored: str | None, ceiling: int) -> tuple[int, int]:
    """Fail closed on invalid scheduling metadata rather than reset fairness."""
    if stored is None:
        return 0, ceiling
    value = json.loads(stored)
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("invalid preparation intake rotation")
    position, ceiling = value
    page_bounds(1, position)
    page_bounds(1, ceiling)
    if position > ceiling:
        raise ValueError("invalid preparation intake rotation")
    return position, ceiling

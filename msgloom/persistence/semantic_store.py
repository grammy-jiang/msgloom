"""SQL operations for immutable semantic data inside Phase 1 transactions."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.engine import Connection

from msgloom.contracts import SemanticDataRef
from msgloom.persistence.errors import (
    DependencyNotReadyError,
    ImmutableRecordError,
    SemanticDataReferenceError,
)
from msgloom.persistence.records import SEMANTIC_DATA
from msgloom.persistence.semantic import EncodedSemanticData, SemanticDataRegistry


def append_semantic_data(connection: Connection, encoded: EncodedSemanticData) -> None:
    """Append semantic bytes idempotently or reject a conflicting replay."""
    ref = encoded.reference
    existing = (
        connection.execute(
            select(SEMANTIC_DATA).where(SEMANTIC_DATA.c.data_id == ref.data_id)
        )
        .mappings()
        .first()
    )
    if existing is not None:
        same = (
            existing["kind"] == ref.kind
            and existing["schema_version"] == ref.schema_version
            and existing["sha256"] == ref.sha256
            and existing["byte_count"] == ref.byte_count
            and existing["payload"] == encoded.payload
        )
        if not same:
            raise ImmutableRecordError(f"semantic data {ref.data_id!r} is immutable")
        return
    connection.execute(
        SEMANTIC_DATA.insert().values(
            data_id=ref.data_id,
            kind=ref.kind,
            schema_version=ref.schema_version,
            sha256=ref.sha256,
            byte_count=ref.byte_count,
            payload=encoded.payload,
        )
    )


def load_semantic_data(
    connection: Connection,
    reference: SemanticDataRef,
    registry: SemanticDataRegistry,
) -> object:
    """Load and validate semantic bytes within an existing connection."""
    row = (
        connection.execute(
            select(SEMANTIC_DATA).where(SEMANTIC_DATA.c.data_id == reference.data_id)
        )
        .mappings()
        .first()
    )
    if row is None:
        raise DependencyNotReadyError("required semantic result data is missing")
    if (
        row["kind"] != reference.kind
        or row["schema_version"] != reference.schema_version
        or row["sha256"] != reference.sha256
        or row["byte_count"] != reference.byte_count
    ):
        raise SemanticDataReferenceError(
            "stored semantic data does not match its declared reference"
        )
    return registry.decode(reference, row["payload"])

"""Bounded intake SQL helpers used only within the neutral store owner."""

from sqlalchemy import and_, select
from sqlalchemy.engine import Connection

from msgloom.contracts import ResultRef, ResultSchemaRegistry, TerminalStatus
from msgloom.persistence.codecs import decode_result_refs
from msgloom.persistence.errors import DependencyNotReadyError
from msgloom.persistence.records import (
    INTAKE_CURSORS,
    SEMANTIC_DATA,
    STAGE_RESULTS,
    result_from_row,
)
from msgloom.preparation_pipeline.intake_models import (
    INTAKE_KIND,
    INTAKE_SCHEMA_VERSION,
    IntakeAnchor,
    IntakeScope,
    IntakeWorksetState,
)


def scope_values(scope: IntakeScope) -> dict[str, str]:
    """Validate and map a stable consumer key to its four SQL key columns."""
    scope.claim_key()
    return {
        "catalog_identity": scope.catalog.catalog_identity,
        "source_id": scope.source_id,
        "stream": scope.stream,
        "consumer_id": scope.consumer_id,
    }


def cursor_predicate(scope: IntakeScope):
    """Return the exact composite cursor-key predicate."""
    return and_(
        *(INTAKE_CURSORS.c[key] == value for key, value in scope_values(scope).items())
    )


def read_cursor(connection: Connection, scope: IntakeScope) -> IntakeAnchor:
    """Read the current anchor, treating an absent row as genesis."""
    row = (
        connection.execute(select(INTAKE_CURSORS).where(cursor_predicate(scope)))
        .mappings()
        .first()
    )
    if row is None:
        return IntakeAnchor()
    return IntakeAnchor(
        last_release_entry_seq=row["last_release_entry_seq"],
        last_release_entry_digest=row["last_release_entry_digest"],
    )


def page_bounds(limit: int, after_seq: int) -> None:
    """Reject coercion and unbounded pending/held lookup requests."""
    if type(limit) is not int or not 1 <= limit <= 1024:
        raise ValueError("intake query limit must be between 1 and 1024")
    if type(after_seq) is not int or not 0 <= after_seq <= 2**63 - 1:
        raise ValueError("intake query position is invalid")


def workset_ref(result_id: str) -> ResultRef:
    """Name one exact immutable intake semantic result."""
    return ResultRef(result_id, INTAKE_KIND, INTAKE_SCHEMA_VERSION)


def workset_state(row) -> IntakeWorksetState:
    """Decode only bounded processing metadata, never source selections."""
    return IntakeWorksetState(
        workset=workset_ref(row["result_id"]),
        cutoff=IntakeAnchor(
            last_release_entry_seq=row["cutoff_release_entry_seq"],
            last_release_entry_digest=row["cutoff_release_entry_digest"] or None,
        ),
        state=row["state"],
        terminal_status=(
            TerminalStatus(row["terminal_status"]) if row["terminal_status"] else None
        ),
        result_refs=decode_result_refs(row["result_refs"]),
    )


def saved_result(
    connection: Connection, ref: ResultRef, registry: ResultSchemaRegistry
):
    """
    Require durable acceptable metadata and its exact semantic association.

    Payload integrity validation happens before final writer ownership. This
    helper repeats dependency checks without decoding potentially large saved
    selections while the cursor transaction is open.
    """
    if not registry.supports(ref.kind, ref.schema_version):
        raise DependencyNotReadyError("unregistered intake dependency schema")
    row = (
        connection.execute(
            select(STAGE_RESULTS).where(STAGE_RESULTS.c.result_id == ref.result_id)
        )
        .mappings()
        .first()
    )
    if row is None:
        raise DependencyNotReadyError("intake dependency is not durable")
    result = result_from_row(row)
    if (
        result.kind != ref.kind
        or result.schema_version != ref.schema_version
        or not result.acceptable
    ):
        raise DependencyNotReadyError("intake dependency is not acceptable")
    data = result.semantic_data_ref
    if data is None:
        if registry.requires_data(ref.kind, ref.schema_version):
            raise DependencyNotReadyError("intake dependency lacks semantic data")
        return result
    if (data.kind, data.schema_version) != (ref.kind, ref.schema_version):
        raise DependencyNotReadyError("intake semantic dependency schema mismatches")
    stored = connection.execute(
        select(
            SEMANTIC_DATA.c.kind,
            SEMANTIC_DATA.c.schema_version,
            SEMANTIC_DATA.c.sha256,
            SEMANTIC_DATA.c.byte_count,
        ).where(SEMANTIC_DATA.c.data_id == data.data_id)
    ).first()
    if stored != (data.kind, data.schema_version, data.sha256, data.byte_count):
        raise DependencyNotReadyError("intake semantic dependency is not durable")
    return result

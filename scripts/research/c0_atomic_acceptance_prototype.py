"""C0 research-only SQLite acceptance transaction, not a production migration.

This intentionally uses Phase1Store private transaction internals ONLY inside
an isolated SQLite fixture. Its write sequence illustrates the new atomic
logical-key contract and is not an authorised msgloom persistence API.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, MetaData, String, Table, select

from msgloom.contracts import ClaimToken, ResultRef, StageResult
from msgloom.persistence.claim_store import require_claim_publication
from msgloom.persistence.errors import ImmutableRecordError
from msgloom.persistence.intake_records import saved_result
from msgloom.persistence.result_store import append_stage_result
from msgloom.persistence.semantic_store import append_semantic_data, load_semantic_data
from msgloom.persistence.store import Phase1Store
from scripts.research.c0_contract_prototype import (
    AcceptedPayload,
    StageIdentity,
    append_or_verify,
)


class ExperimentalA2AcceptanceStore:
    """Transactionally separate logical acceptance key from attempt metadata."""

    def __init__(self, existing_phase1_store: Phase1Store) -> None:
        self.owner = existing_phase1_store
        self.table = Table(
            "c0_research_a2_accepted_stage",
            MetaData(),
            Column("logical_key", String(96), primary_key=True),
            Column("kind", String(64), nullable=False),
            Column("schema_version", String(16), nullable=False),
            Column("result_id", String(96), nullable=False, unique=True),
            Column("sha256", String(64), nullable=False),
            Column("byte_count", String(32), nullable=False),
        )
        # SQL DDL modifies ONLY the caller's temporary, disposable DB.
        self.table.metadata.create_all(self.owner.engine)

    def publish(
        self,
        identity: StageIdentity,
        result: StageResult,
        value: object,
        *,
        claim: ClaimToken,
    ) -> ResultRef:
        """BEGIN IMMEDIATE / check-current-claim / read / verify / insert."""
        logical = identity.logical_acceptance_key()
        if (
            result.result_id != logical
            or result.kind != identity.stage_kind
            or result.schema_version != identity.schema_version
            or result.semantic_data_ref is None
            or not result.acceptable
        ):
            raise ImmutableRecordError("C0 acceptance metadata invalid")
        encoded = self.owner.semantic_registry.encode_for_reference(
            result.semantic_data_ref, value
        )
        expected = AcceptedPayload(
            logical_key=logical,
            output=ResultRef(result.result_id, result.kind, result.schema_version),
            canonical_sha256=encoded.reference.sha256,
            canonical_byte_count=encoded.reference.byte_count,
        )
        with self.owner._write_transaction() as connection:
            require_claim_publication(connection, claim, result, now=datetime.now(UTC))
            row = (
                connection.execute(
                    select(self.table).where(self.table.c.logical_key == logical)
                )
                .mappings()
                .first()
            )
            if row is not None:
                known = AcceptedPayload(
                    logical_key=row["logical_key"],
                    output=ResultRef(
                        row["result_id"], row["kind"], row["schema_version"]
                    ),
                    canonical_sha256=row["sha256"],
                    canonical_byte_count=int(row["byte_count"]),
                )
                append_or_verify(known, expected)
                # The acceptance index must never outlive its exact immutable
                # StageResult and canonical stored semantic bytes.
                stored = saved_result(connection, known.output, self.owner.registry)
                if (
                    stored.semantic_data_ref is None
                    or stored.semantic_data_ref.sha256 != known.canonical_sha256
                    or stored.semantic_data_ref.byte_count != known.canonical_byte_count
                ):
                    raise ImmutableRecordError("C0 accepted semantic reference missing")
                load_semantic_data(
                    connection,
                    stored.semantic_data_ref,
                    self.owner.semantic_registry,
                )
            else:
                append_semantic_data(connection, encoded)
                append_stage_result(connection, result, require_new=True)
                connection.execute(
                    self.table.insert().values(
                        logical_key=logical,
                        result_id=result.result_id,
                        kind=result.kind,
                        schema_version=result.schema_version,
                        sha256=encoded.reference.sha256,
                        byte_count=str(encoded.reference.byte_count),
                    )
                )
            require_claim_publication(connection, claim, result, now=datetime.now(UTC))
        return expected.output

    def count(self) -> int:
        """Read exact accepted row count from research-only scratch table."""
        with self.owner.engine.connect() as connection:
            return len(tuple(connection.execute(select(self.table.c.logical_key))))

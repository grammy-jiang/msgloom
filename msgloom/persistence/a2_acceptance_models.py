"""
Accepted-stage record and the pure append-or-verify decision.

``AcceptedStage`` is the independent proof saved for one logical key: the
result ref, canonical payload SHA and length, stage metadata SHA, lineage
digest, status/limitations digest and the original writer's claim proof.
The key itself is input-only (see ``StageIdentity.logical_key``).

``decide_append_or_verify`` is pure. A replay is equal when every integrity
field matches. The writer claim proof is not an integrity field: a new
attempt by another legitimate claim replays the same stage, and the first
writer proof stays stored. Any other difference, including a changed
status or limitation set under identical payload bytes, fails closed.

CANDIDATE/RESEARCH: this module only models records. It performs no I/O and
is not the production acceptance writer.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    Digest,
    Text,
    canonical_model_bytes,
    sha256_hex,
)
from msgloom.a2_kedro.contracts.identity import (
    ACCEPTED_STATUSES,
    AttemptProof,
    StageIdentity,
    check_stage_matches_identity,
    stage_metadata,
    status_limitations_digest,
)
from msgloom.a2_kedro.contracts.schema_ids import is_accepted_key, require_stage_schema
from msgloom.contracts import ResultRef, StageResult, TerminalStatus

#: Largest payload an accepted stage may claim; mirrors semantic-data bounds.
MAX_PAYLOAD_BYTES = 64 * 1024 * 1024
#: Largest stored record, so a row stays small.
MAX_RECORD_BYTES = 16 * 1024

#: Fields that must match exactly on replay, in reporting order.
INTEGRITY_FIELDS = (
    "output",
    "canonical_sha256",
    "canonical_byte_count",
    "semantic_data_id",
    "stage_metadata_sha256",
    "lineage_digest",
    "status",
    "limitations_digest",
)


class AcceptanceConflict(A2ContractError):
    """
    The same logical key arrived with different integrity fields.

    ``fields`` names the differing fields only. Values are never reported.
    """

    def __init__(self, fields: tuple[str, ...]) -> None:
        super().__init__("a2-accepted-result-integrity-conflict")
        self.fields = fields


class AcceptedStage(A2Model):
    """Durable proof for one accepted stage under one logical key."""

    logical_key: Text
    output: ResultRef
    canonical_sha256: Digest
    canonical_byte_count: Annotated[int, Field(ge=1, le=MAX_PAYLOAD_BYTES)]
    semantic_data_id: Text
    stage_metadata_sha256: Digest
    lineage_digest: Digest
    status: TerminalStatus
    limitations_digest: Digest
    writer: AttemptProof

    @model_validator(mode="after")
    def _closed(self) -> AcceptedStage:
        require_stage_schema(self.output.kind, self.output.schema_version)
        if not is_accepted_key(self.logical_key):
            raise A2ContractError("invalid logical key")
        if self.status not in ACCEPTED_STATUSES:
            raise A2ContractError("only complete or incomplete can be accepted")
        if self.output.result_id != self.logical_key:
            raise A2ContractError("output ref does not carry the logical key")
        return self

    def record_bytes(self) -> bytes:
        """Return bounded canonical bytes of the whole record."""
        return canonical_model_bytes(self, max_bytes=MAX_RECORD_BYTES)

    def record_sha256(self) -> str:
        """Return the SHA-256 of :meth:`record_bytes`."""
        return sha256_hex(self.record_bytes())


def accepted_stage_from_result(
    identity: StageIdentity, result: StageResult, writer: AttemptProof
) -> AcceptedStage:
    """
    Build the accepted record for ``result`` published for ``identity``.

    CANDIDATE/RESEARCH. Verifies the saved result against the frozen
    identity, then derives every digest from the result itself. The caller
    must still verify that stored bytes match ``semantic_data_ref``.
    """
    check_stage_matches_identity(identity, result)
    meta = stage_metadata(result)
    if meta.lineage_digest != identity.lineage():
        raise A2ContractError("result lineage differs from frozen identity")
    return AcceptedStage(
        logical_key=identity.logical_key(),
        output=identity.result_ref(),
        canonical_sha256=meta.semantic_sha256,
        canonical_byte_count=meta.semantic_byte_count,
        semantic_data_id=meta.semantic_data_id,
        stage_metadata_sha256=meta.digest(),
        lineage_digest=meta.lineage_digest,
        status=meta.status,
        limitations_digest=status_limitations_digest(result.status, result.limitations),
        writer=writer,
    )


def decide_append_or_verify(
    known: AcceptedStage | None, proposed: AcceptedStage
) -> Literal["insert", "replay"]:
    """
    Return ``insert`` or ``replay``; raise :exc:`AcceptanceConflict`.

    CANDIDATE/RESEARCH: proof-dependent, not production-ready.

    The database must still make the compare and the insert one atomic
    step. This function is only the decision rule.
    """
    if known is None:
        return "insert"
    if known.logical_key != proposed.logical_key:
        raise AcceptanceConflict(("logical_key",))
    differing = tuple(
        name
        for name in INTEGRITY_FIELDS
        if getattr(known, name) != getattr(proposed, name)
    )
    if differing:
        raise AcceptanceConflict(differing)
    return "replay"

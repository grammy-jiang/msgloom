"""
Provisional C0-00 header for every A2 v2 semantic-data payload.

Each payload starts with a ``StageHeader``. The header names the kind, the
schema version and the provisional wire profile. The decision record is
``docs/decisions/a2-v2-schema-ids.md``.

CANDIDATE/RESEARCH, PROVISIONAL: nothing here is frozen for production.
Body fields of most kinds are not decided. The header only fixes how a
reader tells kinds and versions apart before it decodes a body.

Failure handling: any unknown pair, profile or limit raises
:exc:`A2ContractError`. Messages never carry payload content.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from msgloom.a2_kedro.contracts.codec import (
    MAX_CANONICAL_BYTES,
    A2ContractError,
    A2Model,
    domain_sha256,
)
from msgloom.a2_kedro.contracts.schema_ids import RECEIPT_SCHEMA, STAGE_SCHEMAS

#: Provisional wire profile. A change here is an incompatible wire change.
WIRE_PROFILE = "a2-c0-provisional-1"

#: Kinds that carry a header but are not accepted-stage kinds.
EXTERNAL_SCHEMAS: dict[str, str] = {
    RECEIPT_SCHEMA[0]: RECEIPT_SCHEMA[1],
    "triage_input": "2",
}

#: Provisional per-payload ceilings. Kind-specific limits are unresolved.
LIMITS: dict[str, int] = {
    "max_canonical_bytes": MAX_CANONICAL_BYTES,
    "max_text_bytes": 2048,
    "max_depth": 32,
    "max_roots": 1024,
    "max_transitions": 1024,
}

HEADER_DOMAIN = "a2-payload-header@1"


def approved_pairs() -> dict[str, str]:
    """Return every ``kind -> version`` pair that may carry a header."""
    return {**STAGE_SCHEMAS, **EXTERNAL_SCHEMAS}


class StageHeader(A2Model):
    """Names the kind and version of one canonical A2 v2 payload."""

    kind: str = Field(min_length=1)
    version: str = Field(min_length=1)
    profile: Literal["a2-c0-provisional-1"] = WIRE_PROFILE

    @model_validator(mode="after")
    def _approved_pair(self) -> StageHeader:
        if approved_pairs().get(self.kind) != self.version:
            raise A2ContractError("header kind/version is not approved")
        return self

    def digest(self) -> str:
        """Return the domain-separated digest of the header alone."""
        return domain_sha256(HEADER_DOMAIN, self.model_dump(mode="json"))

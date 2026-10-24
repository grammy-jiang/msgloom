"""
Shared bases and checks for the A2 v2 result records.

Every top-level record has a required
:class:`~msgloom.a2_kedro.contracts.header.StageHeader`. Its
``(kind, version)`` pair comes from
:data:`~msgloom.a2_kedro.contracts.schema_ids.STAGE_SCHEMAS`. A reference to
another stage must be an accepted ``a2-accepted:`` key with the approved kind
and version. The bases hide input values in pydantic error text, so a
rejected payload never echoes an identifier or text.

CANDIDATE/RESEARCH, PROVISIONAL: names and limits are not frozen.
"""

from __future__ import annotations

from typing import Annotated, Any, ClassVar, Literal, Self

from pydantic import AfterValidator, ConfigDict, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    canonical_model_bytes,
    decode_model_bytes,
)
from msgloom.a2_kedro.contracts.header import StageHeader
from msgloom.a2_kedro.contracts.identity import ACCEPTED_STATUSES
from msgloom.a2_kedro.contracts.schema_ids import STAGE_SCHEMAS, is_accepted_key
from msgloom.contracts import Limitation, ResultRef, TerminalStatus

#: Provisional bound.
MAX_LIMITATIONS = 64

Effect = Literal["include", "exclude"]
COMPLETE = TerminalStatus.COMPLETE


def _accepted_status(status: TerminalStatus) -> TerminalStatus:
    if status not in ACCEPTED_STATUSES:
        raise A2ContractError("only complete or incomplete can be accepted")
    return status


def accepted_ref(ref: ResultRef, kind: str) -> ResultRef:
    """Return ``ref`` unless it is not an accepted ``kind`` result."""
    if (ref.kind, ref.schema_version) != (kind, STAGE_SCHEMAS[kind]):
        raise A2ContractError("reference has wrong kind or version")
    if not is_accepted_key(ref.result_id):
        raise A2ContractError("reference is not an accepted key")
    return ref


Accepted = Annotated[TerminalStatus, AfterValidator(_accepted_status)]
ParsedRef = Annotated[
    ResultRef, AfterValidator(lambda ref: accepted_ref(ref, "parsed_parts"))
]
NormalizedRef = Annotated[
    ResultRef, AfterValidator(lambda ref: accepted_ref(ref, "normalized_content"))
]
ZonesRef = Annotated[ResultRef, AfterValidator(lambda ref: accepted_ref(ref, "zones"))]
RelationsRef = Annotated[
    ResultRef, AfterValidator(lambda ref: accepted_ref(ref, "native_relations"))
]
PreparedRef = Annotated[
    ResultRef, AfterValidator(lambda ref: accepted_ref(ref, "prepared"))
]


def header_for(kind: str) -> StageHeader:
    """Return the header of the approved version of ``kind``."""
    return StageHeader(kind=kind, version=STAGE_SCHEMAS[kind])


class ResultPart(A2Model):
    """A2 base that also hides input values in validation errors."""

    model_config = ConfigDict(hide_input_in_errors=True)


class ResultModel(ResultPart):
    """Top-level record: a required header names its approved pair."""

    KIND: ClassVar[str] = ""
    header: StageHeader

    @model_validator(mode="after")
    def _own_header(self) -> Self:
        if (self.header.kind, self.header.version) != (
            self.KIND,
            STAGE_SCHEMAS[self.KIND],
        ):
            raise A2ContractError("header is not the approved pair")
        return self

    def encode(self) -> bytes:
        """Return the bounded canonical bytes of this record."""
        return canonical_model_bytes(self)

    @classmethod
    def decode(cls, data: bytes) -> Self:
        """Strictly decode canonical bytes; reject anything else."""
        return decode_model_bytes(cls, data)


def sorted_unique(keys: list[Any], label: str) -> None:
    if len(set(keys)) != len(keys):
        raise A2ContractError(f"duplicate {label}")
    if keys != sorted(keys):
        raise A2ContractError(f"{label} records are not sorted")


def limitation_keys(limitations: tuple[Limitation, ...]) -> list[Any]:
    return [(item.code, item.detail) for item in limitations]


def check_limitations(
    status: TerminalStatus,
    limitations: tuple[Limitation, ...],
    required: set[str] | None = None,
) -> None:
    if len(limitations) > MAX_LIMITATIONS:
        raise A2ContractError("limitation count is out of bounds")
    sorted_unique(limitation_keys(limitations), "limitation")
    codes = {item.code for item in limitations}
    if not (required or set()) <= codes:
        raise A2ContractError("a required limitation is missing")
    if (status is COMPLETE) == bool(limitations):
        raise A2ContractError("status conflicts with limitations")

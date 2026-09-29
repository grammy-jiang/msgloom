"""Closed opt-in semantic codecs owned by the A3 producer lane."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from msgloom.contracts import AttemptIdentity, ResultRef, SemanticDataRef
from msgloom.triage_input import InputPart, PartState, encode_part

TRIAGE_PART_STATE_KIND = "triage_part_state"
TRIAGE_PART_STATE_SCHEMA_VERSION = "1"
MAX_TRIAGE_PART_STATE_BYTES = 64 * 1024


class TriagePartState(BaseModel):
    """Immutable diagnostic for one exact part attempt."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    part_ref: SemanticDataRef
    attempt: AttemptIdentity
    state: PartState
    ai_response_ref: ResultRef | None = None
    failure_code: str | None = Field(default=None, max_length=64)


class InputPartCodec:
    """Persist exact canonical bytes returned by saved_part_payloads."""

    kind = "triage_input_part"
    schema_version = "1"
    python_type = InputPart
    max_bytes = 4 * 1024 * 1024

    def encode(self, value: object) -> bytes:
        """Revalidate and encode one exact saved input part."""
        if not isinstance(value, InputPart):
            raise TypeError("triage_input_part@1 data must be InputPart")
        try:
            payload = encode_part(value)
            checked = InputPart.model_validate_json(payload, strict=True)
        except (ValidationError, TypeError, ValueError):
            raise TypeError("triage_input_part@1 data failed validation") from None
        canonical = encode_part(checked)
        if len(canonical) > self.max_bytes:
            raise TypeError("triage_input_part@1 data exceeds codec size bound")
        return canonical

    def decode(self, payload: bytes) -> InputPart:
        """Decode only canonical bounded input-part bytes."""
        if not isinstance(payload, bytes) or len(payload) > self.max_bytes:
            raise ValueError("stored triage_input_part@1 data failed validation")
        try:
            value = InputPart.model_validate_json(payload, strict=True)
        except (ValidationError, ValueError):
            raise ValueError(
                "stored triage_input_part@1 data failed validation"
            ) from None
        if self.encode(value) != payload:
            raise ValueError("stored triage_input_part@1 data is not canonical")
        return value


class TriagePartStateCodec:
    """Encode bounded immutable per-part state without private exception text."""

    kind = TRIAGE_PART_STATE_KIND
    schema_version = TRIAGE_PART_STATE_SCHEMA_VERSION
    python_type = TriagePartState
    max_bytes = MAX_TRIAGE_PART_STATE_BYTES

    def encode(self, value: object) -> bytes:
        """Return canonical JSON for one revalidated part state."""
        if not isinstance(value, TriagePartState):
            raise TypeError("triage_part_state@1 data must be TriagePartState")
        try:
            data = value.model_dump(mode="json", round_trip=True, warnings="error")
            payload = json.dumps(
                data,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            checked = TriagePartState.model_validate_json(payload, strict=True)
        except (ValidationError, TypeError, ValueError):
            raise TypeError("triage_part_state@1 data failed validation") from None
        if checked != value or len(payload) > self.max_bytes:
            raise TypeError("triage_part_state@1 data failed validation")
        return payload

    def decode(self, payload: bytes) -> TriagePartState:
        """Decode canonical bounded state bytes."""
        if not isinstance(payload, bytes) or len(payload) > self.max_bytes:
            raise ValueError("stored triage_part_state@1 data failed validation")
        try:
            value = TriagePartState.model_validate_json(payload, strict=True)
        except (ValidationError, ValueError):
            raise ValueError(
                "stored triage_part_state@1 data failed validation"
            ) from None
        if self.encode(value) != payload:
            raise ValueError("stored triage_part_state@1 data is not canonical")
        return value


TRIAGE_PIPELINE_CODECS = (InputPartCodec(), TriagePartStateCodec())
TRIAGE_PIPELINE_RESULT_SCHEMAS = frozenset(
    (codec.kind, codec.schema_version) for codec in TRIAGE_PIPELINE_CODECS
)

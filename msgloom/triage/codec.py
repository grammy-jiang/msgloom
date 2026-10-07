"""Canonical codec for the reviewed triage semantic-data schema."""

from __future__ import annotations

import json

from pydantic import ValidationError
from pydantic_core import PydanticSerializationError

from .models import TriageData

TRIAGE_DATA_KIND = "triage"
TRIAGE_DATA_SCHEMA_VERSION = "1"
MAX_TRIAGE_DATA_BYTES = 4 * 1024 * 1024


class TriageDataCodec:
    """Encode and revalidate exactly triage@1 semantic data."""

    kind = TRIAGE_DATA_KIND
    schema_version = TRIAGE_DATA_SCHEMA_VERSION
    python_type = TriageData
    max_bytes = MAX_TRIAGE_DATA_BYTES

    def encode(self, value: object) -> bytes:
        """Return bounded canonical JSON after full nested revalidation."""
        if not isinstance(value, TriageData):
            raise TypeError("triage@1 data must be TriageData")
        try:
            data = value.model_dump(mode="json", round_trip=True, warnings="error")
            payload = json.dumps(
                data,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            if len(payload) > self.max_bytes:
                raise TypeError("triage@1 data exceeds the canonical size limit")
            TriageData.model_validate_json(payload, strict=True)
        except (
            PydanticSerializationError,
            ValidationError,
            TypeError,
            ValueError,
        ):
            raise TypeError("triage@1 data failed validation") from None
        return payload

    def decode(self, payload: bytes) -> TriageData:
        """Validate bounded canonical bytes without exposing source values."""
        if len(payload) > self.max_bytes:
            raise ValueError("stored triage@1 data exceeds the size limit")
        try:
            value = TriageData.model_validate_json(payload, strict=True)
        except (ValidationError, ValueError):
            raise ValueError("stored triage@1 data failed validation") from None
        if self.encode(value) != payload:
            raise ValueError("stored triage@1 data is not canonical")
        return value

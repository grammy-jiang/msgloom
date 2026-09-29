"""Canonical codec for the registered prepared semantic-data schema."""

from __future__ import annotations

import json

from pydantic import ValidationError

from msgloom.preparation.records import PreparedRecord

PREPARED_DATA_KIND = "prepared"
PREPARED_DATA_SCHEMA_VERSION = "1"
MAX_PREPARED_DATA_BYTES = 16 * 1024 * 1024


class PreparedDataCodec:
    """Encode and validate exactly prepared@1 semantic data."""

    kind = PREPARED_DATA_KIND
    schema_version = PREPARED_DATA_SCHEMA_VERSION
    python_type = PreparedRecord
    max_bytes = MAX_PREPARED_DATA_BYTES

    def encode(self, value: object) -> bytes:
        """Revalidate and return deterministic UTF-8 JSON for a prepared record."""
        if not isinstance(value, PreparedRecord):
            raise TypeError("prepared@1 data must be a PreparedRecord")
        try:
            data = value.model_dump(mode="json", round_trip=True, warnings="error")
            payload = json.dumps(
                data,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            PreparedRecord.model_validate_json(payload, strict=True)
        except (ValidationError, TypeError, ValueError):
            raise TypeError("prepared@1 data failed validation") from None
        return payload

    def decode(self, payload: bytes) -> PreparedRecord:
        """Validate canonical stored bytes back into an immutable record."""
        try:
            record = PreparedRecord.model_validate_json(payload, strict=True)
        except (ValidationError, ValueError):
            raise ValueError("stored prepared@1 data failed validation") from None
        if self.encode(record) != payload:
            raise ValueError("stored prepared@1 data is not canonical")
        return record

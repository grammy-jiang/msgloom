"""Canonical bounded codec for the pre-render report selection snapshot."""

from __future__ import annotations

import json

from pydantic import ValidationError
from pydantic_core import PydanticSerializationError

from .models import FrozenReportSelection

REPORT_SELECTION_KIND = "report_selection"
REPORT_SELECTION_SCHEMA_VERSION = "1"
MAX_REPORT_SELECTION_BYTES = 2 * 1024 * 1024


class ReportSelectionCodec:
    """Encode and strictly revalidate one immutable selection snapshot."""

    kind = REPORT_SELECTION_KIND
    schema_version = REPORT_SELECTION_SCHEMA_VERSION
    python_type = FrozenReportSelection
    max_bytes = MAX_REPORT_SELECTION_BYTES

    def encode(self, value: object) -> bytes:
        """Return canonical finite JSON for one frozen selection."""
        if not isinstance(value, FrozenReportSelection):
            raise TypeError("report_selection@1 data must be FrozenReportSelection")
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
                raise TypeError("report_selection@1 data exceeds its size limit")
            FrozenReportSelection.model_validate_json(payload, strict=True)
        except (PydanticSerializationError, ValidationError, TypeError, ValueError):
            raise TypeError("report_selection@1 data failed validation") from None
        return payload

    def decode(self, payload: bytes) -> FrozenReportSelection:
        """Decode canonical bytes without exposing saved business content."""
        if len(payload) > self.max_bytes:
            raise ValueError("stored report_selection@1 data exceeds its size limit")
        try:
            value = FrozenReportSelection.model_validate_json(payload, strict=True)
        except (ValidationError, ValueError):
            raise ValueError(
                "stored report_selection@1 data failed validation"
            ) from None
        if self.encode(value) != payload:
            raise ValueError("stored report_selection@1 data is not canonical")
        return value

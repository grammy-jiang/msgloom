"""Canonical codec declaration for manager composition of report@1."""

from __future__ import annotations

import json

from pydantic import ValidationError
from pydantic_core import PydanticSerializationError

from .build import ReportBuildError, validate_semantic_coverage
from .models import SavedReport
from .renderer import validate_rendered_coverage

REPORT_KIND = "report"
REPORT_SCHEMA_VERSION = "1"
MAX_REPORT_BYTES = 8 * 1024 * 1024


class ReportCodec:
    """Encode and revalidate the complete saved report product."""

    kind = REPORT_KIND
    schema_version = REPORT_SCHEMA_VERSION
    python_type = SavedReport
    max_bytes = MAX_REPORT_BYTES

    def encode(self, value: object) -> bytes:
        """Return canonical finite JSON after strict nested revalidation."""
        if not isinstance(value, SavedReport):
            raise TypeError("report@1 data must be SavedReport")
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
                raise TypeError("report@1 data exceeds the canonical size limit")
            checked = SavedReport.model_validate_json(payload, strict=True)
            _validate_report(checked)
        except (
            PydanticSerializationError,
            ValidationError,
            ReportBuildError,
            TypeError,
            ValueError,
        ):
            raise TypeError("report@1 data failed validation") from None
        return payload

    def decode(self, payload: bytes) -> SavedReport:
        """Validate canonical bytes without echoing report source values."""
        if len(payload) > self.max_bytes:
            raise ValueError("stored report@1 data exceeds the size limit")
        try:
            value = SavedReport.model_validate_json(payload, strict=True)
            _validate_report(value)
        except (ValidationError, ReportBuildError, ValueError):
            raise ValueError("stored report@1 data failed validation") from None
        if self.encode(value) != payload:
            raise ValueError("stored report@1 data is not canonical")
        return value


def _validate_report(value: SavedReport) -> None:
    """Recheck semantic and rendered coverage without changing saved bytes."""
    validate_semantic_coverage(value.topics, value.overview)
    validate_rendered_coverage(
        value.topics,
        value.parts,
        value.overview,
        value.pending_warnings,
        value.limitations,
        report_ref=value.report_ref,
    )

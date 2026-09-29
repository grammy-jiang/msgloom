"""Canonical bounded codecs for report delivery contracts."""

from __future__ import annotations

import json
from typing import Any, cast

from pydantic import TypeAdapter, ValidationError
from pydantic_core import PydanticSerializationError

from .models import (
    ReportReconciliationPlan,
    ReportSubmissionPlan,
    SubmissionAttempt,
    SubmissionReceipt,
    SubmissionRecord,
)

REPORT_SUBMISSION_KIND = "report_submission"
REPORT_SUBMISSION_SCHEMA_VERSION = "1"
MAX_SUBMISSION_BYTES = 16 * 1024 * 1024


class _ModelCodec[T]:
    """Strict canonical JSON codec for one closed Pydantic model."""

    max_bytes = MAX_SUBMISSION_BYTES

    def __init__(self, model_type: Any) -> None:
        self._adapter = cast(TypeAdapter[T], TypeAdapter(model_type))

    def encode(self, value: object) -> bytes:
        """Return canonical JSON after strict nested revalidation."""
        try:
            data = self._adapter.dump_python(
                cast(T, value), mode="json", warnings="error"
            )
            payload = json.dumps(
                data,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            if len(payload) > self.max_bytes:
                raise TypeError
            self._adapter.validate_json(payload, strict=True)
        except (PydanticSerializationError, ValidationError, TypeError, ValueError):
            raise TypeError("delivery data failed validation") from None
        return payload

    def decode(self, payload: bytes) -> T:
        """Decode exact canonical JSON without echoing private values."""
        if len(payload) > self.max_bytes:
            raise ValueError("stored delivery data exceeds the size limit")
        try:
            value = self._adapter.validate_json(payload, strict=True)
        except (ValidationError, TypeError, ValueError):
            raise ValueError("stored delivery data failed validation") from None
        if self.encode(value) != payload:
            raise ValueError("stored delivery data is not canonical")
        return value


class ReportSubmissionPlanCodec(_ModelCodec[ReportSubmissionPlan]):
    """Codec for one trusted finite submission plan."""

    def __init__(self) -> None:
        super().__init__(ReportSubmissionPlan)


class SubmissionAttemptCodec(_ModelCodec[SubmissionAttempt]):
    """Codec for exact persisted send bytes."""

    def __init__(self) -> None:
        super().__init__(SubmissionAttempt)


class SubmissionReceiptCodec(_ModelCodec[SubmissionReceipt]):
    """Codec for one definite provider receipt."""

    def __init__(self) -> None:
        super().__init__(SubmissionReceipt)


class ReportReconciliationPlanCodec(_ModelCodec[ReportReconciliationPlan]):
    """Codec for one explicit reconciliation request."""

    def __init__(self) -> None:
        super().__init__(ReportReconciliationPlan)


class ReportSubmissionCodec(_ModelCodec[SubmissionRecord]):
    """Persistence codec for all report submission version 1 records."""

    kind = REPORT_SUBMISSION_KIND
    schema_version = REPORT_SUBMISSION_SCHEMA_VERSION

    def __init__(self) -> None:
        super().__init__(SubmissionRecord)

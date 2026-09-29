"""Canonical codec for separately persisted deterministic triage rules."""

from __future__ import annotations

import json

from pydantic import ValidationError
from pydantic_core import PydanticSerializationError

from .rules import TriageRuleEvaluation

TRIAGE_RULES_KIND = "triage_rules"
TRIAGE_RULES_SCHEMA_VERSION = "1"
MAX_TRIAGE_RULES_BYTES = 4 * 1024 * 1024


class TriageRuleEvaluationCodec:
    """Encode and revalidate exactly triage_rules@1 data."""

    kind = TRIAGE_RULES_KIND
    schema_version = TRIAGE_RULES_SCHEMA_VERSION
    python_type = TriageRuleEvaluation
    max_bytes = MAX_TRIAGE_RULES_BYTES

    def encode(self, value: object) -> bytes:
        """Return bounded canonical JSON after complete nested revalidation."""
        if not isinstance(value, TriageRuleEvaluation):
            raise TypeError("triage_rules@1 data must be TriageRuleEvaluation")
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
                raise TypeError("triage_rules@1 data exceeds canonical size limit")
            TriageRuleEvaluation.model_validate_json(payload, strict=True)
        except (
            PydanticSerializationError,
            ValidationError,
            TypeError,
            ValueError,
        ):
            raise TypeError("triage_rules@1 data failed validation") from None
        return payload

    def decode(self, payload: bytes) -> TriageRuleEvaluation:
        """Decode canonical bytes without exposing source or rule values."""
        if len(payload) > self.max_bytes:
            raise ValueError("stored triage_rules@1 data exceeds size limit")
        try:
            value = TriageRuleEvaluation.model_validate_json(payload, strict=True)
        except (ValidationError, ValueError):
            raise ValueError("stored triage_rules@1 data failed validation") from None
        if self.encode(value) != payload:
            raise ValueError("stored triage_rules@1 data is not canonical")
        return value

"""Canonical bounded semantic codec for preparation_intake_workset@1."""

import json

from msgloom.preparation_pipeline.intake_models import (
    INTAKE_KIND,
    INTAKE_SCHEMA_VERSION,
    PreparationIntakeWorkset,
)


class PreparationIntakeWorksetCodec:
    """
    Validate immutable worksets without loading source evidence or selections.
    """

    kind = INTAKE_KIND
    schema_version = INTAKE_SCHEMA_VERSION
    max_bytes = 4 * 1024 * 1024

    def encode(self, value: object) -> bytes:
        """
        Revalidate even forged model instances and return canonical bytes.
        """
        if not isinstance(value, PreparationIntakeWorkset):
            raise TypeError("intake payload must be a PreparationIntakeWorkset")
        data = value.model_dump(mode="json", round_trip=True, warnings="error")
        # Preserve the exact pre-baseline encoding of incremental worksets.
        if value.baseline_approval is None:
            for key in ("baseline_approval", "baseline_sources", "baseline_selections"):
                if data[key]:
                    raise ValueError("baseline fields require explicit approval")
                del data[key]
        payload = json.dumps(
            data,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        if len(payload) > self.max_bytes:
            raise ValueError("intake workset exceeds codec byte bound")
        PreparationIntakeWorkset.model_validate_json(payload, strict=True)
        return payload

    def decode(self, payload: bytes) -> PreparationIntakeWorkset:
        """Reject noncanonical, oversized, or structurally invalid worksets."""
        if len(payload) > self.max_bytes:
            raise ValueError("intake workset exceeds codec byte bound")
        value = PreparationIntakeWorkset.model_validate_json(payload, strict=True)
        if self.encode(value) != payload:
            raise ValueError("intake workset encoding is not canonical")
        return value

"""Canonical bounded codec and version helpers for working context."""

from __future__ import annotations

import json
from hashlib import sha256

from pydantic import ValidationError
from pydantic_core import PydanticSerializationError

from msgloom.contracts import VersionRef
from msgloom.working_context.models import WorkingContextConfig, WorkingContextSnapshot

WORKING_CONTEXT_KIND = "working_context"
WORKING_CONTEXT_SCHEMA_VERSION = "1"
MAX_WORKING_CONTEXT_BYTES = 16 * 1024 * 1024


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def validate_configuration(config: WorkingContextConfig) -> WorkingContextConfig:
    """Revalidate a possibly validation-bypassed configuration opaquely."""
    if not isinstance(config, WorkingContextConfig):
        raise TypeError("working-context configuration is invalid")
    try:
        data = config.model_dump(mode="python", round_trip=True, warnings=False)
        return WorkingContextConfig.model_validate(data, strict=True)
    except (ValidationError, PydanticSerializationError, TypeError, ValueError):
        raise ValueError("working-context configuration is invalid") from None


def configuration_ref(config: WorkingContextConfig) -> VersionRef:
    """Return a deterministic version for the exact private configuration."""
    validated = validate_configuration(config)
    data = validated.model_dump(mode="json", round_trip=True, warnings="error")
    digest = sha256(_canonical(data)).hexdigest()
    return VersionRef("working-context-config", "configured-selection", digest)


def snapshot_digest(snapshot: WorkingContextSnapshot) -> str:
    """Hash every meaning-bearing snapshot field except the digest itself."""
    data = snapshot.model_dump(
        mode="json",
        round_trip=True,
        warnings="error",
        exclude={"snapshot_sha256"},
    )
    return sha256(_canonical(data)).hexdigest()


def _validate_snapshot(snapshot: object) -> WorkingContextSnapshot:
    if not isinstance(snapshot, WorkingContextSnapshot):
        raise TypeError("working_context@1 data must be a WorkingContextSnapshot")
    try:
        data = snapshot.model_dump(mode="json", round_trip=True, warnings="error")
        payload = _canonical(data)
        validated = WorkingContextSnapshot.model_validate_json(payload, strict=True)
    except (
        ValidationError,
        PydanticSerializationError,
        TypeError,
        ValueError,
    ):
        raise TypeError("working_context@1 data failed validation") from None
    if snapshot_digest(validated) != validated.snapshot_sha256:
        raise TypeError("working_context@1 snapshot digest is invalid")
    return validated


def snapshot_ref(snapshot: WorkingContextSnapshot) -> VersionRef:
    """Return the exact semantic snapshot reference used by later stages."""
    validated = _validate_snapshot(snapshot)
    return VersionRef(
        WORKING_CONTEXT_KIND,
        "snapshot",
        validated.snapshot_sha256,
    )


class WorkingContextCodec:
    """Encode and validate exactly working_context@1 semantic data."""

    kind = WORKING_CONTEXT_KIND
    schema_version = WORKING_CONTEXT_SCHEMA_VERSION
    python_type = WorkingContextSnapshot
    max_bytes = MAX_WORKING_CONTEXT_BYTES

    def encode(self, value: object) -> bytes:
        """Revalidate and return deterministic bounded UTF-8 JSON."""
        validated = _validate_snapshot(value)
        data = validated.model_dump(mode="json", round_trip=True, warnings="error")
        payload = _canonical(data)
        if len(payload) > self.max_bytes:
            raise TypeError("working_context@1 data exceeds codec size bound")
        return payload

    def decode(self, payload: bytes) -> WorkingContextSnapshot:
        """Validate canonical bounded stored bytes into an immutable snapshot."""
        if not isinstance(payload, bytes) or len(payload) > self.max_bytes:
            raise ValueError("stored working_context@1 data failed validation")
        try:
            snapshot = WorkingContextSnapshot.model_validate_json(payload, strict=True)
        except (ValidationError, ValueError):
            raise ValueError(
                "stored working_context@1 data failed validation"
            ) from None
        if snapshot_digest(snapshot) != snapshot.snapshot_sha256:
            raise ValueError("stored working_context@1 snapshot digest is invalid")
        try:
            canonical = self.encode(snapshot)
        except TypeError:
            raise ValueError(
                "stored working_context@1 data failed validation"
            ) from None
        if canonical != payload:
            raise ValueError("stored working_context@1 data is not canonical")
        return snapshot

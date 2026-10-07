"""Bounded semantic codec for UTF-8 bytes derived from captured A1 fields."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from msgloom.contracts import VersionRef
from msgloom.preparation.contracts import SourceLocation

DERIVED_BYTES_KIND = "derived_bytes"
DERIVED_BYTES_SCHEMA_VERSION = "1"
MAX_DERIVED_BYTES_CODEC_BYTES = 24 * 1024 * 1024


class DerivedByteArtifact(BaseModel):
    """Replayable UTF-8 parser input with exact component lineage."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    source: VersionRef
    selection: VersionRef
    component: str
    location: SourceLocation
    text: str
    sha256: str
    byte_count: int

    @field_validator("component")
    @classmethod
    def _component(cls, value: str) -> str:
        if not value.strip() or len(value) > 256:
            raise ValueError("derived component must be bounded non-empty text")
        return value

    @model_validator(mode="after")
    def _integrity(self) -> DerivedByteArtifact:
        content = self.text.encode("utf-8")
        if self.byte_count != len(content):
            raise ValueError("derived byte count does not match UTF-8 content")
        if self.sha256 != hashlib.sha256(content).hexdigest():
            raise ValueError("derived byte digest does not match UTF-8 content")
        return self

    @classmethod
    def capture(
        cls,
        source: VersionRef,
        selection: VersionRef,
        component: str,
        location: SourceLocation,
        text: str,
    ) -> DerivedByteArtifact:
        """Capture exact UTF-8 bytes without borrowing an envelope digest."""
        content = text.encode("utf-8")
        return cls(
            source=source,
            selection=selection,
            component=component,
            location=location,
            text=text,
            sha256=hashlib.sha256(content).hexdigest(),
            byte_count=len(content),
        )

    def stable_reference(self) -> str:
        """Return the execution-independent identity of the exact derived bytes."""
        return f"derived:sha256:{self.sha256}"

    def bytes(self) -> bytes:
        """Return the exact verified UTF-8 parser input."""
        return self.text.encode("utf-8")


class DerivedByteArtifactCodec:
    """Canonical bounded codec for derived_bytes@1."""

    kind = DERIVED_BYTES_KIND
    schema_version = DERIVED_BYTES_SCHEMA_VERSION
    max_bytes = MAX_DERIVED_BYTES_CODEC_BYTES

    def encode(self, value: object) -> bytes:
        """Revalidate and encode one canonical artifact."""
        if not isinstance(value, DerivedByteArtifact):
            raise TypeError("derived_bytes@1 data must be a DerivedByteArtifact")
        try:
            payload = json.dumps(
                value.model_dump(mode="json", round_trip=True, warnings="error"),
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            DerivedByteArtifact.model_validate_json(payload, strict=True)
        except (TypeError, ValueError):
            raise TypeError("derived_bytes@1 data failed validation") from None
        if len(payload) > self.max_bytes:
            raise ValueError("derived_bytes@1 data exceeds codec byte limit")
        return payload

    def decode(self, payload: bytes) -> DerivedByteArtifact:
        """Decode only canonical validated artifact bytes."""
        if len(payload) > self.max_bytes:
            raise ValueError("stored derived_bytes@1 data exceeds codec byte limit")
        try:
            value = DerivedByteArtifact.model_validate_json(payload, strict=True)
        except ValueError:
            raise ValueError("stored derived_bytes@1 data failed validation") from None
        if self.encode(value) != payload:
            raise ValueError("stored derived_bytes@1 data is not canonical")
        return value

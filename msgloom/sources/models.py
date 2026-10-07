"""Immutable contracts for reading exact saved A1 source versions."""

from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from msgloom.contracts import Limitation, VersionRef
from msgloom.preparation.contracts import SavedByteReference, SourceLocation
from msgloom.preparation.records import (
    NativeRelationship,
    PreparedParty,
    PreparedRecipient,
    PreparedSourceType,
)


class ContentKind(StrEnum):
    """Source-declared content representation before any parser runs."""

    PLAIN = "plain"
    HTML = "html"
    MIME = "mime"
    JSON = "json"
    BINARY = "binary"


class _FrozenModel(BaseModel):
    """Reject coercion, mutation, and undeclared adapter fields."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        arbitrary_types_allowed=True,
    )


class SourceReaderLimits(_FrozenModel):
    """Finite resource bounds applied to every public reader operation."""

    max_list_results: int = 200
    max_selected_records: int = 100
    max_evidence_bytes: int = 16 * 1024 * 1024
    max_snapshot_bytes: int = 32 * 1024 * 1024
    max_query_rows: int = 2_000
    max_blocking_workers: int = 4
    max_blocking_queue: int = 16
    query_timeout_seconds: float = 5.0

    @field_validator(
        "max_list_results",
        "max_selected_records",
        "max_evidence_bytes",
        "max_snapshot_bytes",
        "max_query_rows",
        "max_blocking_workers",
        "max_blocking_queue",
    )
    @classmethod
    def _positive_integer(cls, value: int) -> int:
        if isinstance(value, bool) or value < 1:
            raise ValueError("reader integer limits must be positive")
        return value

    @field_validator("query_timeout_seconds")
    @classmethod
    def _positive_timeout(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError("query timeout must be positive and finite")
        return value


class SavedSourceReaderConfig(_FrozenModel):
    """Explicit read-only catalog and evidence roots for one adapter."""

    catalog_path: Path
    evidence_roots: tuple[Path, ...]
    limits: SourceReaderLimits = SourceReaderLimits()

    @field_validator("catalog_path")
    @classmethod
    def _catalog_is_absolute(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("catalog_path must be absolute")
        return value

    @field_validator("evidence_roots")
    @classmethod
    def _roots_are_explicit(cls, value: tuple[Path, ...]) -> tuple[Path, ...]:
        if not value:
            raise ValueError("at least one evidence root is required")
        if any(not root.is_absolute() for root in value):
            raise ValueError("evidence roots must be absolute")
        if len(value) != len(set(value)):
            raise ValueError("evidence roots must be unique")
        return value


class CollectedBody(_FrozenModel):
    """One unparsed body field plus evidence for its containing source data.

    ``saved_bytes`` may identify the whole saved provider response containing
    ``content``; it does not claim that the referenced bytes equal the body
    field text.
    """

    kind: ContentKind
    content: str | None
    saved_bytes: SavedByteReference | None
    location: SourceLocation
    limitations: tuple[Limitation, ...] = ()


class CollectedAttachment(_FrozenModel):
    """One attachment metadata version and optional verified saved bytes."""

    reference: VersionRef
    name: str | None
    content_type: str | None
    content_kind: ContentKind
    byte_count: int | None
    inline: bool | None
    saved_bytes: SavedByteReference | None
    location: SourceLocation
    limitations: tuple[Limitation, ...] = ()

    @field_validator("byte_count")
    @classmethod
    def _nonnegative_size(cls, value: int | None) -> int | None:
        if value is not None and (isinstance(value, bool) or value < 0):
            raise ValueError("attachment byte_count must be non-negative")
        return value


class SourceMetadata(_FrozenModel):
    """Small provider-neutral metadata field retained as source data."""

    name: str
    value: str

    @field_validator("name", "value")
    @classmethod
    def _nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("metadata values must be non-empty")
        return value


class CollectedRecord(_FrozenModel):
    """Exact collected source version presented to later A2 preparation."""

    source: VersionRef
    source_scope: VersionRef
    source_type: PreparedSourceType
    semantic_identity: str
    observed_at: datetime
    source_time: datetime
    subject: str | None
    sender: PreparedParty | None
    author: PreparedParty | None
    recipients: tuple[PreparedRecipient, ...]
    source_content_kind: ContentKind
    source_bytes: SavedByteReference | None
    body: CollectedBody | None
    alternate_bodies: tuple[CollectedBody, ...]
    attachments: tuple[CollectedAttachment, ...]
    relationships: tuple[NativeRelationship, ...]
    metadata: tuple[SourceMetadata, ...]
    source_locations: tuple[SourceLocation, ...]
    limitations: tuple[Limitation, ...]

    @field_validator("observed_at", "source_time")
    @classmethod
    def _aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("collected record times must be timezone-aware")
        return value

    @model_validator(mode="after")
    def _one_scope_relationship(self) -> CollectedRecord:
        scopes = [
            relation
            for relation in self.relationships
            if relation.kind == "source_scope"
        ]
        if len(scopes) != 1 or scopes[0].target != self.source_scope:
            raise ValueError(
                "record must contain exactly one source_scope relationship"
            )
        return self


class CollectedSelection(_FrozenModel):
    """Immutable composite selection binding one record and all component refs."""

    source: VersionRef
    selection: VersionRef
    record: CollectedRecord

    @model_validator(mode="after")
    def _lineage_matches(self) -> CollectedSelection:
        if self.record.source != self.source:
            raise ValueError("selection source does not match collected record")
        if self.selection.kind != "collected_selection":
            raise ValueError("selection reference kind is invalid")
        return self


class SourceReaderError(RuntimeError):
    """Base class for privacy-safe saved-source adapter failures."""


class SourceReferenceError(SourceReaderError):
    """The requested source or byte reference is invalid or unavailable."""


class SourceEvidenceError(SourceReaderError):
    """Saved evidence failed containment, type, availability, or integrity checks."""


class SourceEvidenceLimitError(SourceEvidenceError):
    """Saved evidence exceeds the configured finite byte budget."""


@runtime_checkable
class CollectedSourceReader(Protocol):
    """Typed reader boundary implemented by A1 and synthetic test adapters."""

    async def list_versions(
        self,
        source_type: PreparedSourceType,
        *,
        source_id: str,
        limit: int,
    ) -> tuple[VersionRef, ...]:
        """Return a finite deterministic list of exact saved source versions."""
        ...

    async def read(self, source: VersionRef) -> CollectedRecord:
        """Read one source and return its currently captured component selection."""
        ...

    async def read_selection(self, source: VersionRef) -> CollectedSelection:
        """Capture an exact replayable composite selection."""
        ...

    async def read_many(
        self, sources: tuple[VersionRef, ...]
    ) -> tuple[CollectedRecord, ...]:
        """Read an explicitly selected finite set in caller order."""
        ...

    async def load_saved_bytes(self, reference: SavedByteReference) -> bytes:
        """Load and verify bytes named by an adapter-issued reference."""
        ...

    async def close(self) -> None:
        """Drain accepted work and reject new operations."""
        ...

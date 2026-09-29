"""Immutable contracts for explicitly selected working-context files."""

from __future__ import annotations

import math
import os
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import PurePath
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from msgloom.contracts import VersionRef


class _FrozenModel(BaseModel):
    """Reject coercion, unknown fields, and mutation at the capture boundary."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class StalePolicy(StrEnum):
    """Choose whether stale selected content remains available to consumers."""

    CAPTURE = "capture"
    OMIT = "omit"


class FileCaptureState(StrEnum):
    """Visible outcome for one explicitly selected file."""

    CAPTURED = "captured"
    EMPTY = "empty"
    MISSING = "missing"
    STALE = "stale"
    FUTURE_TIMESTAMP = "future_timestamp"
    UNREADABLE = "unreadable"
    CHANGED_DURING_READ = "changed_during_read"
    MALFORMED_ENCODING = "malformed_encoding"
    LIMIT_EXCEEDED = "limit_exceeded"
    PATH_UNSAFE = "path_unsafe"
    NOT_REGULAR = "not_regular"
    TIMED_OUT = "timed_out"


class WorkingContextLimitation(_FrozenModel):
    """Privacy-safe limitation without an opaque source path or exception."""

    code: str
    detail: str

    @field_validator("code", "detail")
    @classmethod
    def _nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("limitation text must be non-empty")
        return value


class MemoryFileSelection(_FrozenModel):
    """Name one exact local memory file selected by trusted configuration."""

    selection_id: str
    path: str

    @field_validator("selection_id")
    @classmethod
    def _selection_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("selection_id must be non-empty")
        return value

    @field_validator("path")
    @classmethod
    def _absolute_path(cls, value: str) -> str:
        if "\x00" in value or not os.path.isabs(value):
            raise ValueError("selected path must be an absolute local path")
        if ".." in PurePath(value).parts:
            raise ValueError("selected path must not contain traversal components")
        return value


class CaptureTimePolicy(_FrozenModel):
    """Declare the timezone basis used to interpret capture and file times."""

    timezone: str

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError:
            raise ValueError("timezone must be an installed IANA timezone") from None
        return value


class WorkingContextConfig(_FrozenModel):
    """Bound one immutable allowlist capture without filesystem discovery."""

    schema_version: Literal["1"] = "1"
    selected_files: tuple[MemoryFileSelection, ...]
    allowed_roots: tuple[str, ...]
    time_policy: CaptureTimePolicy
    stale_policy: StalePolicy
    stale_after_seconds: float
    future_tolerance_seconds: float = 1.0
    max_files: int
    max_bytes_per_file: int
    max_total_bytes: int
    max_capture_seconds: float

    @field_validator("allowed_roots")
    @classmethod
    def _roots(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if not values:
            raise ValueError("at least one allowed root is required")
        for value in values:
            if "\x00" in value or not os.path.isabs(value):
                raise ValueError("allowed roots must be absolute local paths")
            if ".." in PurePath(value).parts:
                raise ValueError("allowed roots must not contain traversal components")
        if len(values) != len(set(values)):
            raise ValueError("allowed roots must be unique")
        return values

    @field_validator("stale_after_seconds", "max_capture_seconds")
    @classmethod
    def _positive_seconds(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError("time bounds must be finite and positive")
        return value

    @field_validator("future_tolerance_seconds")
    @classmethod
    def _nonnegative_seconds(cls, value: float) -> float:
        if not math.isfinite(value) or value < 0:
            raise ValueError("future tolerance must be finite and non-negative")
        return value

    @field_validator("max_files", "max_bytes_per_file", "max_total_bytes")
    @classmethod
    def _positive_int(cls, value: int) -> int:
        if value < 1:
            raise ValueError("capture bounds must be positive")
        return value

    @model_validator(mode="after")
    def _selection_bounds(self) -> WorkingContextConfig:
        if len(self.selected_files) > self.max_files:
            raise ValueError("selected file count exceeds max_files")
        ids = tuple(item.selection_id for item in self.selected_files)
        paths = tuple(item.path for item in self.selected_files)
        if len(ids) != len(set(ids)):
            raise ValueError("selection identifiers must be unique")
        if len(paths) != len(set(paths)):
            raise ValueError("selected paths must be unique")
        normalized_roots = tuple(os.path.normpath(root) for root in self.allowed_roots)
        normalized_paths = tuple(os.path.normpath(path) for path in paths)
        if len(normalized_roots) != len(set(normalized_roots)):
            raise ValueError("allowed roots must be unique after normalization")
        if len(normalized_paths) != len(set(normalized_paths)):
            raise ValueError("selected paths must be unique after normalization")
        for path in paths:
            normalized = os.path.normpath(path)
            if not any(
                os.path.commonpath((normalized, root)) == root
                for root in normalized_roots
            ):
                raise ValueError("selected paths must be within an allowed root")
        return self


class CapturedMemoryFile(_FrozenModel):
    """Retain one selected file outcome and exact content when available."""

    selection_id: str
    path: str
    selection_ref: VersionRef
    state: FileCaptureState
    modified_at: datetime | None = None
    byte_count: int | None = None
    sha256: str | None = None
    content_ref: VersionRef | None = None
    text: str | None = None
    limitations: tuple[WorkingContextLimitation, ...] = ()

    @field_validator("modified_at")
    @classmethod
    def _aware_modified(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("modified_at must be timezone-aware")
        return value

    @field_validator("path")
    @classmethod
    def _captured_path(cls, value: str) -> str:
        if "\x00" in value or not os.path.isabs(value):
            raise ValueError("captured path must be an absolute local path")
        if ".." in PurePath(value).parts:
            raise ValueError("captured path must not contain traversal components")
        return value

    @model_validator(mode="after")
    def _content_integrity(self) -> CapturedMemoryFile:
        if self.selection_ref.kind != "working-context-selection":
            raise ValueError("selection_ref has an unexpected kind")
        if self.selection_ref.identity != self.selection_id:
            raise ValueError("selection_ref identity must match selection_id")
        if self.byte_count is not None and self.byte_count < 0:
            raise ValueError("byte_count must be non-negative")
        content_states = {
            FileCaptureState.CAPTURED,
            FileCaptureState.EMPTY,
            FileCaptureState.FUTURE_TIMESTAMP,
        }
        if self.text is None:
            if self.sha256 is not None or self.content_ref is not None:
                raise ValueError("unavailable content cannot declare a content digest")
            if self.state in content_states:
                raise ValueError("content state requires exact captured text")
            return self
        if self.modified_at is None:
            raise ValueError("captured text requires modification metadata")
        payload = self.text.encode("utf-8")
        digest = sha256(payload).hexdigest()
        if self.byte_count != len(payload) or self.sha256 != digest:
            raise ValueError("captured text integrity fields do not match content")
        if self.content_ref is None:
            raise ValueError("captured text requires a content reference")
        if (
            self.content_ref.kind != "working-context-content"
            or self.content_ref.identity != self.selection_id
            or self.content_ref.version != digest
        ):
            raise ValueError("content_ref does not match captured content")
        if self.state is FileCaptureState.EMPTY and self.text != "":
            raise ValueError("empty state requires exact empty content")
        if self.state is FileCaptureState.CAPTURED and self.text == "":
            raise ValueError("captured state requires non-empty content")
        content_allowed = content_states | {FileCaptureState.STALE}
        if self.state not in content_allowed:
            raise ValueError("unavailable file state cannot carry captured text")
        return self


class WorkingContextSnapshot(_FrozenModel):
    """Immutable bounded capture handed to persistence before semantic AI."""

    kind: Literal["working_context"] = "working_context"
    schema_version: Literal["1"] = "1"
    configuration_ref: VersionRef
    capture_time: datetime
    timezone: str
    files: tuple[CapturedMemoryFile, ...]
    snapshot_sha256: str

    @field_validator("capture_time")
    @classmethod
    def _aware_capture(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("capture_time must be timezone-aware")
        return value

    @field_validator("snapshot_sha256")
    @classmethod
    def _digest_format(cls, value: str) -> str:
        if len(value) != 64 or any(
            character not in "0123456789abcdef" for character in value
        ):
            raise ValueError("snapshot_sha256 must be lowercase hexadecimal")
        return value

    @model_validator(mode="after")
    def _snapshot_refs(self) -> WorkingContextSnapshot:
        if self.configuration_ref.kind != "working-context-config":
            raise ValueError("configuration_ref has an unexpected kind")
        if self.configuration_ref.identity != "configured-selection":
            raise ValueError("configuration_ref has an unexpected identity")
        config_version = self.configuration_ref.version
        if len(config_version) != 64 or any(
            character not in "0123456789abcdef" for character in config_version
        ):
            raise ValueError("configuration_ref version must be a SHA-256 digest")
        try:
            zone = ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            raise ValueError(
                "snapshot timezone must be an installed IANA timezone"
            ) from None
        if not _datetime_matches_zone(self.capture_time, zone):
            raise ValueError("capture_time does not match snapshot timezone")
        ids = tuple(item.selection_id for item in self.files)
        paths = tuple(item.path for item in self.files)
        normalized_paths = tuple(os.path.normpath(path) for path in paths)
        if len(ids) != len(set(ids)):
            raise ValueError("snapshot selection identifiers must be unique")
        if len(normalized_paths) != len(set(normalized_paths)):
            raise ValueError("snapshot selected paths must be unique")
        for item in self.files:
            if item.selection_ref.version != self.configuration_ref.version:
                raise ValueError("selection_ref is not bound to snapshot configuration")
            if item.modified_at is not None and not _datetime_matches_zone(
                item.modified_at,
                zone,
            ):
                raise ValueError(
                    "file modification time does not match snapshot timezone"
                )
        return self


def _datetime_matches_zone(value: datetime, zone: ZoneInfo) -> bool:
    """Return whether an aware instant is represented in the declared zone."""
    localized = value.astimezone(zone)
    return (
        localized.year,
        localized.month,
        localized.day,
        localized.hour,
        localized.minute,
        localized.second,
        localized.microsecond,
        localized.utcoffset(),
    ) == (
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second,
        value.microsecond,
        value.utcoffset(),
    )

"""Closed canonical codec for exact collected-selection snapshots."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from pydantic import ValidationError

from msgloom.contracts import VersionRef
from msgloom.sources.models import (
    CollectedRecord,
    CollectedSelection,
    SourceReferenceError,
)

COLLECTED_SELECTION_KIND = "collected_selection"
COLLECTED_SELECTION_SCHEMA_VERSION = "1"
MAX_COLLECTED_SELECTION_BYTES = 32 * 1024 * 1024


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _reject_duplicates(pairs: Iterable[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


def _reject_constant(_value: str) -> object:
    raise ValueError("non-finite JSON number")


def _validate_record(record: object) -> CollectedRecord:
    if not isinstance(record, CollectedRecord):
        raise TypeError("collected record has the wrong type")
    data = record.model_dump(mode="json", round_trip=True, warnings="error")
    payload = _canonical(data)
    return CollectedRecord.model_validate_json(payload, strict=True)


def _capture_validated(record: CollectedRecord) -> CollectedSelection:
    source_data = {
        "kind": record.source.kind,
        "identity": record.source.identity,
        "version": record.source.version,
    }
    record_data = record.model_dump(
        mode="json",
        round_trip=True,
        warnings="error",
    )
    selection = VersionRef(
        COLLECTED_SELECTION_KIND,
        hashlib.sha256(_canonical(source_data)).hexdigest(),
        hashlib.sha256(_canonical(record_data)).hexdigest(),
    )
    return CollectedSelection(
        source=record.source,
        selection=selection,
        record=record,
    )


def capture_selection(record: CollectedRecord) -> CollectedSelection:
    """Bind a fully revalidated record to a content-derived selection ref."""
    try:
        return _capture_validated(_validate_record(record))
    except (ValidationError, TypeError, ValueError):
        raise SourceReferenceError("collected record is invalid") from None


def _encode_exact(value: object) -> bytes:
    if not isinstance(value, CollectedSelection):
        raise TypeError("collected_selection@1 data must be a CollectedSelection")
    try:
        dumped = value.model_dump(
            mode="json",
            round_trip=True,
            warnings="error",
        )
        payload = _canonical(dumped)
        validated = CollectedSelection.model_validate_json(payload, strict=True)
        expected = _capture_validated(_validate_record(validated.record))
    except (ValidationError, TypeError, ValueError):
        raise TypeError("collected_selection@1 data failed validation") from None
    if expected.source != validated.source or expected.selection != validated.selection:
        raise TypeError("collected_selection@1 data failed validation")
    if len(payload) > MAX_COLLECTED_SELECTION_BYTES:
        raise ValueError("collected_selection@1 data exceeds codec byte limit")
    return payload


def _decode_exact(payload: bytes) -> CollectedSelection:
    if not isinstance(payload, bytes):
        raise TypeError("stored collected_selection@1 data must be bytes")
    if len(payload) > MAX_COLLECTED_SELECTION_BYTES:
        raise ValueError("stored collected_selection@1 data exceeds codec byte limit")
    try:
        text = payload.decode("utf-8")
        json.loads(
            text,
            object_pairs_hook=_reject_duplicates,
            parse_constant=_reject_constant,
        )
        selection = CollectedSelection.model_validate_json(payload, strict=True)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError, ValueError):
        raise ValueError(
            "stored collected_selection@1 data failed validation"
        ) from None
    try:
        canonical = _encode_exact(selection)
    except (TypeError, ValueError):
        raise ValueError(
            "stored collected_selection@1 data failed validation"
        ) from None
    if canonical != payload:
        raise ValueError("stored collected_selection@1 data is not canonical")
    return selection


class CollectedSelectionCodec:
    """Encode and validate exactly collected_selection@1 semantic data."""

    kind = COLLECTED_SELECTION_KIND
    schema_version = COLLECTED_SELECTION_SCHEMA_VERSION
    python_type = CollectedSelection
    max_bytes = MAX_COLLECTED_SELECTION_BYTES

    def encode(self, value: object) -> bytes:
        """Return canonical validated bytes within the fixed codec ceiling."""
        return _encode_exact(value)

    def decode(self, payload: bytes) -> CollectedSelection:
        """Decode only canonical validated bytes within the fixed ceiling."""
        return _decode_exact(payload)


def _configured_limit(max_bytes: int) -> int:
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise SourceReferenceError("selection snapshot byte limit is invalid")
    return min(max_bytes, MAX_COLLECTED_SELECTION_BYTES)


def encode_selection(selection: CollectedSelection, max_bytes: int) -> bytes:
    """Encode one exact selection under configured and fixed byte ceilings."""
    limit = _configured_limit(max_bytes)
    try:
        data = CollectedSelectionCodec().encode(selection)
    except (TypeError, ValueError):
        raise SourceReferenceError("selection snapshot is invalid") from None
    if len(data) > limit:
        raise SourceReferenceError("selection snapshot exceeds configured limit")
    return data


def decode_selection(data: bytes, max_bytes: int) -> CollectedSelection:
    """Decode one canonical selection without consulting mutable A1 state."""
    limit = _configured_limit(max_bytes)
    if not isinstance(data, bytes):
        raise SourceReferenceError("selection snapshot is invalid")
    if len(data) > limit:
        raise SourceReferenceError("selection snapshot exceeds configured limit")
    try:
        return CollectedSelectionCodec().decode(data)
    except (TypeError, ValueError):
        raise SourceReferenceError("selection snapshot is invalid") from None

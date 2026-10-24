"""
Explicit version dispatch between ``triage_input@1`` and ``@2`` (A3 owner).

The A3 handler and a future A3 runner call this module to decide which
reader owns a piece of data. It never converts one version into the other.

Two entry points:

* :func:`read_triage_input` reads saved ``triage_input`` bytes. A v1
  payload goes to the unchanged v1 codec. A v2 payload goes to the strict
  v2 codec, which verifies all digests. Anything else, and anything that
  claims both versions, is refused with a typed error.
* :func:`admit_upstream` classifies the saved upstream results the
  handler loaded (``prepared``, ``filter_result`` and ``group_result``).
  It returns ``None`` for v1 and for an empty family, so the handler
  continues exactly as before. For v2 it returns a :class:`V2Hold` that
  carries every upstream limitation forward.

No lossy projection: :func:`project_to_v1` always refuses. A v2 snapshot
binds ``@2`` references that a v1 snapshot cannot hold. Limitations, held
sources, coverage failures and incomplete state also have no v1 slot.
Refusing keeps all of that state visible to the caller.

Failure handling: every error is a subclass of :exc:`AdapterError` with a
fixed message. No error carries a value, a key or a chained cause. Errors
from the v2 codec keep their own typed classes and are not rewrapped.

CANDIDATE/RESEARCH, PROVISIONAL: the hold code and detail below, and the
absence of an executable v2 path, are not frozen. No A3 builder for
``triage_input@2`` parts exists yet (see
``docs/notes/a2-v2-a3-triage-input-v2.md``), so the handler stops an
upstream-v2 run as INCOMPLETE before any claim or provider call.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import ClassVar, Literal, NoReturn

from msgloom.a2_kedro.contracts.schema_ids import STAGE_SCHEMAS
from msgloom.contracts import (
    Limitation,
    ResultRef,
    StageResult,
    TerminalStatus,
)
from msgloom.triage_input.codec import MAX_TRIAGE_INPUT_BYTES, TriageInputCodec
from msgloom.triage_input.codec_v2 import TriageInputV2Codec
from msgloom.triage_input.models import TriageInputSnapshot as V1Snapshot
from msgloom.triage_input.models_v2 import PartState
from msgloom.triage_input.models_v2 import TriageInputSnapshot as V2Snapshot

#: Upstream result kinds whose version selects the reader.
FAMILY_KINDS: frozenset[str] = frozenset({"prepared", "filter_result", "group_result"})
_V1_PAIRS = frozenset((kind, "1") for kind in FAMILY_KINDS)
_V2_PAIRS = frozenset((kind, STAGE_SCHEMAS[kind]) for kind in FAMILY_KINDS)

#: Same bound as ``msgloom.triage_pipeline.limitations``.
MAX_CARRIED_LIMITATIONS = 64
#: PROVISIONAL hold limitation. Returned with every upstream-v2 stop.
HOLD_CODE = "triage_v2_reader_pending"
HOLD_DETAIL = "Upstream v2 results need an A3 v2 reader that does not exist yet"

Version = Literal["1", "2"]


class AdapterError(ValueError):
    """Base of all adapter errors. The message is fixed and has no value."""

    MESSAGE: ClassVar[str] = "triage version adapter refused the data"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class UnsupportedVersionError(AdapterError):
    MESSAGE = "triage data names a version that has no reader"


class MixedVersionsError(AdapterError):
    MESSAGE = "triage data mixes version 1 and version 2"


class InputTooLargeError(AdapterError):
    MESSAGE = "triage data exceeds the adapter size bound"


class InputUnreadableError(AdapterError):
    MESSAGE = "triage data cannot be read as a versioned JSON object"


class V1ReadError(AdapterError):
    MESSAGE = "triage_input@1 data was rejected by the v1 reader"


class UpstreamStateError(AdapterError):
    MESSAGE = "upstream v2 result state is inconsistent"


class LimitationOverflowError(AdapterError):
    MESSAGE = "upstream v2 limitations exceed the carry bound"


class LossyProjectionError(AdapterError):
    """Refuse a v2 to v1 projection. ``reasons`` uses a fixed vocabulary."""

    MESSAGE = "projection from triage_input@2 to triage_input@1 would lose state"

    def __init__(self, reasons: tuple[str, ...]) -> None:
        super().__init__()
        self.reasons = reasons


@dataclass(frozen=True, slots=True)
class TriageInputRead:
    """One verified snapshot and the version of the reader that produced it."""

    version: Version
    value: V1Snapshot | V2Snapshot


@dataclass(frozen=True, slots=True)
class V2Hold:
    """Handler stop for upstream v2 results. Nothing is dropped or run."""

    status: TerminalStatus
    limitations: tuple[Limitation, ...]


@dataclass(frozen=True, slots=True)
class V2Summary:
    """Handler-facing view of a verified v2 snapshot. All state is kept."""

    complete: bool
    limitations: tuple[Limitation, ...]
    held_sources: int
    coverage_failures: int
    pending_parts: int
    selected_sources: int


def _peek(payload: bytes) -> Version:
    if len(payload) > MAX_TRIAGE_INPUT_BYTES:
        raise InputTooLargeError
    value: object = None
    failed = False
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        failed = True
    if failed or not isinstance(value, dict):
        # Raised outside the handler so no input-bearing context is chained.
        raise InputUnreadableError
    has_header = "header" in value
    has_version = "schema_version" in value
    if has_header and has_version:
        raise MixedVersionsError
    if has_header:
        return "2"
    if has_version and value["schema_version"] == "1":
        return "1"
    raise UnsupportedVersionError


def read_triage_input(payload: bytes) -> TriageInputRead:
    """Return the verified snapshot for ``payload`` from its own reader.

    v1 bytes use the unchanged v1 codec. v2 bytes use the v2 codec, which
    raises its own typed errors (for example a digest mismatch).
    """
    version = _peek(payload)
    if version == "2":
        return TriageInputRead("2", TriageInputV2Codec().decode(payload))
    failed = False
    snapshot: V1Snapshot | None = None
    try:
        snapshot = TriageInputCodec().decode(payload)
    except (TypeError, ValueError):
        failed = True
    if failed or snapshot is None:
        raise V1ReadError
    return TriageInputRead("1", snapshot)


def summarize_v2(snapshot: V2Snapshot) -> V2Summary:
    """Return every incomplete-state fact of a verified v2 snapshot."""
    return V2Summary(
        complete=snapshot.complete,
        limitations=snapshot.limitations,
        held_sources=len(snapshot.held),
        coverage_failures=len(snapshot.failures),
        pending_parts=sum(p.state is PartState.PENDING for p in snapshot.parts),
        selected_sources=len(snapshot.binding.roles),
    )


def project_to_v1(snapshot: V2Snapshot) -> NoReturn:
    """Refuse. No v2 snapshot has a lossless v1 form."""
    reasons = ["v2-references"]
    if snapshot.limitations:
        reasons.append("limitations")
    if snapshot.held:
        reasons.append("held-sources")
    if snapshot.failures:
        reasons.append("coverage-failures")
    if not snapshot.complete:
        reasons.append("incomplete-state")
    if any(role.role.value == "baseline-context" for role in snapshot.binding.roles):
        reasons.append("baseline-context-role")
    raise LossyProjectionError(tuple(reasons))


def classify_upstream(refs: Iterable[ResultRef]) -> Version | None:
    """Return the one version of the family refs, or ``None`` if none.

    A family ref with an unknown version (for example ``prepared@3``) raises
    :exc:`UnsupportedVersionError`, also next to v1 refs. The handler fails
    closed at preflight. Before C0-17c it did not check the version.
    """
    pairs = {(r.kind, r.schema_version) for r in refs if r.kind in FAMILY_KINDS}
    if not pairs:
        return None
    if pairs <= _V1_PAIRS:
        return "1"
    if pairs <= _V2_PAIRS:
        return "2"
    if pairs & _V1_PAIRS and pairs & _V2_PAIRS and pairs <= _V1_PAIRS | _V2_PAIRS:
        raise MixedVersionsError
    raise UnsupportedVersionError


def _check_v2_result(reference: ResultRef, saved: StageResult) -> None:
    data = saved.semantic_data_ref
    if data is None or (data.kind, data.schema_version) != (
        reference.kind,
        reference.schema_version,
    ):
        raise UpstreamStateError
    if saved.failures or (saved.status is TerminalStatus.COMPLETE) == bool(
        saved.limitations
    ):
        raise UpstreamStateError


def admit_upstream(
    loaded: Iterable[tuple[ResultRef, StageResult]],
) -> V2Hold | None:
    """Return ``None`` for v1 upstream, or a hold that keeps v2 limitations.

    Mixed or unknown versions raise a typed error. A v2 result whose
    status and limitations disagree raises :exc:`UpstreamStateError`.
    """
    items = tuple(loaded)
    if classify_upstream(ref for ref, _ in items) != "2":
        return None
    carried: set[Limitation] = set()
    for reference, saved in items:
        if reference.kind not in FAMILY_KINDS:
            continue
        _check_v2_result(reference, saved)
        carried.update(saved.limitations)
    if len(carried) >= MAX_CARRIED_LIMITATIONS:
        raise LimitationOverflowError
    ordered = sorted(carried, key=lambda item: (item.code, item.detail))
    return V2Hold(
        TerminalStatus.INCOMPLETE,
        (*ordered, Limitation(HOLD_CODE, HOLD_DETAIL)),
    )

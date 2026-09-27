"""Provider-independent synchronization cursor contracts.

These types describe durable provider cursor proposals only. Scrapy JOBDIR
continues to own execution resume, while resource spiders and extensions own
completion rules and checkpoint promotion.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

type CursorKind = Literal["delta_link", "history_id"]
type BaseRevision = int | None

_SCOPE_DOMAIN = b"msgloom-sync-scope-v1\0"
_CURSOR_KINDS = frozenset({"delta_link", "history_id"})


def _identifier(value: object, *, name: str) -> str:
    """Validate a non-empty identifier without normalizing it."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value:
        raise ValueError(f"{name} must not be empty")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")
    return value


@dataclass(frozen=True, slots=True)
class SyncScope:
    """Versioned, canonical scope descriptor for one synchronization stream."""

    scheme: str
    parameters: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        """Validate and sort parameter names while preserving values exactly."""
        _identifier(self.scheme, name="scheme")
        if not isinstance(self.parameters, tuple):
            raise TypeError("parameters must be a tuple of string pairs")

        seen: set[str] = set()
        normalized: list[tuple[str, str]] = []
        for pair in self.parameters:
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise TypeError("each scope parameter must be a (name, value) tuple")
            name, value = pair
            name = _identifier(name, name="parameter name")
            if not isinstance(value, str):
                raise TypeError("scope parameter values must be strings")
            if name in seen:
                raise ValueError(f"duplicate scope parameter: {name}")
            seen.add(name)
            normalized.append((name, value))

        object.__setattr__(self, "parameters", tuple(sorted(normalized)))

    @property
    def canonical_json(self) -> str:
        """Return stable ASCII JSON retained beside the derived scope ID."""
        return json.dumps(
            {
                "scheme": self.scheme,
                "parameters": dict(self.parameters),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )

    @property
    def scope_id(self) -> str:
        """Return the domain-separated SHA-256 identity of this scope."""
        material = _SCOPE_DOMAIN + self.canonical_json.encode("ascii")
        return hashlib.sha256(material).hexdigest()


def canonical_scope(
    scheme: str,
    parameters: Mapping[str, str],
) -> SyncScope:
    """Copy a mapping into an immutable canonical synchronization scope."""
    if not isinstance(parameters, Mapping):
        raise TypeError("parameters must be a mapping")
    return SyncScope(scheme=scheme, parameters=tuple(parameters.items()))


@dataclass(frozen=True, slots=True)
class SyncStreamKey:
    """Logical source, provider resource, and exact synchronization scope."""

    source_id: str
    provider: str
    resource: str
    scope: SyncScope

    def __post_init__(self) -> None:
        """Validate names without consulting provider-account identity state."""
        _identifier(self.source_id, name="source_id")
        _identifier(self.provider, name="provider")
        _identifier(self.resource, name="resource")
        if not isinstance(self.scope, SyncScope):
            raise TypeError("scope must be a SyncScope")


@dataclass(frozen=True, slots=True)
class SyncCursor:
    """Opaque provider cursor; pagination tokens are not synchronization cursors."""

    kind: CursorKind
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        """Validate the cursor kind while preserving the value byte-for-byte."""
        if not isinstance(self.kind, str):
            raise TypeError("cursor kind must be a string")
        if self.kind not in _CURSOR_KINDS:
            raise ValueError(f"unsupported cursor kind: {self.kind!r}")
        if not isinstance(self.value, str):
            raise TypeError("cursor value must be a string")
        if not self.value:
            raise ValueError("cursor value must not be empty")


@dataclass(slots=True)
class SyncCursorCandidateItem:
    """Uncommitted cursor proposal from one resource synchronization round."""

    stream: SyncStreamKey
    run_id: str
    cursor: SyncCursor
    base_revision: BaseRevision
    observed_at: str
    evidence_id: str | None

    def __post_init__(self) -> None:
        """Validate fields without implying that promotion is authorized."""
        validate_cursor_candidate(self)


def validate_cursor_candidate(item: SyncCursorCandidateItem) -> None:
    """Validate one cursor proposal independently of resource completion rules."""
    if not isinstance(item.stream, SyncStreamKey):
        raise TypeError("stream must be a SyncStreamKey")
    _identifier(item.run_id, name="run_id")
    if not isinstance(item.cursor, SyncCursor):
        raise TypeError("cursor must be a SyncCursor")

    revision = item.base_revision
    if revision is not None:
        if isinstance(revision, bool) or not isinstance(revision, int):
            raise TypeError("base_revision must be a positive integer or None")
        if revision <= 0:
            raise ValueError("base_revision must be positive")

    if not isinstance(item.observed_at, str):
        raise TypeError("observed_at must be a string")
    if not item.observed_at:
        raise ValueError("observed_at must not be empty")

    if item.evidence_id is not None:
        if not isinstance(item.evidence_id, str):
            raise TypeError("evidence_id must be a string or None")
        if not item.evidence_id:
            raise ValueError("evidence_id must not be empty")

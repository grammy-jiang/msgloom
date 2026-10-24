"""
Closed A2 v2 result-schema and semantic-data registries (C0-21a).

CANDIDATE/RESEARCH. Nothing here is wired into ``msgloom.cli.composition``.
The old ``ResultSchemaRegistry.phase1()`` and
``SemanticDataRegistry.phase1()`` factories, their codecs and the Phase 1
stores are not read, changed or shadowed by this module. Composition
wiring is a later controlled edit.

Allowlist
---------
The only accepted ``kind@version`` pairs are the pairs returned by
:func:`msgloom.a2_kedro.contracts.header.approved_pairs` when this module
is imported. That is every accepted stage in ``STAGE_SCHEMAS`` plus the
header-carrying external kinds. The set is a ``frozenset`` named
:data:`A2_APPROVED_PAIRS`. Each factory call re-reads ``approved_pairs()``
and refuses to build if the live source differs from the frozen set, so a
schema id change cannot silently widen the registry.

Fail-closed rules
-----------------
* A malformed ``kind@version`` string, an unknown kind, an unknown version
  and a wrong kind/version combination raise :exc:`A2RegistryError`.
* A duplicate registration raises :exc:`A2RegistryError`.
* A registry that is missing an approved pair, or holds an extra pair,
  cannot be constructed.
* Old Phase 1 kinds at new versions, historical ``@1`` stage pairs and
  next-version pairs such as ``prepared@999`` are all refused.

Sealing
-------
``ResultSchemaRegistry`` is a frozen dataclass. Its ``with_schema`` method
returns an extended copy, so the A2 subclass overrides it to refuse.
``SemanticDataRegistry`` has no extension method, but it keeps a plain
instance dictionary. The A2 subclass blocks attribute writes and deletes
after construction. Every factory call returns a new, independent object.

Error messages carry a short reason only. They never echo caller input.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, NoReturn

from pydantic import BaseModel

from msgloom.a2_kedro.contracts.codec import (
    MAX_CANONICAL_BYTES,
    A2ContractError,
    canonical_json_bytes,
    decode_canonical_json,
)
from msgloom.a2_kedro.contracts.header import StageHeader, approved_pairs
from msgloom.contracts import ResultSchemaRegistry
from msgloom.persistence.errors import UnknownSemanticDataSchemaError
from msgloom.persistence.semantic import SemanticDataRegistry

#: Closed set of approved ``(kind, version)`` pairs, frozen at import time.
A2_APPROVED_PAIRS: frozenset[tuple[str, str]] = frozenset(approved_pairs().items())

_KINDS = frozenset(kind for kind, _ in A2_APPROVED_PAIRS)
# ASCII only, no whitespace, no newline: ``fullmatch`` with explicit classes.
_PAIR_TEXT = re.compile(r"([a-z][a-z0-9_]{0,63})@([0-9]{1,3})", re.ASCII)


class A2RegistryError(A2ContractError):
    """A registry request is outside the closed A2 v2 allowlist."""


class A2UnknownSchemaError(A2RegistryError, UnknownSemanticDataSchemaError):
    """A semantic lookup named a pair that is not in the allowlist."""


def _live_pairs() -> frozenset[tuple[str, str]]:
    live = frozenset(approved_pairs().items())
    if live != A2_APPROVED_PAIRS:
        raise A2RegistryError("approved schema pairs changed after import")
    return live


def require_a2_pair(kind: object, version: object) -> tuple[str, str]:
    """Return ``(kind, version)`` or raise :exc:`A2RegistryError`."""
    if type(kind) is not str or type(version) is not str:
        raise A2RegistryError("kind and version must be exact text")
    if kind not in _KINDS:
        raise A2RegistryError("unknown kind")
    if (kind, version) not in A2_APPROVED_PAIRS:
        raise A2RegistryError("kind/version pairing is not approved")
    return kind, version


def parse_a2_pair(text: object) -> tuple[str, str]:
    """Parse a strict ``kind@version`` string and check the allowlist."""
    if type(text) is not str:
        raise A2RegistryError("pair text must be exact text")
    match = _PAIR_TEXT.fullmatch(text)
    if match is None:
        raise A2RegistryError("pair text is malformed")
    return require_a2_pair(match.group(1), match.group(2))


def _checked_pairs(pairs: Iterable[tuple[str, str]]) -> frozenset[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    for kind, version in pairs:
        pair = require_a2_pair(kind, version)
        if pair in seen:
            raise A2RegistryError("duplicate registration")
        seen.add(pair)
    if seen != _live_pairs():
        raise A2RegistryError("registry must hold exactly the approved pairs")
    return frozenset(seen)


@dataclass(frozen=True, slots=True)
class A2ResultSchemaRegistry(ResultSchemaRegistry):
    """
    Sealed result-schema registry holding exactly the approved A2 pairs.

    Every approved pair requires semantic data, because every A2 v2 payload
    carries a header and a canonical body. Direct construction with any
    other pair set raises :exc:`A2RegistryError`.
    """

    def __post_init__(self) -> None:
        ResultSchemaRegistry.__post_init__(self)
        if self.schemas != _live_pairs():
            raise A2RegistryError("registry must hold exactly the approved pairs")
        if self.semantic_data_required != self.schemas:
            raise A2RegistryError("every approved pair requires semantic data")

    @classmethod
    def from_pairs(cls, pairs: Iterable[tuple[str, str]]) -> A2ResultSchemaRegistry:
        """Build from explicit pairs; refuse duplicates, unknowns, gaps."""
        checked = _checked_pairs(pairs)
        return cls(checked, checked)

    def with_schema(
        self,
        kind: str,
        schema_version: str,
        *,
        semantic_data_required: bool = False,
    ) -> NoReturn:
        """Refuse: the A2 allowlist is closed and cannot be extended."""
        raise A2RegistryError("the A2 registry cannot be extended")

    def require_supported(self, kind: str, schema_version: str) -> None:
        """Raise :exc:`A2RegistryError` unless the exact pair is approved."""
        require_a2_pair(kind, schema_version)


@dataclass(frozen=True, slots=True)
class A2HeaderCodec:
    """
    Envelope codec for one approved pair.

    It accepts a pydantic model or a plain mapping that starts with a
    ``header`` naming this exact pair. It writes bounded canonical JSON and
    reads it back as a mapping. Body validation stays in the typed contract
    models of ``msgloom.a2_kedro.contracts``. This codec fixes only the
    envelope, so a payload cannot be stored under another pair.
    """

    kind: str
    schema_version: str
    max_bytes: int = MAX_CANONICAL_BYTES

    def __post_init__(self) -> None:
        require_a2_pair(self.kind, self.schema_version)

    def _check_header(self, value: object) -> None:
        header = value.get("header") if isinstance(value, dict) else None
        if not isinstance(header, dict):
            raise A2RegistryError("payload has no header")
        try:
            pair = StageHeader.model_validate(header)
        except ValueError:
            raise A2RegistryError("header is not an approved header") from None
        if (pair.kind, pair.version) != (self.kind, self.schema_version):
            raise A2RegistryError("header does not match the registered pair")

    def encode(self, value: object) -> bytes:
        """Encode a header-carrying model or mapping canonically."""
        if isinstance(value, BaseModel):
            data: Any = value.model_dump(mode="json")
        elif isinstance(value, dict):
            data = value
        else:
            raise TypeError("A2 semantic data must be a model or a mapping")
        self._check_header(data)
        return canonical_json_bytes(data, max_bytes=self.max_bytes)

    def decode(self, payload: bytes) -> object:
        """Decode canonical bytes and check the header pair."""
        try:
            value = decode_canonical_json(payload, max_bytes=self.max_bytes)
        except RecursionError:
            raise A2RegistryError("payload nesting is too deep") from None
        self._check_header(value)
        return value


class A2SemanticDataRegistry(SemanticDataRegistry):
    """
    Sealed semantic-data registry holding exactly the approved A2 codecs.

    Attribute writes and deletes raise after construction.
    """

    def __init__(self, codecs: tuple[A2HeaderCodec, ...]) -> None:
        keys = tuple((codec.kind, codec.schema_version) for codec in codecs)
        _checked_pairs(keys)
        object.__setattr__(self, "_codecs", tuple(codecs))

    def __setattr__(self, name: str, value: object) -> None:
        raise A2RegistryError("the A2 registry is sealed")

    def __delattr__(self, name: str) -> None:
        raise A2RegistryError("the A2 registry is sealed")

    @property
    def pairs(self) -> frozenset[tuple[str, str]]:
        """Return the registered ``(kind, version)`` pairs."""
        return frozenset((c.kind, c.schema_version) for c in self._codecs)

    def _codec(self, kind: str, schema_version: str) -> Any:
        try:
            require_a2_pair(kind, schema_version)
        except A2RegistryError as exc:
            raise A2UnknownSchemaError(str(exc)) from None
        return super()._codec(kind, schema_version)


def build_a2_result_schema_registry() -> A2ResultSchemaRegistry:
    """Return a new sealed registry of the approved A2 result schemas."""
    return A2ResultSchemaRegistry.from_pairs(_live_pairs())


def build_a2_semantic_registry() -> A2SemanticDataRegistry:
    """Return a new sealed registry with one header codec per approved pair."""
    return A2SemanticDataRegistry(
        tuple(A2HeaderCodec(kind, version) for kind, version in sorted(_live_pairs()))
    )

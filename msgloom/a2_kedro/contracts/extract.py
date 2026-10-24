"""
``extracted_components@1``: saved components of one selected occurrence.

An :class:`ExtractedComponents` record lists the primary body, alternate
bodies, attachments and embedded items found for one occurrence. Each
entry keeps a reference to saved bytes, a SHA-256 digest of those bytes and
a closed status. The record never holds component bytes.

Status rules:

* ``present`` and ``partial`` need a reference and a digest.
* ``missing`` carries neither. A missing component stays visible; it is
  never dropped silently.
* ``unsupported`` carries a reference and a digest together, or neither.

Ordering: ``components`` keeps the producer order. The validator does
not sort it. The canonical bytes, and so every digest, depend on that
order. Two orders of the same entries are two different records. Only the
one ``primary`` entry and unique component IDs are required. A later task
may add a sort rule; until then the producer must use a stable order.

Metadata is a bounded, sorted list of text pairs. Keys and values are exact
``str`` and hold no control character (no NUL, tab, newline, DEL, C1,
U+2028 or U+2029). Metadata is identifier-like data, not body text.
``encode_metadata`` and ``decode_metadata`` are the metadata codec. Decode is strict: size limits,
canonical form, text values only and no duplicate keys.

Failure handling: any violation raises :exc:`A2ContractError` (or a pydantic
``ValueError`` subclass at model construction). Messages carry no content.

CANDIDATE/RESEARCH, PROVISIONAL: field names, limits and the ``reference``
text form are not frozen. See ``docs/notes/a2-v2-contract-c0-03.md``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    Digest,
    Text,
    canonical_json_bytes,
    canonical_model_bytes,
    decode_canonical_json,
    decode_model_bytes,
    has_control_character,
)
from msgloom.a2_kedro.contracts.header import StageHeader

KIND = "extracted_components"
VERSION = "1"

#: Provisional bounds. They are wire decisions, not production limits.
MAX_COMPONENTS = 256
MAX_METADATA_ITEMS = 32
MAX_METADATA_KEY_BYTES = 64
MAX_METADATA_VALUE_BYTES = 256
MAX_METADATA_BYTES = 4096

ComponentRole = Literal["primary", "alternate", "attachment", "embedded"]
ComponentStatus = Literal["present", "missing", "partial", "unsupported"]
MetadataPairs = tuple[tuple[str, str], ...]


def _check_pairs(pairs: MetadataPairs) -> None:
    if len(pairs) > MAX_METADATA_ITEMS:
        raise A2ContractError("metadata has too many items")
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        raise A2ContractError("duplicate metadata key")
    if keys != sorted(keys):
        raise A2ContractError("metadata keys are not sorted")
    for key, value in pairs:
        if type(key) is not str or type(value) is not str:
            raise A2ContractError("metadata must hold exact text only")
        if has_control_character(key) or has_control_character(value):
            raise A2ContractError("metadata holds a control character")
        if not key or len(key.encode()) > MAX_METADATA_KEY_BYTES:
            raise A2ContractError("metadata key size is out of bounds")
        if len(value.encode()) > MAX_METADATA_VALUE_BYTES:
            raise A2ContractError("metadata value is too large")


def encode_metadata(metadata: dict[str, str]) -> bytes:
    """Return bounded canonical bytes for a metadata mapping."""
    for key, value in metadata.items():
        if type(key) is not str or type(value) is not str:
            raise A2ContractError("metadata must hold text only")
    _check_pairs(tuple(sorted(metadata.items())))
    return canonical_json_bytes(metadata, max_bytes=MAX_METADATA_BYTES)


def decode_metadata(data: bytes) -> MetadataPairs:
    """Strictly decode canonical metadata bytes into sorted pairs."""
    value = decode_canonical_json(data, max_bytes=MAX_METADATA_BYTES)
    if not isinstance(value, dict):
        raise A2ContractError("metadata is not an object")
    if not all(isinstance(item, str) for item in value.values()):
        raise A2ContractError("metadata must hold text only")
    pairs = tuple(sorted(value.items()))
    _check_pairs(pairs)
    return pairs


class ComponentEntry(A2Model):
    """One component: role, status, saved-bytes reference and digest."""

    component_id: Text
    role: ComponentRole
    status: ComponentStatus
    reference: Text | None = None
    sha256: Digest | None = None
    metadata: MetadataPairs = ()

    @field_validator("metadata")
    @classmethod
    def _bounded_metadata(cls, value: MetadataPairs) -> MetadataPairs:
        _check_pairs(value)
        if len(canonical_json_bytes(dict(value))) > MAX_METADATA_BYTES:
            raise A2ContractError("metadata exceeds byte bound")
        return value

    @model_validator(mode="after")
    def _status_rules(self) -> ComponentEntry:
        has = (self.reference is not None, self.sha256 is not None)
        if self.status == "missing":
            if any(has):
                raise A2ContractError("missing component carries bytes proof")
            return self
        if self.status == "unsupported":
            if has[0] != has[1]:
                raise A2ContractError("reference and digest go together")
            return self
        if not all(has):
            raise A2ContractError("component needs reference and digest")
        return self


class ExtractedComponents(A2Model):
    """All components of one occurrence; exactly one primary entry."""

    header: StageHeader = Field(
        default_factory=lambda: StageHeader(kind=KIND, version=VERSION)
    )
    components: tuple[ComponentEntry, ...]

    @model_validator(mode="after")
    def _closed(self) -> ExtractedComponents:
        if (self.header.kind, self.header.version) != (KIND, VERSION):
            raise A2ContractError("header is not extracted_components@1")
        if not 1 <= len(self.components) <= MAX_COMPONENTS:
            raise A2ContractError("component count is out of bounds")
        ids = [item.component_id for item in self.components]
        if len(set(ids)) != len(ids):
            raise A2ContractError("duplicate component id")
        primaries = [c for c in self.components if c.role == "primary"]
        if len(primaries) != 1:
            raise A2ContractError("exactly one primary component is required")
        return self

    def encode(self) -> bytes:
        """Return the bounded canonical bytes of this record."""
        return canonical_model_bytes(self)

    @classmethod
    def decode(cls, data: bytes) -> ExtractedComponents:
        """Strictly decode canonical bytes; reject anything else."""
        return decode_model_bytes(cls, data)

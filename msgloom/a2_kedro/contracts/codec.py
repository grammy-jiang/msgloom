"""
Bounded canonical serialization and digests for A2 v2 contracts.

All A2 v2 identities hash one canonical byte form: UTF-8 JSON with sorted
keys, no insignificant whitespace, no ``NaN`` and no duplicate keys. Every
encode and decode path enforces an explicit byte bound before it returns
bytes, so an oversized payload fails closed instead of being hashed.

CANDIDATE/RESEARCH: the wire formats here are provisional until C0-00
freezes them.
"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

#: Default upper bound for one canonical contract payload.
MAX_CANONICAL_BYTES = 4 * 1024 * 1024
#: Upper bound for any single identifier-like text field.
MAX_TEXT_BYTES = 2048
#: Nesting bound; deeper values are rejected before encoding.
MAX_DEPTH = 32

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Text = Annotated[str, Field(min_length=1)]


class A2ContractError(ValueError):
    """
    A producer proof is unsafe, oversized or incomplete.

    Messages never contain source payload, addresses or subjects.
    """


class A2Model(BaseModel):
    """Frozen, strict base: no coercion, no unknown fields, bounded text."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    @field_validator("*")
    @classmethod
    def _bounded_text(cls, value: Any) -> Any:
        if isinstance(value, str) and len(value.encode()) > MAX_TEXT_BYTES:
            raise ValueError("text exceeds identifier bound")
        return value


def _check_shape(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise A2ContractError("canonical value nests too deeply")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise A2ContractError("canonical object key is not text")
            _check_shape(item, depth + 1)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _check_shape(item, depth + 1)
        return
    if value is None or isinstance(value, (str, bool, int)):
        return
    raise A2ContractError("value is not canonical JSON data")


def canonical_json_bytes(value: Any, *, max_bytes: int = MAX_CANONICAL_BYTES) -> bytes:
    """
    Return bounded canonical bytes for plain JSON data.

    Floats are rejected on purpose because their text form is not stable
    across producers. Raise :exc:`A2ContractError` for a non-JSON value,
    excess nesting or output above ``max_bytes``.
    """
    _check_shape(value)
    data = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(data) > max_bytes:
        raise A2ContractError("canonical payload exceeds byte bound")
    return data


def canonical_model_bytes(
    model: BaseModel, *, max_bytes: int = MAX_CANONICAL_BYTES
) -> bytes:
    """Return bounded canonical bytes for a validated model."""
    return canonical_json_bytes(model.model_dump(mode="json"), max_bytes=max_bytes)


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise A2ContractError("duplicate key in canonical payload")
    return dict(pairs)


def _reject_constant(_name: str) -> Any:
    raise A2ContractError("non-finite number in canonical payload")


def decode_canonical_json(data: bytes, *, max_bytes: int = MAX_CANONICAL_BYTES) -> Any:
    """
    Decode bytes only when they are exactly the canonical encoding.

    A payload with different key order, extra whitespace, duplicate keys or
    escaped-but-equal text is rejected. Strict round trip keeps one byte
    form for each digest.
    """
    if len(data) > max_bytes:
        raise A2ContractError("canonical payload exceeds byte bound")
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_reject_duplicates,
            parse_constant=_reject_constant,
            parse_float=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
        raise A2ContractError("payload is not valid JSON") from error
    if canonical_json_bytes(value, max_bytes=max_bytes) != data:
        raise A2ContractError("payload is not in canonical form")
    return value


def sha256_hex(data: bytes) -> str:
    """Return the lowercase SHA-256 hex digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


def domain_sha256(domain: str, value: Any) -> str:
    """
    Hash ``value`` under a domain separator and a NUL delimiter.

    ``domain`` names the identity, for example
    ``"a2-stage-accepted-input@1"``. Two identities never share a digest
    for the same value because their domains differ.
    """
    if not domain or "\x00" in domain:
        raise A2ContractError("invalid digest domain")
    return sha256_hex(domain.encode() + b"\x00" + canonical_json_bytes(value))


def decode_model_bytes[ModelT: BaseModel](
    model: type[ModelT], data: bytes, *, max_bytes: int = MAX_CANONICAL_BYTES
) -> ModelT:
    """
    Decode canonical bytes into ``model`` with strict validation.

    The bytes must be the exact canonical form. Validation errors surface
    as :exc:`A2ContractError`, so a caller handles one failure type. The
    message never carries payload content.
    """
    decode_canonical_json(data, max_bytes=max_bytes)
    try:
        return model.model_validate_json(data, strict=True)
    except ValueError as error:
        raise A2ContractError("payload does not match the contract") from error

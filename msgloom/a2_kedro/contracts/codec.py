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

import dataclasses
import hashlib
import json
import unicodedata
from enum import Enum
from typing import Annotated, Any, get_args

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
)

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


#: Unicode categories refused in contract text. ``Cc`` covers C0, DEL and
#: C1 (including U+0085). ``Zl`` and ``Zp`` cover U+2028 and U+2029.
_FORBIDDEN_CATEGORIES = frozenset({"Cc", "Zl", "Zp"})


def has_control_character(text: str) -> bool:
    """
    Return whether ``text`` holds a control or line-separator character.

    The check covers NUL, tab, newline, DEL, the C1 range, U+2028 and
    U+2029.
    """
    return any(unicodedata.category(char) in _FORBIDDEN_CATEGORIES for char in text)


def _enum_annotation(annotation: Any) -> bool:
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return True
    return any(_enum_annotation(arg) for arg in get_args(annotation))


def _walk_text(value: Any, *, allow_enum: bool) -> None:
    if isinstance(value, str):
        if type(value) is not str and not (allow_enum and isinstance(value, Enum)):
            raise ValueError("text must be an exact str")
        return
    if isinstance(value, (tuple, list)):
        for item in value:
            _walk_text(item, allow_enum=allow_enum)
        return
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        for field in dataclasses.fields(value):
            _walk_text(getattr(value, field.name), allow_enum=False)
        return
    if isinstance(value, BaseModel):
        # A nested model, foreign or not, is walked by field value. Its
        # enum members are accepted because annotations are not known here.
        for name in type(value).model_fields:
            _walk_text(getattr(value, name), allow_enum=True)


def _arrays_to_tuples(value: Any) -> Any:
    # A before validator hands strict mode a parsed JSON list, which strict
    # mode refuses for a tuple field. Convert only in JSON mode.
    if isinstance(value, list):
        return tuple(_arrays_to_tuples(item) for item in value)
    return value


def _walk_clean(value: Any) -> None:
    if isinstance(value, Enum):
        return
    if isinstance(value, str):
        if has_control_character(value):
            raise ValueError("text holds a control character")
        return
    if isinstance(value, (tuple, list)):
        for item in value:
            _walk_clean(item)
        return
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        for field in dataclasses.fields(value):
            _walk_clean(getattr(value, field.name))
        return
    if isinstance(value, BaseModel):
        for name in type(value).model_fields:
            _walk_clean(getattr(value, name))


class A2Model(BaseModel):
    """
    Frozen, strict base for every A2 v2 contract model.

    Text rules, applied to every field including text nested in tuples
    and in dataclass values such as ``ResultRef``. Text inside a nested
    pydantic model (for example ``ReleaseEntryRef`` or the foreign
    ``IntakeTransition``) is walked by field value as well:

    * A value must be an exact ``str``. A ``str`` subclass is rejected
      before validation, because pydantic strict mode accepts it. A
      ``StrEnum`` member is accepted only for a field typed as that enum.
    * A text value holds no control character: no C0 or C1 control, no
      NUL, newline, tab, DEL, U+0085, U+2028 or U+2029. No A2 v2 field
      is body text today. A future body-text field must opt in by name
      in its own decision record; it must not relax this base.
    * JSON arrays become tuples before validation, in JSON mode only.
      Python-mode callers must pass tuples.
    * A text value is at most ``MAX_TEXT_BYTES`` bytes in UTF-8.
    """

    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", hide_input_in_errors=True
    )

    @field_validator("*", mode="before")
    @classmethod
    def _exact_text(cls, value: Any, info: ValidationInfo) -> Any:
        field = cls.model_fields.get(info.field_name or "")
        allow_enum = field is not None and _enum_annotation(field.annotation)
        _walk_text(value, allow_enum=allow_enum)
        if info.mode == "json":
            return _arrays_to_tuples(value)
        return value

    @field_validator("*")
    @classmethod
    def _bounded_text(cls, value: Any) -> Any:
        if isinstance(value, str) and len(value.encode()) > MAX_TEXT_BYTES:
            raise ValueError("text exceeds identifier bound")
        _walk_clean(value)
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

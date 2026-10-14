"""Bounded parsing for saved Teams catalog scalar JSON fields."""

import json
from typing import Any

from msgloom.sources.models import SourceReferenceError


def _reject_constant(_value: str) -> object:
    raise ValueError("non-finite JSON number")


def _json_value(value: object, label: str) -> object:
    if value is None or not isinstance(value, str):
        return value
    try:
        return json.loads(value, parse_constant=_reject_constant)
    except (json.JSONDecodeError, ValueError):
        raise SourceReferenceError(f"Teams {label} JSON is invalid") from None


def _optional_dict(value: object, label: str) -> dict[str, Any] | None:
    parsed = _json_value(value, label)
    if parsed is not None and not isinstance(parsed, dict):
        raise SourceReferenceError(f"Teams {label} JSON is invalid")
    return parsed


def _canonical(value: object) -> str:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError):
        raise SourceReferenceError("Teams saved component is invalid") from None

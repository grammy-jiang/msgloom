"""Small strict-validation helpers shared by configuration composition."""

from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, TypeAdapter


def _json_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", round_trip=True)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _json_value(getattr(value, field.name))
            for field in fields(value)
        }
    return value


def canonical_json(value: object) -> str:
    """Return deterministic JSON for already bounded configuration values."""
    return json.dumps(
        _json_value(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def strict_model[T: BaseModel](model: type[T], value: object) -> T:
    """Validate one domain Pydantic model through its strict JSON boundary."""
    return model.model_validate_json(canonical_json(value), strict=True)


def strict_dataclass[T](model: type[T], value: object) -> T:
    """Validate one domain dataclass through Pydantic's strict JSON boundary."""
    return TypeAdapter(model).validate_json(canonical_json(value), strict=True)

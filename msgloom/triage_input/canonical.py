"""Canonical JSON and stable identity helpers for triage input."""

from __future__ import annotations

import json
from hashlib import sha256

from pydantic import BaseModel


def canonical_json(value: BaseModel | object) -> bytes:
    """Encode JSON-compatible input deterministically as UTF-8."""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", round_trip=True, warnings="error")
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: BaseModel | object) -> str:
    """Return a stable SHA-256 digest over canonical JSON."""
    return sha256(canonical_json(value)).hexdigest()

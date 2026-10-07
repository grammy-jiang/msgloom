"""Trusted application policy for schemas, models, credentials, and runtime."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from msgloom.contracts import VersionRef

_ALLOWED_CREDENTIALS = frozenset(
    {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_REGION",
        "AWS_DEFAULT_REGION",
        "AWS_BEARER_TOKEN_BEDROCK",
        "CLAUDE_CODE_USE_BEDROCK",
    }
)


def _freeze_json(value: object) -> object:
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON schema object keys must be strings")
            frozen[key] = _freeze_json(item)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("JSON schema contains a non-finite number")
        return value
    raise TypeError("JSON schema contains a non-JSON value")


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class TrustedPolicy:
    """Closed trusted mappings used to construct an SDK child."""

    schemas: Mapping[VersionRef, Mapping[str, object]]
    models: Mapping[VersionRef, str]

    def __post_init__(self) -> None:
        if not isinstance(self.schemas, Mapping) or not isinstance(
            self.models, Mapping
        ):
            raise TypeError("trusted schemas and models must be mappings")
        if not self.schemas or not self.models:
            raise ValueError("trusted AI policy requires schemas and models")
        frozen_schemas: dict[VersionRef, object] = {}
        for reference, schema in self.schemas.items():
            if not isinstance(reference, VersionRef):
                raise TypeError("trusted schema keys must be VersionRef values")
            if not isinstance(schema, Mapping) or not schema:
                raise ValueError("trusted output schemas must be non-empty mappings")
            frozen_schemas[reference] = _freeze_json(schema)
        object.__setattr__(
            self,
            "schemas",
            MappingProxyType(frozen_schemas),
        )
        for reference in self.models:
            if not isinstance(reference, VersionRef):
                raise TypeError("trusted model keys must be VersionRef values")
        object.__setattr__(self, "models", MappingProxyType(dict(self.models)))
        for model in self.models.values():
            if not isinstance(model, str):
                raise TypeError("trusted model identifiers must be strings")
            if not model or not model.strip():
                raise ValueError("trusted model identifiers must be non-empty")

    def schema_for(self, reference: VersionRef) -> dict[str, object] | None:
        """Return a detached JSON-compatible copy of one trusted schema."""
        frozen = self.schemas.get(reference)
        if frozen is None:
            return None
        thawed = _thaw_json(frozen)
        if not isinstance(thawed, dict):
            raise TypeError("trusted schema storage is invalid")
        return thawed


@dataclass(frozen=True, slots=True)
class RuntimeIsolation:
    """Trusted executable and read-only roots for the isolated SDK worker."""

    python_executable: Path
    bubblewrap_executable: Path
    runtime_roots: tuple[Path, ...]
    cli_path: Path
    credentials: Mapping[str, str]
    storage_root: Path
    termination_grace_seconds: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.runtime_roots, tuple):
            raise TypeError("runtime roots must be a tuple")
        paths = (
            self.python_executable,
            self.bubblewrap_executable,
            self.cli_path,
            self.storage_root,
            *self.runtime_roots,
        )
        if any(not isinstance(path, Path) for path in paths):
            raise TypeError("runtime isolation paths must be Path values")
        if any(not path.is_absolute() for path in paths):
            raise ValueError("runtime isolation paths must be absolute")
        grace = self.termination_grace_seconds
        if isinstance(grace, bool) or not isinstance(grace, (int, float)):
            raise TypeError("termination grace must be a number")
        if not math.isfinite(grace) or grace <= 0:
            raise ValueError("termination grace must be finite and positive")
        if not isinstance(self.credentials, Mapping):
            raise TypeError("credential environment must be a mapping")
        if set(self.credentials) - _ALLOWED_CREDENTIALS:
            raise ValueError("credential environment contains unapproved keys")
        if any(
            not isinstance(value, str) or not value
            for value in self.credentials.values()
        ):
            raise ValueError("credential values must be non-empty strings")
        object.__setattr__(
            self, "credentials", MappingProxyType(dict(self.credentials))
        )

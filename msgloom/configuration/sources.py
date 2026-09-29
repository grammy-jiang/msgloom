"""Explicit context-bound pydantic-settings file sources."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

_CONFIG_FILE: ContextVar[Path | None] = ContextVar("operator_config_file", default=None)
_SECRET_DIR: ContextVar[Path | None] = ContextVar("operator_secret_dir", default=None)


@contextmanager
def bound_sources(config_file: Path, mounted_secret_dir: Path | None) -> Iterator[None]:
    """Bind explicit file sources for one synchronous settings construction."""
    config_token = _CONFIG_FILE.set(config_file)
    secret_token = _SECRET_DIR.set(mounted_secret_dir)
    try:
        yield
    finally:
        _SECRET_DIR.reset(secret_token)
        _CONFIG_FILE.reset(config_token)


def config_file() -> Path:
    """Return the explicit TOML path for the active settings construction."""
    value = _CONFIG_FILE.get()
    if value is None:
        raise RuntimeError("operator TOML source is not bound")
    return value


def secret_dir() -> Path | None:
    """Return the explicit mounted settings directory, when configured."""
    return _SECRET_DIR.get()

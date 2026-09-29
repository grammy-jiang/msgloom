"""Explicit context-bound pydantic-settings mapping sources."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

_CONFIG_VALUES: ContextVar[Mapping[str, object] | None] = ContextVar(
    "operator_config_values", default=None
)
_MOUNTED_VALUES: ContextVar[Mapping[str, object] | None] = ContextVar(
    "operator_mounted_values", default=None
)


class MappingSettingsSource(PydanticBaseSettingsSource):
    """Expose already bounded source values through the public settings API."""

    def __init__(
        self, settings_cls: type[BaseSettings], values: Mapping[str, object]
    ) -> None:
        super().__init__(settings_cls)
        self._values = dict(values)

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        """Return one preloaded value without doing filesystem I/O."""
        del field
        return self._values.get(field_name), field_name, False

    def __call__(self) -> dict[str, Any]:
        """Return a detached mapping for pydantic-settings composition."""
        return dict(self._values)


@contextmanager
def bound_sources(
    config_values: Mapping[str, object],
    mounted_values: Mapping[str, object],
) -> Iterator[None]:
    """Bind safely preloaded file-source values for one settings construction."""
    config_token = _CONFIG_VALUES.set(config_values)
    mounted_token = _MOUNTED_VALUES.set(mounted_values)
    try:
        yield
    finally:
        _MOUNTED_VALUES.reset(mounted_token)
        _CONFIG_VALUES.reset(config_token)


def config_values() -> Mapping[str, object]:
    """Return the explicit TOML values for the active settings construction."""
    value = _CONFIG_VALUES.get()
    if value is None:
        raise RuntimeError("operator TOML source is not bound")
    return value


def mounted_values() -> Mapping[str, object]:
    """Return safely read mounted settings for the active construction."""
    value = _MOUNTED_VALUES.get()
    if value is None:
        raise RuntimeError("operator mounted settings source is not bound")
    return value

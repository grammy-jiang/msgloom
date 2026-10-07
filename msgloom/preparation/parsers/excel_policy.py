"""Closed request settings for spreadsheet hidden-content handling."""

from __future__ import annotations

from dataclasses import dataclass

from msgloom.preparation.contracts import ParserRequest

_TRUE = {"1", "true", "yes"}
_FALSE = {"0", "false", "no"}
_SUPPORTED_PROFILES = {"excel-primary-v1"}
_SETTING_KEYS = {
    "include_hidden_sheets",
    "include_hidden_rows",
    "include_hidden_columns",
}


@dataclass(frozen=True, slots=True)
class HiddenPolicy:
    """Deterministic hidden-content policy derived from request settings."""

    include_sheets: bool = False
    include_rows: bool = False
    include_columns: bool = False


def _setting_bool(value: str, key: str) -> bool:
    normalized = value.strip().lower()
    if normalized in _TRUE:
        return True
    if normalized in _FALSE:
        return False
    raise ValueError(f"{key} must be an explicit boolean string")


def hidden_policy(request: ParserRequest) -> HiddenPolicy:
    """Return the explicit policy; all hidden content defaults to excluded."""
    if request.config.profile not in _SUPPORTED_PROFILES:
        raise ValueError("unsupported Excel parser profile")
    settings = dict(request.config.settings)
    unknown = set(settings) - _SETTING_KEYS
    if unknown:
        raise ValueError(
            "unsupported Excel parser settings: " + ", ".join(sorted(unknown))
        )
    return HiddenPolicy(
        include_sheets=_setting_bool(
            settings.get("include_hidden_sheets", "false"),
            "include_hidden_sheets",
        ),
        include_rows=_setting_bool(
            settings.get("include_hidden_rows", "false"),
            "include_hidden_rows",
        ),
        include_columns=_setting_bool(
            settings.get("include_hidden_columns", "false"),
            "include_hidden_columns",
        ),
    )

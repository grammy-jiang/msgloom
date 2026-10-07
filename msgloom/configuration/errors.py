"""Privacy-safe operator-configuration failures."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class ConfigurationErrorCode(StrEnum):
    """Stable error classifications that never embed private input."""

    INVALID_INPUT = "invalid_input"
    UNKNOWN_INPUT = "unknown_input"
    INPUT_TOO_LARGE = "input_too_large"
    CONFIG_UNAVAILABLE = "config_unavailable"
    SECRET_UNAVAILABLE = "secret_unavailable"
    SECRET_NOT_APPROVED = "secret_not_approved"


_MESSAGES = {
    ConfigurationErrorCode.INVALID_INPUT: "operator configuration is invalid",
    ConfigurationErrorCode.UNKNOWN_INPUT: "operator configuration contains an unknown input",
    ConfigurationErrorCode.INPUT_TOO_LARGE: "operator configuration input exceeds its bound",
    ConfigurationErrorCode.CONFIG_UNAVAILABLE: "requested capability is unavailable",
    ConfigurationErrorCode.SECRET_UNAVAILABLE: "credential material is unavailable",
    ConfigurationErrorCode.SECRET_NOT_APPROVED: "credential reference is not approved",
}

_REASON_MESSAGES = {
    "bound_exceeded": "configuration input exceeds its bound",
    "config_missing": "configuration file does not exist",
    "duplicate_rule_id": "rule identifiers must be unique",
    "duplicate_sequence": "rule sequences must be unique",
    "invalid_file": "configuration file is invalid",
    "invalid_range": "configuration range is invalid",
    "invalid_regex": "pattern is not valid msgloom-regex-v1 syntax",
    "invalid_toml": "invalid TOML syntax",
    "invalid_utf8": "configuration file is not valid UTF-8",
    "unknown_field": "unknown configuration field",
    "unsupported_profile": "unsupported acquisition profile",
}

_SAFE_FIELD_PATH = re.compile("[A-Za-z0-9_" + re.escape(".<>[]-") + "]{1,512}")
_SAFE_REASON = re.compile(r"[a-z0-9_]{1,96}")
_SAFE_SUGGESTION = re.compile(r"[A-Za-z0-9_.:-]{1,128}")
_SAFE_SOURCES = frozenset({"builtin", "default", "explicit"})


@dataclass(frozen=True, slots=True)
class ConfigurationDiagnostic:
    """Bounded diagnostic metadata that is safe to render to an operator."""

    source_label: str | None = None
    field_path: str | None = None
    line: int | None = None
    column: int | None = None
    reason_code: str | None = None
    suggestion: str | None = None

    def __post_init__(self) -> None:
        if self.source_label is not None and self.source_label not in _SAFE_SOURCES:
            raise ValueError("unsafe configuration diagnostic source label")
        if (
            self.field_path is not None
            and _SAFE_FIELD_PATH.fullmatch(self.field_path) is None
        ):
            raise ValueError("unsafe configuration diagnostic field path")
        if (
            self.reason_code is not None
            and _SAFE_REASON.fullmatch(self.reason_code) is None
        ):
            raise ValueError("unsafe configuration diagnostic reason code")
        if (
            self.suggestion is not None
            and _SAFE_SUGGESTION.fullmatch(self.suggestion) is None
        ):
            raise ValueError("unsafe configuration diagnostic suggestion")
        if self.line is not None and self.line < 1:
            raise ValueError("configuration diagnostic line must be positive")
        if self.column is not None and self.column < 1:
            raise ValueError("configuration diagnostic column must be positive")


class ConfigurationError(ValueError):
    """Expose one fixed safe configuration failure code and optional diagnostic."""

    def __init__(
        self,
        code: ConfigurationErrorCode,
        diagnostic: ConfigurationDiagnostic | None = None,
    ) -> None:
        self.code = code
        self.diagnostic = diagnostic
        super().__init__(_MESSAGES[code])


def configuration_error_payload(error: ConfigurationError) -> dict[str, object]:
    """Return only bounded fields that are safe for structured CLI output."""

    payload: dict[str, object] = {"code": error.code.value}
    diagnostic = error.diagnostic
    if diagnostic is None:
        return payload
    if diagnostic.source_label is not None:
        payload["source"] = diagnostic.source_label
    if diagnostic.field_path is not None:
        payload["field"] = diagnostic.field_path
    if diagnostic.line is not None:
        payload["line"] = diagnostic.line
    if diagnostic.column is not None:
        payload["column"] = diagnostic.column
    if diagnostic.reason_code is not None:
        payload["reason"] = diagnostic.reason_code
    if diagnostic.suggestion is not None:
        payload["suggestion"] = diagnostic.suggestion
    return payload


def format_configuration_error(error: ConfigurationError) -> str:
    """Render a safe human diagnostic without arbitrary source values."""

    diagnostic = error.diagnostic
    if diagnostic is None:
        return str(error)

    location: list[str] = []
    if diagnostic.source_label is not None:
        location.append(f"{diagnostic.source_label} config")
    if diagnostic.field_path is not None:
        location.append(diagnostic.field_path)
    if diagnostic.line is not None:
        if diagnostic.column is not None:
            location.append(f"line {diagnostic.line}, column {diagnostic.column}")
        else:
            location.append(f"line {diagnostic.line}")

    reason = (
        _REASON_MESSAGES.get(diagnostic.reason_code, str(error))
        if diagnostic.reason_code is not None
        else str(error)
    )
    prefix = ": ".join(location)
    rendered = f"{prefix}: {reason}" if prefix else reason
    if diagnostic.suggestion is not None:
        rendered += f"; did you mean {diagnostic.suggestion}"
    return rendered


__all__ = [
    "ConfigurationDiagnostic",
    "ConfigurationError",
    "ConfigurationErrorCode",
    "configuration_error_payload",
    "format_configuration_error",
]

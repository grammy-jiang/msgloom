"""Privacy-safe operator-configuration failures."""

from __future__ import annotations

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


class ConfigurationError(ValueError):
    """Expose one fixed safe configuration failure code and message."""

    def __init__(self, code: ConfigurationErrorCode) -> None:
        self.code = code
        super().__init__(_MESSAGES[code])

"""Closed operator configuration for finite Phase 1 composition."""

from .composition import (
    OperationData,
    OperatorConfiguration,
    PreparationOperationData,
    ReportOperationData,
    ReportSubmitOperationData,
    TriageOperationData,
)
from .errors import ConfigurationError, ConfigurationErrorCode
from .loader import load_operator_configuration
from .models import (
    ConfigurationSnapshot,
    SecretBinding,
    SecretPurpose,
    SecretSource,
)
from .secrets import MAX_SECRET_BYTES, SecretResolver

__all__ = [
    "MAX_SECRET_BYTES",
    "ConfigurationError",
    "ConfigurationErrorCode",
    "ConfigurationSnapshot",
    "OperationData",
    "OperatorConfiguration",
    "PreparationOperationData",
    "ReportOperationData",
    "ReportSubmitOperationData",
    "SecretBinding",
    "SecretPurpose",
    "SecretResolver",
    "SecretSource",
    "TriageOperationData",
    "load_operator_configuration",
]

"""Closed operator configuration for finite Phase 1 composition."""

from .composition import (
    OperationData,
    OperatorConfiguration,
    PreparationOperationData,
    ReportOperationData,
    ReportSubmitOperationData,
    TriageOperationData,
)
from .errors import (
    ConfigurationDiagnostic,
    ConfigurationError,
    ConfigurationErrorCode,
    configuration_error_payload,
    format_configuration_error,
)
from .loader import (
    load_operator_configuration,
    load_operator_configuration_from_document,
)
from .models import (
    ConfigurationSnapshot,
    SecretBinding,
    SecretPurpose,
    SecretSource,
)
from .secrets import MAX_SECRET_BYTES, SecretResolver
from .universal import (
    UniversalConfigDocument,
    UniversalConfigSource,
    load_universal_config,
)

__all__ = [
    "MAX_SECRET_BYTES",
    "ConfigurationDiagnostic",
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
    "UniversalConfigDocument",
    "UniversalConfigSource",
    "configuration_error_payload",
    "format_configuration_error",
    "load_operator_configuration",
    "load_operator_configuration_from_document",
    "load_universal_config",
]

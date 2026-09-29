"""Provider-neutral Phase 1 persistence API."""

from msgloom.persistence.async_store import Phase1Persistence
from msgloom.persistence.errors import (
    ClaimUnavailableError,
    DependencyNotReadyError,
    ExternalEffectReconciliationRequired,
    ImmutableRecordError,
    IncompatibleSchemaError,
    Phase1PersistenceError,
    SemanticDataIntegrityError,
    SemanticDataReferenceError,
    SemanticDataTooLargeError,
    SemanticDataTypeError,
    StaleClaimError,
    UnknownResultSchemaError,
    UnknownSemanticDataSchemaError,
)
from msgloom.persistence.semantic import SemanticDataRegistry

__all__ = [
    "ClaimUnavailableError",
    "DependencyNotReadyError",
    "ExternalEffectReconciliationRequired",
    "ImmutableRecordError",
    "IncompatibleSchemaError",
    "Phase1Persistence",
    "Phase1PersistenceError",
    "SemanticDataIntegrityError",
    "SemanticDataReferenceError",
    "SemanticDataRegistry",
    "SemanticDataTooLargeError",
    "SemanticDataTypeError",
    "StaleClaimError",
    "UnknownResultSchemaError",
    "UnknownSemanticDataSchemaError",
]

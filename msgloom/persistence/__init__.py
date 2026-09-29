"""Provider-neutral Phase 1 persistence API."""

from msgloom.persistence.async_store import Phase1Persistence
from msgloom.persistence.errors import (
    ClaimUnavailableError,
    DependencyNotReadyError,
    ExternalEffectReconciliationRequired,
    ImmutableRecordError,
    IncompatibleSchemaError,
    Phase1PersistenceError,
    StaleClaimError,
    UnknownResultSchemaError,
)

__all__ = [
    "ClaimUnavailableError",
    "DependencyNotReadyError",
    "ExternalEffectReconciliationRequired",
    "ImmutableRecordError",
    "IncompatibleSchemaError",
    "Phase1Persistence",
    "Phase1PersistenceError",
    "StaleClaimError",
    "UnknownResultSchemaError",
]

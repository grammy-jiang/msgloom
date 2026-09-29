"""Phase 1 persistence contract failures."""


class Phase1PersistenceError(RuntimeError):
    """Base class for visible provider-neutral persistence failures."""


class UnknownResultSchemaError(Phase1PersistenceError):
    """A required result kind/schema version is not registered."""


class ImmutableRecordError(Phase1PersistenceError):
    """An existing immutable result or outcome conflicts with a rewrite."""


class DependencyNotReadyError(Phase1PersistenceError):
    """A dependent stage input is absent or not explicitly acceptable."""


class ClaimUnavailableError(Phase1PersistenceError):
    """Another live attempt owns the requested durable claim."""


class StaleClaimError(Phase1PersistenceError):
    """A superseded attempt tried to mutate or release a newer claim."""


class ExternalEffectReconciliationRequired(Phase1PersistenceError):
    """A prior attempt may have caused an external effect and blocks retry."""


class IncompatibleSchemaError(Phase1PersistenceError):
    """The neutral table set/version requires an explicit migration."""


class UnknownSemanticDataSchemaError(Phase1PersistenceError):
    """Semantic data has no registered kind/schema codec."""


class SemanticDataTypeError(Phase1PersistenceError):
    """Semantic data does not match the registered Python contract."""


class SemanticDataReferenceError(Phase1PersistenceError):
    """A semantic-data reference does not match its validated payload."""


class SemanticDataIntegrityError(Phase1PersistenceError):
    """Stored semantic data failed its integrity or schema validation."""


class SemanticDataTooLargeError(Phase1PersistenceError):
    """Canonical semantic data exceeds its registered storage bound."""

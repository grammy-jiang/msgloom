"""Read-only adapters from saved A1 evidence to later Phase 1 preparation."""

from msgloom.sources._snapshot import (
    COLLECTED_SELECTION_KIND,
    COLLECTED_SELECTION_SCHEMA_VERSION,
    MAX_COLLECTED_SELECTION_BYTES,
    CollectedSelectionCodec,
)
from msgloom.sources.handoff_catalog import HandoffCatalog
from msgloom.sources.handoff_models import (
    A1CatalogIdentity,
    ReleasedFact,
    ReleaseEntry,
    ReleaseEntryPage,
    ReleaseEntryRef,
)
from msgloom.sources.models import (
    CollectedAttachment,
    CollectedBody,
    CollectedRecord,
    CollectedSelection,
    CollectedSourceReader,
    ContentKind,
    SavedSourceReaderConfig,
    SourceEvidenceError,
    SourceEvidenceLimitError,
    SourceMetadata,
    SourceReaderError,
    SourceReaderLimits,
    SourceReferenceError,
)
from msgloom.sources.reader import SavedSourceReader
from msgloom.sources.release_models import (
    ReleasedInput,
    ScopedTransition,
    SupportingContext,
)
from msgloom.sources.release_reader import ReleaseSourceReader

__all__ = [
    "COLLECTED_SELECTION_KIND",
    "COLLECTED_SELECTION_SCHEMA_VERSION",
    "MAX_COLLECTED_SELECTION_BYTES",
    "A1CatalogIdentity",
    "CollectedAttachment",
    "CollectedBody",
    "CollectedRecord",
    "CollectedSelection",
    "CollectedSelectionCodec",
    "CollectedSourceReader",
    "ContentKind",
    "HandoffCatalog",
    "ReleaseEntry",
    "ReleaseEntryPage",
    "ReleaseEntryRef",
    "ReleaseSourceReader",
    "ReleasedFact",
    "ReleasedInput",
    "SavedSourceReader",
    "SavedSourceReaderConfig",
    "ScopedTransition",
    "SourceEvidenceError",
    "SourceEvidenceLimitError",
    "SourceMetadata",
    "SourceReaderError",
    "SourceReaderLimits",
    "SourceReferenceError",
    "SupportingContext",
]

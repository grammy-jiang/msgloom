"""Read-only adapters from saved A1 evidence to later Phase 1 preparation."""

from msgloom.sources._snapshot import (
    COLLECTED_SELECTION_KIND,
    COLLECTED_SELECTION_SCHEMA_VERSION,
    MAX_COLLECTED_SELECTION_BYTES,
    CollectedSelectionCodec,
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

__all__ = [
    "COLLECTED_SELECTION_KIND",
    "COLLECTED_SELECTION_SCHEMA_VERSION",
    "MAX_COLLECTED_SELECTION_BYTES",
    "CollectedAttachment",
    "CollectedBody",
    "CollectedRecord",
    "CollectedSelection",
    "CollectedSelectionCodec",
    "CollectedSourceReader",
    "ContentKind",
    "SavedSourceReader",
    "SavedSourceReaderConfig",
    "SourceEvidenceError",
    "SourceEvidenceLimitError",
    "SourceMetadata",
    "SourceReaderError",
    "SourceReaderLimits",
    "SourceReferenceError",
]

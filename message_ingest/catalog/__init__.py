"""Local acquisition catalog and its SQLAlchemy models."""

from message_ingest.catalog.models import (
    AttachmentRecord,
    Base,
    CalendarEventObservation,
    DeltaCheckpoint,
    DeltaCheckpointCandidate,
    MailFolderRecord,
    MessageObservation,
    MessageRecord,
    MessageSurface,
    RawHttpEvidence,
    SourceBinding,
)
from message_ingest.catalog.store import Catalog

__all__ = [
    "AttachmentRecord",
    "Base",
    "CalendarEventObservation",
    "Catalog",
    "DeltaCheckpoint",
    "DeltaCheckpointCandidate",
    "MailFolderRecord",
    "MessageObservation",
    "MessageRecord",
    "MessageSurface",
    "RawHttpEvidence",
    "SourceBinding",
]

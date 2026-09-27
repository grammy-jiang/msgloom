"""Local acquisition catalog and its SQLAlchemy models."""

from message_ingest.catalog.models import (
    AttachmentRecord,
    Base,
    CalendarEventObservation,
    CalendarEventRecord,
    CalendarRecord,
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
    "CalendarEventRecord",
    "CalendarRecord",
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

"""Local Outlook catalog and its SQLAlchemy models."""

from message_ingest.catalog.models import (
    AttachmentRecord,
    Base,
    DeltaCheckpoint,
    DeltaCheckpointCandidate,
    MailFolderRecord,
    MessageObservation,
    MessageRecord,
    MessageSurface,
    RawHttpEvidence,
)
from message_ingest.catalog.store import Catalog

__all__ = [
    "AttachmentRecord",
    "Base",
    "Catalog",
    "DeltaCheckpoint",
    "DeltaCheckpointCandidate",
    "MailFolderRecord",
    "MessageObservation",
    "MessageRecord",
    "MessageSurface",
    "RawHttpEvidence",
]

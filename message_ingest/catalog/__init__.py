"""Local acquisition catalog and its SQLAlchemy models."""

from message_ingest.catalog.models import (
    AttachmentRecord,
    Base,
    CalendarDeltaCheckpoint,
    CalendarDeltaCheckpointCandidate,
    CalendarDeltaEventState,
    CalendarDeltaObservation,
    CalendarEventAttachmentRecord,
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
from message_ingest.catalog.stores.evidence import RawEvidenceStore
from message_ingest.catalog.stores.microsoft.outlook import (
    OutlookCalendarStore,
    OutlookMailStore,
)

__all__ = [
    "AttachmentRecord",
    "Base",
    "CalendarDeltaCheckpoint",
    "CalendarDeltaCheckpointCandidate",
    "CalendarDeltaEventState",
    "CalendarDeltaObservation",
    "CalendarEventAttachmentRecord",
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
    "OutlookCalendarStore",
    "OutlookMailStore",
    "RawEvidenceStore",
    "RawHttpEvidence",
    "SourceBinding",
]

"""SQLAlchemy catalog models grouped by acquisition domain."""

from .acquisition import RawHttpEvidence, SourceBinding
from .base import Base
from .microsoft.outlook import (
    AttachmentRecord,
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
    "DeltaCheckpoint",
    "DeltaCheckpointCandidate",
    "MailFolderRecord",
    "MessageObservation",
    "MessageRecord",
    "MessageSurface",
    "RawHttpEvidence",
    "SourceBinding",
]

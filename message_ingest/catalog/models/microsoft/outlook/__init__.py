"""Outlook catalog model domains."""

from .calendar import (
    CalendarDeltaCheckpoint,
    CalendarDeltaCheckpointCandidate,
    CalendarDeltaEventState,
    CalendarDeltaObservation,
    CalendarEventAttachmentRecord,
    CalendarEventObservation,
    CalendarEventRecord,
    CalendarEventSighting,
    CalendarEventSurface,
    CalendarRecord,
)
from .email import (
    AttachmentRecord,
    DeltaCheckpoint,
    DeltaCheckpointCandidate,
    MailFolderRecord,
    MessageObservation,
    MessageRecord,
    MessageSurface,
)

__all__ = [
    "AttachmentRecord",
    "CalendarDeltaCheckpoint",
    "CalendarDeltaCheckpointCandidate",
    "CalendarDeltaEventState",
    "CalendarDeltaObservation",
    "CalendarEventAttachmentRecord",
    "CalendarEventObservation",
    "CalendarEventRecord",
    "CalendarEventSighting",
    "CalendarEventSurface",
    "CalendarRecord",
    "DeltaCheckpoint",
    "DeltaCheckpointCandidate",
    "MailFolderRecord",
    "MessageObservation",
    "MessageRecord",
    "MessageSurface",
]

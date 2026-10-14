"""Advance a Mail folder's absent checkpoint epoch under its writer lock."""

from sqlalchemy.orm import Session

from message_ingest.catalog.models.microsoft.outlook.email import (
    MailDeltaAbsenceGeneration,
)


def bump_absence_generation(writer: Session, source_id: str, folder_id: str) -> None:
    """Invalidate all requests born before this authoritative cursor deletion."""
    epoch = writer.get(MailDeltaAbsenceGeneration, (source_id, folder_id))
    if epoch is None:
        writer.add(
            MailDeltaAbsenceGeneration(
                source_id=source_id,
                folder_id=folder_id,
                generation=1,
            )
        )
    else:
        epoch.generation += 1


__all__ = ["bump_absence_generation"]

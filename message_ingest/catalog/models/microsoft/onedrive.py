"""Source-scoped OneDrive current state, resync, content, and checkpoints."""

from sqlalchemy import JSON, Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class OneDriveRecord(Base):
    """Share source identity and provenance for current OneDrive captures."""

    __abstract__ = True

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True, sort_order=-1)
    latest_observed_at: Mapped[str] = mapped_column(String(40), index=True)
    latest_evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)
    latest_run_id: Mapped[str | None] = mapped_column(String(32), index=True)


class OneDriveDriveRecord(OneDriveRecord):
    """Latest signed-in account drive metadata for one logical source."""

    __tablename__ = "onedrive_drives"

    drive_id: Mapped[str] = mapped_column(Text)
    drive_type: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str | None] = mapped_column(Text)
    web_url: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[dict[str, object] | None] = mapped_column(JSON)
    quota: Mapped[dict[str, object] | None] = mapped_column(JSON)
    created_date_time: Mapped[str | None] = mapped_column(Text)
    last_modified_date_time: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict[str, object]] = mapped_column(JSON)


class OneDriveItemRecord(OneDriveRecord):
    """Latest item state with useful metadata preserved across absence."""

    __tablename__ = "onedrive_items"

    item_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)
    size: Mapped[int | None] = mapped_column(Integer)
    created_date_time: Mapped[str | None] = mapped_column(Text)
    last_modified_date_time: Mapped[str | None] = mapped_column(Text)
    web_url: Mapped[str | None] = mapped_column(Text)
    e_tag: Mapped[str | None] = mapped_column(Text)
    c_tag: Mapped[str | None] = mapped_column(Text)
    parent_reference: Mapped[dict[str, object] | None] = mapped_column(JSON)
    file: Mapped[dict[str, object] | None] = mapped_column(JSON)
    folder: Mapped[dict[str, object] | None] = mapped_column(JSON)
    deleted: Mapped[dict[str, object] | None] = mapped_column(JSON)
    package: Mapped[dict[str, object] | None] = mapped_column(JSON)
    remote_item: Mapped[dict[str, object] | None] = mapped_column(JSON)
    file_system_info: Mapped[dict[str, object] | None] = mapped_column(JSON)
    special_folder: Mapped[dict[str, object] | None] = mapped_column(JSON)
    # True also represents absence proved by a completed full resync. In that
    # case provider ``deleted`` and ``raw`` remain unchanged so inferred absence
    # cannot masquerade as a provider tombstone.
    is_deleted: Mapped[bool] = mapped_column(Boolean)
    raw: Mapped[dict[str, object]] = mapped_column(JSON)


class OneDriveContentRecord(OneDriveRecord):
    """Latest explicit capture metadata without duplicate bytes."""

    __tablename__ = "onedrive_contents"

    item_id: Mapped[str] = mapped_column(Text, primary_key=True)
    content_sha256: Mapped[str] = mapped_column(String(64))
    content_bytes: Mapped[int] = mapped_column(Integer)


class OneDriveContentCapture(Base):
    """Append-only association between one content capture and metadata version."""

    __tablename__ = "onedrive_content_captures"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    item_id: Mapped[str] = mapped_column(Text, index=True)
    content_sha256: Mapped[str] = mapped_column(String(64))
    content_bytes: Mapped[int] = mapped_column(Integer)
    planned_metadata_observed_at: Mapped[str | None] = mapped_column(String(40))
    planned_metadata_evidence_id: Mapped[str | None] = mapped_column(String(32))
    planned_e_tag: Mapped[str | None] = mapped_column(Text)
    planned_c_tag: Mapped[str | None] = mapped_column(Text)
    response_e_tag: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    run_id: Mapped[str | None] = mapped_column(String(32), index=True)


class OneDriveDeltaCheckpoint(Base):
    """Promoted opaque delta cursor for one signed-in account source."""

    __tablename__ = "onedrive_delta_checkpoints"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    delta_link: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer)
    observed_at: Mapped[str] = mapped_column(String(40))
    evidence_id: Mapped[str] = mapped_column(String(32))
    run_id: Mapped[str] = mapped_column(String(32))


class OneDriveDeltaCheckpointCandidate(Base):
    """One persisted terminal cursor that cannot itself resume a crawl."""

    __tablename__ = "onedrive_delta_checkpoint_candidates"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    base_revision: Mapped[int | None] = mapped_column(Integer)
    delta_link: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[str] = mapped_column(String(40))
    evidence_id: Mapped[str] = mapped_column(String(32))


class OneDriveDeltaResyncAttempt(Base):
    """Durable start marker for one full enumeration after HTTP 410."""

    __tablename__ = "onedrive_delta_resync_attempts"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    reset_attempt: Mapped[int] = mapped_column(Integer, primary_key=True)
    base_revision: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[str] = mapped_column(String(40))
    trigger_evidence_id: Mapped[str] = mapped_column(String(32))


class OneDriveDeltaResyncObservation(Base):
    """Append-only driveItem sighting from one fresh resync enumeration."""

    __tablename__ = "onedrive_delta_resync_observations"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "run_id",
            "reset_attempt",
            "page_number",
            "entry_index",
            name="uq_onedrive_resync_position",
        ),
    )

    observation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    reset_attempt: Mapped[int] = mapped_column(Integer)
    base_revision: Mapped[int] = mapped_column(Integer)
    item_id: Mapped[str] = mapped_column(Text, index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    entry_index: Mapped[int] = mapped_column(Integer)
    observed_at: Mapped[str] = mapped_column(String(40))
    evidence_id: Mapped[str] = mapped_column(String(32))
    raw: Mapped[dict[str, object]] = mapped_column(JSON)


__all__ = [
    "OneDriveContentCapture",
    "OneDriveContentRecord",
    "OneDriveDeltaCheckpoint",
    "OneDriveDeltaCheckpointCandidate",
    "OneDriveDeltaResyncAttempt",
    "OneDriveDeltaResyncObservation",
    "OneDriveDriveRecord",
    "OneDriveItemRecord",
]

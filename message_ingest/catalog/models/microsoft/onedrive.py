"""Source-scoped OneDrive current state and pending delta checkpoints."""

from sqlalchemy import JSON, Boolean, Integer, String, Text
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
    """
    Latest item state, retaining useful metadata across sparse tombstones.

    Only a provider ``deleted`` facet marks deletion. ``raw`` always records
    the current observation, including an otherwise metadata-free tombstone.
    """

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
    is_deleted: Mapped[bool] = mapped_column(Boolean)
    raw: Mapped[dict[str, object]] = mapped_column(JSON)


class OneDriveContentRecord(OneDriveRecord):
    """Latest explicit capture metadata without duplicate bytes."""

    __tablename__ = "onedrive_contents"

    item_id: Mapped[str] = mapped_column(Text, primary_key=True)
    content_sha256: Mapped[str] = mapped_column(String(64))
    content_bytes: Mapped[int] = mapped_column(Integer)


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


__all__ = [
    "OneDriveContentRecord",
    "OneDriveDeltaCheckpoint",
    "OneDriveDeltaCheckpointCandidate",
    "OneDriveDriveRecord",
    "OneDriveItemRecord",
]

"""Personal Contacts current state, snapshot sightings, and delta staging."""

from sqlalchemy import JSON, Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class ContactFolderRecord(Base):
    """Latest custom contact-folder metadata; absence never deletes this row."""

    __tablename__ = "contact_folders"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    folder_id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(Text)
    parent_folder_id: Mapped[str | None] = mapped_column(Text)
    latest_observed_at: Mapped[str] = mapped_column(String(40), index=True)
    latest_evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)
    raw: Mapped[dict[str, object]] = mapped_column(JSON)


class ContactFolderPresence(Base):
    """Authoritative custom-folder presence from the latest clean snapshot."""

    __tablename__ = "contact_folder_presence"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    folder_id: Mapped[str] = mapped_column(Text, primary_key=True)
    is_present: Mapped[bool] = mapped_column(Boolean)
    removed_reason: Mapped[str | None] = mapped_column(Text)
    latest_run_id: Mapped[str] = mapped_column(String(32), index=True)
    latest_observed_at: Mapped[str] = mapped_column(String(40))
    latest_evidence_id: Mapped[str | None] = mapped_column(String(32))


class ContactFolderSighting(Base):
    """One run-scoped positive custom-folder sighting."""

    __tablename__ = "contact_folder_sightings"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    folder_id: Mapped[str] = mapped_column(Text, primary_key=True)
    observed_at: Mapped[str] = mapped_column(String(40))
    evidence_id: Mapped[str | None] = mapped_column(String(32))
    run_started_at: Mapped[str] = mapped_column(String(40))


class ContactRecord(Base):
    """Latest semantic contact projection, scoped separately from folder inventory."""

    __tablename__ = "contacts"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    scope_key: Mapped[str] = mapped_column(Text, primary_key=True)
    contact_id: Mapped[str] = mapped_column(Text, primary_key=True)
    folder_id: Mapped[str | None] = mapped_column(Text)
    is_default_scope: Mapped[bool] = mapped_column(Boolean)
    display_name: Mapped[str | None] = mapped_column(Text)
    given_name: Mapped[str | None] = mapped_column(Text)
    surname: Mapped[str | None] = mapped_column(Text)
    initials: Mapped[str | None] = mapped_column(Text)
    nick_name: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    company_name: Mapped[str | None] = mapped_column(Text)
    department: Mapped[str | None] = mapped_column(Text)
    job_title: Mapped[str | None] = mapped_column(Text)
    email_addresses: Mapped[list[dict[str, object]] | None] = mapped_column(JSON)
    business_phones: Mapped[list[str] | None] = mapped_column(JSON)
    home_phones: Mapped[list[str] | None] = mapped_column(JSON)
    mobile_phone: Mapped[str | None] = mapped_column(Text)
    birthday: Mapped[str | None] = mapped_column(Text)
    parent_folder_id: Mapped[str | None] = mapped_column(Text)
    last_modified_date_time: Mapped[str | None] = mapped_column(Text)
    latest_observed_at: Mapped[str] = mapped_column(String(40), index=True)
    latest_evidence_id: Mapped[str | None] = mapped_column(String(32), index=True)
    raw: Mapped[dict[str, object]] = mapped_column(JSON)


class ContactPresence(Base):
    """Authoritative presence for one default/custom contact collection."""

    __tablename__ = "contact_presence"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    scope_key: Mapped[str] = mapped_column(Text, primary_key=True)
    contact_id: Mapped[str] = mapped_column(Text, primary_key=True)
    is_present: Mapped[bool] = mapped_column(Boolean)
    removed_reason: Mapped[str | None] = mapped_column(Text)
    latest_run_id: Mapped[str] = mapped_column(String(32), index=True)
    latest_observed_at: Mapped[str] = mapped_column(String(40))
    latest_evidence_id: Mapped[str | None] = mapped_column(String(32))


class ContactSighting(Base):
    """One run-scoped contact sighting used only for snapshot promotion."""

    __tablename__ = "contact_sightings"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    scope_key: Mapped[str] = mapped_column(Text, primary_key=True)
    contact_id: Mapped[str] = mapped_column(Text, primary_key=True)
    observed_at: Mapped[str] = mapped_column(String(40))
    evidence_id: Mapped[str | None] = mapped_column(String(32))
    run_started_at: Mapped[str] = mapped_column(String(40))


class ContactCollectionCompletion(Base):
    """Durable terminal-page marker for a run-scoped snapshot collection."""

    __tablename__ = "contact_collection_completions"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    collection_kind: Mapped[str] = mapped_column(String(32), primary_key=True)
    scope_key: Mapped[str] = mapped_column(Text, primary_key=True)
    folder_id: Mapped[str | None] = mapped_column(Text)
    is_default_scope: Mapped[bool] = mapped_column(Boolean)
    observed_at: Mapped[str] = mapped_column(String(40))
    evidence_id: Mapped[str | None] = mapped_column(String(32))
    run_started_at: Mapped[str] = mapped_column(String(40))


class ContactsSnapshotState(Base):
    """Latest clean authoritative snapshot run for one logical source."""

    __tablename__ = "contacts_snapshot_state"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    latest_run_id: Mapped[str] = mapped_column(String(32), unique=True)
    latest_run_started_at: Mapped[str] = mapped_column(String(40))
    committed_at: Mapped[str] = mapped_column(String(40))


class ContactPromotionGeneration(Base):
    """Shared snapshot/delta authority generation for one Contacts source."""

    __tablename__ = "contact_promotion_generations"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer)


class ContactPromotionBase(Base):
    """Generation ownership captured durably before one provider traversal."""

    __tablename__ = "contact_promotion_bases"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    operation: Mapped[str] = mapped_column(Text)
    base_generation: Mapped[int] = mapped_column(Integer)


class ContactDeltaObservation(Base):
    """Staged custom-folder delta entry; current state changes only on promotion."""

    __tablename__ = "contact_delta_observations"
    __table_args__ = (UniqueConstraint("source_id", "folder_id", "run_id", "ordinal"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    folder_id: Mapped[str] = mapped_column(Text)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    contact_id: Mapped[str] = mapped_column(Text)
    is_removed: Mapped[bool] = mapped_column(Boolean)
    removed_reason: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[str] = mapped_column(String(40))
    evidence_id: Mapped[str | None] = mapped_column(String(32))
    raw: Mapped[dict[str, object]] = mapped_column(JSON)


class ContactDeltaCheckpointCandidate(Base):
    """Terminal opaque cursor staged for one custom-folder delta round."""

    __tablename__ = "contact_delta_checkpoint_candidates"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    folder_id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    base_revision: Mapped[int | None] = mapped_column(Integer)
    delta_link: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[str] = mapped_column(String(40))
    evidence_id: Mapped[str] = mapped_column(String(32))


class ContactDeltaCheckpoint(Base):
    """Committed opaque delta cursor for one concrete custom folder."""

    __tablename__ = "contact_delta_checkpoints"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    folder_id: Mapped[str] = mapped_column(Text, primary_key=True)
    delta_link: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer)
    run_id: Mapped[str] = mapped_column(String(32))
    committed_at: Mapped[str] = mapped_column(String(40))


__all__ = [
    "ContactCollectionCompletion",
    "ContactDeltaCheckpoint",
    "ContactDeltaCheckpointCandidate",
    "ContactDeltaObservation",
    "ContactFolderPresence",
    "ContactFolderRecord",
    "ContactFolderSighting",
    "ContactPresence",
    "ContactPromotionBase",
    "ContactPromotionGeneration",
    "ContactRecord",
    "ContactSighting",
    "ContactsSnapshotState",
]

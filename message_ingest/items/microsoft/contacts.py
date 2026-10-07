"""Personal Contacts provider projections with msgloom run provenance."""

from dataclasses import dataclass
from typing import Literal

from microsoft_graph.items.contacts import ContactFolderItem as GraphContactFolderItem
from microsoft_graph.items.contacts import ContactItem as GraphContactItem


@dataclass(slots=True)
class ContactFolderItem(GraphContactFolderItem):
    """One custom-folder observation linked to raw response evidence."""

    observed_at: str
    evidence_id: str | None
    run_id: str
    run_started_at: str


@dataclass(slots=True)
class ContactItem(GraphContactItem):
    """One snapshot or delta contact observation with explicit folder scope."""

    observation_kind: Literal["snapshot", "delta"]
    observed_at: str
    evidence_id: str | None
    run_id: str
    run_started_at: str


@dataclass(slots=True)
class ContactCollectionCompleteItem:
    """Durable terminal-page fact for one Contacts snapshot collection."""

    collection_kind: Literal["folder_inventory", "child_folders", "contacts"]
    folder_id: str | None
    is_default_scope: bool
    observed_at: str
    evidence_id: str | None
    run_id: str
    run_started_at: str


@dataclass(slots=True)
class ContactDeltaCheckpointCandidateItem:
    """Terminal opaque cursor candidate for one concrete custom folder."""

    folder_id: str
    delta_link: str
    base_revision: int | None
    observed_at: str
    evidence_id: str
    run_id: str


__all__ = [
    "ContactCollectionCompleteItem",
    "ContactDeltaCheckpointCandidateItem",
    "ContactFolderItem",
    "ContactItem",
]

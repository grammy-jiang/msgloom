"""OneDrive metadata, resync observations, and explicit content provenance."""

from dataclasses import dataclass
from typing import Any, Self

from microsoft_graph.items.onedrive import OneDriveDriveItem as GraphOneDriveDriveItem
from microsoft_graph.items.onedrive import OneDriveItem as GraphOneDriveItem


def _without_download_urls(value: Any) -> Any:
    """Copy only containers that contain preauthenticated download URLs."""
    if isinstance(value, dict):
        clean = {
            key: _without_download_urls(child)
            for key, child in value.items()
            if key != "@microsoft.graph.downloadUrl"
        }
        if len(clean) == len(value) and all(
            clean[key] is child for key, child in value.items()
        ):
            return value
        return clean
    if isinstance(value, list):
        clean = [_without_download_urls(child) for child in value]
        return (
            value if all(a is b for a, b in zip(value, clean, strict=True)) else clean
        )
    return value


@dataclass(slots=True)
class OneDriveDriveItem(GraphOneDriveDriveItem):
    """One drive observation with evidence and run provenance."""

    observed_at: str
    evidence_id: str | None
    run_id: str | None

    @classmethod
    def from_graph(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Apply app retention policy before provider identity validation."""
        return super(OneDriveDriveItem, cls).from_graph(
            _without_download_urls(resource), **kwargs
        )


@dataclass(slots=True)
class OneDriveItem(GraphOneDriveItem):
    """One driveItem observation with no retained preauthenticated URL."""

    observed_at: str
    evidence_id: str | None
    run_id: str | None

    @classmethod
    def from_graph(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Strip download URL annotations, including nested remote items."""
        return super(OneDriveItem, cls).from_graph(
            _without_download_urls(resource), **kwargs
        )


@dataclass(slots=True)
class OneDriveDeltaResyncObservationItem(OneDriveItem):
    """One staged server sighting from a fresh post-410 enumeration."""

    reset_attempt: int
    base_revision: int
    page_number: int
    entry_index: int


@dataclass(slots=True)
class OneDriveDeltaResyncAttemptItem:
    """Durable reset start marker linked to the redacted HTTP 410 evidence."""

    reset_attempt: int
    base_revision: int
    started_at: str
    trigger_evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class OneDriveContentItem:
    """Explicit capture metadata; body bytes exist only in raw evidence."""

    item_id: str
    content_sha256: str
    content_bytes: int
    observed_at: str
    evidence_id: str | None
    run_id: str | None
    planned_metadata_observed_at: str | None = None
    planned_metadata_evidence_id: str | None = None
    planned_e_tag: str | None = None
    planned_c_tag: str | None = None
    response_e_tag: str | None = None


@dataclass(slots=True)
class OneDriveDeltaCheckpointCandidateItem:
    """Terminal opaque cursor awaiting clean-run checkpoint promotion."""

    delta_link: str
    base_revision: int | None
    observed_at: str
    evidence_id: str | None
    run_id: str | None


__all__ = [
    "OneDriveContentItem",
    "OneDriveDeltaCheckpointCandidateItem",
    "OneDriveDeltaResyncAttemptItem",
    "OneDriveDeltaResyncObservationItem",
    "OneDriveDriveItem",
    "OneDriveItem",
]

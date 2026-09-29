"""OneDrive metadata and explicit content with application provenance."""

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
        return value if all(a is b for a, b in zip(value, clean)) else clean
    return value


@dataclass(slots=True)
class OneDriveDriveItem(GraphOneDriveDriveItem):
    """
    One drive observation with evidence and run provenance.

    Semantic metadata excludes ``@microsoft.graph.downloadUrl`` recursively.
    Raw HTTP body evidence remains exact. Other provider fields and unchanged
    containers retain their values and identity.
    """

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
class OneDriveContentItem:
    """Latest explicit capture metadata; body bytes exist only in evidence."""

    item_id: str
    content_sha256: str
    content_bytes: int
    observed_at: str
    evidence_id: str | None
    run_id: str | None


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
    "OneDriveDriveItem",
    "OneDriveItem",
]

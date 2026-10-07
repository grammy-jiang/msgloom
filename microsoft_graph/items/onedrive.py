"""Optional OneDrive projections with original JSON and no app provenance."""

from dataclasses import dataclass, field
from typing import Any, Self

from microsoft_graph.protocol import graph_object


def _resource(resource: dict[str, Any], context: str) -> dict[str, Any]:
    """Require a provider object and stable ID without validating metadata."""
    raw = graph_object(resource, context=context)
    if not isinstance(raw.get("id"), str) or not raw["id"]:
        raise ValueError(f"{context} requires a non-empty id")
    return raw


@dataclass(slots=True)
class OneDriveDriveItem:
    """
    Project a Graph ``drive`` resource, the account's file container.

    ``raw`` retains the original dictionary. Missing optional fields remain
    ``None``; present values, including falsey and nested values, are unchanged.
    :meth:`from_graph` validates only object and stable ID identity.
    """

    id: str
    raw: dict[str, Any]
    drive_type: str | None = field(init=False)
    name: str | None = field(init=False)
    web_url: str | None = field(init=False)
    owner: dict[str, Any] | None = field(init=False)
    quota: dict[str, Any] | None = field(init=False)
    created_date_time: str | None = field(init=False)
    last_modified_date_time: str | None = field(init=False)

    def __post_init__(self) -> None:
        """Snapshot drive fields without copying or interpreting values."""
        self.drive_type = self.raw.get("driveType")
        self.name = self.raw.get("name")
        self.web_url = self.raw.get("webUrl")
        self.owner = self.raw.get("owner")
        self.quota = self.raw.get("quota")
        self.created_date_time = self.raw.get("createdDateTime")
        self.last_modified_date_time = self.raw.get("lastModifiedDateTime")

    @classmethod
    def from_graph(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Map a drive; keyword arguments supply consumer subclass fields."""
        raw = _resource(resource, "OneDrive drive")
        return cls(id=raw["id"], raw=raw, **kwargs)


@dataclass(slots=True)
class OneDriveItem:
    """
    Project a Graph ``driveItem`` resource within the drive hierarchy.

    Facets retain provider identity and values. A deleted facet is preserved
    even when empty; consumers decide how tombstones affect stored metadata.
    No body content or traversal policy belongs to this projection.
    """

    id: str
    raw: dict[str, Any]
    name: str | None = field(init=False)
    size: int | None = field(init=False)
    created_date_time: str | None = field(init=False)
    last_modified_date_time: str | None = field(init=False)
    web_url: str | None = field(init=False)
    e_tag: str | None = field(init=False)
    c_tag: str | None = field(init=False)
    parent_reference: dict[str, Any] | None = field(init=False)
    file: dict[str, Any] | None = field(init=False)
    folder: dict[str, Any] | None = field(init=False)
    deleted: dict[str, Any] | None = field(init=False)
    package: dict[str, Any] | None = field(init=False)
    remote_item: dict[str, Any] | None = field(init=False)
    file_system_info: dict[str, Any] | None = field(init=False)
    special_folder: dict[str, Any] | None = field(init=False)

    def __post_init__(self) -> None:
        """Snapshot item fields while retaining nested object identity."""
        self.name = self.raw.get("name")
        self.size = self.raw.get("size")
        self.created_date_time = self.raw.get("createdDateTime")
        self.last_modified_date_time = self.raw.get("lastModifiedDateTime")
        self.web_url = self.raw.get("webUrl")
        self.e_tag = self.raw.get("eTag")
        self.c_tag = self.raw.get("cTag")
        self.parent_reference = self.raw.get("parentReference")
        self.file = self.raw.get("file")
        self.folder = self.raw.get("folder")
        self.deleted = self.raw.get("deleted")
        self.package = self.raw.get("package")
        self.remote_item = self.raw.get("remoteItem")
        self.file_system_info = self.raw.get("fileSystemInfo")
        self.special_folder = self.raw.get("specialFolder")

    @classmethod
    def from_graph(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Map a drive item; keyword arguments supply consumer state."""
        raw = _resource(resource, "OneDrive drive item")
        return cls(id=raw["id"], raw=raw, **kwargs)


__all__ = ["OneDriveDriveItem", "OneDriveItem"]

"""Microsoft OneDrive read scopes and signed-in-account v1.0 paths."""

from typing import ClassVar
from urllib.parse import quote, urlencode

from .graph import MicrosoftGraphSpider


class MicrosoftOneDriveSpider(MicrosoftGraphSpider):
    """Supply read paths; consumers own traversal and content retention."""

    graph_permissions: ClassVar[tuple[str, ...]] = ("Files.Read",)

    def drive_path(self) -> str:
        """Address the signed-in account's drive metadata."""
        return "/me/drive"

    def root_children_path(self, *, page_size: int | None = None) -> str:
        """List root children with only a newly constructed page-size query."""
        path = f"{self.drive_path()}/root/children"
        if page_size is None:
            return path
        return f"{path}?{urlencode({'$top': page_size})}"

    def item_children_path(self, item_id: str, *, page_size: int | None = None) -> str:
        """Encode the raw item ID once to address its children collection."""
        path = f"{self.drive_path()}/items/{quote(item_id, safe='')}/children"
        if page_size is None:
            return path
        return f"{path}?{urlencode({'$top': page_size})}"

    def delta_path(self, *, page_size: int | None = None) -> str:
        """Start metadata delta; continuation URLs remain opaque elsewhere."""
        path = f"{self.drive_path()}/root/delta"
        if page_size is None:
            return path
        return f"{path}?{urlencode({'$top': page_size})}"

    def content_path(self, item_id: str) -> str:
        """Address content for one explicit raw item ID encoded once."""
        return f"{self.drive_path()}/items/{quote(item_id, safe='')}/content"


__all__ = ["MicrosoftOneDriveSpider"]

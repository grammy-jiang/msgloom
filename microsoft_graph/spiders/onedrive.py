"""Microsoft OneDrive read scopes and signed-in-account v1.0 paths."""

from typing import Any, ClassVar
from urllib.parse import quote, urlencode

from scrapy import Request

from .graph import MicrosoftGraphSpider

ONEDRIVE_CONTENT_META_KEY = "_microsoft_graph_onedrive_content"


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

    def content_request(
        self,
        item_id: str,
        *,
        callback=None,
        errback=None,
        cb_kwargs: dict[str, Any] | None = None,
        operation: str = "onedrive-content",
        download_maxsize: int | None = None,
    ) -> Request:
        """
        Build an uncached binary GET that permits native offsite redirects.

        Scrapy copies the private marker across redirects and retries. Enable
        the extension in :mod:`microsoft_graph.extensions.onedrive`
        to sanitize native logs for these requests. Native redirect
        handling removes cross-origin Authorization. Consumers still own
        evidence, retained URLs, failure records, and content storage policy.
        """
        request = self.graph_request(
            self.content_path(item_id),
            callback=callback,
            errback=errback,
            cb_kwargs=cb_kwargs,
            operation=operation,
            accept="application/octet-stream",
            dont_cache=True,
            download_maxsize=download_maxsize,
        )
        request.meta.update({"allow_offsite": True, ONEDRIVE_CONTENT_META_KEY: True})
        return request


__all__ = ["ONEDRIVE_CONTENT_META_KEY", "MicrosoftOneDriveSpider"]

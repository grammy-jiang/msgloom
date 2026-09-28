"""Provider-only attachment requests; consumer callbacks own traversal policy."""

from microsoft_graph.protocol.attachments import (
    attachment_list_path,
    attachment_raw_path,
    item_attachment_path,
)
from microsoft_graph.scrapy.spiders import MicrosoftGraphSpider


class OutlookAttachmentSpider(MicrosoftGraphSpider):
    """Construct attachment requests without evidence or completeness policy."""

    def attachment_list_request(
        self,
        parent_path: str,
        *,
        url: str | None = None,
        page_size: int | None = None,
        **kwargs,
    ):
        """List metadata or follow an opaque attachment continuation link."""
        if url is not None:
            return self.continuation_request(url, **kwargs)
        return self.graph_request(
            attachment_list_path(parent_path, page_size=page_size), **kwargs
        )

    def attachment_raw_request(self, parent_path: str, attachment_id: str, **kwargs):
        """Request file/item bytes with a representation-sensitive Accept header."""
        return self.graph_request(
            attachment_raw_path(parent_path, attachment_id),
            **{"accept": "*/*", **kwargs},
        )

    def item_attachment_request(self, parent_path: str, attachment_id: str, **kwargs):
        """Request expanded Graph item metadata with named consumer callbacks."""
        return self.graph_request(
            item_attachment_path(parent_path, attachment_id), **kwargs
        )

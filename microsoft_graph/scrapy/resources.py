"""Small object and collection spiders with replaceable item factories."""

from collections.abc import AsyncIterator, Iterator
from typing import Any

from scrapy.http import TextResponse

from microsoft_graph.protocol import GraphCollectionPage, graph_object
from microsoft_graph.scrapy.items import GraphResourceItem
from microsoft_graph.scrapy.spiders import MicrosoftGraphSpider


class GraphObjectSpider(MicrosoftGraphSpider):
    """
    Read a declared endpoint with no required pipeline or application state.

    Subclasses declare ``name``, ``endpoint``, and ``graph_permissions``.
    Override ``resource_to_item`` or ``make_item`` to return a custom dataclass,
    Scrapy Item, or dict. HTTP and protocol failures use native Scrapy handling.
    """

    endpoint = ""
    operation = "object"

    async def start(self) -> AsyncIterator[Any]:
        """Schedule the declared object endpoint through the native scheduler."""
        if not self.endpoint:
            raise ValueError("Graph resource spider requires an endpoint")
        yield self.graph_request(
            self.endpoint, callback=self.parse, operation=self.operation
        )

    def parse(self, response: TextResponse, **kwargs) -> Iterator[Any]:
        """Validate one JSON object before passing it to the consumer hook."""
        resource = graph_object(response.json())
        yield self.resource_to_item(resource, response)

    def resource_to_item(self, resource: dict[str, Any], response: TextResponse) -> Any:
        """Project a provider object through the replaceable item factory."""
        return self.make_item(resource, response)

    def make_item(self, resource: dict[str, Any], response: TextResponse) -> Any:
        """Build an optional default item without evidence or catalog fields."""
        return GraphResourceItem(resource=resource, url=response.url)


class GraphCollectionSpider(GraphObjectSpider):
    """Iterate collection objects and follow opaque provider next links."""

    operation = "collection"

    def parse(self, response: TextResponse, **kwargs) -> Iterator[Any]:
        """Yield items before scheduling the next page with a named callback."""
        page = GraphCollectionPage.from_payload(response.json())
        for resource in page.values:
            yield self.resource_to_item(graph_object(resource), response)
        if page.next_link:
            yield self.continuation_request(
                page.next_link, callback=self.parse, operation=self.operation
            )


__all__ = ["GraphCollectionSpider", "GraphObjectSpider"]

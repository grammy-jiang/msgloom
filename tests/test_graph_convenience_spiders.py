"""Use Graph convenience spiders without application settings or pipelines."""

import asyncio
import json
from dataclasses import dataclass

import pytest
from itemadapter import ItemAdapter
from scrapy import Field, Item, Request
from scrapy.http import TextResponse
from scrapy.utils.request import request_from_dict
from scrapy.utils.test import get_crawler

from microsoft_graph.items import GraphResourceItem
from microsoft_graph.protocol import GraphProtocolError
from microsoft_graph.spiders import GraphCollectionSpider, GraphObjectSpider


class ContactsSpider(GraphCollectionSpider):
    name = "contacts"
    endpoint = "/me/contacts"
    graph_permissions = ("Contacts.Read",)


def response(spider, payload):
    request = spider.graph_request(spider.endpoint, callback=spider.parse)
    return TextResponse(
        request.url,
        request=request,
        encoding="utf-8",
        body=json.dumps(payload).encode(),
    )


def test_minimal_collection_default_item_and_opaque_pagination():
    crawler = get_crawler(ContactsSpider)
    spider = ContactsSpider.from_crawler(crawler)

    async def first():
        return await anext(spider.start())

    request = asyncio.run(first())
    if request.url != "https://graph.microsoft.com/v1.0/me/contacts":
        pytest.fail("Declarative endpoint must schedule the first request")
    if crawler.settings.getdict("ITEM_PIPELINES"):
        pytest.fail("Framework must not require persistence pipelines")
    link = request.url + "?$skiptoken=A%2fb+%2B"
    outputs = list(
        spider.parse(
            response(
                spider,
                {
                    "value": [{"id": "one"}, {"id": "two"}],
                    "@odata.nextLink": link,
                },
            )
        )
    )
    if len(outputs) != 3 or not isinstance(outputs[0], GraphResourceItem):
        pytest.fail("Default collection must emit one item per resource")
    if ItemAdapter(outputs[0]).asdict()["resource"] != {"id": "one"}:
        pytest.fail("Default dataclass must work with Scrapy's item adapter")
    continuation = outputs[-1]
    if not isinstance(continuation, Request) or continuation.url != link:
        pytest.fail("Pagination must emit a native request preserving URL bytes")
    restored = request_from_dict(continuation.to_dict(spider=spider), spider=spider)
    if restored.callback != spider.parse or not restored.meta.get("verbatim_url"):
        pytest.fail("Pagination must survive named-callback serialization")
    if list(spider.parse(response(spider, {"value": []}))) != []:
        pytest.fail("Terminal empty collections must finish without requests")


@dataclass
class Contact:
    id: str


class ContactItem(Item):
    id = Field()


@pytest.mark.parametrize("factory", [Contact, ContactItem, dict])
def test_resource_hook_supports_custom_dataclass_scrapy_item_and_dict(factory):
    class CustomContacts(ContactsSpider):
        def resource_to_item(self, resource, response):
            return factory(id=resource["id"])

    spider = CustomContacts()
    outputs = list(spider.parse(response(spider, {"value": [{"id": "one"}]})))
    if ItemAdapter(outputs[0]).asdict() != {"id": "one"}:
        pytest.fail("A consumer may replace the complete default item schema")


def test_object_validation_and_make_item_override():
    class Profile(GraphObjectSpider):
        name = "profile_example"
        endpoint = "/me"

        def make_item(self, resource, response):
            return resource

    spider = Profile()
    if list(spider.parse(response(spider, {"id": "user"}))) != [{"id": "user"}]:
        pytest.fail("Object spider must call the replaceable item factory")
    with pytest.raises(GraphProtocolError):
        list(spider.parse(response(spider, [])))


def test_collection_validates_resource_objects():
    spider = ContactsSpider()
    with pytest.raises(GraphProtocolError):
        list(spider.parse(response(spider, {"value": [42]})))

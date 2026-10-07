"""Exercise Graph envelopes independently of Scrapy and persistence."""

import pytest

from microsoft_graph.protocol import (
    GraphCollectionPage,
    GraphDeltaPage,
    GraphError,
    GraphProtocolError,
    graph_object,
)


@pytest.mark.parametrize("payload", [None, [], "object", 42])
def test_object_requires_json_object(payload):
    with pytest.raises(GraphProtocolError):
        graph_object(payload)


@pytest.mark.parametrize("payload", [{}, {"value": None}, {"value": {}}])
def test_collection_requires_value_list(payload):
    with pytest.raises(GraphProtocolError):
        GraphCollectionPage.from_payload(payload)


@pytest.mark.parametrize("link", ["", 0, [], {}, True])
@pytest.mark.parametrize("key", ["@odata.nextLink", "@odata.deltaLink"])
def test_links_require_nonempty_strings(link, key):
    with pytest.raises(GraphProtocolError):
        GraphDeltaPage.from_payload({"value": [], key: link}, strict=False)


def test_collection_preserves_opaque_link_and_values():
    link = "https://graph.microsoft.com/v1.0/me/contacts?$skiptoken=a%2fb+%2B&x=2&x=1"
    values = [{"id": "c1"}]
    page = GraphCollectionPage.from_payload({"value": values, "@odata.nextLink": link})
    if page.values is not values or page.next_link != link:
        pytest.fail("Graph values and opaque links must be preserved")


@pytest.mark.parametrize(
    "links",
    [{}, {"@odata.nextLink": "next", "@odata.deltaLink": "delta"}],
)
def test_delta_strict_state_requires_exactly_one_link(links):
    with pytest.raises(GraphProtocolError):
        GraphDeltaPage.from_payload({"value": [], **links})


def test_delta_compatibility_keeps_both_links_for_consumer_decision():
    page = GraphDeltaPage.from_payload(
        {"@odata.nextLink": "next", "@odata.deltaLink": "delta"},
        strict=False,
        missing_value_empty=True,
    )
    if page.values != [] or (page.next_link, page.delta_link) != ("next", "delta"):
        pytest.fail("Non-strict parsing must retain both links")
    with pytest.raises(GraphProtocolError):
        page.validate_state()


def test_legacy_links_can_be_validated_after_semantic_outputs():
    page = GraphDeltaPage.from_payload(
        {"value": [], "@odata.nextLink": "next", "@odata.deltaLink": 123},
        strict=False,
        validate_links=False,
        empty_links_absent=True,
    )
    if page.next_link != "next":
        pytest.fail("Next link must be readable without parsing unused delta link")
    with pytest.raises(GraphProtocolError):
        _ = page.delta_link


def test_error_envelope_walks_both_inner_error_spellings():
    error = GraphError.from_payload(
        {
            "error": {
                "code": "outer",
                "message": "private",
                "innerError": {"code": "inner", "innererror": {"code": "deep"}},
            }
        }
    )
    if error.codes != ("outer", "inner", "deep") or error.message != "private":
        pytest.fail("Expected outer-to-inner error codes")


@pytest.mark.parametrize("payload", [[], {}, {"error": []}])
def test_error_requires_an_object_envelope(payload):
    with pytest.raises(GraphProtocolError):
        GraphError.from_payload(payload)

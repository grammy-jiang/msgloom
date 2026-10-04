"""Keep encoded resource links separate from opaque provider identities."""

import json

import pytest
from scrapy import Request
from scrapy.crawler import Crawler
from scrapy.http import TextResponse
from scrapy.settings import Settings
from scrapy.utils.request import RequestFingerprinter

from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.teams.topology import TeamsChannelItem
from message_ingest.spiders.microsoft.teams.channel import (
    MicrosoftTeamsChannelDiscoverSpider,
)


def _inventory(channel_id: str):
    settings = Settings()
    settings.setmodule("message_ingest.settings")
    crawler = Crawler(MicrosoftTeamsChannelDiscoverSpider, settings)
    crawler.request_fingerprinter = RequestFingerprinter()
    spider = MicrosoftTeamsChannelDiscoverSpider.from_crawler(crawler)
    link = (
        "https://graph.microsoft.com/v1.0/tenants/tenant%2Fa/"
        "teams/team%2Fa/channels/channel%252Fa"
    )
    request = Request("https://graph.microsoft.com/v1.0/inventory")
    response = TextResponse(
        request.url,
        request=request,
        encoding="utf-8",
        body=json.dumps(
            {
                "value": [
                    {"id": channel_id, "membershipType": "shared", "@odata.id": link}
                ]
            }
        ).encode(),
    )
    return spider.parse_incoming_channels(
        response,
        purpose="link-identity",
        inventory_team_id="receiver",
        receiving_tenant_id="receiving-tenant",
    )


def test_incoming_channel_decodes_identity_once_and_encodes_followups_once():
    outputs = list(_inventory("channel%2Fa"))
    channels = [item for item in outputs if isinstance(item, TeamsChannelItem)]
    if len(channels) != 1:
        pytest.fail("Incoming channel observation was lost")
    channel = channels[0]
    if (channel.host_team_id, channel.host_tenant_id) != ("team/a", "tenant/a"):
        pytest.fail("Encoded URL segments became opaque provider identities")
    requests = [item for item in outputs if isinstance(item, Request)]
    if len(requests) != 5:
        pytest.fail("Expected detail, sharing, both memberships, and messages")
    prefix = "https://graph.microsoft.com/v1.0/teams/team%2Fa/channels/channel%252Fa"
    if any(not request.url.startswith(prefix) for request in requests):
        pytest.fail("Shared-channel follow-up double-encoded its team ID")


def test_incoming_link_channel_mismatch_fails_after_raw_evidence():
    outputs = _inventory("another-channel")
    if not isinstance(next(outputs), RawHttpEvidenceItem):
        pytest.fail("Invalid resource link lost its raw response evidence")
    with pytest.raises(ValueError, match="channel.*identity"):
        list(outputs)

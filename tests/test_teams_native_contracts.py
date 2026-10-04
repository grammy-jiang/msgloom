"""Run native Scrapy contracts against the actual Teams callback methods."""

from pathlib import Path

import pytest
from teams_support import crawl, json_reply, serve_graph

_WRAPPERS = '''
from scrapy.contracts import Contract
from scrapy.exceptions import ContractFail
from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.spiders.microsoft.teams.chat import MicrosoftTeamsChatDiscoverSpider
from message_ingest.spiders.microsoft.teams.channel import MicrosoftTeamsChannelDiscoverSpider

class EvidenceFirstContract(Contract):
    name = "evidence_first"

    def post_process(self, output):
        if not output or not isinstance(output[0], RawHttpEvidenceItem):
            raise ContractFail("Callback did not emit raw evidence first")
        raw = output[0]
        for item in output[1:]:
            if hasattr(item, "evidence_id") and item.evidence_id != raw.evidence_id:
                raise ContractFail("Semantic item lost its response evidence")

class ChatContractSpider(MicrosoftTeamsChatDiscoverSpider):
    name = "teams_chat_contract"

    def contract_inventory(self, response):
        """
        @url {chat_url}
        @returns items 2 2
        @returns requests 2 2
        @evidence_first
        """
        yield from self.parse_chats(response, purpose="teams-chat-contract")

class ChannelContractSpider(MicrosoftTeamsChannelDiscoverSpider):
    name = "teams_channel_contract"

    def contract_inventory(self, response):
        """
        @url {channel_url}
        @returns items 2 2
        @returns requests 4 4
        @evidence_first
        """
        yield from self.parse_associated_teams(response, purpose="teams-channel-contract")
'''


def test_native_scrapy_checks_real_teams_callback_contracts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Contracts exercise callbacks; separate crawl tests qualify persistence.

    Temporary subclasses add only local sample URLs and contract directives.
    Their wrappers invoke the production callbacks without replacing parsing,
    request builders, evidence construction, or provider settings.
    """
    with serve_graph() as fixture:
        fixture.add(
            "/v1.0/contract/chats",
            json_reply({"value": [{"id": "chat", "chatType": "group"}]}),
        )
        fixture.add(
            "/v1.0/contract/teams",
            json_reply({"value": [{"id": "team", "tenantId": "tenant"}]}),
        )
        module = tmp_path / "teams_contract_spiders.py"
        module.write_text(
            _WRAPPERS.format(
                chat_url=fixture.url("/v1.0/contract/chats"),
                channel_url=fixture.url("/v1.0/contract/teams"),
            )
        )
        monkeypatch.setenv("PYTHONPATH", str(tmp_path))
        result = crawl(
            tmp_path,
            fixture,
            ["check", "teams_chat_contract", "teams_channel_contract", "-v"],
            extra_settings={
                "SPIDER_MODULES": "teams_contract_spiders",
                "SPIDER_CONTRACTS": {
                    "teams_contract_spiders.EvidenceFirstContract": 100,
                },
            },
        )
        if result.returncode or "ERROR" in result.stderr:
            pytest.fail(result.stderr[-6000:])
        if "Ran 6 contracts" not in result.stderr or "OK" not in result.stderr:
            pytest.fail("Native check did not execute all six callback contracts")
        if sorted(seen.target for seen in fixture.seen) != [
            "/v1.0/contract/chats",
            "/v1.0/contract/teams",
        ]:
            pytest.fail("Contracts fetched unexpected URLs or skipped sample requests")

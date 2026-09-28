"""Verify the one-shot Microsoft Graph user-profile boundary."""

from __future__ import annotations

import argparse
import asyncio
import json

import pytest
from scrapy import Request
from scrapy.http import TextResponse
from scrapy.utils.test import get_crawler

from message_ingest.commands import microsoft as microsoft_command
from message_ingest.items import RawHttpEvidenceItem
from message_ingest.spiders.microsoft_profile import MicrosoftProfileSpider


def _spider() -> MicrosoftProfileSpider:
    crawler = get_crawler(MicrosoftProfileSpider)
    return MicrosoftProfileSpider.from_crawler(crawler)


def _response(spider: MicrosoftProfileSpider, payload: object) -> TextResponse:
    request = spider._request(
        f"{spider.graph_root}/me",
        callback=spider.parse_profile,
        purpose="user-profile",
        cb_kwargs={},
    )
    return TextResponse(
        request.url,
        request=request,
        body=json.dumps(payload).encode(),
        encoding="utf-8",
        headers={"Content-Type": "application/json"},
    )


def test_profile_spider_owns_user_read_and_evidence_only_pipeline() -> None:
    spider = _spider()
    settings = spider.crawler.settings

    if settings.getlist("MS_GRAPH_SCOPES") != ["User.Read"]:
        pytest.fail("Expected Microsoft profile to own User.Read")
    if settings.getbool("MSGLOOM_DELTA_CHECKPOINT_ENABLED"):
        pytest.fail("Expected Mail delta checkpoint disabled")
    if settings.getbool("MSGLOOM_CRAWL_STATUS_ENABLED"):
        pytest.fail("Expected Mail crawl status disabled")
    if settings.getdict("ITEM_PIPELINES") != {
        "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
    }:
        pytest.fail("Expected profile command to persist raw evidence only")


def test_profile_start_schedules_exactly_one_me_request() -> None:
    spider = _spider()

    async def request_sequence() -> Request:
        stream = spider.start()
        request = await anext(stream)
        with pytest.raises(StopAsyncIteration):
            await anext(stream)
        return request

    request = asyncio.run(request_sequence())
    if request.url != "https://graph.microsoft.com/v1.0/me":
        pytest.fail(f"Unexpected profile endpoint: {request.url}")
    if request.callback != spider.parse_profile or request.errback != spider.errback:
        pytest.fail("Expected provider-native callback and errback wiring")
    if request.cb_kwargs != {"purpose": "user-profile"}:
        pytest.fail("Expected serializable profile callback context")


def test_profile_parse_emits_evidence_before_retaining_profile() -> None:
    spider = _spider()
    payload = {
        "id": "user-1",
        "displayName": "Example User",
        "mail": "user@example.test",
    }

    output = spider.parse_profile(
        _response(spider, payload),
        purpose="user-profile",
    )
    first = next(output)
    if not isinstance(first, RawHttpEvidenceItem):
        pytest.fail("Expected raw evidence before accepting profile JSON")
    if spider.profile is not None:
        pytest.fail("Expected profile validation after raw evidence emission")

    with pytest.raises(StopIteration):
        next(output)
    if spider.profile != payload:
        pytest.fail("Expected validated Graph profile retained for command output")
    if spider.crawler.stats.get_value("msgloom/crawl/profile/retrieved_count") != 1:
        pytest.fail("Expected one profile retrieval stat")


def test_profile_rejects_missing_user_id_after_evidence() -> None:
    spider = _spider()
    output = spider.parse_profile(
        _response(spider, {"displayName": "Missing ID"}),
        purpose="user-profile",
    )
    if not isinstance(next(output), RawHttpEvidenceItem):
        pytest.fail("Expected malformed response evidence before validation")
    with pytest.raises(ValueError, match="non-empty id"):
        next(output)
    if spider.profile is not None:
        pytest.fail("Expected malformed profile not to become command output")


class FakeStats:
    """Return fixed counters for command result-gating tests."""

    def __init__(self, values: dict[str, int]) -> None:
        self.values = values

    def get_value(self, key: str, default=0):
        return self.values.get(key, default)


def test_profile_command_prints_validated_profile(monkeypatch, capsys) -> None:
    payload = {"id": "user-1", "displayName": "Example User"}

    class FakeCrawler:
        spider = type("SpiderResult", (), {"profile": payload})()
        stats = FakeStats({"msgloom/evidence/response_persisted_count": 1})

    monkeypatch.setattr(
        microsoft_command,
        "run_graph",
        lambda _command, _spider_name, _spider_args: FakeCrawler(),
    )
    command = microsoft_command.Command()
    command.exitcode = 0
    command.run([], _profile_opts())

    if json.loads(capsys.readouterr().out) != payload:
        pytest.fail("Expected command stdout to contain the profile JSON")


def test_profile_command_fails_when_no_profile_was_retrieved(
    monkeypatch, capsys
) -> None:
    class FakeCrawler:
        spider = type("SpiderResult", (), {"profile": None})()
        stats = FakeStats({"msgloom/evidence/response_persisted_count": 1})

    monkeypatch.setattr(
        microsoft_command,
        "run_graph",
        lambda _command, _spider_name, _spider_args: FakeCrawler(),
    )
    command = microsoft_command.Command()
    command.exitcode = 0
    command.run([], _profile_opts())

    if command.exitcode != 1:
        pytest.fail("Expected missing profile to fail the command")
    if capsys.readouterr().out:
        pytest.fail("Expected failed profile command not to print JSON")


def test_profile_command_fails_when_evidence_did_not_persist(
    monkeypatch, capsys
) -> None:
    payload = {"id": "user-1", "displayName": "Example User"}

    class FakeCrawler:
        spider = type("SpiderResult", (), {"profile": payload})()
        stats = FakeStats({})

    monkeypatch.setattr(
        microsoft_command,
        "run_graph",
        lambda _command, _spider_name, _spider_args: FakeCrawler(),
    )
    command = microsoft_command.Command()
    command.exitcode = 0
    command.run([], _profile_opts())

    if command.exitcode != 1:
        pytest.fail("Expected missing evidence persistence to fail the command")
    if capsys.readouterr().out:
        pytest.fail("Expected unpersisted profile not to be printed")


def _profile_opts() -> argparse.Namespace:
    return argparse.Namespace(
        section="profile",
        resource_or_action=None,
        action=None,
        message_ids=[],
        json=False,
        yes=False,
        folder=None,
        page_size=None,
        max_pages=None,
        reconcile=None,
        operation=None,
        acquisition_profile=None,
        start=None,
        end=None,
        calendar=None,
    )

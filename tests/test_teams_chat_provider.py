"""Pin the standalone Microsoft Teams T1 chat topology contract."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import fields
from urllib.parse import parse_qs, urlsplit

import pytest
from itemadapter import ItemAdapter
from scrapy.settings import Settings

from microsoft_graph.items.teams.chat import (
    TeamsChatItem,
    TeamsChatMemberItem,
    TeamsChatPinItem,
)
from microsoft_graph.spiders.teams.chat import MicrosoftTeamsChatSpider


def test_t1_scope_and_frozen_paths_encode_opaque_ids_once() -> None:
    spider = MicrosoftTeamsChatSpider(name="provider")
    chat_id = "19:A/B+=%2F ?é#@thread.v2"
    message_id = "msg/A+=%2F ?#"
    hosted_id = "host/A+=%2F ?#"
    chat = "/chats/19%3AA%2FB%2B%3D%252F%20%3F%C3%A9%23%40thread.v2"
    message = chat + "/messages/msg%2FA%2B%3D%252F%20%3F%23"
    hosted = message + "/hostedContents/host%2FA%2B%3D%252F%20%3F%23"
    cases = [
        (spider.chat_path(chat_id), chat),
        (spider.chat_members_path(chat_id), chat + "/members"),
        (spider.chat_message_path(chat_id, message_id), message),
        (spider.chat_pins_path(chat_id), chat + "/pinnedMessages"),
        (
            spider.hosted_contents_path(chat_id, message_id),
            message + "/hostedContents",
        ),
        (spider.hosted_content_path(chat_id, message_id, hosted_id), hosted),
        (
            spider.hosted_content_bytes_path(chat_id, message_id, hosted_id),
            hosted + "/$value",
        ),
    ]
    for actual, expected in cases:
        if actual != expected:
            pytest.fail(f"Teams T1 path changed: {actual!r} != {expected!r}")

    chat_query = parse_qs(urlsplit(spider.chats_path()).query)
    message_query = parse_qs(urlsplit(spider.chat_messages_path(chat_id)).query)
    if chat_query != {"$top": ["50"]} or message_query != {"$top": ["50"]}:
        pytest.fail("Frozen chat/message inventories must default to $top=50")

    settings = Settings()
    spider.update_settings(settings)
    if spider.required_graph_permissions(settings) != ("Chat.Read",):
        pytest.fail("T1 chat provider must require Chat.Read only")
    if settings.getlist("MS_GRAPH_SCOPES") != ["Chat.Read"]:
        pytest.fail("T1 chat provider must not request optional or write scopes")


@pytest.mark.parametrize("page_size", [1, 17, 50])
def test_chat_and_message_page_size_accepts_only_frozen_bounds(page_size: int) -> None:
    spider = MicrosoftTeamsChatSpider(name="provider")
    for path in (
        spider.chats_path(page_size=page_size),
        spider.chat_messages_path("chat", page_size=page_size),
    ):
        if parse_qs(urlsplit(path).query).get("$top") != [str(page_size)]:
            pytest.fail(f"Page size {page_size} was not retained")


@pytest.mark.parametrize("page_size", [0, 51, -1, True, 1.5, "50"])
def test_chat_and_message_page_size_rejects_invalid_values(page_size) -> None:
    spider = MicrosoftTeamsChatSpider(name="provider")
    with pytest.raises((TypeError, ValueError)):
        spider.chats_path(page_size=page_size)
    with pytest.raises((TypeError, ValueError)):
        spider.chat_messages_path("chat", page_size=page_size)


def test_modified_window_uses_matching_descending_filter() -> None:
    spider = MicrosoftTeamsChatSpider(name="provider")
    lower = "2026-10-01T00:00:00.123Z"
    upper = "2026-10-04T00:00:00+00:00"
    path = spider.chat_messages_path(
        "chat",
        page_size=7,
        modified_after=lower,
        modified_before=upper,
    )
    query = parse_qs(urlsplit(path).query)
    expected_filter = (
        f"lastModifiedDateTime gt {lower} and lastModifiedDateTime lt {upper}"
    )
    if query != {
        "$top": ["7"],
        "$orderby": ["lastModifiedDateTime desc"],
        "$filter": [expected_filter],
    }:
        pytest.fail(f"Modified-time query changed: {query!r}")


@pytest.mark.parametrize(
    ("lower", "upper"),
    [
        (None, "2026-10-04T00:00:00Z"),
        ("2026-10-01T00:00:00Z", None),
        ("2026-10-01T00:00:00", "2026-10-04T00:00:00Z"),
        ("2026-10-01T01:00:00+01:00", "2026-10-04T00:00:00Z"),
        ("2026-10-04T00:00:00Z", "2026-10-04T00:00:00Z"),
        ("2026-10-05T00:00:00Z", "2026-10-04T00:00:00Z"),
        (" 2026-10-01T00:00:00Z", "2026-10-04T00:00:00Z"),
        ("not-a-time", "2026-10-04T00:00:00Z"),
    ],
)
def test_modified_window_rejects_partial_non_utc_or_non_increasing_bounds(
    lower: str | None,
    upper: str | None,
) -> None:
    spider = MicrosoftTeamsChatSpider(name="provider")
    with pytest.raises((TypeError, ValueError)):
        spider.chat_messages_path(
            "chat",
            modified_after=lower,
            modified_before=upper,
        )


@pytest.mark.parametrize(
    "operation,args",
    [
        ("chat_path", ("",)),
        ("chat_members_path", (None,)),
        ("chat_message_path", ("chat", "")),
        ("chat_pins_path", (False,)),
        ("hosted_contents_path", ("chat", "")),
        ("hosted_content_path", ("chat", "message", "")),
        ("hosted_content_bytes_path", ("chat", "message", None)),
    ],
)
def test_path_helpers_reject_missing_opaque_identity(
    operation: str, args: tuple
) -> None:
    spider = MicrosoftTeamsChatSpider(name="provider")
    with pytest.raises((TypeError, ValueError)):
        getattr(spider, operation)(*args)


def test_chat_projection_preserves_raw_falsey_and_nested_provider_fields() -> None:
    raw = {
        "id": "19:A/B%2F@thread.v2",
        "topic": "",
        "createdDateTime": "",
        "lastUpdatedDateTime": "",
        "chatType": "meeting",
        "webUrl": "",
        "tenantId": "",
        "onlineMeetingInfo": {},
        "viewpoint": {"isHidden": False, "lastMessageReadDateTime": ""},
        "isHiddenForAllMembers": False,
        "future": {"unknown": [0, False, ""]},
    }
    item = TeamsChatItem.from_graph(raw)
    if item.raw is not raw or item.chat_id != raw["id"]:
        pytest.fail("Chat raw object or opaque identity changed")
    mapping = {
        "topic": "topic",
        "created_date_time": "createdDateTime",
        "last_updated_date_time": "lastUpdatedDateTime",
        "chat_type": "chatType",
        "web_url": "webUrl",
        "tenant_id": "tenantId",
        "online_meeting_info": "onlineMeetingInfo",
        "viewpoint": "viewpoint",
        "is_hidden_for_all_members": "isHiddenForAllMembers",
    }
    for name, key in mapping.items():
        if getattr(item, name) is not raw[key]:
            pytest.fail(f"Chat field {key} was normalized or copied")


def test_member_projection_keeps_federation_context_and_opaque_membership_id() -> None:
    raw = {
        "id": "M/A+=%2F opaque",
        "@odata.type": "#microsoft.graph.aadUserConversationMember",
        "displayName": "",
        "roles": [],
        "visibleHistoryStartDateTime": "",
        "email": "",
        "tenantId": "tenant/opaque",
        "userId": "user/opaque",
        "future": {"identityType": False},
    }
    item = TeamsChatMemberItem.from_graph(raw, chat_id="chat/opaque")
    if (item.chat_id, item.member_id, item.raw) != (
        "chat/opaque",
        "M/A+=%2F opaque",
        raw,
    ):
        pytest.fail("Member scoped identity or raw provider object changed")
    mapping = {
        "odata_type": "@odata.type",
        "display_name": "displayName",
        "roles": "roles",
        "visible_history_start_date_time": "visibleHistoryStartDateTime",
        "email": "email",
        "tenant_id": "tenantId",
        "user_id": "userId",
    }
    for name, key in mapping.items():
        if getattr(item, name) is not raw[key]:
            pytest.fail(f"Member field {key} was normalized or copied")


def test_pin_projection_is_a_separate_relation_without_message_parsing() -> None:
    expanded = {"id": "message/opaque", "body": {"content": ""}, "future": False}
    raw = {"id": "message/opaque", "message": expanded, "unknown": 0}
    item = TeamsChatPinItem.from_graph(raw, chat_id="chat/opaque")
    if (item.chat_id, item.message_id, item.raw) != (
        "chat/opaque",
        "message/opaque",
        raw,
    ):
        pytest.fail("Pin relation lost chat-scoped opaque identity")
    if item.message is not expanded:
        pytest.fail("Expanded pin message must remain raw nested provider data")


@pytest.mark.parametrize(
    "provider,context",
    [
        (TeamsChatItem, {}),
        (TeamsChatMemberItem, {"chat_id": "chat"}),
        (TeamsChatPinItem, {"chat_id": "chat"}),
    ],
)
@pytest.mark.parametrize("raw", [None, [], {}, {"id": ""}, {"id": False}])
def test_provider_items_reject_unstable_resource_identity(
    provider,
    context: dict[str, str],
    raw,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        provider.from_graph(raw, **context)


@pytest.mark.parametrize(
    "provider",
    [TeamsChatItem, TeamsChatMemberItem, TeamsChatPinItem],
)
def test_provider_items_are_slotted_raw_and_without_application_provenance(
    provider,
) -> None:
    context = {} if provider is TeamsChatItem else {"chat_id": "chat"}
    item = provider.from_graph(
        {"id": "opaque", "unknown": [0, False, ""]},
        **context,
    )
    if hasattr(item, "__dict__"):
        pytest.fail("Teams provider items must remain slotted dataclasses")
    if ItemAdapter(item).asdict()["raw"]["unknown"] != [0, False, ""]:
        pytest.fail("ItemAdapter must retain unknown provider values")
    forbidden = {"observed_at", "evidence_id", "run_id", "source_id"}
    if forbidden.intersection(field.name for field in fields(provider)):
        pytest.fail("Application provenance leaked into Teams provider items")


@pytest.mark.parametrize("provider", [TeamsChatMemberItem, TeamsChatPinItem])
def test_scoped_relations_require_parent_chat_identity(provider) -> None:
    with pytest.raises(ValueError):
        provider.from_graph({"id": "resource"}, chat_id="")


def test_teams_chat_provider_imports_without_application_or_message_lane() -> None:
    code = """
import importlib.abc
import sys
class Forbid(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        forbidden = {
            "message_ingest",
            "msgloom",
            "sqlalchemy",
            "microsoft_graph.items.teams.message",
        }
        if fullname in forbidden or fullname.split(".")[0] in {
            "message_ingest",
            "msgloom",
            "sqlalchemy",
        }:
            raise ImportError(f"Forbidden dependency: {fullname}")
sys.meta_path.insert(0, Forbid())
from microsoft_graph.items.teams.chat import (
    TeamsChatItem, TeamsChatMemberItem, TeamsChatPinItem,
)
from microsoft_graph.spiders.teams.chat import MicrosoftTeamsChatSpider
spider = MicrosoftTeamsChatSpider(name="standalone")
spider.graph_request(spider.chats_path())
spider.graph_request(spider.chat_messages_path("chat"))
TeamsChatItem.from_graph({"id": "chat"})
TeamsChatMemberItem.from_graph({"id": "member"}, chat_id="chat")
TeamsChatPinItem.from_graph({"id": "message"}, chat_id="chat")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode:
        pytest.fail(result.stderr)

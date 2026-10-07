"""Verify the mailbox-level Outlook mailFolder delta lifecycle."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from scrapy.http import TextResponse
from scrapy.utils.test import get_crawler
from sqlalchemy import text

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.items.microsoft.outlook.email import (
    OutlookFolderDeltaCheckpointCandidateItem,
    OutlookMailFolderItem,
    OutlookMailFolderRemovalItem,
)
from message_ingest.spiders.microsoft.outlook.email.folder_delta import (
    OutlookFolderDeltaSpider,
)
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
    OutlookFolderDeltaCheckpointStore,
)


def _spider(tmp_path: Path) -> OutlookFolderDeltaSpider:
    crawler = get_crawler(
        OutlookFolderDeltaSpider,
        settings_dict={
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        },
    )
    spider = OutlookFolderDeltaSpider.from_crawler(crawler, page_size="50")
    crawler.spider = spider
    return spider


async def _collect_start(spider):
    return [value async for value in spider.start()]


def _response(request, payload: dict) -> TextResponse:
    return TextResponse(
        request.url,
        request=request,
        body=json.dumps(payload).encode(),
        encoding="utf-8",
        headers={"Content-Type": ["application/json"]},
    )


def test_initial_folder_delta_follows_opaque_nextlink_and_stages_cursor(
    tmp_path: Path,
) -> None:
    spider = _spider(tmp_path)
    first = asyncio.run(_collect_start(spider))[0]
    if "/me/mailFolders/delta?" not in first.url:
        pytest.fail("Expected initial mailFolder delta request")
    next_link = (
        "https://graph.microsoft.com/v1.0/me/mailFolders/delta?$skiptoken=opaque"
    )
    output = list(
        spider.parse_folder_delta(
            _response(
                first,
                {
                    "value": [
                        {
                            "id": "f1",
                            "displayName": "Inbox",
                            "childFolderCount": 0,
                            "totalItemCount": 1,
                            "unreadItemCount": 0,
                            "isHidden": False,
                        }
                    ],
                    "@odata.nextLink": next_link,
                },
            ),
            **first.cb_kwargs,
        )
    )
    if not any(isinstance(value, OutlookMailFolderItem) for value in output):
        pytest.fail("Expected folder delta upsert item")
    continuation = next(value for value in output if hasattr(value, "url"))
    if (
        continuation.url != next_link
        or continuation.meta.get("verbatim_url") is not True
    ):
        pytest.fail("Expected opaque mailFolder continuation URL")

    final = list(
        spider.parse_folder_delta(
            _response(
                continuation,
                {
                    "value": [{"id": "gone", "@removed": {"reason": "deleted"}}],
                    "@odata.deltaLink": "https://graph.microsoft.com/v1.0/me/mailFolders/delta?$deltatoken=done",
                },
            ),
            **continuation.cb_kwargs,
        )
    )
    if not any(isinstance(value, OutlookMailFolderRemovalItem) for value in final):
        pytest.fail("Expected explicit folder removal item")
    if not any(
        isinstance(value, OutlookFolderDeltaCheckpointCandidateItem) for value in final
    ):
        pytest.fail("Expected terminal folder delta checkpoint candidate")


def test_folder_delta_removal_clears_message_cursor(tmp_path: Path) -> None:
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        store = OutlookMailStore(catalog, source_id="source-1")
        store.upsert_folder(
            folder={"id": "gone", "displayName": "Gone"},
            evidence_id=None,
            observed_at="2026-09-28T00:00:00+00:00",
            run_id="baseline",
        )
        checkpoints = OutlookDeltaCheckpointStore(catalog, "source-1")
        checkpoints.write_candidate(
            run_id="baseline",
            folder_id="gone",
            delta_link="https://graph.test/gone?$deltatoken=old",
            observed_at="2026-09-28T00:00:00+00:00",
        )
        checkpoints.commit("baseline")
        store.mark_folder_removed(
            folder_id="gone",
            run_id="folder-delta-run",
            observed_at="2026-09-28T01:00:00+00:00",
            evidence_id=None,
            reason="deleted",
        )
        folders = OutlookFolderDeltaCheckpointStore(catalog, "source-1")
        folder_cursor = "https://graph.test/me/mailFolders/delta?$deltatoken=done"
        folders.write_candidate(
            run_id="folder-delta-run",
            delta_link=folder_cursor,
            observed_at="2026-09-28T01:00:00+00:00",
        )
        if store.folder_presence(folder_id="gone") is not True:
            pytest.fail("Staged folder removal changed committed presence")
        if checkpoints.get_delta_link("gone") != (
            "https://graph.test/gone?$deltatoken=old"
        ):
            pytest.fail("Staged folder removal changed the message cursor")
        if folders.get_delta_link() is not None:
            pytest.fail("Staged folder candidate advanced the folder cursor")
        with catalog.Session() as session:
            release_count = session.execute(
                text("SELECT count(*) FROM acquisition_release_groups")
            ).scalar_one()
        if release_count != 0:
            pytest.fail("Staged folder removal published an authority release")

        folders.commit("folder-delta-run")
        if store.folder_presence(folder_id="gone") is not False:
            pytest.fail("Expected folder delta tombstone to mark folder absent")
        if checkpoints.get_delta_link("gone") is not None:
            pytest.fail("Expected folder removal to clear stale message delta cursor")
        if folders.get_delta_link() != folder_cursor:
            pytest.fail("Expected committed folder delta cursor")
        with catalog.Session() as session:
            groups = [
                json.loads(payload)
                for payload in session.scalars(
                    text("SELECT payload FROM acquisition_release_groups")
                )
            ]
            entries = [
                json.loads(payload)
                for payload in session.scalars(
                    text("SELECT payload FROM acquisition_release_entries")
                )
            ]
        if len(groups) != 1 or (
            groups[0]["source_id"],
            groups[0]["owner_run_id"],
            groups[0]["subject_kind"],
        ) != ("source-1", "folder-delta-run", "folder_delta"):
            pytest.fail("Expected one matching folder authority release")
        if not any(
            entry["entry_kind"] == "transition"
            and entry["resource_kind"] == "mail_folder"
            and entry["resource_identity"] == "gone"
            and entry["scope_kind"] == "mail_folder"
            and entry["scope_identity"] == "gone"
            for entry in entries
        ):
            pytest.fail("Folder authority release omitted the scoped removal")
    finally:
        catalog.close()


def test_folder_delta_checkpoint_store_promotes_only_candidate(tmp_path: Path) -> None:
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        store = OutlookFolderDeltaCheckpointStore(catalog, "source-1")
        if store.get_delta_link() is not None:
            pytest.fail("Expected no initial folder delta cursor")
        store.write_candidate(
            run_id="run-1",
            delta_link="https://graph.test/me/mailFolders/delta?$deltatoken=done",
            observed_at="2026-09-28T00:00:00+00:00",
        )
        if store.get_delta_link() is not None:
            pytest.fail("Candidate must not be visible as committed cursor")
        store.commit("run-1")
        if "$deltatoken=done" not in (store.get_delta_link() or ""):
            pytest.fail("Expected committed folder delta cursor")
    finally:
        catalog.close()


def _http_failure(request, status: int):
    from scrapy.http import Response
    from scrapy.spidermiddlewares.httperror import HttpError
    from twisted.python.failure import Failure

    response = Response(request.url, status=status, request=request)
    failure = Failure(HttpError(response, "filtered"))
    failure.__dict__["request"] = request
    return failure


def test_folder_delta_410_resets_once_without_failing_run(tmp_path: Path) -> None:
    from scrapy import Request

    spider = _spider(tmp_path)
    request = spider._delta_request(
        "https://graph.microsoft.com/v1.0/me/mailFolders/delta?$deltatoken=old",
        page_number=1,
        from_checkpoint=True,
        reset_count=0,
    )
    output = list(spider.errback(_http_failure(request, 410)))
    reset = next(value for value in output if isinstance(value, Request))
    if reset.cb_kwargs["reset_count"] != 1:
        pytest.fail("Expected one bounded mailFolder delta reset")
    if "$deltatoken=" in reset.url:
        pytest.fail("Expected reset to restart initial mailFolder delta")
    if spider.run_failed:
        pytest.fail("First expired folder cursor should be recoverable")


def test_folder_delta_second_410_fails_instead_of_looping(tmp_path: Path) -> None:
    from message_ingest.items.acquisition import AcquisitionFailureItem

    spider = _spider(tmp_path)
    request = spider._initial_request(reset_count=1)
    output = list(spider.errback(_http_failure(request, 410)))
    if not spider.run_failed:
        pytest.fail("Second folder delta 410 must fail the logical run")
    if not any(isinstance(value, AcquisitionFailureItem) for value in output):
        pytest.fail("Expected terminal acquisition failure after second 410")


@pytest.mark.parametrize(
    ("url", "page_number", "from_checkpoint", "opaque"),
    [
        ("https://graph.microsoft.com/v1.0/local?$skiptoken=literal", 1, False, False),
        ("https://graph.microsoft.com/v1.0/cursor?state=A%2fb+z", 1, True, True),
        ("https://graph.microsoft.com/v1.0/cursor?state=A%2fb+z", 2, False, True),
    ],
)
def test_folder_delta_provenance_controls_opaque_urls(
    tmp_path: Path,
    url: str,
    page_number: int,
    from_checkpoint: bool,
    opaque: bool,
) -> None:
    spider = _spider(tmp_path)
    request = spider._delta_request(
        url,
        page_number=page_number,
        from_checkpoint=from_checkpoint,
        reset_count=0,
    )
    if bool(request.meta.get("verbatim_url")) != opaque:
        pytest.fail("Folder cursor handling must follow provenance, not URL text")
    if opaque and request.url != url:
        pytest.fail("Provider cursor bytes changed")
    if request.headers.get("Prefer") != b"odata.maxpagesize=50":
        pytest.fail("Folder delta representation preference changed")

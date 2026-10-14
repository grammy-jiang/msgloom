"""Committed Mail checkpoint URL and Scrapy request provenance contracts."""

import asyncio
from pathlib import Path

import pytest

from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
)
from tests.test_outlook_mail_delta import _collect_start, _db_url, _spider


def test_existing_checkpoint_is_used_verbatim_and_bypasses_http_cache(
    tmp_path: Path,
) -> None:
    store = OutlookDeltaCheckpointStore(_db_url(tmp_path), "test-source")
    store.write_candidate(
        baseline_identity=store.get_delta_start("folder-inbox")[1],
        run_id="setup",
        folder_id="folder-inbox",
        delta_link="https://graph.microsoft.com/v1.0/me/mailFolders/folder-inbox/messages/delta?$deltatoken=opaque-existing",
        observed_at="2026-09-26T00:00:00+00:00",
    )
    store.commit("setup")
    store.close()

    spider = _spider(tmp_path)
    asyncio.run(_collect_start(spider))
    request = spider._message_delta_start_request("folder-inbox")
    if not request.url.endswith("$deltatoken=opaque-existing"):
        pytest.fail('Expected: request.url.endswith("$deltatoken=opaque-existing")')
    if request.meta["dont_cache"] is not True:
        pytest.fail('Expected: request.meta["dont_cache"] is True')
    if request.cb_kwargs["folder_id"] != "folder-inbox":
        pytest.fail('Expected: request.cb_kwargs["folder_id"] == "folder-inbox"')

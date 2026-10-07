"""Check release visibility through the existing native Scrapy command path."""

import json

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog.models.handoff import AcquisitionReleaseGroup
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from tests.test_onedrive_resync_crawl import (
    _baseline,
    _catalog,
    _crawl,
    resync_server,
)

__all__ = ["resync_server"]


def _entries(catalog):
    """Read the immutable public release API for the local fixture source."""
    ledger = AcquisitionHandoffStore(catalog)
    return ledger.list_release_entries(
        "onedrive-resync-fixture", AcquisitionStream.ONEDRIVE
    )


@pytest.mark.parametrize("failure", ["http_error", "malformed", "item_failure"])
def test_incomplete_native_reset_retains_prior_publication(
    tmp_path, resync_server, failure
):
    """Failure after partial or terminal input cannot publish reset absence."""
    origin, state, _seen = resync_server
    _baseline(tmp_path, origin, state)
    catalog = _catalog(tmp_path)
    try:
        before = _entries(catalog)
        if not before:
            pytest.fail("Native baseline checkpoint did not publish its entries")
        setup = ""
        if failure == "item_failure":
            setup = """
from message_ingest.items.microsoft.onedrive import (
    OneDriveDeltaCheckpointCandidateItem,
)
from message_ingest.pipelines.microsoft.onedrive import OneDrivePipeline
original_process = OneDrivePipeline.process_item

async def fail_after_candidate(self, item):
    result = await original_process(self, item)
    if isinstance(item, OneDriveDeltaCheckpointCandidateItem):
        raise RuntimeError("injected terminal item failure")
    return result

OneDrivePipeline.process_item = fail_after_candidate
"""
        else:
            state["mode"] = failure
        result = _crawl(tmp_path, origin, setup=setup)
        if result.returncode != 1:
            pytest.fail("Incomplete reset did not fail the native command")
        if _entries(catalog) != before:
            pytest.fail("Incomplete native reset advanced the release stream")
    finally:
        catalog.close()


def test_complete_native_reset_publishes_one_exact_revision_group(
    tmp_path, resync_server
):
    """Natural idle publishes exact staged observations after pipeline drain."""
    origin, state, _seen = resync_server
    _baseline(tmp_path, origin, state)
    result = _crawl(tmp_path, origin)
    if result.returncode or "ERROR" in result.stderr:
        pytest.fail(result.stderr)
    catalog = _catalog(tmp_path)
    try:
        with catalog.Session() as session:
            rows = [
                json.loads(payload)
                for payload in session.scalars(select(AcquisitionReleaseGroup.payload))
            ]
        if sorted(row["authority_revision"] for row in rows) != ["1", "2"]:
            pytest.fail("Native reset did not publish exactly one new group")
        group_id = next(
            row["release_group_id"]
            for row in _entries(catalog)
            if json.loads(row["payload"])["resource_identity"] == "new"
        )
        ledger = AcquisitionHandoffStore(catalog)
        facts = [
            fact
            for row in _entries(catalog)
            if row["release_group_id"] == group_id
            for fact in ledger.load_release_facts(row["release_entry_seq"])
        ]
        primary = [fact for fact in facts if fact.fact_kind == "resource_observation"]
        absent = [fact for fact in facts if fact.transition_reason == "resync_absent"]
        if {fact.resource_identity for fact in primary} != {"kept", "new"}:
            pytest.fail("Native reset published another attempt's resources")
        if any(
            fact.source_version_locator is None
            or fact.source_version_locator.kind != "observation"
            for fact in primary
        ):
            pytest.fail("Native reset lost immutable observation locators")
        if [fact.resource_identity for fact in absent] != ["absent"]:
            pytest.fail("Native reset absence does not match its complete scope")
    finally:
        catalog.close()

"""Keep reuse admission separate from current-attempt refresh obligations."""

import asyncio
import json

import pytest
from _full_completion_fixtures import LATER, set_surface
from scrapy import signals
from sqlalchemy import select
from test_handoff_release_extension import entries, release_case

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

__all__ = ["release_case"]


@pytest.mark.parametrize("operation", ["enrich", "refresh"])
def test_idle_reuse_does_not_weaken_refresh_attempt(release_case, operation):
    """Enrich can bind old completion; an unexecuted refresh cannot."""
    crawler, spider, service, _, _ = release_case
    spider.operation = operation
    spider.run_id = "later-run"
    with service.catalog.Session() as session:
        before = dict(
            session.execute(
                select(AcquisitionFact.fact_id, AcquisitionFact.payload)
            ).all()
        )
    crawler.signals.send_catch_log(signal=signals.spider_idle, spider=spider)
    rows = entries(release_case)
    if operation == "enrich":
        if (
            len(rows) != 1
            or json.loads(rows[0]["payload"])["resource_identity"] != "one"
        ):
            pytest.fail("Explicit enrich did not release its complete reused target")
    elif rows:
        pytest.fail("Old completion satisfied an unexecuted refresh attempt")
    with service.catalog.Session() as session:
        after = dict(
            session.execute(
                select(AcquisitionFact.fact_id, AcquisitionFact.payload)
            ).all()
        )
    if after != before:
        pytest.fail("Release revalidation rewrote acquisition facts")


def test_idle_rechecks_invalid_surface_after_planner(release_case):
    """Planning success cannot authorize a surface invalidated before idle."""
    crawler, spider, service, _, stream = release_case
    family = "mail" if stream == AcquisitionStream.OUTLOOK_MAIL else "calendar"
    spider.operation = "enrich"
    spider.run_id = "later-run"
    # Calendar's fixture uses the same persisted state as its native planner.
    # Mail's native no-work planner is covered by the local Graph crawl tests.
    if family == "calendar":
        spider.event_ids = ("one",)

        async def collect_start():
            return [item async for item in spider.start()]

        if asyncio.run(collect_start()):
            pytest.fail("Complete Calendar fixture unexpectedly scheduled work")
    store_cls = OutlookMailStore if family == "mail" else OutlookCalendarStore
    store = store_cls(service.catalog, source_id="source")
    set_surface(
        store,
        family,
        "one",
        "attachments",
        f"{family}-one-run-attachments",
        run="later-run",
        # Mail stores only terminal statuses; an older profile is incomplete.
        status="acquired" if family == "mail" else "failed",
        profile="outlook-mail-full-v0" if family == "mail" else None,
        at=LATER,
    )
    crawler.signals.send_catch_log(signal=signals.spider_idle, spider=spider)
    if entries(release_case):
        pytest.fail("Idle reused a profile after its required surface failed")

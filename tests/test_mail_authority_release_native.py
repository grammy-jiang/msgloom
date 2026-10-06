"""Exercise authority admission through native crawler idle signals."""

import pytest
from scrapy import signals
from scrapy.utils.misc import build_from_crawler
from sqlalchemy import text
from test_outlook_delta_integrity import _complete_candidate, _crawler, _enabled_policy

from message_ingest.extensions.catalog import CatalogService
from message_ingest.extensions.microsoft.outlook.email.checkpoint import (
    OutlookDeltaCheckpointExtension,
)
from message_ingest.spiders.microsoft.outlook.email._delta_state import (
    MailDeltaCommitMode,
)
from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider
from message_ingest.sync.microsoft.outlook.email.promotion import (
    promote_validated_mail_delta,
)


@pytest.mark.parametrize("deferred", [False, True])
def test_native_idle_defers_rules_enabled_authority(tmp_path, deferred):
    crawler = _crawler(tmp_path)
    kwargs = {}
    if deferred:
        kwargs = {
            "_mail_rule_policy": _enabled_policy(),
            "_mail_delta_commit_mode": MailDeltaCommitMode.DEFERRED,
        }
    spider = OutlookDeltaSpider.from_crawler(crawler, **kwargs)
    service = CatalogService.from_crawler(crawler)
    try:
        _complete_candidate(crawler, spider)
        extension = build_from_crawler(OutlookDeltaCheckpointExtension, crawler)
        store = extension.lifecycle
        store.upsert_folder(
            folder={"id": "folder-inbox"},
            run_id=spider.run_id,
            evidence_id=None,
            observed_at="2026-10-01T00:00:00+00:00",
        )
        store.write_folder_snapshot_candidate(
            run_id=spider.run_id,
            observed_at="2026-10-01T00:00:00+00:00",
            evidence_id=None,
        )
        store.write_message_presence_candidate(
            run_id=spider.run_id,
            observed_at="2026-10-01T00:00:00+00:00",
            evidence_id=None,
        )
        crawler.signals.send_catch_log(signals.spider_idle, spider=spider)
        with service.catalog.Session() as session:
            groups = session.execute(
                text("SELECT count(*) FROM acquisition_release_groups")
            ).scalar_one()
        if groups != (0 if deferred else 1):
            pytest.fail("Native idle did not preserve Mail authority ownership")
        if not deferred:
            return
        if extension.store.get_delta_link("folder-inbox") is not None:
            pytest.fail("Deferred native idle committed its cursor")
        validated = spider.validated_delta_run
        if validated is None:
            pytest.fail("Deferred native idle lost its validated handoff")
        promote_validated_mail_delta(
            service.catalog, source_id="test-source", validated=validated
        )
        with service.catalog.Session() as session:
            groups = session.execute(
                text("SELECT count(*) FROM acquisition_release_groups")
            ).scalar_one()
        if groups != 1 or extension.store.get_delta_link("folder-inbox") is None:
            pytest.fail("Shared deferred promotion failed to publish authority")
    finally:
        service.spider_closed(spider, "finished")

"""Real Scrapy callbacks, pipelines and idle CAS over local Graph fixtures."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from scrapy import signals
from scrapy.crawler import AsyncCrawlerRunner
from scrapy.http import TextResponse
from scrapy.settings import Settings
from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.microsoft.outlook.email import (
    MessageObservation,
    MessageRecord,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.items.microsoft.outlook.email import OutlookMailItem
from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
)


class FixtureGraphHandler:
    """Supply deterministic Graph responses through the native downloader API."""

    lazy = False
    winner_captured: asyncio.Event
    loser_captured: asyncio.Event
    winner_closed: asyncio.Event

    def __init__(self, crawler):
        self.flavor = crawler.settings["FIXTURE_FLAVOR"]

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    async def download_request(self, request):
        path = urlsplit(request.url).path
        if path.endswith("/mailFolders"):
            payload = {"value": [{"id": "inbox", "childFolderCount": 0}]}
        elif path.endswith("/childFolders"):
            payload = {"value": []}
        elif path.endswith("/messages/delta"):
            if self.flavor == "loser":
                await asyncio.wait_for(self.winner_captured.wait(), 30)
            payload = {
                "value": [
                    {
                        "id": "m",
                        "parentFolderId": "moved-to",
                        "changeKey": self.flavor,
                        "subject": self.flavor,
                    }
                ],
                "@odata.nextLink": "https://graph.microsoft.com/" + self.flavor,
            }
        elif path == "/winner":
            await asyncio.wait_for(self.loser_captured.wait(), 30)
            payload = {
                "value": [],
                "@odata.deltaLink": "https://graph.microsoft.com/won",
            }
        elif path == "/loser":
            await asyncio.wait_for(self.winner_closed.wait(), 30)
            payload = {
                "value": [
                    {
                        "id": "m",
                        "parentFolderId": "moved-again",
                        "changeKey": "late",
                        "subject": "late-loser",
                    }
                ],
                "@odata.deltaLink": "https://graph.microsoft.com/lost",
            }
        else:
            raise ValueError(f"Unexpected local Graph fixture URL: {path}")
        return TextResponse(
            request.url,
            request=request,
            encoding="utf-8",
            headers={"Content-Type": "application/json"},
            body=json.dumps(payload).encode(),
        )

    async def close(self):
        pass


async def run_fixture(root):
    """Overlap independent crawlers while preserving real pipeline ordering."""
    for name in ("winner_captured", "loser_captured", "winner_closed"):
        setattr(FixtureGraphHandler, name, asyncio.Event())
    settings = Settings()
    settings.setmodule("message_ingest.settings")
    settings.setdict(
        {
            "TWISTED_REACTOR_ENABLED": False,
            "DOWNLOAD_HANDLERS": {"https": FixtureGraphHandler},
            "MS_GRAPH_AUTH_METHOD": "none",
            "MS_GRAPH_AUTH_ENABLED": False,
            "MSGLOOM_SOURCE_ID": "native-authority",
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{root / 'catalog.db'}",
            "MSGLOOM_RAW_EVIDENCE_DIR": str(root / "evidence"),
            "AUTOTHROTTLE_ENABLED": False,
            "HTTPCACHE_ENABLED": False,
            "LOG_ENABLED": False,
        },
        priority="cmdline",
    )
    runner = AsyncCrawlerRunner(settings)
    tasks = []
    crawlers = []
    errors = []
    for flavor in ("winner", "loser"):
        crawler = runner.create_crawler(OutlookDeltaSpider)
        crawler.settings.set("FIXTURE_FLAVOR", flavor, priority="cmdline")
        crawlers.append((flavor, crawler))

        def scraped(item, response, spider, selected=flavor):
            if isinstance(item, OutlookMailItem):
                getattr(FixtureGraphHandler, selected + "_captured").set()

        crawler.signals.connect(scraped, signal=signals.item_scraped, weak=False)

        def failed(item, response, spider, failure):
            errors.append(failure.getTraceback())

        crawler.signals.connect(failed, signal=signals.item_error, weak=False)
        if flavor == "winner":

            def closed(spider, reason):
                FixtureGraphHandler.winner_closed.set()

            crawler.signals.connect(closed, signal=signals.spider_closed, weak=False)
        tasks.append(runner.crawl(crawler, reconcile_global="0"))
    try:
        await asyncio.wait_for(asyncio.gather(*tasks), 60)
    finally:
        (root / "errors.json").write_text(json.dumps(errors))
        (root / "stats.json").write_text(
            json.dumps(
                {flavor: crawler.stats.get_stats() for flavor, crawler in crawlers},
                default=str,
            )
        )


def test_native_late_loser_preserves_exact_original_folder_scope(tmp_path):
    """A callback after winner idle must neither publish nor change its row."""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import asyncio,sys; from pathlib import Path; "
                "from tests.test_mail_provisional_native import run_fixture; "
                "asyncio.run(run_fixture(Path(sys.argv[1])))"
            ),
            str(tmp_path),
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if completed.returncode:
        pytest.fail(completed.stderr[-6000:])
    stats = json.loads((tmp_path / "stats.json").read_text())
    if any(
        values.get("msgloom/persistence/item_error_count", 0)
        for values in stats.values()
    ):
        pytest.fail((tmp_path / "errors.json").read_text())
    if (
        stats["winner"].get("msgloom/checkpoint/outcome") != "committed"
        or stats["loser"].get("msgloom/checkpoint/error_stage") != "commit"
    ):
        pytest.fail("Native cursors did not resolve at the authority commit gate")
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.db'}")
    try:
        with catalog.Session() as session:
            row = session.scalar(
                select(MessageRecord).filter_by(
                    source_id="native-authority", message_id="m"
                )
            )
            if row is None or (row.subject, row.parent_folder_id) != (
                "winner",
                "moved-to",
            ):
                pytest.fail("Native projection did not retain the winning capture")
        ledger = AcquisitionHandoffStore(catalog)
        facts = [
            fact
            for entry in ledger.list_release_entries(
                "native-authority", AcquisitionStream.OUTLOOK_MAIL
            )
            for fact in ledger.load_release_facts(entry["release_entry_seq"])
            if fact.resource_kind == "message" and fact.component_kind is None
        ]
        if len(facts) != 1 or facts[0].evidence_id != row.latest_evidence_id:
            pytest.fail("Native release did not select the exact winning evidence")
        with catalog.Session() as session:
            captures = session.scalars(
                select(MessageObservation).filter_by(
                    source_id="native-authority", message_id="m"
                )
            ).all()
            if len(captures) != 3:
                pytest.fail("Native fixture did not retain the late losing callback")
        checkpoints = OutlookDeltaCheckpointStore(catalog, "native-authority")
        if checkpoints.get_delta_link("inbox") != "https://graph.microsoft.com/won":
            pytest.fail("Native original scope did not own the winning cursor")
    finally:
        catalog.close()

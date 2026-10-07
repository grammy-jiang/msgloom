"""Exercise default release registration through the public native lifecycle."""

import json
import subprocess
import sys

import pytest
from handoff_release_reader_helpers import bind_fixture_source
from scrapy.crawler import Crawler
from scrapy.exceptions import NotConfigured
from scrapy.spiderloader import SpiderLoader
from scrapy.utils.project import get_project_settings
from sqlalchemy import select
from test_outlook_crawls import ROOT, RUN_COMMAND, graph_server

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import AcquisitionReleaseGroup
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.extensions.handoff import HandoffReleaseExtension

__all__ = ["graph_server"]
EXTENSION = "message_ingest.extensions.handoff.HandoffReleaseExtension"


@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize("disabled", [False, True])
def test_default_crawl_publishes_unless_explicitly_disabled(
    tmp_path, graph_server, direct, disabled
):
    """Default settings must publish once after actual request/item drain."""
    bind_fixture_source(tmp_path / "mail.db", "source")
    database = f"sqlite:///{tmp_path / 'mail.db'}"
    settings = {
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_DATABASE_URL": database,
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        "MSGLOOM_SOURCE_ID": "source",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
        "MSGLOOM_CATALOG_ENABLED": "True",
        "MSGLOOM_RAW_EVIDENCE_ENABLED": "True",
        "HTTPCACHE_ENABLED": "False",
        "AUTOTHROTTLE_ENABLED": "False",
        "LOG_LEVEL": "INFO",
    }
    if disabled:
        settings["EXTENSIONS"] = json.dumps({EXTENSION: None})
    command = (
        ["crawl", "outlook_discover"]
        if direct
        else ["microsoft", "outlook", "mail", "discover"]
    )
    args = [sys.executable, "-c", RUN_COMMAND, graph_server, *command]
    for key, value in settings.items():
        args.extend(["-s", f"{key}={value}"])
    result = subprocess.run(
        args, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False
    )
    if result.returncode or "ERROR" in result.stderr:
        pytest.fail(result.stderr)
    catalog = Catalog(database)
    try:
        entries = AcquisitionHandoffStore(catalog).list_release_entries(
            "source", AcquisitionStream.OUTLOOK_MAIL
        )
        with catalog.Session() as session:
            groups = session.scalars(select(AcquisitionReleaseGroup.payload)).all()
        if disabled:
            if entries or groups:
                pytest.fail("Explicit extension disable still published a release")
            return
        if len(entries) != 2 or len(groups) != 1:
            pytest.fail("Default crawl did not publish two entries in one group")
        group = json.loads(groups[0])
        if group["coverage_kind"] != "complete" or group["authority_revision"]:
            pytest.fail("Default discovery changed completion or authority")
    finally:
        catalog.close()


@pytest.mark.parametrize(
    "name",
    [
        "microsoft_profile",
        "outlook_delta",
        "outlook_folder_delta",
        "outlook_calendar_delta",
        "microsoft_todo_sync",
        "microsoft_contacts_sync",
        "microsoft_contacts_delta",
        "microsoft_onedrive_delta",
    ],
)
def test_default_registration_preserves_authority_and_profile_exclusion(name):
    """Only supported non-authoritative subjects may own idle publication."""
    settings = get_project_settings()
    spider_class = SpiderLoader(settings).load(name)
    crawler = Crawler(spider_class, settings)
    with pytest.raises(NotConfigured, match="supported completion verifier"):
        HandoffReleaseExtension.from_crawler(crawler)

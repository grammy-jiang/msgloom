"""Exercise Mail discovery release through the native local Graph lifecycle."""

import json
import subprocess
import sys

import pytest
from handoff_release_reader_helpers import bind_fixture_source, read_published
from sqlalchemy import select
from test_outlook_crawls import ROOT, RUN_COMMAND, graph_server

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import AcquisitionReleaseGroup
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

__all__ = ["graph_server"]


@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize(
    "max_pages, count, coverage", [(0, 2, "complete"), (1, 1, "truncated")]
)
def test_native_mail_discovery_release(
    tmp_path, graph_server, direct, max_pages, count, coverage
):
    """Opt in locally while preserving default global activation policy."""
    bind_fixture_source(tmp_path / "mail.db", "source")
    runner = RUN_COMMAND.replace(
        'execute(["scrapy",',
        "import message_ingest.settings as settings\n"
        'settings.EXTENSIONS["message_ingest.extensions.handoff.HandoffReleaseExtension"] = 70\n'
        'execute(["scrapy",',
    )
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
    command = (
        ["crawl", "outlook_discover"]
        if direct
        else ["microsoft", "outlook", "mail", "discover"]
    )
    args = [
        sys.executable,
        "-c",
        runner,
        graph_server,
        *command,
    ]
    args.extend(
        ["-a", f"max_pages={max_pages}"] if direct else ["--max-pages", str(max_pages)]
    )
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
        primary = [
            row
            for row in entries
            if json.loads(row["payload"])["entry_kind"] == "resource"
        ]
        if len(entries) != count or len(primary) != count or len(groups) != 1:
            pytest.fail("Native discovery lost positive entries or its group")
        group = json.loads(groups[0])
        if group["coverage_kind"] != coverage or group["authority_revision"]:
            pytest.fail("Native discovery changed coverage or absence authority")
        if not direct:
            reads = read_published(
                tmp_path / "mail.db", tmp_path / "raw", "source", "outlook_mail"
            )
            expected = {
                (
                    json.loads(row["payload"])["entry_kind"],
                    json.loads(row["payload"])["resource_kind"],
                    json.loads(row["payload"])["resource_identity"],
                )
                for row in entries
            }
            if {
                (entry.entry_kind, entry.resource_kind, entry.resource_identity)
                for entry, _ in reads
            } != expected:
                pytest.fail("Mail Reader lost typed published entries")
            if any(entry.group.coverage_kind != coverage for entry, _ in reads):
                pytest.fail("Mail Reader changed complete/truncated coverage")
    finally:
        catalog.close()

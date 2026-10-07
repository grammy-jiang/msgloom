"""Real local Scrapy cache replay retains the second logical Mail run."""

import json
import subprocess
import sys

import pytest
from sqlalchemy import select
from test_outlook_crawls import ROOT, RUN_COMMAND, graph_server

from message_ingest.acquisition.handoff import FactSpec
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import (
    AcquisitionFact,
    AcquisitionReleaseEntry,
)
from message_ingest.catalog.models.microsoft.outlook.email import MessageObservation

__all__ = ["graph_server"]


@pytest.mark.parametrize("interrupted", [False, True])
def test_real_scrapy_http_cache_replay_retains_logical_run(
    tmp_path, graph_server, interrupted
):
    """Exercise native HttpCacheMiddleware and the enabled pipeline chain."""
    settings = {
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'mail.db'}",
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        "MSGLOOM_SOURCE_ID": "source",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
        "MSGLOOM_CATALOG_ENABLED": "True",
        "MSGLOOM_RAW_EVIDENCE_ENABLED": "True",
        "HTTPCACHE_ENABLED": "True",
        "HTTPCACHE_DIR": str(tmp_path / "cache"),
        "AUTOTHROTTLE_ENABLED": "False",
        "LOG_LEVEL": "INFO",
    }
    args = [
        sys.executable,
        "-c",
        RUN_COMMAND,
        graph_server,
        "microsoft",
        "outlook",
        "mail",
        "discover",
    ]
    for key, value in settings.items():
        args.extend(["-s", f"{key}={value}"])
    first_run = set()
    first_facts = []
    released_entries = []
    interrupt = """
from pathlib import Path
original_parse = OutlookDiscoverSpider.parse

def interrupted_parse(self, response, **kwargs):
    yield from original_parse(self, response, **kwargs)
    if kwargs.get("page_number") == 2:
        Path(__file__).with_suffix(".interrupted").write_text("page-2")
        raise RuntimeError("controlled traversal interruption")

OutlookDiscoverSpider.parse = interrupted_parse
"""
    for attempt in range(3):
        command = list(args)
        if interrupted and attempt == 0:
            runner = tmp_path / "interrupted_discovery.py"
            runner.write_text(
                f"import sys\nsys.path.insert(0, {str(ROOT)!r})\n"
                + RUN_COMMAND.replace(
                    'execute(["scrapy",', interrupt + '\nexecute(["scrapy",'
                )
            )
            command = [sys.executable, str(runner), *args[3:]]
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False
        )
        (tmp_path / f"crawl-{attempt}.stderr.log").write_text(result.stderr)
        (tmp_path / f"crawl-{attempt}.stdout.log").write_text(result.stdout)
        if interrupted and attempt == 0:
            marker = tmp_path / "interrupted_discovery.interrupted"
            if not marker.exists() or marker.read_text() != "page-2":
                pytest.fail("First traversal missed the controlled interruption")
            if "'spider_exceptions/RuntimeError': 1" not in result.stderr:
                pytest.fail("Controlled callback failure did not reach Scrapy")
        elif result.returncode or "ERROR" in result.stderr:
            pytest.fail(result.stderr)
        if attempt and "'httpcache/hit':" not in result.stderr:
            pytest.fail("Second crawl did not exercise native HTTP cache")
        catalog = Catalog(settings["MSGLOOM_DATABASE_URL"])
        try:
            with catalog.Session() as session:
                all_facts = [
                    FactSpec.from_json(p)
                    for p in session.scalars(select(AcquisitionFact.payload))
                ]
                primary = [
                    f for f in all_facts if f.fact_kind == "resource_observation"
                ]
                count = len(session.scalars(select(MessageObservation)).all())
                entries = [
                    (row.release_entry_seq, row.payload)
                    for row in session.scalars(select(AcquisitionReleaseEntry))
                ]
            if attempt == 0:
                first_facts = primary
                first_run = {f.run_id for f in primary}
                if len(first_run) != 1 or not primary:
                    pytest.fail("First real crawl did not stage primary state")
                if interrupted:
                    if entries:
                        pytest.fail("Interrupted traversal published staged facts")
                else:
                    if len(entries) != len(primary):
                        pytest.fail("Completed discovery did not publish every target")
                    released_entries = entries
                continue
            replay = [f for f in primary if f.run_id not in first_run]
            if len(replay) != attempt * len(first_facts) or count != len(first_facts):
                pytest.fail("Cache run lost provenance or duplicated observations")
            old = {f.resource_identity: f for f in first_facts}
            for fact in replay:
                original = old[fact.resource_identity]
                if (fact.storage_relation, fact.source_state_key, fact.evidence_id) != (
                    "current_equivalent",
                    original.source_state_key,
                    original.evidence_id,
                ):
                    pytest.fail(
                        "Real cache replay changed source state or canonical evidence"
                    )
            if len(entries) != len(first_facts):
                pytest.fail("Cache recovery lost or duplicated release entries")
            published = {
                json.loads(payload)["resource_identity"]: json.loads(payload)["facts"][
                    0
                ][0]
                for _, payload in entries
            }
            if published != {key: fact.fact_id for key, fact in old.items()}:
                pytest.fail("Publication did not bind the original advanced facts")
            if released_entries and entries != released_entries:
                pytest.fail("Already published cache replay created repeated work")
            released_entries = entries
        finally:
            catalog.close()

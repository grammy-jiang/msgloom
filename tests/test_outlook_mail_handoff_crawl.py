"""Real local Scrapy cache replay retains the second logical Mail run."""

import json
import subprocess
import sys

import pytest
from sqlalchemy import select
from test_outlook_crawls import ROOT, RUN_COMMAND, graph_server
from test_outlook_mail_handoff_facts import publish

from message_ingest.acquisition.handoff import FactSpec
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.outlook.email import MessageObservation
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

__all__ = ["graph_server"]


def test_real_scrapy_http_cache_replay_retains_logical_run(tmp_path, graph_server):
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
    for attempt in range(2):
        result = subprocess.run(
            args, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False
        )
        if result.returncode or "ERROR" in result.stderr:
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
            if attempt == 0:
                first_facts = primary
                first_run = {f.run_id for f in primary}
                if len(first_run) != 1 or not primary:
                    pytest.fail("First real crawl did not stage primary state")
                continue
            replay = [f for f in primary if f.run_id not in first_run]
            if len(replay) != len(first_facts) or count != len(first_facts):
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
            store = OutlookMailStore(catalog, source_id="source")
            entries = publish(store, replay[0], replay[0].run_id)
            if len(entries) != 1:
                pytest.fail("Real cache replay did not recover its unreleased state")
            if json.loads(entries[0]["payload"])["facts"][0][0] != (
                old[replay[0].resource_identity].fact_id
            ):
                pytest.fail("Recovery did not bind the exact original advanced fact")
        finally:
            catalog.close()

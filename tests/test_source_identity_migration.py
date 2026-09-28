"""Verify source-identity race serialization and legacy schema migration."""

from __future__ import annotations

from pathlib import Path
from queue import Queue
from threading import Barrier, Thread

import pytest
from scrapy.utils.test import get_crawler

from message_ingest.acquisition.source_identity import (
    SourceIdentity,
    SourceIdentityBootstrapRequired,
    SourceIdentityMismatch,
    SourceIdentityService,
)
from message_ingest.catalog import SourceBinding
from message_ingest.extensions.catalog import CatalogService


def _crawler(tmp_path: Path, *, source_id: str = "source-1"):
    return get_crawler(
        settings_dict={
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": source_id,
            "MSGLOOM_SOURCE_IDENTITY_BOOTSTRAP_CONFIRM": "",
        }
    )


def _identity(account_key: str = "opaque-home-account-id") -> SourceIdentity:
    return SourceIdentity(
        provider="microsoft_graph",
        key_scheme="msal_home_account_id/sha256-v1",
        account_key=account_key,
    )


def _binding(crawler, source_id: str = "source-1") -> SourceBinding | None:
    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        return session.get(SourceBinding, source_id)


def _close(crawler) -> None:
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def test_concurrent_catalogs_serialize_same_identity_first_bind(
    tmp_path: Path,
) -> None:
    one = _crawler(tmp_path)
    two = _crawler(tmp_path)
    services = [
        SourceIdentityService.from_crawler(one),
        SourceIdentityService.from_crawler(two),
    ]
    barrier = Barrier(2)
    results: Queue[object] = Queue()

    def bind(service: SourceIdentityService) -> None:
        barrier.wait()
        try:
            results.put(service.bind_or_verify(_identity()))
        except Exception as exc:  # noqa: BLE001 - thread outcome under test
            results.put(exc)

    threads = [Thread(target=bind, args=(service,)) for service in services]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    values = [results.get_nowait(), results.get_nowait()]

    if sorted(value for value in values if isinstance(value, str)) != [
        "bound",
        "verified",
    ]:
        pytest.fail(f"Unexpected concurrent binding outcomes: {values!r}")
    _close(one)
    _close(two)


def test_concurrent_catalogs_fail_closed_for_different_first_identities(
    tmp_path: Path,
) -> None:
    one = _crawler(tmp_path)
    two = _crawler(tmp_path)
    services = [
        SourceIdentityService.from_crawler(one),
        SourceIdentityService.from_crawler(two),
    ]
    identities = [_identity("account-a"), _identity("account-b")]
    barrier = Barrier(2)
    results: Queue[object] = Queue()

    def bind(service: SourceIdentityService, identity: SourceIdentity) -> None:
        barrier.wait()
        try:
            results.put(service.bind_or_verify(identity))
        except Exception as exc:  # noqa: BLE001 - thread outcome under test
            results.put(exc)

    threads = [
        Thread(target=bind, args=pair)
        for pair in zip(services, identities, strict=True)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    values = [results.get_nowait(), results.get_nowait()]

    if sum(value == "bound" for value in values) != 1:
        pytest.fail(f"Expected exactly one first binding winner: {values!r}")
    if sum(isinstance(value, SourceIdentityMismatch) for value in values) != 1:
        pytest.fail(f"Expected losing identity to fail closed: {values!r}")
    _close(one)
    _close(two)


LEGACY_SOURCE_ROWS = {
    "attachments": {
        "message_id": "m1",
        "attachment_id": "a1",
        "latest_observed_at": "2026-09-27T00:00:00+00:00",
    },
    "delta_checkpoint_candidates": {
        "run_id": "r1",
        "folder_id": "f1",
        "delta_link": "https://graph.microsoft.com/delta?candidate=1",
        "observed_at": "2026-09-27T00:00:00+00:00",
    },
    "delta_checkpoints": {
        "folder_id": "f1",
        "delta_link": "https://graph.microsoft.com/delta?committed=1",
        "committed_at": "2026-09-27T00:00:00+00:00",
        "run_id": "r1",
    },
    "mail_folders": {
        "folder_id": "f1",
        "latest_observed_at": "2026-09-27T00:00:00+00:00",
    },
    "message_observations": {
        "observation_id": "o1",
        "message_id": "m1",
        "kind": "discovery",
        "observed_at": "2026-09-27T00:00:00+00:00",
    },
    "message_surfaces": {
        "message_id": "m1",
        "surface": "discovery",
        "status": "acquired",
        "observed_at": "2026-09-27T00:00:00+00:00",
    },
    "messages": {
        "message_id": "m1",
        "is_removed": False,
        "latest_observed_at": "2026-09-27T00:00:00+00:00",
    },
    "raw_http_evidence": {
        "evidence_id": "e1",
        "observed_at": "2026-09-27T00:00:00+00:00",
        "origin": "network",
        "request_fingerprint": "f" * 64,
        "request_url": "https://graph.microsoft.com/v1.0/me",
        "request_method": "GET",
        "request_headers": {},
        "request_body_sha256": "0" * 64,
        "request_body_path": "/tmp/request",
        "request_body_bytes": 0,
        "response_headers": {},
        "response_body_sha256": "1" * 64,
        "response_body_path": "/tmp/response",
        "response_body_bytes": 0,
        "response_flags": [],
    },
}


@pytest.mark.parametrize("table_name", sorted(LEGACY_SOURCE_ROWS))
def test_every_source_bearing_table_requires_legacy_bootstrap(
    tmp_path: Path,
    table_name: str,
) -> None:
    from message_ingest.catalog import Base

    crawler = _crawler(tmp_path, source_id="legacy-source")
    service = CatalogService.from_crawler(crawler)
    table = Base.metadata.tables[table_name]
    values = {"source_id": "legacy-source", **LEGACY_SOURCE_ROWS[table_name]}
    with service.catalog.engine.begin() as connection:
        connection.execute(table.insert().values(**values))

    with pytest.raises(SourceIdentityBootstrapRequired):
        SourceIdentityService.from_crawler(crawler).bind_or_verify(_identity())

    if _binding(crawler, "legacy-source") is not None:
        pytest.fail(f"Expected {table_name} history to remain unbound")
    _close(crawler)


def test_upgrade_adds_binding_table_without_changing_legacy_rows(
    tmp_path: Path,
) -> None:
    from sqlalchemy import create_engine, func, inspect, select

    from message_ingest.catalog import Base, Catalog

    path = tmp_path / "legacy.sqlite3"
    url = f"sqlite:///{path}"
    engine = create_engine(url)
    legacy_tables = [
        table
        for table in Base.metadata.sorted_tables
        if table is not SourceBinding.__table__
    ]
    Base.metadata.create_all(engine, tables=legacy_tables)
    with engine.begin() as connection:
        connection.execute(
            Base.metadata.tables["messages"]
            .insert()
            .values(
                source_id="legacy-source",
                message_id="m1",
                is_removed=False,
                latest_observed_at="2026-09-27T00:00:00+00:00",
            )
        )
    before_tables = set(inspect(engine).get_table_names())
    engine.dispose()
    if "source_bindings" in before_tables:
        pytest.fail("Expected pre-binding schema fixture without source_bindings")

    catalog = Catalog(url)
    try:
        after_tables = set(inspect(catalog.engine).get_table_names())
        if "source_bindings" not in after_tables:
            pytest.fail("Expected additive source_bindings table on reopen")
        with catalog.Session() as session:
            message_count = session.scalar(
                select(func.count()).select_from(Base.metadata.tables["messages"])
            )
            binding_count = session.scalar(
                select(func.count()).select_from(SourceBinding)
            )
        if message_count != 1:
            pytest.fail("Expected legacy message row to remain unchanged")
        if binding_count != 0:
            pytest.fail("Expected upgrade not to auto-claim legacy source identity")
    finally:
        catalog.close()

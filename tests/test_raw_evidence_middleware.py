from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import select
from scrapy.http import Request, Response
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler

from msgloom.catalog import RawHttpEvidence
from msgloom.evidence import (
    META_EVIDENCE_ID,
    META_PURPOSE,
    META_RUN_ID,
    CachedEvidenceLinkMiddleware,
    RawNetworkEvidenceMiddleware,
)
from msgloom.spiders.outlook_mail import OutlookMailSpider


def _crawler(tmp_path: Path):
    return get_crawler(
        OutlookMailSpider,
        settings_dict={
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
            "MSGLOOM_SOURCE_ID": "source-1",
        },
    )


def test_network_response_is_durably_persisted_before_spider_and_linked_to_request(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    middleware = build_from_crawler(RawNetworkEvidenceMiddleware, crawler)
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        meta={META_PURPOSE: "message-list", META_RUN_ID: "run-1"},
    )
    response = Response(
        request.url,
        status=200,
        headers={"Content-Type": "application/json"},
        body=b'{"value":[]}',
        request=request,
    )

    returned = asyncio.run(middleware.process_response(request, response))
    assert returned is response
    evidence_id = request.meta[META_EVIDENCE_ID]
    with middleware.catalog.Session() as session:
        evidence = session.scalar(
            select(RawHttpEvidence).where(RawHttpEvidence.evidence_id == evidence_id)
        )
        assert evidence is not None
        assert evidence.origin == "network"
        assert evidence.purpose == "message-list"
        assert evidence.run_id == "run-1"
        raw_path = Path(evidence.body_path)
        assert raw_path.read_bytes() == response.body
        assert raw_path.stat().st_mode & 0o777 == 0o600


def test_cached_response_reuses_existing_network_evidence(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    network = build_from_crawler(RawNetworkEvidenceMiddleware, crawler)
    cached = build_from_crawler(CachedEvidenceLinkMiddleware, crawler)
    url = "https://graph.microsoft.com/v1.0/me/messages"

    request1 = Request(url, meta={META_PURPOSE: "message-list", META_RUN_ID: "run-1"})
    response1 = Response(url, status=200, body=b'{"value":[]}', request=request1)
    asyncio.run(network.process_response(request1, response1))
    first_id = request1.meta[META_EVIDENCE_ID]

    request2 = Request(url, meta={META_PURPOSE: "message-list", META_RUN_ID: "run-2"})
    response2 = Response(
        url,
        status=200,
        body=b'{"value":[]}',
        request=request2,
        flags=["cached"],
    )
    asyncio.run(cached.process_response(request2, response2))

    assert request2.meta[META_EVIDENCE_ID] == first_id
    with network.catalog.Session() as session:
        assert len(session.scalars(select(RawHttpEvidence)).all()) == 1
    assert crawler.stats.get_value("msgloom/evidence/cache_link_count") == 1


def test_cache_without_prior_catalog_evidence_is_recovered_but_marked_as_cache_origin(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    cached = build_from_crawler(CachedEvidenceLinkMiddleware, crawler)
    request = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        meta={META_PURPOSE: "message-list", META_RUN_ID: "run-legacy"},
    )
    response = Response(
        request.url,
        status=200,
        body=b'{"value":[]}',
        request=request,
        flags=["cached"],
    )
    asyncio.run(cached.process_response(request, response))

    evidence_id = request.meta[META_EVIDENCE_ID]
    with cached.catalog.Session() as session:
        evidence = session.scalar(
            select(RawHttpEvidence).where(RawHttpEvidence.evidence_id == evidence_id)
        )
        assert evidence is not None
        assert evidence.origin == "http_cache"
    assert crawler.stats.get_value("msgloom/evidence/cache_recovery_count") == 1

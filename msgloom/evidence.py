from __future__ import annotations

import asyncio
import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from scrapy.exceptions import NotConfigured

from msgloom.services import get_catalog_service

GRAPH_HOST = "graph.microsoft.com"
META_PURPOSE = "msgloom_purpose"
META_RUN_ID = "msgloom_run_id"
META_EVIDENCE_ID = "_msgloom_raw_evidence_id"


class _EvidenceBase:
    def __init__(self, *, crawler) -> None:
        service = get_catalog_service(crawler)
        self.catalog = service.catalog
        self._write_lock = service.write_lock
        self.raw_dir = Path(crawler.settings["MSGLOOM_RAW_EVIDENCE_DIR"])
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.raw_dir, 0o700)
        self.source_id = crawler.settings["MSGLOOM_SOURCE_ID"]
        self.stats = crawler.stats

    @classmethod
    def _from_crawler_common(cls, crawler):
        if not crawler.settings.getbool("MSGLOOM_RAW_EVIDENCE_ENABLED"):
            raise NotConfigured("Raw HTTP evidence disabled")
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("Raw HTTP evidence requires the SQLAlchemy catalog")
        return cls(crawler=crawler)

    async def _persist_new(self, request, response, *, origin: str) -> str:
        body = response.body
        digest = hashlib.sha256(body).hexdigest()
        headers = self._headers(response.headers)
        async with self._write_lock:
            evidence_id, stat_values = await asyncio.to_thread(
                self._persist_response,
                request.url,
                request.method,
                request.meta.get(META_RUN_ID),
                request.meta.get(META_PURPOSE),
                response.status,
                headers,
                body,
                digest,
                origin,
            )
        for key, count in stat_values:
            self._inc(key, count=count)
        return evidence_id

    def _persist_response(
        self,
        request_url: str,
        request_method: str,
        run_id: str | None,
        purpose: str | None,
        response_status: int,
        response_headers: dict[str, list[str]],
        body: bytes,
        digest: str,
        origin: str,
    ) -> tuple[str, list[tuple[str, int]]]:
        stats: list[tuple[str, int]] = []
        raw_path = self.raw_dir / f"{digest}.bin"
        if not raw_path.exists():
            temp_path = raw_path.with_suffix(".tmp")
            temp_path.write_bytes(body)
            os.chmod(temp_path, 0o600)
            temp_path.replace(raw_path)
            os.chmod(raw_path, 0o600)
            stats.append(("msgloom/evidence/raw_blob_created_count", 1))
            stats.append(("msgloom/evidence/raw_blob_created_bytes", len(body)))
        else:
            stats.append(("msgloom/evidence/raw_blob_reused_count", 1))

        evidence_id = self.catalog.record_raw_http_evidence(
            source_id=self.source_id,
            run_id=run_id,
            purpose=purpose,
            request_url=request_url,
            request_method=request_method,
            response_status=response_status,
            response_headers=response_headers,
            body_sha256=digest,
            body_path=str(raw_path),
            body_bytes=len(body),
            observed_at=datetime.now(UTC).isoformat(),
            origin=origin,
        )
        stats.append(("msgloom/evidence/response_persisted_count", 1))
        stats.append((f"msgloom/evidence/origin_count/{origin}", 1))
        return evidence_id, stats

    def _inc(self, key: str, count: int = 1) -> None:
        self.stats.inc_value(key, count=count)

    @staticmethod
    def _headers(headers) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for name in headers.keys():
            key = name.decode("latin-1") if isinstance(name, bytes) else str(name)
            result[key] = [
                value.decode("latin-1") if isinstance(value, bytes) else str(value)
                for value in headers.getlist(name)
            ]
        return result


class RawNetworkEvidenceMiddleware(_EvidenceBase):
    """Durably persist downloaded Graph responses before HttpCache/Spider use."""

    @classmethod
    def from_crawler(cls, crawler):
        return cls._from_crawler_common(crawler)

    async def process_response(self, request, response):
        if urlsplit(request.url).hostname != GRAPH_HOST or "cached" in response.flags:
            return response
        evidence_id = await self._persist_new(request, response, origin="network")
        request.meta[META_EVIDENCE_ID] = evidence_id
        return response


class CachedEvidenceLinkMiddleware(_EvidenceBase):
    """Relink an HTTP-cache response to the original durable evidence."""

    @classmethod
    def from_crawler(cls, crawler):
        return cls._from_crawler_common(crawler)

    async def process_response(self, request, response):
        if urlsplit(request.url).hostname != GRAPH_HOST or "cached" not in response.flags:
            return response
        digest = hashlib.sha256(response.body).hexdigest()
        async with self._write_lock:
            evidence_id = await asyncio.to_thread(
                self.catalog.find_raw_http_evidence,
                source_id=self.source_id,
                request_url=request.url,
                body_sha256=digest,
            )
        if evidence_id is None:
            evidence_id = await self._persist_new(
                request,
                response,
                origin="http_cache",
            )
            self._inc("msgloom/evidence/cache_recovery_count")
        else:
            self._inc("msgloom/evidence/cache_link_count")
        request.meta[META_EVIDENCE_ID] = evidence_id
        return response

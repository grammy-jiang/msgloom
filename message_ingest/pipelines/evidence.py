"""Content-addressed storage for spider-visible HTTP evidence."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from pathlib import Path

from scrapy.exceptions import NotConfigured

from message_ingest.catalog.models import RawHttpEvidence
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.acquisition import RawHttpEvidenceItem

logger = logging.getLogger(__name__)


class RawEvidencePipeline:
    """
    Persist spider-visible HTTP evidence before dependent semantic items.

    Blob files are content-addressed; SQL records identify individual captures.
    HTTP-cache replay may link to an existing capture instead of creating a
    newer observation of the same bytes. This is not a log of every downloader
    attempt.
    """

    def __init__(
        self,
        *,
        service: CatalogService,
        raw_dir: str,
        source_id: str,
        stats=None,
    ) -> None:
        """
        Borrow the shared write lock and prepare a private raw-payload
        directory.
        """
        self.service = service
        self.catalog = service.catalog
        self._write_lock = service.write_lock
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.raw_dir, 0o700)
        self.source_id = source_id
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        """Enable raw capture only when the catalog can store its metadata."""
        if not crawler.settings.getbool("MSGLOOM_RAW_EVIDENCE_ENABLED"):
            raise NotConfigured("Raw HTTP evidence pipeline disabled")
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("Raw HTTP evidence requires the SQLAlchemy catalog")
        return cls(
            service=CatalogService.from_crawler(crawler),
            raw_dir=crawler.settings["MSGLOOM_RAW_EVIDENCE_DIR"],
            source_id=crawler.settings["MSGLOOM_SOURCE_ID"],
            stats=crawler.stats,
        )

    def close_spider(self) -> None:
        """Close the crawler-shared catalog before terminal lifecycle signals."""
        self.service.close()

    async def process_item(self, item):
        """
        Await both file and SQL persistence, then publish the canonical
        evidence alias.

        Return the item only after its evidence can be referenced. The
        configured serial callback output ensures dependent semantic items
        cannot overtake this stage.
        """
        if not isinstance(item, RawHttpEvidenceItem):
            return item
        async with self._write_lock:
            canonical_id, observed_at, stat_keys = await asyncio.to_thread(
                self._persist_sync, item
            )
        provisional_id = item.evidence_id
        self.service.register_evidence_alias(provisional_id, canonical_id, observed_at)
        item.evidence_id = canonical_id
        item.observed_at = observed_at
        for stat_key in stat_keys:
            self._inc(stat_key)
        logger.debug(
            "Raw HTTP evidence persisted: purpose=%s origin=%s status=%s evidence_id=%s canonicalized=%s",
            item.purpose,
            item.origin,
            item.response_status,
            item.evidence_id,
            provisional_id != item.evidence_id,
        )
        return item

    def _persist_sync(
        self, item: RawHttpEvidenceItem
    ) -> tuple[str, str, tuple[str, ...]]:
        """
        Reuse a cache capture or write both blobs before inserting its SQL
        record.

        A file write may leave an unreferenced content-addressed blob if the
        SQL insert fails. The failure propagates; no successful semantic
        reference is fabricated.
        """
        if item.origin == "http_cache":
            response_digest = hashlib.sha256(item.response_body).hexdigest()
            existing = self.catalog.find_raw_http_evidence(
                source_id=self.source_id,
                request_fingerprint=item.request_fingerprint,
                response_body_sha256=response_digest,
            )
            if existing is not None:
                evidence_id, observed_at = existing
                return (
                    evidence_id,
                    observed_at,
                    ("msgloom/evidence/cache_link_count",),
                )

        request_digest, request_path, request_created = self._store_blob(
            item.request_body
        )
        response_digest, response_path, response_created = self._store_blob(
            item.response_body
        )
        self.catalog.record_raw_http_evidence(
            RawHttpEvidence(
                evidence_id=item.evidence_id,
                source_id=self.source_id,
                run_id=item.run_id,
                purpose=item.purpose,
                observed_at=item.observed_at,
                origin=item.origin,
                request_fingerprint=item.request_fingerprint,
                request_url=item.request_url,
                request_method=item.request_method,
                request_headers=item.request_headers,
                request_body_sha256=request_digest,
                request_body_path=str(request_path),
                request_body_bytes=len(item.request_body),
                response_url=item.response_url,
                response_status=item.response_status,
                response_headers=item.response_headers,
                response_body_sha256=response_digest,
                response_body_path=str(response_path),
                response_body_bytes=len(item.response_body),
                response_flags=item.response_flags,
                error_type=item.error_type,
                error_message=item.error_message,
            )
        )
        stats = [
            "msgloom/evidence/response_persisted_count",
            f"msgloom/evidence/origin_count/{item.origin}",
        ]
        for created in (request_created, response_created):
            outcome = "created" if created else "reused"
            stats.append(f"msgloom/evidence/raw_blob_{outcome}_count")
        if item.origin == "http_cache":
            stats.append("msgloom/evidence/cache_recovery_count")
        return item.evidence_id, item.observed_at, tuple(stats)

    def _store_blob(self, body: bytes) -> tuple[str, Path, bool]:
        """
        Reuse digest-named bytes, or atomically replace a private temporary
        file under the write lock.
        """
        digest = hashlib.sha256(body).hexdigest()
        path = self.raw_dir / f"{digest}.bin"
        if path.exists():
            return digest, path, False
        temp = path.with_suffix(".tmp")
        temp.write_bytes(body)
        os.chmod(temp, 0o600)
        temp.replace(path)
        os.chmod(path, 0o600)
        return digest, path, True

    def _inc(self, key: str, count: int = 1) -> None:
        """
        Allow direct pipeline use without a stats collector; stats do not
        control persistence.
        """
        if self.stats is not None:
            self.stats.inc_value(key, count=count)

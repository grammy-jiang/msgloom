"""One catalog and write lock shared by the crawler components."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from scrapy.exceptions import NotConfigured

from message_ingest.catalog import Catalog

_SERVICE_ATTR = "_msgloom_catalog_service"


class CatalogService:
    """
    Own one engine, write lock, and evidence alias map for a crawler.

    Pipelines and checkpoint consumers borrow this service. Persistence
    pipelines close it idempotently during Scrapy pipeline shutdown, before
    terminal lifecycle observers classify the run.
    """

    def __init__(self, crawler) -> None:
        """
        Create the resources that all enabled persistence components must
        share.
        """
        self.catalog = Catalog(crawler.settings["MSGLOOM_DATABASE_URL"])
        self.write_lock = asyncio.Lock()
        self.evidence_aliases: dict[str, tuple[str, str]] = {}
        self._closed = False

    @classmethod
    def from_crawler(cls, crawler):
        """
        Return the crawler-cached instance, creating shared resources once.
        """
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("SQLAlchemy catalog service disabled")
        if (existing := getattr(crawler, _SERVICE_ATTR, None)) is not None:
            return existing
        service = cls(crawler)
        setattr(crawler, _SERVICE_ATTR, service)
        return service

    async def write[T](
        self,
        operation: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Serialize a thread write and drain it before propagating cancellation.

        Cancellation cannot stop a running thread. Keep catalog ownership until
        its file/SQL work finishes, including repeated cancellation requests.
        Restore each request after drain and chain a concurrent write failure.
        The caller publishes success state only when this method returns.
        """
        await self.write_lock.acquire()
        worker = asyncio.create_task(asyncio.to_thread(operation, *args, **kwargs))
        cancellation: asyncio.CancelledError | None = None
        consumed_cancellations = 0
        current = asyncio.current_task()
        try:
            while True:
                try:
                    outcome = await asyncio.shield(worker)
                    break
                except asyncio.CancelledError as exc:
                    if current is None or current.cancelling() == 0:
                        raise
                    if cancellation is None:
                        cancellation = exc
                    pending = current.cancelling()
                    for _unused in range(pending):
                        current.uncancel()
                        consumed_cancellations += 1
                except BaseException as write_error:
                    if cancellation is None:
                        raise
                    self._restore_cancellation(current, consumed_cancellations)
                    raise cancellation from write_error

            if cancellation is not None:
                self._restore_cancellation(current, consumed_cancellations)
                raise cancellation
            return outcome
        finally:
            self.write_lock.release()

    @staticmethod
    def _restore_cancellation(
        current: asyncio.Task[Any] | None,
        count: int,
    ) -> None:
        """Restore every consumed cancellation request after worker drain."""
        if current is None:
            return
        for _unused in range(count):
            current.cancel()

    def register_evidence_alias(
        self, provisional_id: str, canonical_id: str, observed_at: str
    ) -> None:
        """
        Map this run's provisional evidence ID to the canonical persisted
        capture.
        """
        self.evidence_aliases[provisional_id] = (canonical_id, observed_at)

    def resolve_evidence(
        self, evidence_id: str | None, observed_at: str
    ) -> tuple[str | None, str]:
        """
        Return canonical ID/time together so cache replay cannot advance
        semantic timestamps.
        """
        if evidence_id is None:
            return None, observed_at
        return self.evidence_aliases.get(evidence_id, (evidence_id, observed_at))

    def close(self) -> None:
        """Dispose the shared catalog exactly once after pipeline work."""
        if self._closed:
            return
        self.catalog.close()
        self._closed = True

    def spider_closed(self, *_args, **_kwargs) -> None:
        """Compatibility helper for direct tests; no signal is registered."""
        self.close()

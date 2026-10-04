"""Instrument native Teams item ordering without replacing persistence.

Each fixture crawl runs in its own process. The pending set therefore belongs
only to that crawl. A bounded event-loop timer holds a raw item before its
real pipeline write. The semantic probe runs before evidence linking, reads a
separate SQL session and verifies both stored blobs at that exact boundary.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

from scrapy import signals

from message_ingest.acquisition.evidence_link import EvidenceLinkPipeline
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.teams.message import TeamsMessageItem
from message_ingest.pipelines.evidence import RawEvidencePipeline

_PENDING: set[str] = set()


def _record(path: Path, event: str, evidence_id: str) -> None:
    """Append boundary observations in event-loop execution order."""
    with path.open("a") as stream:
        stream.write(json.dumps([event, evidence_id]) + "\n")


class DelayedRawEvidencePipeline(RawEvidencePipeline):
    """Hold message-page evidence before the normal awaited blob/SQL write."""

    trace: Path

    @classmethod
    def from_crawler(cls, crawler):
        """Reuse production setup and install the optional negative control."""
        pipeline = super().from_crawler(crawler)
        pipeline.trace = Path(crawler.settings["TEAMS_ORDER_TRACE"])
        if crawler.settings.getbool("TEAMS_ORDER_BROKEN_CONTROL"):
            # Test-only fault injection after application initialization. The
            # real spider rejects an unsafe CONCURRENT_ITEMS setting. Change
            # the native scraper directly to test the ordering probe itself;
            # production code and settings validation stay unchanged.
            def break_order() -> None:
                if crawler.engine is None:
                    raise RuntimeError("Ordering control requires a native engine")
                crawler.engine.scraper.concurrent_items = 2

            crawler.signals.connect(break_order, signals.spider_opened, weak=False)
        return pipeline

    async def process_item(self, item: Any) -> Any:
        """Release the bounded hold before awaiting the real evidence write."""
        if not isinstance(item, RawHttpEvidenceItem):
            return await super().process_item(item)
        if item.purpose != "teams-chat-messages":
            return await super().process_item(item)
        evidence_id = item.evidence_id
        _PENDING.add(evidence_id)
        _record(self.trace, "held", evidence_id)
        released = asyncio.Event()
        timer = asyncio.get_running_loop().call_later(0.1, released.set)
        try:
            await asyncio.wait_for(released.wait(), timeout=5)
            _record(self.trace, "released", evidence_id)
            result = await super().process_item(item)
            _PENDING.remove(evidence_id)
            _record(self.trace, "committed", evidence_id)
            return result
        finally:
            timer.cancel()


class EntryEvidenceLinkPipeline(EvidenceLinkPipeline):
    """Check durable evidence at semantic entry, before the normal linker."""

    trace: Path

    @classmethod
    def from_crawler(cls, crawler):
        """Use the same shared catalog as the real pipeline chain."""
        pipeline = super().from_crawler(crawler)
        pipeline.trace = Path(crawler.settings["TEAMS_ORDER_TRACE"])
        return pipeline

    async def process_item(self, item: Any) -> Any:
        """Reject overtaking and verify durable SQL and exact blob digests."""
        if not isinstance(item, TeamsMessageItem):
            return await super().process_item(item)
        evidence_id = item.evidence_id
        if evidence_id is None:
            raise RuntimeError("Ordering fixture message has no evidence")
        _record(self.trace, "semantic-enter", evidence_id)
        with self.catalog.Session() as session:
            row = session.get(RawHttpEvidence, evidence_id)
        if evidence_id in _PENDING or row is None:
            _record(self.trace, "overtook", evidence_id)
            raise RuntimeError("Teams semantic item overtook durable evidence")
        for body_path, digest, length in (
            (row.request_body_path, row.request_body_sha256, row.request_body_bytes),
            (row.response_body_path, row.response_body_sha256, row.response_body_bytes),
        ):
            body = Path(body_path).read_bytes()
            if hashlib.sha256(body).hexdigest() != digest or len(body) != length:
                raise RuntimeError("Teams semantic entry found invalid evidence bytes")
        _record(self.trace, "semantic-ready", evidence_id)
        return await super().process_item(item)

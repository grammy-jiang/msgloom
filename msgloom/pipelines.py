from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from itemadapter import ItemAdapter
from scrapy.exceptions import NotConfigured

from msgloom.services import get_catalog_service
from msgloom.items import (
    AcquisitionFailureItem,
    OutlookAttachmentItem,
    OutlookDeltaCheckpointCandidateItem,
    OutlookMailDetailItem,
    OutlookMailFolderItem,
    OutlookMailItem,
    OutlookMailRemovalItem,
    OutlookMessageSurfaceItem,
)


class CatalogPipeline:
    """Persist queryable Outlook catalog/state through SQLAlchemy only."""

    def __init__(
        self,
        *,
        catalog,
        write_lock: asyncio.Lock,
        source_id: str,
        stats=None,
    ) -> None:
        self.catalog = catalog
        self.source_id = source_id
        self.stats = stats
        self._write_lock = write_lock

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("SQLAlchemy catalog pipeline disabled")
        service = get_catalog_service(crawler)
        return cls(
            catalog=service.catalog,
            write_lock=service.write_lock,
            source_id=crawler.settings["MSGLOOM_SOURCE_ID"],
            stats=crawler.stats,
        )

    async def process_item(self, item):
        async with self._write_lock:
            stat_key = await asyncio.to_thread(self._process_item_sync, item)
        if stat_key:
            self._inc(stat_key)
        return item

    def _process_item_sync(self, item) -> str | None:
        if isinstance(item, OutlookMailItem):
            self.catalog.record_message(
                source_id=self.source_id,
                run_id=item.run_id,
                message=item.raw,
                kind=item.observation_kind,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
            )
            self.catalog.set_message_surface(
                source_id=self.source_id,
                message_id=item.message_id,
                surface="discovery",
                status="acquired",
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
            )
            return "msgloom/catalog/message_observation_count"
        if isinstance(item, OutlookMailDetailItem):
            self.catalog.record_message(
                source_id=self.source_id,
                run_id=item.run_id,
                message=item.raw,
                kind="detail",
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
            )
            self.catalog.set_message_surface(
                source_id=self.source_id,
                message_id=item.message_id,
                surface="detail",
                status="acquired",
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
            )
            return "msgloom/catalog/message_detail_count"
        if isinstance(item, OutlookMailFolderItem):
            self.catalog.upsert_folder(
                source_id=self.source_id,
                folder=item.raw,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
            )
            return "msgloom/catalog/folder_observation_count"
        if isinstance(item, OutlookMailRemovalItem):
            self.catalog.record_message(
                source_id=self.source_id,
                run_id=item.run_id,
                message=item.raw,
                kind="removed",
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
                removed_reason=item.removed_reason,
            )
            return "msgloom/catalog/message_removal_count"
        if isinstance(item, OutlookMessageSurfaceItem):
            self.catalog.set_message_surface(
                source_id=self.source_id,
                message_id=item.message_id,
                surface=item.surface,
                status=item.status,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
                profile_version=item.profile_version,
            )
            return f"msgloom/catalog/surface_count/{item.surface}/{item.status}"
        if isinstance(item, OutlookDeltaCheckpointCandidateItem):
            self.catalog.write_delta_candidate(
                run_id=item.run_id,
                source_id=self.source_id,
                folder_id=item.folder_id,
                delta_link=item.delta_link,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
            )
            return "msgloom/catalog/delta_checkpoint_candidate_count"
        return None

    def _inc(self, key: str, count: int = 1) -> None:
        if self.stats is not None:
            self.stats.inc_value(key, count=count)


class LocalJsonlPipeline:
    """Keep append-only semantic observation logs for inspection and recovery."""

    def __init__(self, data_dir: str, stats=None) -> None:
        self.data_dir = Path(data_dir)
        self.stats = stats
        self._messages = None
        self._details = None
        self._attachments = None
        self._folders = None
        self._removals = None
        self._failures = None
        self._write_lock = asyncio.Lock()

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool("MSGLOOM_JSONL_ENABLED"):
            raise NotConfigured("Local JSONL pipeline disabled")
        return cls(crawler.settings["MSGLOOM_DATA_DIR"], crawler.stats)

    def open_spider(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.data_dir, 0o700)
        self._messages = self._open("outlook-mail.jsonl")
        self._details = self._open("outlook-mail-details.jsonl")
        self._attachments = self._open("outlook-attachments.jsonl")
        self._folders = self._open("outlook-mail-folders.jsonl")
        self._removals = self._open("outlook-mail-removals.jsonl")
        self._failures = self._open("failures.jsonl")

    def close_spider(self) -> None:
        for handle in (
            self._messages,
            self._details,
            self._attachments,
            self._folders,
            self._removals,
            self._failures,
        ):
            if handle is not None:
                handle.close()

    async def process_item(self, item):
        async with self._write_lock:
            stat_key = await asyncio.to_thread(self._write_item_sync, item)
        if stat_key:
            self._inc(stat_key)
        return item

    def _write_item_sync(self, item) -> str | None:
        if isinstance(item, OutlookMailItem):
            self._write_jsonl(self._messages, self._to_dict(item))
            return "msgloom/storage/item_count/outlook_mail"
        if isinstance(item, OutlookMailDetailItem):
            self._write_jsonl(self._details, self._to_dict(item))
            return "msgloom/storage/item_count/outlook_mail_detail"
        if isinstance(item, OutlookAttachmentItem):
            self._write_jsonl(self._attachments, self._to_dict(item))
            return "msgloom/storage/item_count/outlook_attachment"
        if isinstance(item, OutlookMailFolderItem):
            self._write_jsonl(self._folders, self._to_dict(item))
            return "msgloom/storage/item_count/outlook_mail_folder"
        if isinstance(item, OutlookMailRemovalItem):
            self._write_jsonl(self._removals, self._to_dict(item))
            return "msgloom/storage/item_count/outlook_mail_removal"
        if isinstance(item, AcquisitionFailureItem):
            self._write_jsonl(self._failures, self._to_dict(item))
            return "msgloom/storage/item_count/acquisition_failure"
        return None

    def _open(self, name: str):
        path = self.data_dir / name
        handle = path.open("a", encoding="utf-8")
        os.chmod(path, 0o600)
        return handle

    def _inc(self, key: str, count: int = 1) -> None:
        if self.stats is not None:
            self.stats.inc_value(key, count=count)

    @staticmethod
    def _to_dict(item: Any) -> dict[str, Any]:
        if is_dataclass(item):
            return asdict(item)
        return ItemAdapter(item).asdict()

    @staticmethod
    def _write_jsonl(handle, value: dict[str, Any]) -> None:
        assert handle is not None
        handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
        handle.write("\n")
        handle.flush()

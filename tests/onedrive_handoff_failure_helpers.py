"""Inject source-inspectable OneDrive faults with fixture-owned proof."""

import json
from pathlib import Path

from scrapy import signals


class InjectedFailure(ValueError):
    """Carry fixture identity through the native failure signal."""

    def __init__(self, mode, failure, target, event_path):
        super().__init__(failure)
        self.event = {
            "mode": mode,
            "failure": failure,
            "target": target,
            "exception_type": "InjectedFailure",
        }
        self.event_path = event_path


class InjectionRecorder:
    """Record only fixture exceptions observed by native error signals."""

    @classmethod
    def from_crawler(cls, crawler):
        recorder = cls()
        crawler.signals.connect(recorder.record, signal=signals.spider_error)
        crawler.signals.connect(recorder.record, signal=signals.item_error)
        return recorder

    def record(self, failure):
        if not isinstance(error := failure.value, InjectedFailure):
            return
        with Path(error.event_path).open("a") as stream:
            stream.write(json.dumps(error.event) + "\n")


def install_failure(mode, failure, event_path):
    """Patch one subprocess and observe each fault at its native boundary.

    Keep callbacks in this file so Scrapy can inspect generator source. The
    event file belongs to the fixture and is independent of sanitized logs.
    The parent removes earlier events before starting each subprocess.
    """
    from message_ingest import settings
    from message_ingest.items.microsoft.onedrive import (
        OneDriveContentItem,
        OneDriveItem,
    )
    from message_ingest.pipelines.microsoft.onedrive import OneDrivePipeline
    from message_ingest.spiders.microsoft.onedrive.content import (
        MicrosoftOneDriveContentSpider,
    )
    from message_ingest.spiders.microsoft.onedrive.discover import (
        MicrosoftOneDriveDiscoverSpider,
    )

    if mode not in {"discover", "content"}:
        raise ValueError(f"Unknown injection mode: {mode}")
    if failure not in {"injected callback failure", "injected item failure"}:
        raise ValueError(f"Unknown injection failure: {failure}")

    settings.EXTENSIONS["onedrive_handoff_failure_helpers.InjectionRecorder"] = 0

    def raise_failure(target):
        raise InjectedFailure(mode, failure, target, event_path)

    if failure == "injected item failure":
        original_item = OneDrivePipeline.process_item

        async def failed_item(self, item):
            if mode == "discover" and isinstance(item, OneDriveItem):
                raise_failure(item.id)
            if (
                mode == "content"
                and isinstance(item, OneDriveContentItem)
                and item.item_id == "two"
            ):
                raise_failure(item.item_id)
            return await original_item(self, item)

        OneDrivePipeline.process_item = failed_item
        return

    if mode == "discover":
        original_children = MicrosoftOneDriveDiscoverSpider.parse_children

        def failed_children(self, response, **kwargs):
            yield from original_children(self, response, **kwargs)
            raise_failure("root")

        MicrosoftOneDriveDiscoverSpider.parse_children = failed_children
        return

    original_content = MicrosoftOneDriveContentSpider.parse_content

    def failed_content(self, response, **kwargs):
        yield from original_content(self, response, **kwargs)
        if kwargs["item_id"] == "two":
            raise_failure(kwargs["item_id"])

    MicrosoftOneDriveContentSpider.parse_content = failed_content

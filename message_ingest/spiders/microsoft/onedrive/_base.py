"""OneDrive source identity and evidence pipeline selection."""

from scrapy.settings import BaseSettings

from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider
from microsoft_graph.spiders.onedrive import MicrosoftOneDriveSpider


class OneDriveSpider(MicrosoftOneDriveSpider, MicrosoftGraphSpider):
    """Compose provider paths with signed-in-account acquisition policy."""

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Select OneDrive storage at spider priority; cmdline settings win."""
        settings.set(
            "MSGLOOM_SOURCE_ID",
            settings.get("MSGLOOM_ONEDRIVE_SOURCE_ID", "microsoft-onedrive-default"),
            priority="spider",
        )
        for key in (
            "MSGLOOM_DELTA_CHECKPOINT_ENABLED",
            "MSGLOOM_FOLDER_DELTA_CHECKPOINT_ENABLED",
            "MSGLOOM_CALENDAR_DELTA_CHECKPOINT_ENABLED",
            "MSGLOOM_CRAWL_STATUS_ENABLED",
        ):
            settings.set(key, False, priority="spider")
        settings.set(
            "ITEM_PIPELINES",
            {
                "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
                "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
                "message_ingest.pipelines.microsoft.onedrive.OneDrivePipeline": 300,
            },
            priority="spider",
        )
        super().update_settings(settings)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Refuse scheduler resume until OneDrive JOBDIR semantics are tested."""
        if crawler.settings.get("JOBDIR"):
            raise ValueError("OneDrive acquisition does not support JOBDIR yet")
        return super().from_crawler(crawler, *args, **kwargs)

"""Shared Teams application source, evidence, and initial-discovery policy."""

from typing import Any

from scrapy import Request
from scrapy.settings import BaseSettings

from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider


class MicrosoftTeamsBaseSpider(MicrosoftGraphSpider):
    """
    Bind Teams discovery to existing Graph integrity and evidence persistence.

    Concrete spiders put their provider composition class first in the MRO
    and this application base second. Provider helpers supply paths; concrete
    application spiders select scopes. Named application callbacks emit raw
    evidence before parsing or semantics.
    Initial discovery has no absence promotion, cursor, or JOBDIR resume.
    """

    source_id: str

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Select Teams storage and one source while honoring command priority."""
        settings.set(
            "MSGLOOM_SOURCE_ID",
            settings.get("MSGLOOM_TEAMS_SOURCE_ID", "microsoft-teams-default"),
            priority="spider",
        )
        for key in (
            "MSGLOOM_DELTA_CHECKPOINT_ENABLED",
            "MSGLOOM_FOLDER_DELTA_CHECKPOINT_ENABLED",
            "MSGLOOM_CALENDAR_DELTA_CHECKPOINT_ENABLED",
            "MSGLOOM_ONEDRIVE_DELTA_CHECKPOINT_ENABLED",
            "MSGLOOM_CONTACTS_SNAPSHOT_PROMOTION_ENABLED",
            "MSGLOOM_CONTACTS_DELTA_CHECKPOINT_ENABLED",
            "MSGLOOM_CRAWL_STATUS_ENABLED",
        ):
            settings.set(key, False, priority="spider")
        settings.set(
            "ITEM_PIPELINES",
            {
                "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
                "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
                "message_ingest.pipelines.microsoft.teams.TeamsPipeline": 300,
            },
            priority="spider",
        )
        super().update_settings(settings)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Reject unsupported resume and unsafe evidence settings before I/O."""
        settings = crawler.settings
        # Command settings can override provider defaults. Enforce the selected
        # application profile before construction/auth; standalone providers
        # retain their consumer-controlled scope policy.
        required = cls.required_graph_permissions(settings)
        if set(settings.getlist("MS_GRAPH_SCOPES")) != set(required):
            raise ValueError(
                "Teams acquisition requires exactly " + ", ".join(required)
            )
        if settings.get("JOBDIR"):
            raise ValueError("Teams discovery does not support JOBDIR yet")
        if settings.getint("CONCURRENT_ITEMS") != 1:
            raise ValueError("Teams discovery requires CONCURRENT_ITEMS=1")
        if not settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise ValueError("Teams discovery requires the SQL catalog")
        if not settings.getbool("MSGLOOM_RAW_EVIDENCE_ENABLED"):
            raise ValueError("Teams discovery requires raw evidence persistence")
        source_id = settings.get("MSGLOOM_SOURCE_ID")
        if not isinstance(source_id, str) or not source_id:
            raise ValueError("Teams discovery requires a non-empty source ID")
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider.source_id = source_id
        return spider

    def graph_request(self, url: str, **kwargs: Any) -> Request:
        """Require fresh reads for discovery while retaining native transport."""
        kwargs["dont_cache"] = True
        return super().graph_request(url, **kwargs)

    def _teams_provenance(self, evidence: RawHttpEvidenceItem) -> dict[str, Any]:
        """Supply constructor provenance; the existing linker resolves aliases."""
        return {
            "source_id": self.source_id,
            "observed_at": evidence.observed_at,
            "evidence_id": evidence.evidence_id,
            "run_id": self.run_id,
        }

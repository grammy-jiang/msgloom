"""Retrieve the signed-in Microsoft Graph user profile once."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

from scrapy.http import TextResponse
from scrapy.settings import BaseSettings

from message_ingest.providers.microsoft_graph.spider import MicrosoftGraphSpider


class MicrosoftProfileSpider(MicrosoftGraphSpider):
    """
    Fetch the signed-in user profile through the shared Graph lifecycle.

    The profile is command output, not a continuously synchronized catalog
    resource. Raw HTTP evidence is still persisted before the parsed profile is
    accepted, so authentication, diagnostics, retries, source identity, and
    evidence capture remain on the normal Scrapy path.
    """

    name = "microsoft_profile"

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Declare least-privilege profile scope and one-shot components."""
        settings.set("MS_GRAPH_SCOPES", ["User.Read"], priority="spider")
        settings.set(
            "MSGLOOM_DELTA_CHECKPOINT_ENABLED",
            False,
            priority="spider",
        )
        settings.set(
            "MSGLOOM_CRAWL_STATUS_ENABLED",
            False,
            priority="spider",
        )
        settings.set(
            "ITEM_PIPELINES",
            {
                "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
            },
            priority="spider",
        )
        super().update_settings(settings)

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the one profile result retained for command output."""
        super().__init__(*args, **kwargs)
        self.profile: dict[str, Any] | None = None

    async def start(self) -> AsyncIterator[Any]:
        """Schedule exactly one signed-in-user profile request."""
        self.crawler.stats.set_value("msgloom/crawl/mode", "profile")
        yield self._request(
            f"{self.graph_root}/me",
            callback=self.parse_profile,
            purpose="user-profile",
            cb_kwargs={},
        )

    def parse_profile(
        self,
        response: TextResponse,
        *,
        purpose: str,
    ) -> Iterator[Any]:
        """Persist raw evidence, validate the response, then retain the profile."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence

        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("Microsoft profile response must be a JSON object")
        user_id = payload.get("id")
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("Microsoft profile response must contain a non-empty id")

        self.profile = payload
        self.crawler.stats.inc_value("msgloom/crawl/profile/retrieved_count")

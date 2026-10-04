"""Reconcile saved trusted Microsoft Teams notification envelopes locally."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, ClassVar

from scrapy import signals
from scrapy.http import TextResponse
from twisted.python.failure import Failure

from message_ingest.extensions.catalog import CatalogService
from message_ingest.spiders.microsoft.teams._base import MicrosoftTeamsBaseSpider
from microsoft_graph.protocol.teams_notifications import TeamsNotificationError
from microsoft_graph.spiders.teams.channel_composition import (
    MicrosoftTeamsChannelCompositionSpider,
)
from microsoft_graph.spiders.teams.chat_composition import (
    MicrosoftTeamsChatCompositionSpider,
)

from ._notification_intake import (
    NotificationInputError,
    NotificationItemBarrier,
    NotificationReplayConflict,
    aggregate_coverage_items,
    deletion_items,
    inbound_evidence,
    load_local_gap,
    load_trusted_subscriptions,
    parse_authenticated_events,
    require_exact_evidence_replay,
)
from ._notification_readback import (
    NotificationReadbackContext,
    readback_contexts,
    readback_coverage,
    readback_message,
    readback_request,
)


class MicrosoftTeamsNotificationReconcileSpider(
    MicrosoftTeamsChatCompositionSpider,
    MicrosoftTeamsChannelCompositionSpider,
    MicrosoftTeamsBaseSpider,
):
    """
    Persist a saved basic webhook envelope and reconcile targeted messages.

    All notification, subscription, capture, and gap inputs are caller-local.
    This spider never exposes a webhook server, mutates a subscription, adds a
    scheduler, or treats notification resource text as an arbitrary fetch URL.
    """

    name = "microsoft_teams_notification_reconcile"
    graph_permissions: ClassVar[tuple[str, ...]] = (
        "Chat.Read",
        "ChannelMessage.Read.All",
    )
    failure_context_keys: ClassVar[tuple[str, ...]] = ()

    def __init__(
        self,
        *args: Any,
        envelope_path: str | None = None,
        trusted_subscriptions_path: str | None = None,
        envelope_id: str | None = None,
        captured_at: str | None = None,
        delivery_url: str | None = None,
        local_gap_path: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Keep explicit local inputs; validation occurs before dependent work."""
        super().__init__(*args, **kwargs)
        self.envelope_path = envelope_path
        self.trusted_subscriptions_path = trusted_subscriptions_path
        self.envelope_id = envelope_id
        self.captured_at = captured_at
        self.delivery_url = delivery_url
        self.local_gap_path = local_gap_path
        self._notification_barrier = NotificationItemBarrier()

    @classmethod
    def from_crawler(cls, crawler, *args: Any, **kwargs: Any):
        """Attach native item signals used as durable dependency barriers."""
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(
            spider._notification_barrier.item_scraped,
            signal=signals.item_scraped,
            weak=False,
        )
        crawler.signals.connect(
            spider._notification_barrier.item_error,
            signal=signals.item_error,
            weak=False,
        )
        crawler.signals.connect(
            spider._notification_barrier.item_dropped,
            signal=signals.item_dropped,
            weak=False,
        )
        return spider

    def _required_argument(self, value: str | None, *, name: str) -> str:
        if not isinstance(value, str) or not value:
            raise NotificationInputError(f"{name} is required")
        return value

    def _envelope_bytes(self) -> bytes:
        path = self._required_argument(self.envelope_path, name="envelope_path")
        try:
            return Path(path).read_bytes()
        except OSError as exc:
            raise NotificationInputError(
                "notification envelope file is unavailable"
            ) from exc

    async def _persist_item(self, item: Any) -> AsyncIterator[Any]:
        """Yield one item and wait for its complete configured pipeline result."""
        completion = self._notification_barrier.watch(item)
        yield item
        await completion

    async def start(self) -> AsyncIterator[Any]:
        """Persist raw input, validate atomically, then persist facts before GETs."""
        try:
            trusted_path = self._required_argument(
                self.trusted_subscriptions_path,
                name="trusted_subscriptions_path",
            )
            body = self._envelope_bytes()
            envelope_id = self._required_argument(
                self.envelope_id,
                name="envelope_id",
            )
            captured_at = self._required_argument(
                self.captured_at,
                name="captured_at",
            )
            delivery_url = self._required_argument(
                self.delivery_url,
                name="delivery_url",
            )
            trusted = load_trusted_subscriptions(
                trusted_path,
                source_id=self.source_id,
            )
            evidence = inbound_evidence(
                body=body,
                evidence_id=envelope_id,
                captured_at=captured_at,
                delivery_url=delivery_url,
                run_id=self.run_id,
            )
            service = CatalogService.from_crawler(self.crawler)
            require_exact_evidence_replay(
                service.catalog,
                source_id=self.source_id,
                item=evidence,
            )
        except NotificationReplayConflict:
            self.mark_run_failed("notification_replay_conflict")
            return
        except NotificationInputError:
            self.mark_run_failed("notification_input_invalid")
            return

        async for output in self._persist_item(evidence):
            yield output

        try:
            events = parse_authenticated_events(
                body,
                trusted=trusted,
                captured_at=captured_at,
            )
            local_gap = load_local_gap(
                self.local_gap_path,
                trusted=trusted,
                source_id=self.source_id,
                delivery_url=delivery_url,
                run_id=self.run_id,
            )
            if local_gap is not None:
                require_exact_evidence_replay(
                    service.catalog,
                    source_id=self.source_id,
                    item=local_gap.evidence,
                )
        except NotificationReplayConflict:
            self.mark_run_failed("notification_replay_conflict")
            return
        except (NotificationInputError, TeamsNotificationError):
            self.mark_run_failed("notification_invalid")
            return

        for item in aggregate_coverage_items(
            events,
            source_id=self.source_id,
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        ):
            async for output in self._persist_item(item):
                yield output

        for item in deletion_items(
            events,
            source_id=self.source_id,
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        ):
            async for output in self._persist_item(item):
                yield output

        if local_gap is not None:
            async for output in self._persist_item(local_gap.evidence):
                yield output
            async for output in self._persist_item(local_gap.coverage):
                yield output

        for context in readback_contexts(
            events,
            notification_evidence_id=evidence.evidence_id,
            notification_observed_at=evidence.observed_at,
        ):
            yield readback_request(self, context)

    async def parse_notification_readback(
        self,
        response: TextResponse,
        *,
        context: NotificationReadbackContext,
        purpose: str,
    ) -> AsyncIterator[Any]:
        """Persist actual Graph evidence before parsing and storing one message."""
        evidence = self._raw_http_evidence_item(response, purpose)
        async for output in self._persist_item(evidence):
            yield output

        message = readback_message(
            response,
            context=context,
            evidence=evidence,
            spider=self,
        )
        async for output in self._persist_item(message):
            yield output

        association = readback_coverage(
            context=context,
            evidence=evidence,
            spider=self,
            status="succeeded",
        )
        async for output in self._persist_item(association):
            yield output

    async def errback_notification_readback(
        self,
        failure: Failure,
    ) -> AsyncIterator[Any]:
        """Retain inherited terminal evidence before additive failed association."""
        request = self._failure_request(failure)
        context = request.cb_kwargs.get("context")
        if not isinstance(context, NotificationReadbackContext):
            raise TypeError("notification readback failure lacks trusted context")

        inherited = MicrosoftTeamsBaseSpider.errback(self, failure)
        evidence = next(inherited)
        async for output in self._persist_item(evidence):
            yield output

        failure_item = next(inherited)
        async for output in self._persist_item(failure_item):
            yield output

        association = readback_coverage(
            context=context,
            evidence=evidence,
            spider=self,
            status="failed",
        )
        async for output in self._persist_item(association):
            yield output


__all__ = ["MicrosoftTeamsNotificationReconcileSpider"]

"""Evidence-first channel hosted-content traversal and limitation callbacks."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from scrapy import Request
from scrapy.http import Response, TextResponse
from twisted.python.failure import Failure

from message_ingest.items.microsoft.teams.content import (
    TeamsHostedContentBytesItem,
    TeamsHostedContentFailureItem,
    TeamsHostedContentItem,
)
from message_ingest.items.microsoft.teams.coverage import TeamsCoverageItem
from message_ingest.items.microsoft.teams.message import TeamsMessageTrigger
from microsoft_graph.protocol import GraphCollectionPage
from microsoft_graph.spiders.teams.channel_composition import (
    parse_channel_hosted_contents,
)


class ChannelContentMixin:
    """Fetch hosted content per exact triggering message observation."""

    def _contextual_hosted_request(
        self: Any,
        request: Request,
        trigger: TeamsMessageTrigger,
    ) -> Request | None:
        """Bypass native dedup only after bounding one URL per exact trigger."""
        key = (trigger.evidence_id, trigger.identity.scope_key, request.url)
        if key in self._hosted_request_keys:
            return None
        self._hosted_request_keys.add(key)
        return request.replace(dont_filter=True)

    def _hosted_collection_request(
        self: Any,
        trigger: TeamsMessageTrigger,
    ) -> Request | None:
        """Schedule hosted metadata enumeration for one message observation."""
        purpose = "teams-channel-hosted-contents"
        request = self.hosted_contents_request(
            trigger.identity,
            callback=self.parse_hosted_contents,
            errback=self.hosted_errback,
            cb_kwargs={"purpose": purpose, "trigger": trigger},
            operation=purpose,
        )
        return self._contextual_hosted_request(request, trigger)

    def parse_hosted_contents(
        self: Any,
        response: TextResponse,
        *,
        purpose: str,
        trigger: TeamsMessageTrigger,
    ) -> Iterator[Any]:
        """Persist list metadata, then fetch current detail for every hosted ID."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(),
            context="Teams channel hosted-content collection",
            validate_links=False,
        )
        items = parse_channel_hosted_contents(
            page.values,
            message_identity=trigger.identity,
            item_type=TeamsHostedContentItem,
            trigger=trigger,
            **self._teams_provenance(evidence),
        )
        for item in items:
            yield item
            detail_purpose = "teams-channel-hosted-content"
            request = self.hosted_content_request(
                trigger.identity,
                item.hosted_content_id,
                callback=self.parse_hosted_content,
                errback=self.hosted_errback,
                cb_kwargs={
                    "purpose": detail_purpose,
                    "trigger": trigger,
                    "hosted_content_id": item.hosted_content_id,
                },
                operation=detail_purpose,
            )
            contextual = self._contextual_hosted_request(request, trigger)
            if contextual is not None:
                yield contextual

        if next_link := page.next_link:
            continuation = self.hosted_contents_continuation_request(
                next_link,
                callback=self.parse_hosted_contents,
                errback=self.hosted_errback,
                cb_kwargs={"purpose": purpose, "trigger": trigger},
                operation=purpose,
            )
            contextual = self._contextual_hosted_request(continuation, trigger)
            if contextual is not None:
                yield contextual

    def parse_hosted_content(
        self: Any,
        response: TextResponse,
        *,
        purpose: str,
        trigger: TeamsMessageTrigger,
        hosted_content_id: str,
    ) -> Iterator[Any]:
        """Persist current hosted metadata before scheduling its byte response."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        item = TeamsHostedContentItem.from_graph(
            response.json(),
            message_identity=trigger.identity,
            trigger=trigger,
            **self._teams_provenance(evidence),
        )
        if item.hosted_content_id != hosted_content_id:
            raise ValueError("Teams hosted-content ID differs from traversal scope")
        yield item

        bytes_purpose = "teams-channel-hosted-content-bytes"
        request = self.hosted_content_bytes_request(
            trigger.identity,
            hosted_content_id,
            callback=self.parse_hosted_content_bytes,
            errback=self.hosted_errback,
            cb_kwargs={
                "purpose": bytes_purpose,
                "trigger": trigger,
                "hosted_content_id": hosted_content_id,
            },
            operation=bytes_purpose,
        )
        contextual = self._contextual_hosted_request(request, trigger)
        if contextual is not None:
            yield contextual

    def parse_hosted_content_bytes(
        self: Any,
        response: Response,
        *,
        purpose: str,
        trigger: TeamsMessageTrigger,
        hosted_content_id: str,
    ) -> Iterator[Any]:
        """Persist byte digest/length that exactly match the linked raw response."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        raw_content_type = response.headers.get("Content-Type")
        content_type = (
            raw_content_type.decode("latin-1")
            if isinstance(raw_content_type, bytes)
            else raw_content_type
        )
        yield TeamsHostedContentBytesItem.from_bytes(
            body=response.body,
            message_identity=trigger.identity,
            hosted_content_id=hosted_content_id,
            trigger=trigger,
            content_type=content_type,
            **self._teams_provenance(evidence),
        )

    def hosted_errback(
        self: Any,
        failure: Failure,
    ) -> Iterator[Any]:
        """Retain inherited terminal failure plus hosted-specific limitation."""
        request = self._failure_request(failure)
        outputs = self._inherited_teams_errback(failure)
        evidence = next(outputs)
        yield evidence
        yield from outputs

        trigger = request.cb_kwargs.get("trigger")
        if not isinstance(trigger, TeamsMessageTrigger):
            raise TypeError("Teams hosted failure lacks its triggering observation")
        hosted_content_id = request.cb_kwargs.get("hosted_content_id")
        if isinstance(hosted_content_id, str) and hosted_content_id:
            yield TeamsHostedContentFailureItem(
                message_identity=trigger.identity,
                hosted_content_id=hosted_content_id,
                trigger=trigger,
                failure_kind="provider-request-failure",
                status_code=evidence.response_status,
                details={"purpose": request.cb_kwargs.get("purpose")},
                **self._teams_provenance(evidence),
            )
            return

        yield TeamsCoverageItem(
            scope_kind="hosted-content",
            scope=trigger.identity.scope_key,
            fact_kind="hosted-collection",
            status="unavailable",
            history_incomplete=True,
            details={
                "purpose": request.cb_kwargs.get("purpose"),
                "status_code": evidence.response_status,
            },
            **self._teams_provenance(evidence),
        )

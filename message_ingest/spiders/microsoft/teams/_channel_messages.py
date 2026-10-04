"""Evidence-first channel root/reply message traversal callbacks."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

from scrapy.http import TextResponse

from message_ingest.items.microsoft.teams.content import (
    TeamsReferenceResolutionItem,
)
from message_ingest.items.microsoft.teams.message import (
    TeamsMessageItem,
    TeamsMessageTrigger,
)
from microsoft_graph.protocol import GraphCollectionPage
from microsoft_graph.protocol.teams import TeamsAttachmentKind
from microsoft_graph.spiders.teams.channel_composition import (
    parse_channel_replies,
    parse_channel_root_messages,
)


class ChannelMessagesMixin:
    """Persist scoped root/reply observations before content follow-ups."""

    def parse_root_messages(
        self: Any,
        response: TextResponse,
        *,
        purpose: str,
        host_team_id: str,
        channel_id: str,
    ) -> Iterator[Any]:
        """Persist roots, then schedule every replies collection and content."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(),
            context="Teams channel root-message collection",
            validate_links=False,
        )
        messages = cast(
            tuple[TeamsMessageItem, ...],
            parse_channel_root_messages(
                page.values,
                host_team_id=host_team_id,
                channel_id=channel_id,
                item_type=TeamsMessageItem,
                **self._teams_provenance(evidence),
            ),
        )
        for message in messages:
            yield message
            yield from self._message_semantics(message)
            replies_purpose = "teams-channel-replies"
            yield self.replies_request(
                host_team_id,
                channel_id,
                message.message_id,
                callback=self.parse_replies,
                errback=self.errback,
                cb_kwargs={
                    "purpose": replies_purpose,
                    "host_team_id": host_team_id,
                    "channel_id": channel_id,
                    "root_message_id": message.message_id,
                },
                operation=replies_purpose,
            )
            hosted = self._hosted_collection_request(
                TeamsMessageTrigger.from_message(message)
            )
            if hosted is not None:
                yield hosted

        if next_link := page.next_link:
            yield self.message_continuation_request(
                next_link,
                callback=self.parse_root_messages,
                errback=self.errback,
                cb_kwargs={
                    "purpose": purpose,
                    "host_team_id": host_team_id,
                    "channel_id": channel_id,
                },
                operation=purpose,
            )

    def parse_replies(
        self: Any,
        response: TextResponse,
        *,
        purpose: str,
        host_team_id: str,
        channel_id: str,
        root_message_id: str,
    ) -> Iterator[Any]:
        """Persist every reply page under its traversal-path root identity."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(),
            context="Teams channel reply collection",
            validate_links=False,
        )
        messages = cast(
            tuple[TeamsMessageItem, ...],
            parse_channel_replies(
                page.values,
                host_team_id=host_team_id,
                channel_id=channel_id,
                root_message_id=root_message_id,
                item_type=TeamsMessageItem,
                **self._teams_provenance(evidence),
            ),
        )
        for message in messages:
            yield message
            yield from self._message_semantics(message)
            hosted = self._hosted_collection_request(
                TeamsMessageTrigger.from_message(message)
            )
            if hosted is not None:
                yield hosted

        if next_link := page.next_link:
            yield self.message_continuation_request(
                next_link,
                callback=self.parse_replies,
                errback=self.errback,
                cb_kwargs={
                    "purpose": purpose,
                    "host_team_id": host_team_id,
                    "channel_id": channel_id,
                    "root_message_id": root_message_id,
                },
                operation=purpose,
            )

    @staticmethod
    def _message_semantics(message: TeamsMessageItem) -> Iterator[Any]:
        """Emit explicit file-reference non-resolution using message evidence."""
        trigger = TeamsMessageTrigger.from_message(message)
        for ordinal, attachment in enumerate(message.attachment_items):
            if attachment.kind is not TeamsAttachmentKind.REFERENCE:
                continue
            yield TeamsReferenceResolutionItem(
                source_id=message.source_id,
                trigger=trigger,
                attachment_ordinal=ordinal,
                state="not-attempted",
                observed_at=message.observed_at,
                evidence_id=message.evidence_id,
                run_id=message.run_id,
                details={
                    "reason": "broad-file-profile-unselected",
                    "attachment_kind": attachment.kind.value,
                },
            )

"""Outlook Mail resource contracts layered on Microsoft Graph transport."""

from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar

from message_ingest.items.microsoft.outlook.email import OutlookMailItem
from message_ingest.spiders.microsoft.outlook._mailbox import OutlookMailboxSpider
from microsoft_graph.spiders.outlook.mail import OutlookMailSpider as GraphMail


class OutlookMailSpider(GraphMail, OutlookMailboxSpider, ABC):
    """
    Add Mail provenance and failure context to provider acquisition.

    The framework Mail base owns scopes, fields, and immutable-ID preference.
    This adapter adds provenance and failure callback context, using
    the msgloom Graph base for evidence and logical run integrity.
    """

    failure_context_keys: ClassVar[tuple[str, ...]] = (
        "message_id",
        "attachment_id",
        "folder_id",
    )

    def _message_item(
        self,
        message: dict[str, Any],
        source_response_url: str,
        observed_at: str,
        *,
        observation_kind: str,
        evidence_id: str | None,
    ) -> OutlookMailItem:
        """Retain the raw message beside searchable Mail projections."""
        return OutlookMailItem.from_graph(
            message,
            source_response_url=source_response_url,
            observed_at=observed_at,
            observation_kind=observation_kind,
            evidence_id=evidence_id,
            run_id=self.run_id,
        )

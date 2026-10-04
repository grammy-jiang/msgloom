"""Targeted Teams notification readback context and semantic helpers."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from scrapy import Request
from scrapy.http import TextResponse

from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.teams.coverage import TeamsCoverageItem
from message_ingest.items.microsoft.teams.message import TeamsMessageItem
from microsoft_graph.protocol.teams import TeamsMessageIdentity, TeamsMessageLocation
from microsoft_graph.protocol.teams_notifications import TeamsNotificationEvent
from microsoft_graph.spiders.teams.chat_composition import parse_chat_message

_READBACK_PURPOSE = "teams-notification-message-readback"


@dataclass(frozen=True, slots=True)
class NotificationReadbackContext:
    """Pickle-safe trigger for one deduplicated targeted message readback."""

    identity: TeamsMessageIdentity
    scope_kind: str
    scope: tuple[str, ...]
    notification_evidence_id: str
    notification_observed_at: str
    change_types: tuple[str, ...]


def readback_contexts(
    events: tuple[TeamsNotificationEvent, ...],
    *,
    notification_evidence_id: str,
    notification_observed_at: str,
) -> tuple[NotificationReadbackContext, ...]:
    """Coalesce one GET per scoped identity while retaining change kinds."""
    grouped: OrderedDict[
        TeamsMessageIdentity, tuple[str, tuple[str, ...], list[str]]
    ] = OrderedDict()
    for event in events:
        if event.identity is None or event.change_type is None:
            continue
        existing = grouped.get(event.identity)
        if existing is None:
            grouped[event.identity] = (
                event.scope_kind,
                event.scope,
                [event.change_type],
            )
            continue
        if event.change_type not in existing[2]:
            existing[2].append(event.change_type)

    return tuple(
        NotificationReadbackContext(
            identity=identity,
            scope_kind=scope_kind,
            scope=scope,
            notification_evidence_id=notification_evidence_id,
            notification_observed_at=notification_observed_at,
            change_types=tuple(change_types),
        )
        for identity, (scope_kind, scope, change_types) in grouped.items()
    )


def readback_request(spider: Any, context: NotificationReadbackContext) -> Request:
    """Use only existing provider builders for chat, root, or reply GETs."""
    kwargs = {
        "callback": spider.parse_notification_readback,
        "errback": spider.errback_notification_readback,
        "cb_kwargs": {"context": context, "purpose": _READBACK_PURPOSE},
        "operation": _READBACK_PURPOSE,
    }
    identity = context.identity
    if identity.location is TeamsMessageLocation.CHAT:
        if identity.chat_id is None:
            raise ValueError("notification chat identity is missing chat_id")
        return spider.chat_message_request(
            identity.chat_id,
            identity.message_id,
            **kwargs,
        )
    return spider.message_detail_request(identity, **kwargs)


def readback_message(
    response: TextResponse,
    *,
    context: NotificationReadbackContext,
    evidence: RawHttpEvidenceItem,
    spider: Any,
) -> TeamsMessageItem:
    """Parse one targeted response under its trusted request-path identity."""
    identity = context.identity
    provenance = spider._teams_provenance(evidence)
    if identity.location is TeamsMessageLocation.CHAT:
        if identity.chat_id is None:
            raise ValueError("notification chat identity is missing chat_id")
        item = parse_chat_message(
            response.json(),
            chat_id=identity.chat_id,
            message_id=identity.message_id,
            item_type=TeamsMessageItem,
            **provenance,
        )
        if not isinstance(item, TeamsMessageItem):
            raise TypeError("notification chat parser returned wrong application item")
        return item
    return TeamsMessageItem.from_graph(
        response.json(),
        identity=identity,
        **provenance,
    )


def _identity_details(identity: TeamsMessageIdentity) -> dict[str, Any]:
    return {
        "location": identity.location.value,
        "message_id": identity.message_id,
        "chat_id": identity.chat_id,
        "team_id": identity.team_id,
        "channel_id": identity.channel_id,
        "root_message_id": identity.root_message_id,
    }


def readback_coverage(
    *,
    context: NotificationReadbackContext,
    evidence: RawHttpEvidenceItem,
    spider: Any,
    status: str,
) -> TeamsCoverageItem:
    """Associate a later GET capture additively with immutable notification evidence."""
    if status not in {"succeeded", "failed"}:
        raise ValueError("notification readback status is unsupported")
    details: dict[str, Any] = {
        "notification_evidence_id": context.notification_evidence_id,
        "notification_observed_at": context.notification_observed_at,
        "message_identity": _identity_details(context.identity),
        "change_types": list(context.change_types),
        "readback_state": status,
    }
    if status == "failed":
        details["response_status"] = evidence.response_status
    return TeamsCoverageItem(
        source_id=spider.source_id,
        scope_kind=context.scope_kind,
        scope=context.scope,
        fact_kind="notification-readback",
        status=status,
        history_incomplete=False,
        observed_at=evidence.observed_at,
        evidence_id=evidence.evidence_id,
        run_id=spider.run_id,
        details=details,
    )


__all__ = [
    "NotificationReadbackContext",
    "readback_contexts",
    "readback_coverage",
    "readback_message",
    "readback_request",
]

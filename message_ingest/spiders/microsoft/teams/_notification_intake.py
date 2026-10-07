"""Local saved-envelope preparation for Teams notification reconciliation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.teams.coverage import TeamsCoverageItem
from message_ingest.items.microsoft.teams.message import TeamsMessageDeletionItem
from microsoft_graph.protocol.teams import TeamsMessageIdentity
from microsoft_graph.protocol.teams_notifications import (
    TeamsNotificationEvent,
    TeamsTrustedSubscription,
    teams_notifications_from_payload,
)

_EVIDENCE_ID = re.compile(r"^[0-9a-f]{32}$")
_LOCAL_GAP_KINDS = frozenset({"delivery-interruption", "subscription-expired"})


class NotificationInputError(ValueError):
    """Report invalid caller-local notification input without private values."""


class NotificationReplayConflict(NotificationInputError):
    """Report changed bytes or metadata under a stable evidence identifier."""


class NotificationItemProcessingError(RuntimeError):
    """Report a failed awaited item pipeline without exposing item contents."""


class NotificationItemBarrier:
    """Await native Scrapy item completion before dependent notification work."""

    def __init__(self) -> None:
        self._waiting: dict[int, asyncio.Future[None]] = {}

    def watch(self, item: object) -> asyncio.Future[None]:
        """Register an exact yielded item before handing it to Scrapy."""
        key = id(item)
        if key in self._waiting:
            raise RuntimeError("notification item is already awaiting persistence")
        future = asyncio.get_running_loop().create_future()
        self._waiting[key] = future
        return future

    def item_scraped(self, item: object, **_kwargs: Any) -> None:
        """Release a dependent operation only after every pipeline completed."""
        self._finish(item)

    def item_error(self, item: object, **_kwargs: Any) -> None:
        """Fail a dependent operation when native item processing fails."""
        self._finish(item, failed=True)

    def item_dropped(self, item: object, **_kwargs: Any) -> None:
        """Treat an intentional drop as a failed acquisition dependency."""
        self._finish(item, failed=True)

    def _finish(self, item: object, *, failed: bool = False) -> None:
        future = self._waiting.pop(id(item), None)
        if future is None or future.done():
            return
        if failed:
            future.set_exception(
                NotificationItemProcessingError(
                    "notification item did not complete the configured pipelines"
                )
            )
            return
        future.set_result(None)


@dataclass(frozen=True, slots=True)
class LocalGap:
    """One caller-trusted local delivery/validity gap with exact raw evidence."""

    evidence: RawHttpEvidenceItem
    coverage: TeamsCoverageItem


def _read_bytes(path: str, *, name: str) -> bytes:
    if not isinstance(path, str) or not path:
        raise NotificationInputError(f"{name} path is required")
    try:
        return Path(path).read_bytes()
    except OSError as exc:
        raise NotificationInputError(f"{name} file is unavailable") from exc


def _json_object(body: bytes, *, name: str) -> dict[str, Any]:
    try:
        value = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NotificationInputError(f"{name} must contain one JSON object") from exc
    if not isinstance(value, dict):
        raise NotificationInputError(f"{name} must contain one JSON object")
    return value


def _timestamp(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise NotificationInputError(f"{name} must be a non-empty UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise NotificationInputError(f"{name} must be a valid UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise NotificationInputError(f"{name} must be UTC")
    return value


def _evidence_id(value: object, *, name: str) -> str:
    if not isinstance(value, str) or _EVIDENCE_ID.fullmatch(value) is None:
        raise NotificationInputError(f"{name} must be a 32-character lowercase hex ID")
    return value


def load_trusted_subscriptions(
    path: str,
    *,
    source_id: str,
) -> dict[str, TeamsTrustedSubscription]:
    """Load caller-owned subscription records and bind every record to source."""
    payload = _json_object(
        _read_bytes(path, name="trusted subscriptions"), name="trusted subscriptions"
    )
    values = payload.get("subscriptions")
    if not isinstance(values, list) or not values:
        raise NotificationInputError("trusted subscriptions require a non-empty list")

    result: dict[str, TeamsTrustedSubscription] = {}
    for value in values:
        if not isinstance(value, Mapping):
            raise NotificationInputError("trusted subscription entry must be an object")
        bound_source = value.get("source_id")
        if not isinstance(bound_source, str) or not bound_source:
            raise NotificationInputError("trusted subscription record is invalid")
        if bound_source != source_id:
            raise NotificationInputError(
                "trusted subscription source does not match crawl"
            )
        try:
            record = TeamsTrustedSubscription.from_mapping(value)
        except (TypeError, ValueError) as exc:
            raise NotificationInputError(
                "trusted subscription record is invalid"
            ) from exc
        if record.subscription_id in result:
            raise NotificationInputError("trusted subscription IDs must be unique")
        result[record.subscription_id] = record
    return result


def inbound_evidence(
    *,
    body: bytes,
    evidence_id: str,
    captured_at: str,
    delivery_url: str,
    run_id: str,
) -> RawHttpEvidenceItem:
    """Represent saved inbound webhook bytes without fabricating a response."""
    evidence = _evidence_id(evidence_id, name="envelope_id")
    observed = _timestamp(captured_at, name="captured_at")
    if not isinstance(delivery_url, str) or not delivery_url:
        raise NotificationInputError("delivery_url is required")
    fingerprint = hashlib.sha256(
        b"POST\0" + delivery_url.encode("utf-8") + b"\0" + body
    ).hexdigest()
    return RawHttpEvidenceItem(
        evidence_id=evidence,
        run_id=run_id,
        purpose="teams-notification-envelope",
        observed_at=observed,
        origin="inbound-webhook",
        request_fingerprint=fingerprint,
        request_url=delivery_url,
        request_method="POST",
        request_headers={},
        request_body=body,
        response_url=None,
        response_status=None,
        response_headers={},
        response_body=b"",
        response_flags=[],
    )


def require_exact_evidence_replay(
    catalog,
    *,
    source_id: str,
    item: RawHttpEvidenceItem,
) -> bool:
    """Fail if an existing stable evidence ID differs from the supplied capture."""
    with catalog.Session() as session:
        existing = session.get(RawHttpEvidence, item.evidence_id)
        if existing is None:
            return False
        expected = (
            source_id,
            item.purpose,
            item.observed_at,
            item.origin,
            item.request_fingerprint,
            item.request_url,
            item.request_method,
            item.request_headers,
            hashlib.sha256(item.request_body).hexdigest(),
            len(item.request_body),
            item.response_url,
            item.response_status,
            item.response_headers,
            hashlib.sha256(item.response_body).hexdigest(),
            len(item.response_body),
            item.response_flags,
            item.error_type,
            item.error_message,
        )
        stored = (
            existing.source_id,
            existing.purpose,
            existing.observed_at,
            existing.origin,
            existing.request_fingerprint,
            existing.request_url,
            existing.request_method,
            existing.request_headers,
            existing.request_body_sha256,
            existing.request_body_bytes,
            existing.response_url,
            existing.response_status,
            existing.response_headers,
            existing.response_body_sha256,
            existing.response_body_bytes,
            existing.response_flags,
            existing.error_type,
            existing.error_message,
        )
    if stored != expected:
        raise NotificationReplayConflict(
            "stable notification evidence ID was reused with changed bytes or metadata"
        )
    return True


def parse_authenticated_events(
    body: bytes,
    *,
    trusted: Mapping[str, TeamsTrustedSubscription],
    captured_at: str,
) -> tuple[TeamsNotificationEvent, ...]:
    """Parse JSON only after raw persistence, then validate the whole envelope."""
    payload = _json_object(body, name="notification envelope")
    return teams_notifications_from_payload(
        payload,
        trusted_subscriptions=trusted,
        captured_at=captured_at,
    )


def _identity_details(identity: TeamsMessageIdentity | None) -> dict[str, Any] | None:
    if identity is None:
        return None
    return {
        "location": identity.location.value,
        "message_id": identity.message_id,
        "chat_id": identity.chat_id,
        "team_id": identity.team_id,
        "channel_id": identity.channel_id,
        "root_message_id": identity.root_message_id,
    }


def aggregate_coverage_items(
    events: tuple[TeamsNotificationEvent, ...],
    *,
    source_id: str,
    observed_at: str,
    evidence_id: str,
    run_id: str,
) -> tuple[TeamsCoverageItem, ...]:
    """Aggregate all ordered sanitized events by durable Teams coverage scope."""
    grouped: OrderedDict[tuple[str, tuple[str, ...]], list[TeamsNotificationEvent]] = (
        OrderedDict()
    )
    for event in events:
        grouped.setdefault((event.scope_kind, event.scope), []).append(event)

    items: list[TeamsCoverageItem] = []
    for (scope_kind, scope), scope_events in grouped.items():
        subscriptions = {
            (event.subscription_id, event.valid_from, event.valid_until)
            for event in scope_events
        }
        subscription_id = valid_from = valid_until = None
        if len(subscriptions) == 1:
            subscription_id, valid_from, valid_until = next(iter(subscriptions))
        gaps = [event.gap_kind for event in scope_events if event.gap_kind is not None]
        gap_kind = None
        if gaps:
            gap_kind = gaps[0] if len(set(gaps)) == 1 else "notification-gap"
        details = {
            "events": [
                {
                    "ordinal": event.ordinal,
                    "subscription_id": event.subscription_id,
                    "subscription_valid_from": event.valid_from,
                    "subscription_valid_until": event.valid_until,
                    "change_type": event.change_type,
                    "lifecycle_event": event.lifecycle_event,
                    "gap_kind": event.gap_kind,
                    "message_identity": _identity_details(event.identity),
                }
                for event in scope_events
            ]
        }
        items.append(
            TeamsCoverageItem(
                source_id=source_id,
                scope_kind=scope_kind,
                scope=scope,
                fact_kind="notification-envelope",
                status="observed",
                history_incomplete=bool(gaps),
                observed_at=observed_at,
                evidence_id=evidence_id,
                run_id=run_id,
                subscription_id=subscription_id,
                subscription_valid_from=valid_from,
                subscription_valid_until=valid_until,
                gap_kind=gap_kind,
                details=details,
            )
        )
    return tuple(items)


def deletion_items(
    events: tuple[TeamsNotificationEvent, ...],
    *,
    source_id: str,
    observed_at: str,
    evidence_id: str,
    run_id: str,
) -> tuple[TeamsMessageDeletionItem, ...]:
    """Return one immutable explicit declaration per deleted scoped message."""
    seen: set[TeamsMessageIdentity] = set()
    result: list[TeamsMessageDeletionItem] = []
    for event in events:
        if event.change_type != "deleted" or event.identity is None:
            continue
        if event.identity in seen:
            continue
        seen.add(event.identity)
        result.append(
            TeamsMessageDeletionItem(
                source_id=source_id,
                identity=event.identity,
                deletion_kind="notification",
                declared_deleted_at=None,
                observed_at=observed_at,
                evidence_id=evidence_id,
                run_id=run_id,
                readback_state="not-attempted",
            )
        )
    return tuple(result)


def load_local_gap(
    path: str | None,
    *,
    trusted: Mapping[str, TeamsTrustedSubscription],
    source_id: str,
    delivery_url: str,
    run_id: str,
) -> LocalGap | None:
    """Load optional caller-trusted gap evidence and derive scope from subscription."""
    if path is None:
        return None
    body = _read_bytes(path, name="local gap")
    payload = _json_object(body, name="local gap")
    evidence_id = _evidence_id(payload.get("evidence_id"), name="gap evidence_id")
    captured_at = _timestamp(payload.get("captured_at"), name="gap captured_at")
    subscription_id = payload.get("subscription_id")
    if not isinstance(subscription_id, str):
        raise NotificationInputError("local gap subscription_id is required")
    record = trusted.get(subscription_id)
    if record is None:
        raise NotificationInputError("local gap subscription is unknown")
    gap_kind = payload.get("gap_kind")
    if not isinstance(gap_kind, str) or gap_kind not in _LOCAL_GAP_KINDS:
        raise NotificationInputError("local gap kind is unsupported")
    fingerprint = hashlib.sha256(
        b"LOCAL\0" + delivery_url.encode("utf-8") + b"\0" + body
    ).hexdigest()
    evidence = RawHttpEvidenceItem(
        evidence_id=evidence_id,
        run_id=run_id,
        purpose="teams-notification-local-gap",
        observed_at=captured_at,
        origin="local-gap",
        request_fingerprint=fingerprint,
        request_url=delivery_url,
        request_method="LOCAL",
        request_headers={},
        request_body=body,
        response_url=None,
        response_status=None,
        response_headers={},
        response_body=b"",
        response_flags=[],
    )
    coverage = TeamsCoverageItem(
        source_id=source_id,
        scope_kind=record.scope_kind,
        scope=record.scope,
        fact_kind="notification-gap",
        status="incomplete",
        history_incomplete=True,
        observed_at=captured_at,
        evidence_id=evidence_id,
        run_id=run_id,
        subscription_id=record.subscription_id,
        subscription_valid_from=record.valid_from,
        subscription_valid_until=record.valid_until,
        gap_kind=gap_kind,
        details={"source": "trusted-local-gap", "gap_kind": gap_kind},
    )
    return LocalGap(evidence=evidence, coverage=coverage)


__all__ = [
    "LocalGap",
    "NotificationInputError",
    "NotificationItemBarrier",
    "NotificationItemProcessingError",
    "NotificationReplayConflict",
    "aggregate_coverage_items",
    "deletion_items",
    "inbound_evidence",
    "load_local_gap",
    "load_trusted_subscriptions",
    "parse_authenticated_events",
    "require_exact_evidence_replay",
]

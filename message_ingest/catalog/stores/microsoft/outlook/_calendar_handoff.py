"""Calendar-owned fact keys and immutable evidence locators.

Only hashes of allowlisted semantic projections enter the ledger. Mutable
provider rows remain planning state. Callers own strong writer transactions
and let any staging failure roll back their domain mutations.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind,
    AcquisitionStream,
    FactSpec,
    SourceVersionLocator,
    StorageRelation,
    canonical_json,
    source_state_key,
)
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

if TYPE_CHECKING:
    from message_ingest.catalog.store import Catalog

EVENT_FIELDS = (
    "id",
    "subject",
    "start",
    "end",
    "type",
    "seriesMasterId",
    "isAllDay",
    "isCancelled",
    "lastModifiedDateTime",
    "iCalUId",
    "recurrence",
)
CALENDAR_FIELDS = (
    "id",
    "changeKey",
    "name",
    "color",
    "hexColor",
    "owner",
    "isDefaultCalendar",
    "canEdit",
    "canShare",
    "canViewPrivateItems",
    "allowedOnlineMeetingProviders",
    "defaultOnlineMeetingProvider",
)
ATTACHMENT_FIELDS = (
    "id",
    "@odata.type",
    "name",
    "contentType",
    "size",
    "isInline",
    "lastModifiedDateTime",
    "contentId",
    "contentLocation",
    "item",
)
SERIES_FIELDS = (
    "id",
    "changeKey",
    "recurrence",
    "cancelledOccurrences",
    "exceptionOccurrences",
)


def semantic_digest(value: Any) -> str:
    """Hash provider meaning while excluding nested transport-only annotations."""

    def clean(item: Any) -> Any:
        if isinstance(item, list):
            return [clean(child) for child in item]
        if isinstance(item, dict):
            return {
                key: clean(child)
                for key, child in item.items()
                if key
                not in {
                    "@odata.context",
                    "@odata.nextLink",
                    "@odata.deltaLink",
                    "@microsoft.graph.downloadUrl",
                    "access_token",
                    "accessToken",
                    "authorization",
                    "Authorization",
                }
            }
        return item

    encoded = json.dumps(
        clean(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


class CalendarProvenance(Protocol):
    """Logical acquisition provenance independent of canonical capture owner."""

    run_id: str | None
    evidence_id: str | None
    observed_at: str


def projection(raw: dict[str, Any] | None, fields: tuple[str, ...]) -> dict[str, str]:
    """Hash retained fields individually so large content stays outside metadata."""
    raw = raw or {}
    return {name: semantic_digest(raw.get(name)) for name in fields}


def event_projection(raw: dict[str, Any]) -> dict[str, Any]:
    """Keep primary versions independent of richer Full component fields."""
    change_key = raw.get("changeKey")
    if isinstance(change_key, str) and change_key:
        return {"changeKey": change_key}
    return projection(raw, EVENT_FIELDS)


class CalendarFactStore:
    """Share Calendar fact construction without owning transaction boundaries."""

    def __init__(self, catalog: Catalog, *, source_id: str) -> None:
        self.catalog = catalog
        self.source_id = source_id
        self.handoff = AcquisitionHandoffStore(catalog)

    def _evidence_digest(self, session: Session, evidence_id: str | None) -> str | None:
        """Read the digest of bytes already saved by the evidence pipeline."""
        if evidence_id is None:
            return None
        digest = session.scalar(
            select(RawHttpEvidence.response_body_sha256).where(
                RawHttpEvidence.source_id == self.source_id,
                RawHttpEvidence.evidence_id == evidence_id,
            )
        )
        if digest is None:
            raise ValueError("Calendar fact requires durable source evidence")
        return digest

    def _surface_digest(
        self,
        session: Session,
        evidence_id: str | None,
        surface: str,
    ) -> str | None:
        """Hash JSON metadata semantically and raw attachment bytes exactly."""
        if evidence_id is None:
            return None
        row = session.scalar(
            select(RawHttpEvidence).where(
                RawHttpEvidence.source_id == self.source_id,
                RawHttpEvidence.evidence_id == evidence_id,
            )
        )
        if row is None:
            raise ValueError("Calendar fact requires durable source evidence")
        body = Path(row.response_body_path).read_bytes()
        if hashlib.sha256(body).hexdigest() != row.response_body_sha256:
            raise ValueError("Calendar surface evidence digest mismatch")
        if surface.startswith("attachment_raw:"):
            return row.response_body_sha256
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            return row.response_body_sha256
        return semantic_digest(payload)

    def _stage_fact(
        self,
        session: Session,
        item: CalendarProvenance,
        *,
        resource_kind: str,
        identity: str,
        state: object,
        outcome: str,
        spider_name: str = "outlook_calendar_full",
        component: str | None = None,
        parent: str | None = None,
        observation_id: str | None = None,
        resource_version: str | None = None,
        scope: str | None = None,
        order: int | None = None,
        reason: str | None = None,
        authority: bool = False,
    ) -> FactSpec:
        """Stage exact provenance; never substitute evidence ownership for run ID."""
        if not item.run_id:
            raise ValueError("Calendar facts require explicit logical run_id")
        # Validate source ownership without equating capture and logical runs.
        self._evidence_digest(session, item.evidence_id)
        locator = None
        if item.evidence_id is not None:
            locator = SourceVersionLocator(
                kind="observation" if observation_id else "evidence",
                evidence_id=item.evidence_id,
                resource_identity=identity,
                observation_id=observation_id,
                component_kind=component,
                resource_version=resource_version,
            )
        relation = (
            StorageRelation.STALE
            if outcome == "stale"
            else StorageRelation.CURRENT_EQUIVALENT
            if outcome in {"unchanged", "replay"}
            else StorageRelation.ADVANCED
        )
        spec = FactSpec(
            source_id=self.source_id,
            stream=AcquisitionStream.OUTLOOK_CALENDAR,
            run_id=item.run_id,
            spider_name=spider_name,
            fact_kind=(
                AcquisitionFactKind.COMPONENT_OBSERVATION
                if component
                else AcquisitionFactKind.CONTROL_CONTEXT
                if resource_kind == "calendar"
                else AcquisitionFactKind.RESOURCE_OBSERVATION
            ),
            resource_kind=resource_kind,
            resource_identity=identity,
            provider_observed_at=item.observed_at,
            source_state_key=source_state_key(state),
            source_version_locator=locator,
            storage_relation=relation,
            parent_resource_kind="calendar_event" if parent else None,
            parent_resource_identity=parent,
            component_kind=component,
            scope_kind="calendar_window" if scope else None,
            scope_identity=scope,
            evidence_id=item.evidence_id,
            provider_order=order,
            transition_reason=reason,
        )
        if authority:
            return self.handoff.stage_authority_fact_in_session(session, spec)
        current = self.handoff.current_effective_state(session, spec.effective_key)
        if (
            relation == StorageRelation.CURRENT_EQUIVALENT
            and current is not None
            and current["source_state_key"] != spec.source_state_key
        ):
            # Legacy counters compare provider rows, which do not contain all
            # component version bindings. A changed accepted binding advances
            # its ledger state; unchanged pre-ledger rows still stay unindexed.
            spec = replace(spec, storage_relation=StorageRelation.ADVANCED)
        return self.handoff.stage_state_fact_in_session(session, spec)

    def _stage_event(self, session, item, outcome, observation_id=None) -> None:
        """Retain observation identity while delta remains authority staging."""
        self._stage_fact(
            session,
            item,
            resource_kind="calendar_event",
            identity=item.event_id,
            state=event_projection(item.raw),
            outcome=outcome,
            spider_name=f"outlook_calendar_{item.observation_kind}",
            observation_id=observation_id,
            resource_version=item.provider.change_key,
            authority=item.observation_kind == "delta",
        )

    def _stage_delta(self, session, item, observation_id: str) -> None:
        """Bind attempt/order to an immutable ordered window observation."""
        scope = canonical_json(
            [
                item.calendar_scope,
                item.start_datetime,
                item.end_datetime,
            ]
        )
        reason = canonical_json(
            {
                "attempt": item.attempt,
                "page_number": item.page_number,
                "entry_index": item.entry_index,
                "kind": item.kind,
                "removed_reason": (
                    item.removed_reason
                    if item.removed_reason in {None, "deleted", "changed"}
                    else "other"
                ),
            }
        )
        self._stage_fact(
            session,
            item,
            resource_kind="calendar_event",
            identity=item.event_id,
            state={"event": event_projection(item.raw), "kind": item.kind},
            outcome="created",
            spider_name="outlook_calendar_delta",
            observation_id=observation_id,
            scope=scope,
            order=(item.page_number << 32) + item.entry_index,
            reason=reason,
            authority=True,
        )

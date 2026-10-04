"""Persistence for Teams attachment resolution and hosted-content responses."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from message_ingest.catalog.models.microsoft.teams.content import (
    TeamsHostedContentObservation,
    TeamsReferenceResolutionCurrent,
    TeamsReferenceResolutionObservation,
)
from message_ingest.catalog.models.microsoft.teams.message import (
    TeamsMessageAttachmentObservation,
    TeamsMessageObservation,
)
from message_ingest.catalog.store import Catalog
from message_ingest.items.microsoft.teams.content import (
    TeamsHostedContentBytesItem,
    TeamsHostedContentFailureItem,
    TeamsHostedContentItem,
    TeamsReferenceResolutionItem,
)
from message_ingest.items.microsoft.teams.message import TeamsMessageTrigger

from ._common import (
    Outcome,
    compare_observed,
    require_evidence,
    require_source,
)
from .message import message_scope


class TeamsContentStore:
    """Store explicit content outcomes without following arbitrary provider URLs."""

    def __init__(self, catalog: Catalog, *, source_id: str) -> None:
        self.catalog = catalog
        self.source_id = source_id

    def persist_reference(
        self,
        item: TeamsReferenceResolutionItem,
        *,
        trigger_evidence_id: str | None = None,
        trigger_observed_at: str | None = None,
        evidence_id: str | None = None,
        observed_at: str | None = None,
    ) -> Outcome:
        """Append one attachment-resolution fact and update its current state."""
        require_source(item.source_id, self.source_id)
        trigger_id = trigger_evidence_id or item.trigger.evidence_id
        trigger_time = trigger_observed_at or item.trigger.observed_at
        response_id = evidence_id or item.evidence_id
        response_time = observed_at or item.observed_at
        with self.catalog.writer_session() as session:
            trigger = self._require_trigger(
                session,
                item.trigger,
                evidence_id=trigger_id,
                observed_at=trigger_time,
            )
            response = require_evidence(
                session,
                source_id=self.source_id,
                evidence_id=response_id,
                observed_at=response_time,
            )
            attachment = session.get(
                TeamsMessageAttachmentObservation,
                (trigger.observation_id, item.attachment_ordinal),
            )
            if attachment is None:
                raise ValueError(
                    "Teams reference resolution requires the triggering "
                    "attachment observation"
                )

            existing = session.scalar(
                select(TeamsReferenceResolutionObservation).filter_by(
                    source_id=self.source_id,
                    trigger_scope_sha256=trigger.scope_key_sha256,
                    trigger_evidence_id=trigger.evidence_id,
                    attachment_ordinal=item.attachment_ordinal,
                    evidence_id=response.evidence_id,
                )
            )
            if existing is not None:
                if existing.state != item.state or existing.details != item.details:
                    raise ValueError("Teams reference replay changed immutable facts")
                return "replay"

            observation = TeamsReferenceResolutionObservation(
                source_id=self.source_id,
                trigger_scope_sha256=trigger.scope_key_sha256,
                trigger_evidence_id=trigger.evidence_id,
                trigger_observed_at=trigger.observed_at,
                attachment_ordinal=item.attachment_ordinal,
                state=item.state,
                observed_at=response_time,
                evidence_id=response.evidence_id,
                run_id=item.run_id,
                evidence_run_id=response.run_id,
                details=item.details,
            )
            session.add(observation)
            session.flush()
            current_key = (
                self.source_id,
                trigger.scope_key_sha256,
                trigger.evidence_id,
                item.attachment_ordinal,
            )
            current = session.get(TeamsReferenceResolutionCurrent, current_key)
            if current is None:
                session.add(
                    TeamsReferenceResolutionCurrent(
                        source_id=self.source_id,
                        trigger_scope_sha256=trigger.scope_key_sha256,
                        trigger_evidence_id=trigger.evidence_id,
                        attachment_ordinal=item.attachment_ordinal,
                        observation_id=observation.observation_id,
                        state=item.state,
                        latest_observed_at=response_time,
                        latest_evidence_id=response.evidence_id,
                        latest_run_id=item.run_id,
                        latest_evidence_run_id=response.run_id,
                        details=item.details,
                    )
                )
                return "created"
            ordering = compare_observed(response_time, current.latest_observed_at)
            if ordering < 0:
                return "stale"
            if ordering == 0:
                return "tie"
            current.observation_id = observation.observation_id
            current.state = item.state
            current.latest_observed_at = response_time
            current.latest_evidence_id = response.evidence_id
            current.latest_run_id = item.run_id
            current.latest_evidence_run_id = response.run_id
            current.details = item.details
            return "advanced"

    def persist_hosted_metadata(
        self,
        item: TeamsHostedContentItem,
        **aliases: str | None,
    ) -> Outcome:
        """Append one hosted-content metadata response."""
        return self._persist_hosted(
            item,
            observation_kind="metadata",
            raw=item.raw,
            content_type=item.content_type,
            content_sha256=None,
            content_bytes=None,
            failure_kind=None,
            status_code=None,
            details={},
            **aliases,
        )

    def persist_hosted_bytes(
        self,
        item: TeamsHostedContentBytesItem,
        **aliases: str | None,
    ) -> Outcome:
        """Append one hosted byte retrieval represented by digest metadata."""
        return self._persist_hosted(
            item,
            observation_kind="bytes",
            raw=None,
            content_type=item.content_type,
            content_sha256=item.content_sha256,
            content_bytes=item.content_bytes,
            failure_kind=None,
            status_code=None,
            details={},
            **aliases,
        )

    def persist_hosted_failure(
        self,
        item: TeamsHostedContentFailureItem,
        **aliases: str | None,
    ) -> Outcome:
        """Append an explicit hosted retrieval failure or provider limitation."""
        return self._persist_hosted(
            item,
            observation_kind="failure",
            raw=None,
            content_type=None,
            content_sha256=None,
            content_bytes=None,
            failure_kind=item.failure_kind,
            status_code=item.status_code,
            details=item.details,
            **aliases,
        )

    def _persist_hosted(
        self,
        item: TeamsHostedContentItem
        | TeamsHostedContentBytesItem
        | TeamsHostedContentFailureItem,
        *,
        observation_kind: str,
        raw: dict[str, object] | None,
        content_type: object | None,
        content_sha256: str | None,
        content_bytes: int | None,
        failure_kind: str | None,
        status_code: int | None,
        details: dict[str, object],
        trigger_evidence_id: str | None = None,
        trigger_observed_at: str | None = None,
        evidence_id: str | None = None,
        observed_at: str | None = None,
    ) -> Outcome:
        """Append hosted content tied to the exact committed trigger response."""
        require_source(item.source_id, self.source_id)
        if item.message_identity != item.trigger.identity:
            raise ValueError("Teams hosted content identity differs from its trigger")
        trigger_id = trigger_evidence_id or item.trigger.evidence_id
        trigger_time = trigger_observed_at or item.trigger.observed_at
        response_id = evidence_id or item.evidence_id
        response_time = observed_at or item.observed_at
        with self.catalog.writer_session() as session:
            trigger = self._require_trigger(
                session,
                item.trigger,
                evidence_id=trigger_id,
                observed_at=trigger_time,
            )
            response = require_evidence(
                session,
                source_id=self.source_id,
                evidence_id=response_id,
                observed_at=response_time,
            )
            # Byte metadata must describe the same durable raw response.
            # This also validates aliases before an idempotent replay returns.
            if observation_kind == "bytes" and (
                content_sha256 != response.response_body_sha256
                or content_bytes != response.response_body_bytes
            ):
                raise ValueError("Teams hosted content differs from response bytes")
            existing = session.scalar(
                select(TeamsHostedContentObservation).filter_by(
                    source_id=self.source_id,
                    trigger_scope_sha256=trigger.scope_key_sha256,
                    trigger_evidence_id=trigger.evidence_id,
                    hosted_content_id=item.hosted_content_id,
                    observation_kind=observation_kind,
                    evidence_id=response.evidence_id,
                )
            )
            values = {
                "raw": raw,
                "content_type": content_type,
                "content_sha256": content_sha256,
                "content_bytes": content_bytes,
                "failure_kind": failure_kind,
                "status_code": status_code,
                "details": details,
            }
            if existing is not None:
                if any(
                    getattr(existing, name) != value for name, value in values.items()
                ):
                    raise ValueError("Teams hosted replay changed immutable facts")
                return "replay"
            session.add(
                TeamsHostedContentObservation(
                    source_id=self.source_id,
                    trigger_scope_sha256=trigger.scope_key_sha256,
                    trigger_evidence_id=trigger.evidence_id,
                    trigger_observed_at=trigger.observed_at,
                    hosted_content_id=item.hosted_content_id,
                    observation_kind=observation_kind,
                    provider_version_bound=False,
                    observed_at=response_time,
                    evidence_id=response.evidence_id,
                    run_id=item.run_id,
                    evidence_run_id=response.run_id,
                    **values,
                )
            )
            return "created"

    def _require_trigger(
        self,
        session: Session,
        trigger: TeamsMessageTrigger,
        *,
        evidence_id: str,
        observed_at: str,
    ) -> TeamsMessageObservation:
        """Resolve a canonicalized trigger to the exact committed message row."""
        require_source(trigger.source_id, self.source_id)
        _scope, digest = message_scope(trigger.identity)
        observation = session.scalar(
            select(TeamsMessageObservation).filter_by(
                source_id=self.source_id,
                scope_key_sha256=digest,
                evidence_id=evidence_id,
            )
        )
        if observation is None or observation.observed_at != observed_at:
            raise ValueError(
                "Teams content requires the exact triggering message observation"
            )
        return observation


__all__ = ["TeamsContentStore"]

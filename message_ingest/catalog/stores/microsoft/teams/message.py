"""Persistence for immutable Teams message captures and explicit deletion."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from message_ingest.catalog.models.microsoft.teams.message import (
    TeamsMessageAttachmentObservation,
    TeamsMessageCurrent,
    TeamsMessageDeletionObservation,
    TeamsMessageObservation,
)
from message_ingest.catalog.store import Catalog
from message_ingest.items.microsoft.teams.message import (
    TeamsMessageDeletionItem,
    TeamsMessageItem,
)
from microsoft_graph.protocol.teams import TeamsMessageIdentity

from ._common import (
    Outcome,
    compare_observed,
    require_evidence,
    require_source,
    scope_digest,
)


def message_scope(
    identity: TeamsMessageIdentity,
) -> tuple[list[str | None], str]:
    """Return canonical message scope values and their durable digest."""
    return scope_digest(("message", *identity.scope_key))


def _identity_values(identity: TeamsMessageIdentity) -> dict[str, str | None]:
    """Project path-owned opaque identity without relying on payload fields."""
    return {
        "location": identity.location.value,
        "message_id": identity.message_id,
        "chat_id": identity.chat_id,
        "team_id": identity.team_id,
        "channel_id": identity.channel_id,
        "root_message_id": identity.root_message_id,
    }


class TeamsMessageStore:
    """Store every observed response while keeping current state explicit."""

    def __init__(self, catalog: Catalog, *, source_id: str) -> None:
        self.catalog = catalog
        self.source_id = source_id

    def persist_message(self, item: TeamsMessageItem) -> Outcome:
        """
        Append one observed message and advance current only when strictly newer.

        Provider etags are retained as equality facts. They never determine
        chronological order. The exact source/scope/evidence replay is
        idempotent even if a later crawl reused that canonical response.
        """
        require_source(item.source_id, self.source_id)
        scope_key, digest = message_scope(item.identity)
        with self.catalog.writer_session() as session:
            evidence = require_evidence(
                session,
                source_id=self.source_id,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
            )
            existing = session.scalar(
                select(TeamsMessageObservation).filter_by(
                    source_id=self.source_id,
                    scope_key_sha256=digest,
                    evidence_id=item.evidence_id,
                )
            )
            if existing is not None:
                if existing.raw != item.raw:
                    raise ValueError(
                        "Teams message replay changed immutable provider facts"
                    )
                return "replay"

            observation = TeamsMessageObservation(
                source_id=self.source_id,
                scope_key=scope_key,
                scope_key_sha256=digest,
                provider_etag=item.etag,
                deleted_date_time=item.deleted_date_time,
                observed_at=item.observed_at,
                evidence_id=item.evidence_id,
                run_id=item.run_id,
                evidence_run_id=evidence.run_id,
                raw=item.raw,
                **_identity_values(item.identity),
            )
            session.add(observation)
            session.flush()
            self._append_attachments(session, observation, item)
            if item.deleted_date_time is not None:
                self._append_direct_deletion(
                    session,
                    item=item,
                    digest=digest,
                    scope_key=scope_key,
                    evidence_run_id=evidence.run_id,
                )
            return self._project_message_current(
                session,
                observation=observation,
                item=item,
                digest=digest,
                scope_key=scope_key,
                evidence_run_id=evidence.run_id,
            )

    def persist_deletion(
        self,
        item: TeamsMessageDeletionItem,
        *,
        evidence_id: str | None = None,
        observed_at: str | None = None,
        readback_evidence_id: str | None = None,
        readback_observed_at: str | None = None,
    ) -> Outcome:
        """Persist an explicit deletion declaration without discarding old body."""
        require_source(item.source_id, self.source_id)
        effective_evidence = evidence_id or item.evidence_id
        effective_observed = observed_at or item.observed_at
        effective_readback_evidence = (
            readback_evidence_id
            if readback_evidence_id is not None
            else item.readback_evidence_id
        )
        effective_readback_observed = (
            readback_observed_at
            if readback_observed_at is not None
            else item.readback_observed_at
        )
        scope_key, digest = message_scope(item.identity)

        with self.catalog.writer_session() as session:
            evidence = require_evidence(
                session,
                source_id=self.source_id,
                evidence_id=effective_evidence,
                observed_at=effective_observed,
            )
            readback_run_id = None
            if effective_readback_evidence is not None:
                if effective_readback_observed is None:
                    raise ValueError(
                        "Teams deletion readback observation time is missing"
                    )
                readback = require_evidence(
                    session,
                    source_id=self.source_id,
                    evidence_id=effective_readback_evidence,
                    observed_at=effective_readback_observed,
                )
                readback_run_id = readback.run_id

            existing = session.scalar(
                select(TeamsMessageDeletionObservation).filter_by(
                    source_id=self.source_id,
                    scope_key_sha256=digest,
                    evidence_id=evidence.evidence_id,
                )
            )
            if existing is not None:
                if (
                    existing.deletion_kind != item.deletion_kind
                    or existing.readback_evidence_id != effective_readback_evidence
                    or existing.readback_observed_at != effective_readback_observed
                    or existing.readback_state != item.readback_state
                    or existing.declared_deleted_at != item.declared_deleted_at
                ):
                    raise ValueError("Teams deletion replay changed immutable facts")
                return "replay"

            session.add(
                TeamsMessageDeletionObservation(
                    source_id=self.source_id,
                    scope_key=scope_key,
                    scope_key_sha256=digest,
                    deletion_kind=item.deletion_kind,
                    declared_deleted_at=item.declared_deleted_at,
                    observed_at=effective_observed,
                    evidence_id=evidence.evidence_id,
                    run_id=item.run_id,
                    evidence_run_id=evidence.run_id,
                    readback_state=item.readback_state,
                    readback_observed_at=effective_readback_observed,
                    readback_evidence_id=effective_readback_evidence,
                    readback_evidence_run_id=readback_run_id,
                )
            )
            return self._project_deletion_current(
                session,
                item=item,
                digest=digest,
                scope_key=scope_key,
                observed_at=effective_observed,
                evidence_id=evidence.evidence_id,
                evidence_run_id=evidence.run_id,
            )

    @staticmethod
    def _append_attachments(
        session: Session,
        observation: TeamsMessageObservation,
        item: TeamsMessageItem,
    ) -> None:
        """Retain embedded attachment order even when IDs repeat or are absent."""
        for ordinal, attachment in enumerate(item.attachment_items):
            attachment_id = (
                attachment.attachment_id
                if isinstance(attachment.attachment_id, str)
                else None
            )
            session.add(
                TeamsMessageAttachmentObservation(
                    message_observation_id=observation.observation_id,
                    ordinal=ordinal,
                    source_id=observation.source_id,
                    scope_key_sha256=observation.scope_key_sha256,
                    attachment_id=attachment_id,
                    kind=attachment.kind.value,
                    content_type=attachment.content_type,
                    raw=attachment.raw,
                )
            )

    @staticmethod
    def _append_direct_deletion(
        session: Session,
        *,
        item: TeamsMessageItem,
        digest: str,
        scope_key: list[str | None],
        evidence_run_id: str | None,
    ) -> None:
        """Record deletedDateTime as explicit provider deletion evidence."""
        session.add(
            TeamsMessageDeletionObservation(
                source_id=item.source_id,
                scope_key=scope_key,
                scope_key_sha256=digest,
                deletion_kind="direct",
                declared_deleted_at=item.deleted_date_time,
                observed_at=item.observed_at,
                evidence_id=item.evidence_id,
                run_id=item.run_id,
                evidence_run_id=evidence_run_id,
                readback_state="not-attempted",
                readback_observed_at=None,
                readback_evidence_id=None,
                readback_evidence_run_id=None,
            )
        )

    @staticmethod
    def _project_message_current(
        session: Session,
        *,
        observation: TeamsMessageObservation,
        item: TeamsMessageItem,
        digest: str,
        scope_key: list[str | None],
        evidence_run_id: str | None,
    ) -> Outcome:
        """Apply strict capture-time projection semantics."""
        current = session.get(TeamsMessageCurrent, (item.source_id, digest))
        values = {
            "scope_key": scope_key,
            "message_observation_id": observation.observation_id,
            "provider_etag": item.etag,
            "deleted_date_time": item.deleted_date_time,
            "is_deleted": item.deleted_date_time is not None,
            "latest_observed_at": item.observed_at,
            "latest_evidence_id": item.evidence_id,
            "latest_run_id": item.run_id,
            "latest_evidence_run_id": evidence_run_id,
            "raw": item.raw,
            **_identity_values(item.identity),
        }
        if current is None:
            session.add(
                TeamsMessageCurrent(
                    source_id=item.source_id,
                    scope_key_sha256=digest,
                    **values,
                )
            )
            return "created"
        ordering = compare_observed(item.observed_at, current.latest_observed_at)
        if ordering < 0:
            return "stale"
        if ordering == 0:
            return "tie"
        for name, value in values.items():
            setattr(current, name, value)
        return "advanced"

    @staticmethod
    def _project_deletion_current(
        session: Session,
        *,
        item: TeamsMessageDeletionItem,
        digest: str,
        scope_key: list[str | None],
        observed_at: str,
        evidence_id: str,
        evidence_run_id: str | None,
    ) -> Outcome:
        """Apply an explicit deletion only when its capture is strictly newer."""
        current = session.get(TeamsMessageCurrent, (item.source_id, digest))
        if current is None:
            session.add(
                TeamsMessageCurrent(
                    source_id=item.source_id,
                    scope_key_sha256=digest,
                    scope_key=scope_key,
                    message_observation_id=None,
                    provider_etag=None,
                    deleted_date_time=item.declared_deleted_at,
                    is_deleted=True,
                    latest_observed_at=observed_at,
                    latest_evidence_id=evidence_id,
                    latest_run_id=item.run_id,
                    latest_evidence_run_id=evidence_run_id,
                    raw=None,
                    **_identity_values(item.identity),
                )
            )
            return "created"
        ordering = compare_observed(observed_at, current.latest_observed_at)
        if ordering < 0:
            return "stale"
        if ordering == 0:
            return "tie"
        current.is_deleted = True
        current.deleted_date_time = item.declared_deleted_at
        current.latest_observed_at = observed_at
        current.latest_evidence_id = evidence_id
        current.latest_run_id = item.run_id
        current.latest_evidence_run_id = evidence_run_id
        return "advanced"


__all__ = ["TeamsMessageStore", "message_scope"]

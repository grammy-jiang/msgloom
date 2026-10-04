"""Mail-owned semantic keys and transaction-neutral acquisition facts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind as Kind,
)
from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    FactSpec,
    SourceVersionLocator,
    StorageRelation,
)
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from microsoft_graph.spiders.outlook.mail import OutlookMailSpider

if TYPE_CHECKING:
    from message_ingest.catalog.store import Catalog

_PRIMARY_FIELDS = set(OutlookMailSpider.discovery_fields) - {
    "changeKey",
    "webLink",
}


@dataclass(frozen=True)
class MailPersistenceOutcome:
    """Separate observation insertion, domain freshness, and immutable fact."""

    fact: FactSpec
    storage_relation: StorageRelation
    observation_created: bool = False


def semantic_digest(value: object) -> str:
    """Hash retained state without imposing the ledger metadata byte limit."""
    digest = hashlib.sha256()
    encoder = json.JSONEncoder(
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    for chunk in encoder.iterencode(value):
        digest.update(chunk.encode())
    return digest.hexdigest()


def primary_projection(message: dict[str, Any]) -> dict[str, Any]:
    """
    Use the provider version, or a bounded primary projection when absent.

    Full-only components and transport values cannot reversion the primary.
    """
    change_key = message.get("changeKey")
    if change_key:
        return {"changeKey": change_key}
    return {k: v for k, v in message.items() if k in _PRIMARY_FIELDS}


def is_stale(observed_at: str, previous: str | None) -> bool:
    """Compare provider observation timestamps as instants."""
    return previous is not None and (
        datetime.fromisoformat(observed_at) < datetime.fromisoformat(previous)
    )


def verified_digest(session: Session, source_id: str, evidence_id: str | None) -> str:
    """Verify saved content before accepting an acquired byte component."""
    row = session.get(RawHttpEvidence, evidence_id) if evidence_id else None
    if row is None or row.source_id != source_id:
        raise ValueError("Acquired Mail component requires saved source evidence")
    with Path(row.response_body_path).open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
        size = stream.tell()
    if digest != row.response_body_sha256 or size != row.response_body_bytes:
        raise ValueError("Saved Mail component digest or size mismatch")
    return digest


def previous_primary_key(
    session: Session,
    source_id: str,
    evidence_id: str | None,
    message_id: str,
) -> str | None:
    """Use exact pre-ledger evidence to avoid fabricated bootstrap work."""
    row = session.get(RawHttpEvidence, evidence_id) if evidence_id else None
    if row is None or row.source_id != source_id:
        return None
    try:
        payload = json.loads(Path(row.response_body_path).read_bytes())
    except (OSError, ValueError):
        return None
    values = payload.get("value", [payload]) if isinstance(payload, dict) else []
    for value in values:
        if isinstance(value, dict) and value.get("id") == message_id:
            return semantic_digest(primary_projection(value))
    return None


class MailFactWriter:
    """Stage Mail facts in the caller-owned strong writer transaction."""

    def __init__(self, catalog: Catalog, source_id: str, spider_name: str) -> None:
        self.catalog = catalog
        self.source_id = source_id
        self.spider_name = spider_name
        self.ledger = AcquisitionHandoffStore(catalog)

    def stage(
        self,
        session: Session,
        *,
        run_id: str | None,
        resource_id: str,
        state: object,
        evidence_id: str | None,
        observed_at: str,
        kind: Kind = Kind.RESOURCE_OBSERVATION,
        resource_kind: str = "message",
        component: str | None = None,
        parent_id: str | None = None,
        scope_id: str | None = None,
        observation_id: str | None = None,
        resource_version: str | None = None,
        stale: bool = False,
        equivalent: bool = False,
        authority: bool = False,
        reason: str | None = None,
    ) -> MailPersistenceOutcome:
        """Stage logical run provenance independently of canonical evidence."""
        if not run_id:
            raise ValueError("Mail persistence requires explicit logical run_id")
        relation = (
            StorageRelation.STALE
            if stale
            else StorageRelation.CURRENT_EQUIVALENT
            if equivalent
            else StorageRelation.ADVANCED
        )
        locator = None
        if evidence_id:
            locator = SourceVersionLocator(
                kind="observation" if observation_id else "evidence",
                evidence_id=evidence_id,
                resource_identity=resource_id,
                observation_id=observation_id,
                component_kind=component,
                resource_version=resource_version,
            )
        spec = FactSpec(
            source_id=self.source_id,
            stream=AcquisitionStream.OUTLOOK_MAIL,
            run_id=run_id,
            spider_name=self.spider_name,
            fact_kind=kind,
            resource_kind=resource_kind,
            resource_identity=resource_id,
            provider_observed_at=observed_at,
            source_state_key=semantic_digest(state),
            source_version_locator=locator,
            storage_relation=relation,
            evidence_id=evidence_id,
            component_kind=component,
            parent_resource_kind="message" if parent_id else None,
            parent_resource_identity=parent_id,
            scope_kind="mail_folder" if scope_id else None,
            scope_identity=scope_id,
            transition_reason=reason,
        )
        if relation == StorageRelation.CURRENT_EQUIVALENT and not authority:
            current = self.ledger.current_effective_state(session, spec.effective_key)
            if (
                current is not None
                and current["source_state_key"] != spec.source_state_key
            ):
                # Domain columns omit component/version semantics. The exact
                # key, not evidence reuse, decides post-ledger advancement.
                spec = replace(spec, storage_relation=StorageRelation.ADVANCED)
        if authority and not stale:
            fact = self.ledger.stage_authority_fact_in_session(session, spec)
        else:
            fact = self.ledger.stage_state_fact_in_session(session, spec)
            relation = StorageRelation(fact.storage_relation)
        return MailPersistenceOutcome(fact, relation)

    def run_primary_version(
        self,
        session: Session,
        run_id: str | None,
        message_id: str,
    ) -> str | None:
        """Bind this run's primary representation when available."""
        payloads = session.scalars(
            select(AcquisitionFact.payload).where(
                AcquisitionFact.source_id == self.source_id,
                AcquisitionFact.stream == AcquisitionStream.OUTLOOK_MAIL,
                AcquisitionFact.run_id == run_id,
            )
        )
        candidates = [FactSpec.from_json(p) for p in payloads]
        candidates = [
            f
            for f in candidates
            if f.resource_kind == "message"
            and f.resource_identity == message_id
            and f.component_kind is None
            and f.fact_kind == Kind.RESOURCE_OBSERVATION
            and f.storage_relation != StorageRelation.STALE
        ]
        if not candidates:
            return None
        return max(
            candidates, key=lambda f: datetime.fromisoformat(f.provider_observed_at)
        ).source_state_key

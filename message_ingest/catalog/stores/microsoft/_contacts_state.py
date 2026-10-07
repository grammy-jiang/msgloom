"""Shared Contacts state mutation and cross-mode promotion ordering."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from message_ingest.catalog.models.microsoft.contacts import (
    ContactPresence,
    ContactPromotionBase,
    ContactPromotionGeneration,
    ContactRecord,
)
from message_ingest.catalog.store import Catalog
from message_ingest.items.microsoft.contacts import ContactItem


def observation_time(value: str) -> datetime:
    """Parse one offset-aware provider observation time."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Contacts observation times must include a timezone offset")
    return parsed


class ContactsPromotionOrder:
    """Own the durable generation shared by snapshot and delta promotion."""

    def __init__(self, catalog: Catalog, *, source_id: str) -> None:
        self.catalog = catalog
        self.source_id = source_id

    def begin(self, *, run_id: str, operation: str) -> int:
        """Capture and durably stage the generation before provider traversal."""
        with self.catalog.writer_session() as session:
            identity = {"source_id": self.source_id, "run_id": run_id}
            existing = session.get(ContactPromotionBase, identity)
            if existing is not None:
                if existing.operation != operation:
                    raise RuntimeError("Contacts run promotion ownership changed")
                return existing.base_generation
            generation = session.get(ContactPromotionGeneration, self.source_id)
            base = generation.revision if generation is not None else 0
            session.add(
                ContactPromotionBase(
                    **identity,
                    operation=operation,
                    base_generation=base,
                )
            )
            return base

    def require_base(self, session: Session, *, run_id: str, operation: str) -> int:
        """Verify that this run still owns the generation captured at start."""
        base = session.get(
            ContactPromotionBase,
            {"source_id": self.source_id, "run_id": run_id},
        )
        if base is None or base.operation != operation:
            raise RuntimeError("Contacts promotion base is missing")
        generation = session.get(ContactPromotionGeneration, self.source_id)
        current = generation.revision if generation is not None else 0
        if base.base_generation != current:
            raise RuntimeError("Contacts promotion generation is stale")
        return current

    def advance(self, session: Session, *, expected: int) -> None:
        """Advance the shared authority generation inside the promotion commit."""
        generation = session.get(ContactPromotionGeneration, self.source_id)
        current = generation.revision if generation is not None else 0
        if current != expected:
            raise RuntimeError("Contacts promotion generation changed")
        if generation is None:
            session.add(
                ContactPromotionGeneration(
                    source_id=self.source_id,
                    revision=expected + 1,
                )
            )
        else:
            generation.revision = expected + 1


class ContactStateWriter:
    """Apply semantic contact changes with timestamp and presence ordering."""

    def __init__(self, *, source_id: str) -> None:
        self.source_id = source_id

    @staticmethod
    def values(raw: dict[str, object]) -> dict[str, object]:
        """Map the intentionally bounded provider projection to catalog columns."""
        mapping = {
            "display_name": "displayName",
            "given_name": "givenName",
            "surname": "surname",
            "initials": "initials",
            "nick_name": "nickName",
            "title": "title",
            "company_name": "companyName",
            "department": "department",
            "job_title": "jobTitle",
            "email_addresses": "emailAddresses",
            "business_phones": "businessPhones",
            "home_phones": "homePhones",
            "mobile_phone": "mobilePhone",
            "birthday": "birthday",
            "parent_folder_id": "parentFolderId",
            "last_modified_date_time": "lastModifiedDateTime",
        }
        return {name: raw.get(provider) for name, provider in mapping.items()}

    def record(self, item: ContactItem, *, scope_key: str) -> ContactRecord:
        """Build a current-state row from one complete snapshot observation."""
        return ContactRecord(
            source_id=self.source_id,
            scope_key=scope_key,
            contact_id=item.contact_id,
            folder_id=item.folder_id,
            is_default_scope=item.is_default_scope,
            **self.values(item.raw),
            latest_observed_at=item.observed_at,
            latest_evidence_id=item.evidence_id,
            raw=item.raw,
        )

    def assign(
        self,
        record: ContactRecord,
        raw: dict[str, object],
        observed_at: str,
        evidence_id: str | None,
    ) -> None:
        """Replace current semantic fields from a complete merged provider view."""
        for name, value in self.values(raw).items():
            setattr(record, name, value)
        record.latest_observed_at = observed_at
        record.latest_evidence_id = evidence_id
        record.raw = raw

    def set_presence(
        self,
        session: Session,
        *,
        identity: dict[str, str],
        is_present: bool,
        reason: str | None,
        run_id: str,
        observed_at: str,
        evidence_id: str | None,
    ) -> None:
        """Publish one authoritative presence observation."""
        record = session.get(ContactPresence, identity)
        values = {
            "is_present": is_present,
            "removed_reason": reason,
            "latest_run_id": run_id,
            "latest_observed_at": observed_at,
            "latest_evidence_id": evidence_id,
        }
        if record is None:
            session.add(ContactPresence(**identity, **values))
            return
        for name, value in values.items():
            setattr(record, name, value)

    def delta_is_stale(
        self,
        session: Session,
        *,
        identity: dict[str, str],
        run_id: str,
        observed_at: str,
    ) -> bool:
        """Reject delta state older than snapshot/delta authority already saved.

        Equal timestamps are accepted only after this same ordered delta run has
        already published presence, preserving last-wins semantics within a page.
        """
        observed = observation_time(observed_at)
        record = session.get(ContactRecord, identity)
        presence = session.get(ContactPresence, identity)
        latest = []
        if record is not None:
            latest.append(observation_time(record.latest_observed_at))
        if presence is not None:
            latest.append(observation_time(presence.latest_observed_at))
        if not latest:
            return False
        newest = max(latest)
        if observed < newest:
            return True
        return observed == newest and (
            presence is None or presence.latest_run_id != run_id
        )

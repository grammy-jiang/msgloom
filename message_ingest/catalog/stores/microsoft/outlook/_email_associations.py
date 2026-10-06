"""
Retain Mail selections and reconcile only an accepted primary application.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import AcquisitionFactKind as Kind
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
    MailApplicationBinding as Binding,
)
from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
    MailComponentCapture as Capture,
)
from message_ingest.catalog.models.microsoft.outlook.email import (
    AttachmentRecord,
    MessageSurface,
)

from ._email_handoff import (
    MailPersistenceOutcome,
    is_stale,
    previous_primary_key,
    semantic_digest,
    surface_reason,
    verified_digest,
)


@dataclass(frozen=True)
class DeferredMailCapture:
    """A saved association with no permission to change effective state."""

    capture_id: str
    fact: None = None


def bounded_json(value: object, limit: int = 8192) -> str:
    """Bound local structured metadata independently of shared wire fields."""
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(text.encode()) > limit:
        raise ValueError("Oversized Mail binding metadata")
    return text


def identifier(value: str, limit: int = 2048) -> str:
    """Reject absent, oversized or non-string association identities."""
    if not isinstance(value, str) or not value or len(value.encode()) > limit:
        raise ValueError("Invalid Mail binding identifier")
    return value


def append_row(session: Session, model, key, values: dict[str, Any]):
    """Accept exact repeats; reject conflicting identities before insertion."""
    existing = session.get(model, key)
    if existing is not None:
        if any(getattr(existing, name) != value for name, value in values.items()):
            raise ValueError("Conflicting immutable Mail binding")
        return existing
    row = model(**values)
    session.add(row)
    session.flush()
    return row


def projection(attachment: dict[str, Any]) -> dict[str, Any]:
    """Retain only the existing attachment metadata representation."""
    if not isinstance(attachment, dict):
        raise TypeError("Invalid attachment metadata")
    for field in ("@odata.type", "name", "contentType"):
        value = attachment.get(field)
        if value is not None and (
            not isinstance(value, str) or len(value.encode()) > 4096
        ):
            raise ValueError("Invalid attachment text metadata")
    size, inline = attachment.get("size"), attachment.get("isInline")
    if size is not None and (type(size) is not int or not 0 <= size < 2**63):
        raise ValueError("Invalid attachment size")
    if inline is not None and type(inline) is not bool:
        raise ValueError("Invalid attachment inline flag")
    return {
        "attachment_id": identifier(attachment["id"]),
        "attachment_type": attachment.get("@odata.type"),
        "name": attachment.get("name"),
        "content_type": attachment.get("contentType"),
        "size": attachment.get("size"),
        "is_inline": attachment.get("isInline"),
    }


class MailAssociations:
    """Use caller-owned writer sessions; never establish parent precedence."""

    def __init__(self, store):
        self.store = store
        self.writer = store._facts()
        self.source = store.source_id

    def selection(self, session: Session, message: str, selection: str):
        key = semantic_digest([self.source, message, selection, "primary"])
        return session.get(Binding, key)

    def bind_primary(self, session, selection, outcome, evidence_id):
        """Record the primary decision and apply its saved captures."""
        fact = outcome.fact
        message = fact.resource_identity
        primary_id = (
            fact.revalidated_fact_id
            if (fact.storage_relation == "current_equivalent")
            else fact.fact_id
        )
        primary_id = primary_id or fact.fact_id
        selection = selection or semantic_digest(["primary", fact.fact_id])
        identifier(selection, 64)
        key = semantic_digest([self.source, message, selection, "primary"])
        values = {
            "binding_id": key,
            "source_id": self.source,
            "message_id": message,
            "selection_id": selection,
            "capture_id": None,
            "primary_fact_id": primary_id,
            "fact_id": fact.fact_id,
            "payload": bounded_json(
                {"parent_key": fact.source_state_key, "parent_evidence_id": evidence_id}
            ),
        }
        existing = self.selection(session, message, selection)
        if existing is not None:
            # Repeating the same operation may produce a ledger revalidation.
            # It may not move its immutable selection to a later ABA return.
            if (
                existing.primary_fact_id != primary_id
                and fact.storage_relation != "stale"
            ) or existing.payload != values["payload"]:
                raise ValueError("Mail selection changed its primary application")
        else:
            append_row(session, Binding, key, values)
        self.reconcile(session, message)
        return selection

    def retain(
        self,
        session,
        *,
        message_id,
        selection_id,
        resource_version,
        parent_evidence_id,
        component,
        resource_id,
        status,
        profile_version,
        evidence_id,
        observed_at,
        run_id,
        metadata=None,
        capture_id=None,
        inventory_page_id=None,
    ):
        """Retain exact provenance before checking applicability."""
        for value in (
            self.source,
            message_id,
            resource_id,
            run_id,
            evidence_id,
            parent_evidence_id,
        ):
            identifier(value)
        identifier(selection_id, 64)
        identifier(resource_version, 64)
        identifier(component)
        surface_reason(status, profile_version)
        datetime.fromisoformat(observed_at)
        verified_digest(session, self.source, parent_evidence_id)
        if (
            previous_primary_key(session, self.source, parent_evidence_id, message_id)
            != resource_version
        ):
            raise ValueError("Mail capture parent evidence does not match pin")
        digest = verified_digest(session, self.source, evidence_id)
        data = {
            "parent_evidence_id": parent_evidence_id,
            "evidence_id": evidence_id,
            "run_id": run_id,
            "status": status,
            "profile_version": profile_version,
            "metadata": metadata,
            "content_sha256": digest,
            "inventory_page_id": inventory_page_id,
        }
        if metadata is not None:
            bounded_json(metadata, 4096)
        payload = bounded_json(data)
        identity = {
            "source_id": self.source,
            "message_id": message_id,
            "selection_id": selection_id,
            "parent_key": resource_version,
            "component": component,
            "resource_id": resource_id,
            "observed_at": observed_at,
            "payload": payload,
        }
        capture_id = capture_id or semantic_digest(identity)
        identifier(capture_id, 64)
        existing = session.get(Capture, capture_id)
        ordinal = (
            existing.ordinal
            if existing
            else (
                session.scalar(
                    select(func.max(Capture.ordinal)).where(
                        Capture.source_id == self.source,
                        Capture.message_id == message_id,
                    )
                )
                or 0
            )
            + 1
        )
        if existing:
            ordinal = existing.ordinal
        row = append_row(
            session,
            Capture,
            capture_id,
            dict(
                capture_id=capture_id,
                ordinal=ordinal,
                **identity,
            ),
        )
        self.reconcile(session, message_id)
        application = session.scalar(
            select(Binding).where(
                Binding.source_id == self.source,
                Binding.capture_id == capture_id,
            )
        )
        if application is None:
            return DeferredMailCapture(row.capture_id)
        payload = json.loads(application.payload)
        fact_row = session.get(AcquisitionFact, payload["staged_fact_id"])
        from message_ingest.acquisition.handoff import FactSpec, StorageRelation

        fact = FactSpec.from_json(fact_row.payload)
        return MailPersistenceOutcome(fact, StorageRelation(fact.storage_relation))

    def reconcile(self, session: Session, message_id: str):
        """Apply captures explicitly bound to the current primary."""
        current = self.writer.effective_fact(session, "message", message_id)
        if current is None:
            return
        selections = session.scalars(
            select(Binding).where(
                Binding.source_id == self.source,
                Binding.message_id == message_id,
                Binding.capture_id.is_(None),
                Binding.primary_fact_id == current.fact_id,
            )
        ).all()
        selected = {row.selection_id: row for row in selections}
        if not selected:
            return
        rows = session.scalars(
            select(Capture).where(
                Capture.source_id == self.source,
                Capture.message_id == message_id,
                Capture.selection_id.in_(selected),
            )
        ).all()
        # Existing same-parent timestamp/tie policy only. The explicit ordinal
        # records capture acceptance ties; it never compares primary versions.
        rows = sorted(
            rows,
            key=lambda row: (
                row.component == "attachments",
                datetime.fromisoformat(row.observed_at),
                row.ordinal,
            ),
        )
        for row in rows:
            if row.parent_key != current.source_state_key:
                raise ValueError("Mail selection disagrees with captured parent")
            data = json.loads(row.payload)
            parent = json.loads(selected[row.selection_id].payload)
            if data["parent_evidence_id"] != parent["parent_evidence_id"]:
                raise ValueError("Mail selection changed canonical parent evidence")
            if (
                session.scalar(
                    select(Binding.binding_id).where(
                        Binding.source_id == self.source,
                        Binding.capture_id == row.capture_id,
                    )
                )
                is not None
            ):
                continue
            self.apply(session, row, data, current.fact_id)

    def apply(self, session, row, data, primary_id):
        """Atomically stage an eligible component and its exact application."""
        from ._email_inventory import inventory_manifest

        metadata = data["metadata"]
        attachment = row.component == "attachment_metadata"
        kind = "attachment" if attachment else "message_surface"
        previous = self.writer.effective_fact(
            session,
            kind,
            row.resource_id,
            row.component,
            row.message_id,
        )
        prior_binding = self.current_binding(session, previous, primary_id)
        stale = prior_binding is not None and is_stale(
            row.observed_at,
            previous.provider_observed_at,
        )
        state = {
            "component": row.component,
            "resource_version": row.parent_key,
            "status": data["status"],
            "profile_version": data["profile_version"],
        }
        manifest = None
        if row.component == "attachments":
            manifest = inventory_manifest(session, row, data, primary_id)
            if manifest is None:
                return
            state["membership_sha256"] = manifest["semantic_sha256"]
        elif attachment:
            state["metadata"] = metadata
        elif data["status"] == "acquired":
            state["content_sha256"] = verified_digest(
                session,
                self.source,
                data["evidence_id"],
            )
        if not stale:
            self.project(session, row, data)
        outcome = self.writer.stage(
            session,
            run_id=data["run_id"],
            resource_id=row.resource_id,
            state=state,
            evidence_id=data["evidence_id"],
            observed_at=row.observed_at,
            kind=Kind.COMPONENT_OBSERVATION,
            resource_kind=kind,
            component=row.component,
            parent_id=row.message_id,
            resource_version=row.parent_key,
            reason=surface_reason(data["status"], data["profile_version"]),
            stale=stale,
        )
        fact = outcome.fact
        capture_manifest = manifest
        if manifest is not None:
            original = session.scalar(
                select(Binding).where(
                    Binding.fact_id == fact.fact_id,
                    Binding.capture_id.is_not(None),
                )
            )
            if original is not None:
                # The fact keeps its original manifest. This application also
                # records the independently validated current capture chain;
                # exact fact reuse after ABA cannot erase that association.
                manifest = json.loads(original.payload)["manifest"]
        values = {
            "source_id": self.source,
            "message_id": row.message_id,
            "selection_id": row.selection_id,
            "capture_id": row.capture_id,
            "primary_fact_id": primary_id,
            "fact_id": fact.fact_id,
            "payload": bounded_json(
                {
                    "staged_fact_id": fact.fact_id,
                    "manifest": manifest,
                    "capture_manifest": capture_manifest,
                }
            ),
        }
        key = semantic_digest([row.capture_id, primary_id, fact.fact_id])
        append_row(session, Binding, key, dict(binding_id=key, **values))

    @staticmethod
    def project(session, row, data):
        """Update only the existing domain representation, not history."""
        if row.component == "attachment_metadata":
            model, query = (
                AttachmentRecord,
                {
                    "source_id": row.source_id,
                    "message_id": row.message_id,
                    "attachment_id": row.resource_id,
                },
            )
            values = {k: v for k, v in data["metadata"].items() if k != "attachment_id"}
            values.update(
                latest_evidence_id=data["evidence_id"],
                latest_observed_at=row.observed_at,
            )
        else:
            model, query = (
                MessageSurface,
                {
                    "source_id": row.source_id,
                    "message_id": row.message_id,
                    "surface": row.component,
                },
            )
            values = {
                "status": data["status"],
                "evidence_id": data["evidence_id"],
                "observed_at": row.observed_at,
                "profile_version": data["profile_version"],
            }
        record = session.scalar(select(model).filter_by(**query))
        if record is None:
            record = model(**query)
            session.add(record)
        for name, value in values.items():
            setattr(record, name, value)
        session.flush()

    @staticmethod
    def current_binding(session, fact, primary_id):
        """Require an exact recorded application, including ABA returns."""
        if fact is None:
            return None
        from message_ingest.acquisition.handoff import FactSpec

        bindings = session.scalars(
            select(Binding).where(
                Binding.source_id == fact.source_id,
                Binding.primary_fact_id == primary_id,
                Binding.capture_id.is_not(None),
            )
        ).all()
        for binding in bindings:
            if binding.fact_id == fact.fact_id:
                return binding
            row = session.get(AcquisitionFact, binding.fact_id)
            staged = FactSpec.from_json(row.payload)
            if (
                staged.storage_relation == "current_equivalent"
                and staged.revalidated_fact_id == fact.fact_id
            ):
                return binding
        return None

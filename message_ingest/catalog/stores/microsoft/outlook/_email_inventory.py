"""Exact page-chain retention and current Mail inventory validation."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

from sqlalchemy import select

from message_ingest.acquisition.handoff import FactSpec
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
    MailApplicationBinding as Binding,
)
from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
    MailComponentCapture as Capture,
)
from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
    MailInventoryMember as Member,
)
from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
    MailInventoryPage as Page,
)

from ._email_associations import (
    MailAssociations,
    append_row,
    bounded_json,
    identifier,
    projection,
)
from ._email_handoff import (
    previous_primary_key,
    semantic_digest,
    surface_reason,
    verified_digest,
)


def page_payload(session, source, message, evidence, status):
    """Validate saved page bytes and target before retaining member claims."""
    verified_digest(session, source, evidence)
    row = session.get(RawHttpEvidence, evidence)
    path = unquote(urlsplit(row.request_url).path)
    target = f"/messages/{message}/attachments"
    if not path.endswith(target):
        raise ValueError("Inventory evidence names a different target")
    values, next_link = [], None
    if status == "acquired":
        payload = json.loads(Path(row.response_body_path).read_bytes())
        if not isinstance(payload, dict) or not isinstance(
            payload.get("value", []), list
        ):
            raise ValueError("Invalid inventory page payload")
        values = [projection(value) for value in payload.get("value", [])]
        next_link = payload.get("@odata.nextLink") or None
        if next_link is not None:
            identifier(next_link, 4096)
    return values, next_link, row.request_url


def record_page(store, session, item):
    """Retain a native page and its exact metadata references atomically."""
    source = store.source_id
    for value in (item.page_id, item.inventory_id, item.selection_id):
        identifier(value, 64)
    for value in (
        source,
        item.message_id,
        item.run_id,
        item.evidence_id,
        item.parent_evidence_id,
    ):
        identifier(value)
    identifier(item.resource_version, 64)
    if item.previous_page_id is not None:
        identifier(item.previous_page_id, 64)
    datetime.fromisoformat(item.observed_at)
    verified_digest(session, source, item.parent_evidence_id)
    if (
        previous_primary_key(
            session,
            source,
            item.parent_evidence_id,
            item.message_id,
        )
        != item.resource_version
    ):
        raise ValueError("Inventory parent evidence does not match pin")
    surface_reason(item.status, item.profile_version)
    values, next_link, request_url = page_payload(
        session,
        source,
        item.message_id,
        item.evidence_id,
        item.status,
    )
    if len(values) != len(item.member_capture_ids):
        raise ValueError("Inventory member reference count mismatch")
    if item.page_number < 1 or (item.page_number == 1) != (
        item.previous_page_id is None
    ):
        raise ValueError("Inventory root/predecessor mismatch")
    data = {
        "evidence_id": item.evidence_id,
        "parent_evidence_id": item.parent_evidence_id,
        "status": item.status,
        "profile_version": item.profile_version,
        "next_link": next_link,
        "request_url": request_url,
        "run_id": item.run_id,
        "observed_at": item.observed_at,
    }
    append_row(
        session,
        Page,
        item.page_id,
        {
            "page_id": item.page_id,
            "source_id": source,
            "message_id": item.message_id,
            "selection_id": item.selection_id,
            "parent_key": item.resource_version,
            "inventory_id": item.inventory_id,
            "page_number": item.page_number,
            "previous_page_id": item.previous_page_id,
            "payload": bounded_json(data),
        },
    )
    for value, capture_id in zip(values, item.member_capture_ids, strict=True):
        identifier(capture_id, 64)
        append_row(
            session,
            Member,
            (item.page_id, value["attachment_id"]),
            {
                "page_id": item.page_id,
                "member_id": value["attachment_id"],
                "capture_id": capture_id,
                "payload": bounded_json(value, 4096),
            },
        )
    associations = MailAssociations(store)
    if next_link is None:
        return associations.retain(
            session,
            message_id=item.message_id,
            selection_id=item.selection_id,
            resource_version=item.resource_version,
            parent_evidence_id=item.parent_evidence_id,
            component="attachments",
            resource_id=item.message_id,
            status=item.status,
            profile_version=item.profile_version,
            evidence_id=item.evidence_id,
            observed_at=item.observed_at,
            run_id=item.run_id,
            inventory_page_id=item.page_id,
        )
    associations.reconcile(session, item.message_id)
    return None


def chain(session, capture, data):
    """Follow explicit predecessor references, validating all saved pages."""
    page_id = data["inventory_page_id"]
    pages, seen = [], set()
    while page_id is not None:
        if page_id in seen:
            raise ValueError("Cyclic Mail inventory")
        seen.add(page_id)
        page = session.get(Page, page_id)
        if page is None:
            return None
        if (page.source_id, page.message_id, page.selection_id, page.parent_key) != (
            capture.source_id,
            capture.message_id,
            capture.selection_id,
            capture.parent_key,
        ):
            raise ValueError("Cross-selection Mail inventory page")
        pd = json.loads(page.payload)
        if (pd["parent_evidence_id"], pd["profile_version"]) != (
            data["parent_evidence_id"],
            data["profile_version"],
        ):
            raise ValueError("Inventory changed selected parent or profile")
        actual, link, url = page_payload(
            session,
            page.source_id,
            page.message_id,
            pd["evidence_id"],
            pd["status"],
        )
        if (link, url) != (pd["next_link"], pd["request_url"]):
            raise ValueError("Inventory continuation evidence changed")
        members = session.scalars(
            select(Member)
            .where(
                Member.page_id == page.page_id,
            )
            .order_by(Member.member_id)
        ).all()
        expected = {}
        for value in actual:
            key = value["attachment_id"]
            if key in expected and expected[key] != value:
                raise ValueError("Conflicting duplicate inventory member")
            expected[key] = value
        if {m.member_id: json.loads(m.payload) for m in members} != expected:
            raise ValueError("Inventory members disagree with saved evidence")
        if pages:
            following, following_data, _ = pages[-1]
            if (
                following.inventory_id != page.inventory_id
                or following.page_number != page.page_number + 1
                or pd["status"] != "acquired"
                or pd["next_link"] != following_data["request_url"]
            ):
                raise ValueError("Broken selected inventory page chain")
        elif pd["next_link"] is not None or pd["status"] != data["status"]:
            raise ValueError("Inventory capture does not name a terminal page")
        pages.append((page, pd, members))
        page_id = page.previous_page_id
    if not pages or pages[-1][0].page_number != 1:
        return None
    return list(reversed(pages))


def inventory_manifest(session, capture, data, primary_id):
    """Seal only a complete exact traversal with current member metadata."""
    pages = chain(session, capture, data)
    if pages is None:
        return None
    members = {}
    for _page, pd, entries in pages:
        for member in entries:
            value = json.loads(member.payload)
            if member.member_id in members and members[member.member_id] != value:
                raise ValueError("Conflicting cross-page inventory member")
            members[member.member_id] = value
            if data["status"] != "acquired":
                continue
            metadata = session.get(Capture, member.capture_id)
            if metadata is None:
                return None
            md = json.loads(metadata.payload)
            if (
                metadata.source_id,
                metadata.message_id,
                metadata.selection_id,
                metadata.parent_key,
                metadata.component,
                md["evidence_id"],
                md["metadata"],
            ) != (
                capture.source_id,
                capture.message_id,
                capture.selection_id,
                capture.parent_key,
                "attachment_metadata",
                pd["evidence_id"],
                value,
            ):
                raise ValueError("Unbound or substituted inventory metadata")
            applied = session.scalar(
                select(Binding).where(
                    Binding.capture_id == metadata.capture_id,
                    Binding.primary_fact_id == primary_id,
                )
            )
            if applied is None:
                return None
    semantic_members = (
        [members[key] for key in sorted(members)]
        if data["status"] == "acquired"
        else []
    )
    return {
        "terminal_page_id": pages[-1][0].page_id,
        "semantic_sha256": semantic_digest(semantic_members),
        "provenance_sha256": semantic_digest(
            [
                [page.page_id, pd["evidence_id"], [m.capture_id for m in entries]]
                for page, pd, entries in pages
            ]
        ),
        "page_count": len(pages),
        "member_count": len(semantic_members),
    }


def binding_state(store, message_id):
    """Read primary, components and selected members in one snapshot."""
    from message_ingest.acquisition.microsoft.outlook.email.profile import FULL_V1

    result = {
        "surfaces": {},
        "attachments": [],
        "resource_version": None,
        "primary_observed_at": None,
        "selection_id": None,
        "parent_evidence_id": None,
    }
    with store.catalog.Session() as session:
        associations = MailAssociations(store)
        primary = associations.writer.effective_fact(session, "message", message_id)
        if primary is None:
            return result
        selected = session.scalar(
            select(Binding).where(
                Binding.source_id == store.source_id,
                Binding.message_id == message_id,
                Binding.primary_fact_id == primary.fact_id,
                Binding.capture_id.is_(None),
            )
        )
        if selected is None:
            return result
        result.update(
            resource_version=primary.source_state_key,
            primary_observed_at=primary.provider_observed_at,
            selection_id=selected.selection_id,
            parent_evidence_id=json.loads(selected.payload)["parent_evidence_id"],
        )
        bindings = session.scalars(
            select(Binding).where(
                Binding.source_id == store.source_id,
                Binding.message_id == message_id,
                Binding.primary_fact_id == primary.fact_id,
                Binding.capture_id.is_not(None),
            )
        ).all()
        inventory = None
        metadata = {}
        priorities = {}
        for binding in bindings:
            cap = session.get(Capture, binding.capture_id)
            data = json.loads(cap.payload)
            kind = (
                "attachment"
                if cap.component == "attachment_metadata"
                else "message_surface"
            )
            fact = associations.writer.effective_fact(
                session,
                kind,
                cap.resource_id,
                cap.component,
                message_id,
            )
            staged_row = session.get(AcquisitionFact, binding.fact_id)
            staged = FactSpec.from_json(staged_row.payload)
            exact = fact is not None and fact.fact_id == staged.fact_id
            equivalent = (
                fact is not None
                and staged.storage_relation == "current_equivalent"
                and staged.revalidated_fact_id == fact.fact_id
            )
            if (
                not (exact or equivalent)
                or data["profile_version"] != FULL_V1
                or staged.storage_relation == "stale"
            ):
                continue
            identity = (kind, cap.resource_id, cap.component)
            priority = 0 if exact else 1
            if priorities.get(identity, 2) <= priority:
                continue
            priorities[identity] = priority
            try:
                verified_digest(session, store.source_id, data["evidence_id"])
            except (ValueError, OSError):
                continue
            if kind == "attachment":
                metadata[cap.resource_id] = dict(
                    **data["metadata"],
                    latest_evidence_id=data["evidence_id"],
                    latest_observed_at=cap.observed_at,
                )
                continue
            if cap.component == "attachments":
                try:
                    manifest = inventory_manifest(session, cap, data, primary.fact_id)
                except (ValueError, OSError):
                    continue
                if manifest != json.loads(binding.payload)["capture_manifest"]:
                    continue
                inventory = (cap, data)
            result["surfaces"][cap.component] = {
                "status": data["status"],
                "evidence_id": data["evidence_id"],
                "observed_at": cap.observed_at,
                "profile_version": data["profile_version"],
            }
        if inventory is not None and inventory[1]["status"] == "acquired":
            pages = chain(session, *inventory)
            required = {}
            for _, _, entries in pages or []:
                for member in entries:
                    required[member.member_id] = json.loads(member.payload)
            for member_id, value in required.items():
                current = metadata.get(member_id)
                if current is None or any(current[k] != v for k, v in value.items()):
                    result["surfaces"].pop("attachments", None)
                    result["attachments"] = []
                    break
                result["attachments"].append(current)
    return result

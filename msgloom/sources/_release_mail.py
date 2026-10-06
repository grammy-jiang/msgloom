"""Validate and map Mail components from retained facts and saved bytes."""

import json
from contextlib import closing

from message_ingest.catalog.stores.microsoft.outlook._email_handoff import (
    decode_surface_reason,
    primary_projection,
)
from msgloom.contracts import Limitation, VersionRef
from msgloom.preparation.contracts import DocumentLocation
from msgloom.sources._catalog import encode_parts
from msgloom.sources._mapping import content_kind, graph_object
from msgloom.sources._release_evidence import digest, fact_reference
from msgloom.sources._release_records import record
from msgloom.sources.models import (
    CollectedAttachment,
    CollectedBody,
    ContentKind,
    SourceEvidenceError,
    SourceReferenceError,
)


def outcome(fact):
    """Reject legacy outcomes instead of deriving status from current rows."""
    try:
        return decode_surface_reason(fact.transition_reason)
    except ValueError:
        raise SourceReferenceError("Invalid immutable Mail outcome metadata") from None


def _rows(evidence, sql, args):
    """Read bounded immutable associations only, never effective projections."""
    with closing(evidence.catalog._connect()) as connection:
        rows = connection.execute(sql + " LIMIT 129", args).fetchall()
    if len(rows) > 128:
        raise SourceReferenceError("Mail immutable association limit exceeded")
    return [dict(row) for row in rows]


def _application(primary, fact, evidence):
    """Resolve an exact retained application when this is a selected capture."""
    bindings = _rows(
        evidence,
        "SELECT * FROM mail_application_bindings WHERE source_id=? AND fact_id=? "
        "AND capture_id IS NOT NULL",
        (fact.source_id, fact.fact_id),
    )
    if not bindings:
        return None
    for binding in bindings:
        if binding["primary_fact_id"] != primary.fact_id:
            continue
        captures = _rows(
            evidence,
            "SELECT * FROM mail_component_captures WHERE capture_id=?",
            (binding["capture_id"],),
        )
        if len(captures) != 1:
            continue
        capture = captures[0]
        data = json.loads(capture["payload"])
        if (
            capture["source_id"],
            capture["message_id"],
            capture["parent_key"],
            capture["component"],
            capture["resource_id"],
            data["evidence_id"],
        ) != (
            fact.source_id,
            primary.resource_identity,
            primary.source_state_key,
            fact.component_kind,
            fact.resource_identity,
            fact.evidence_id,
        ):
            continue
        parents = _rows(
            evidence,
            "SELECT * FROM mail_application_bindings WHERE source_id=? "
            "AND selection_id=? AND primary_fact_id=? AND capture_id IS NULL",
            (fact.source_id, capture["selection_id"], primary.fact_id),
        )
        if not any(
            json.loads(parent["payload"])
            == {
                "parent_key": primary.source_state_key,
                "parent_evidence_id": data["parent_evidence_id"],
            }
            for parent in parents
        ):
            continue
        return capture, data, json.loads(binding["payload"])
    raise SourceReferenceError("Mail component lacks exact primary application")


def _inventory(fact, evidence, application):
    """Read a selected predecessor chain or one exact unpaged inventory."""
    if application is None:
        data, _ = evidence.load(fact.evidence_id, fact.source_id)
        payload = json.loads(data)
        if payload.get("@odata.nextLink"):
            raise SourceReferenceError("Mail inventory lacks retained page chain")
        return payload.get("value", [])
    capture, data, binding = application
    page_id = data["inventory_page_id"]
    pages, seen, values = [], set(), []
    following = None
    while page_id is not None:
        if page_id in seen or len(seen) >= 128:
            raise SourceReferenceError("Invalid bounded Mail inventory chain")
        seen.add(page_id)
        found = _rows(
            evidence, "SELECT * FROM mail_inventory_pages WHERE page_id=?", (page_id,)
        )
        if len(found) != 1:
            raise SourceReferenceError("Missing retained Mail inventory page")
        page = found[0]
        pd = json.loads(page["payload"])
        if any(
            page[key] != capture[key]
            for key in ("source_id", "message_id", "selection_id", "parent_key")
        ):
            raise SourceReferenceError("Mail inventory page ownership mismatch")
        if (pd["parent_evidence_id"], pd["profile_version"]) != (
            data["parent_evidence_id"],
            data["profile_version"],
        ):
            raise SourceReferenceError("Mail inventory parent or profile mismatch")
        raw, _ = evidence.load(pd["evidence_id"], fact.source_id)
        # Failed terminal responses retain verified bytes, not member JSON.
        payload = json.loads(raw) if pd["status"] == "acquired" else {}
        if (payload.get("@odata.nextLink") or None) != pd["next_link"]:
            raise SourceReferenceError("Mail inventory continuation mismatch")
        if following is not None:
            if (
                page["inventory_id"] != following[0]["inventory_id"]
                or page["page_number"] + 1 != following[0]["page_number"]
                or pd["status"] != "acquired"
                or pd["next_link"] != following[1]["request_url"]
            ):
                raise SourceReferenceError("Broken Mail inventory chain")
        elif (
            pd["next_link"] is not None
            or pd["evidence_id"] != fact.evidence_id
            or pd["status"] != data["status"]
        ):
            raise SourceReferenceError("Mail inventory terminal mismatch")
        members = _rows(
            evidence,
            "SELECT * FROM mail_inventory_members WHERE page_id=? ORDER BY member_id",
            (page_id,),
        )
        page_values = payload.get("value", [])
        if {item["id"] for item in page_values} != {m["member_id"] for m in members}:
            raise SourceReferenceError("Mail inventory membership mismatch")
        for member in members:
            item = graph_object(payload, member["member_id"])
            if _projection(item) != json.loads(member["payload"]):
                raise SourceReferenceError("Mail inventory metadata mismatch")
        # A terminal limitation seals empty semantic membership. Earlier
        # acquired pages remain checked provenance, not released attachments.
        if data["status"] == "acquired":
            values.extend(page_values)
        pages.append((page, pd, members))
        following = page, pd
        page_id = page["previous_page_id"]
    if not pages or pages[-1][0]["page_number"] != 1:
        raise SourceReferenceError("Mail inventory root missing")
    semantic = {
        _projection(item)["attachment_id"]: _projection(item) for item in values
    }
    manifest = {
        "terminal_page_id": pages[0][0]["page_id"],
        "semantic_sha256": digest([semantic[key] for key in sorted(semantic)]),
        "provenance_sha256": digest(
            [
                [p["page_id"], pd["evidence_id"], [m["capture_id"] for m in members]]
                for p, pd, members in reversed(pages)
            ]
        ),
        "page_count": len(pages),
        "member_count": len(semantic),
    }
    if manifest != binding["capture_manifest"]:
        raise SourceReferenceError("Mail inventory retained manifest mismatch")
    return values


def _projection(raw):
    """Keep the producer's immutable attachment metadata projection."""
    return dict(
        zip(
            (
                "attachment_id",
                "attachment_type",
                "name",
                "content_type",
                "size",
                "is_inline",
            ),
            (
                raw.get(key)
                for key in (
                    "id",
                    "@odata.type",
                    "name",
                    "contentType",
                    "size",
                    "isInline",
                )
            ),
        )
    )


def validate(primary, facts, evidence):
    """Bind every component to one exact message and inventory membership."""
    # Discovery and delta may release only the primary. Its exact saved
    # state must still agree even when no enrichment components are named.
    if primary is not None and primary.resource_kind == "message":
        raw, _ = evidence.object(primary)
        if digest(primary_projection(raw)) != primary.source_state_key:
            raise SourceReferenceError("Mail primary state mismatch")
    components = [
        f for f in facts if f.fact_kind == "component_observation" and f.role != "proof"
    ]
    if not components:
        return
    if primary is None or primary.resource_kind != "message":
        raise SourceReferenceError("Mail components require one exact primary")
    inventory, metadata, raw_ids = None, {}, set()
    seen = set()
    for fact in components:
        key = fact.resource_kind, fact.resource_identity, fact.component_kind
        if key in seen:
            raise SourceReferenceError("Duplicate Mail component")
        seen.add(key)
        if (fact.parent_resource_kind, fact.parent_resource_identity) != (
            "message",
            primary.resource_identity,
        ):
            raise SourceReferenceError("Mail component parent mismatch")
        if (
            fact.resource_kind == "message_surface"
            and fact.resource_identity != primary.resource_identity
        ):
            raise SourceReferenceError("Mail surface message mismatch")
        status, profile = outcome(fact)
        locator = fact.source_version_locator
        if locator is not None:
            evidence.validate_locator(fact)
            if locator.resource_version != primary.source_state_key:
                raise SourceReferenceError("Mail component version mismatch")
        elif fact.evidence_id is not None or status == "acquired":
            raise SourceReferenceError("Acquired Mail component lacks evidence")
        saved = None
        if fact.evidence_id:
            _, saved = evidence.load(fact.evidence_id, fact.source_id)
        content_sha256 = saved.sha256 if saved is not None else None
        if status == "acquired" and content_sha256 is None:
            raise SourceReferenceError("Acquired Mail component lacks saved evidence")
        app = _application(primary, fact, evidence)
        component = fact.component_kind
        state = {
            "surface": component,
            "status": status,
            "profile": profile,
            "resource_version": primary.source_state_key,
        }
        if app:
            if (app[1]["status"], app[1]["profile_version"]) != (status, profile):
                raise SourceReferenceError("Mail capture outcome mismatch")
            state = {
                "component": component,
                "status": status,
                "profile_version": profile,
                "resource_version": primary.source_state_key,
            }
        if component == "attachment_metadata":
            item, _ = evidence.object(fact)
            projection = _projection(item)
            metadata[fact.resource_identity] = projection
            state = (
                {**state, "metadata": projection}
                if app
                else {
                    "id": fact.resource_identity,
                    **{k: v for k, v in projection.items() if k != "attachment_id"},
                    "resource_version": primary.source_state_key,
                    "status": status,
                    "profile_version": profile,
                }
            )
        elif component == "attachments" and (status == "acquired" or app):
            values = _inventory(fact, evidence, app)
            inventory = {item["id"]: _projection(item) for item in values}
            state["membership_sha256" if app else "content_sha256"] = (
                digest([inventory[key] for key in sorted(inventory)])
                if app
                else content_sha256
            )
        elif status == "acquired":
            state[
                "representation"
                if component == "discovery" and not app
                else "content_sha256"
            ] = (
                primary.source_state_key
                if component == "discovery" and not app
                else content_sha256
            )
        if digest(state) != fact.source_state_key:
            raise SourceReferenceError("Mail immutable component state mismatch")
        if component and component.startswith("attachment_raw:"):
            raw_ids.add(component.split(":", 1)[1])
    # A named inventory remains authoritative when every metadata fact is
    # absent. Genuinely empty and terminal-limitation inventories stay empty.
    if (inventory is not None or metadata or raw_ids) and (
        inventory is None or metadata != inventory or not raw_ids <= metadata.keys()
    ):
        raise SourceReferenceError("Mail attachment lacks exact inventory membership")


def component(fact, evidence, scope):
    """Keep raw MIME and attachments distinct from JSON representations."""
    status, profile = outcome(fact)
    saved = None
    if fact.evidence_id:
        _, saved = evidence.load(fact.evidence_id, fact.source_id)
    if status == "acquired" and saved is None:
        raise SourceReferenceError("Acquired Mail component lacks saved evidence")
    raw = {"id": fact.resource_identity}
    kind = fact.component_kind or ""
    if status == "acquired" and kind in {"detail", "discovery", "attachment_metadata"}:
        raw, saved = evidence.object(fact)
    raw = {**raw, "status": status, "profile_version": profile}
    value = record(fact, raw, saved, scope)
    if status != "acquired":
        return value.model_copy(
            update={
                "limitations": (
                    Limitation(f"mail-{status}", "Released Mail component limitation."),
                )
            }
        ), None
    attachment = None
    if kind == "mime":
        value = value.model_copy(
            update={
                "source_content_kind": ContentKind.MIME,
                "alternate_bodies": (
                    CollectedBody(
                        kind=ContentKind.MIME,
                        content=None,
                        saved_bytes=saved,
                        location=DocumentLocation(part="mime"),
                    ),
                ),
            }
        )
    if kind == "attachment_metadata" or kind.startswith("attachment_raw:"):
        identity = (
            fact.resource_identity
            if kind == "attachment_metadata"
            else kind.split(":", 1)[1]
        )
        binary = kind != "attachment_metadata"
        mime = raw.get("contentType")
        if mime is not None and not isinstance(mime, str):
            raise SourceEvidenceError("Mail attachment MIME type must be a string")
        attachment = CollectedAttachment(
            reference=VersionRef(
                "a1_released_attachment",
                encode_parts(fact.source_id, fact.parent_resource_identity, identity),
                fact_reference(fact).version,
            ),
            name=raw.get("name"),
            content_type=mime,
            content_kind=content_kind(mime),
            byte_count=saved.byte_count
            if binary and saved is not None
            else raw.get("size"),
            inline=raw.get("isInline"),
            saved_bytes=saved if binary else None,
            location=DocumentLocation(part="saved-bytes" if binary else "graph-json"),
        )
        if binary:
            value = value.model_copy(update={"source_content_kind": ContentKind.BINARY})
    return value, attachment

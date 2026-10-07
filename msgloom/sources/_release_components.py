"""Enrich parents exclusively from exact component facts in the entry."""

import json

from msgloom.contracts import Limitation
from msgloom.preparation.contracts import DocumentLocation
from msgloom.preparation.records import NativeRelationship
from msgloom.sources._mapping import content_kind, graph_object
from msgloom.sources._release_evidence import ReleaseEvidence, fact_reference
from msgloom.sources._release_observations import content_capture
from msgloom.sources._release_records import record
from msgloom.sources.handoff_models import ReleasedFact
from msgloom.sources.models import (
    CollectedAttachment,
    ContentKind,
    SourceEvidenceError,
    SourceReferenceError,
)

_TERMINAL = {
    "acquired",
    "unsupported",
    "not_applicable",
    "omitted_size_limit",
    "unauthorized",
    "unavailable",
}


def _attachment(fact, raw, saved=None):
    """Describe exact attachment metadata or verified raw content."""
    mime = raw.get("contentType")
    if mime is not None and not isinstance(mime, str):
        raise SourceEvidenceError("Calendar attachment MIME type must be a string")
    return CollectedAttachment(
        reference=fact_reference(fact),
        name=raw.get("name"),
        content_type=mime,
        content_kind=content_kind(mime),
        byte_count=saved.byte_count if saved else raw.get("size"),
        inline=raw.get("isInline"),
        saved_bytes=saved,
        location=DocumentLocation(part="saved-bytes" if saved else "graph-json"),
    )


def component(fact: ReleasedFact, evidence: ReleaseEvidence, scope):
    """Return exact component data plus optional parent attachment."""
    if fact.stream == "outlook_mail":
        from msgloom.sources._release_mail import component as mail_component

        return mail_component(fact, evidence, scope)
    if fact.source_version_locator is not None:
        evidence.validate_locator(fact)
    elif fact.evidence_id is not None or fact.resource_kind not in {
        "calendar_event_surface",
        "calendar_series",
    }:
        raise SourceReferenceError("Released component lacks exact evidence")
    if fact.stream == "onedrive" and fact.component_kind == "item_content":
        capture = content_capture(evidence.catalog, fact)
        data, saved = evidence.load(fact.evidence_id or "", fact.source_id)
        if (
            saved.sha256 != capture["content_sha256"]
            or len(data) != capture["content_bytes"]
        ):
            raise SourceReferenceError("Content capture integrity mismatch")
        metadata, _ = evidence.load(
            capture["planned_metadata_evidence_id"], fact.source_id
        )
        raw = graph_object(json.loads(metadata), fact.resource_identity)
        if raw.get("eTag") != capture["planned_e_tag"]:
            raise SourceReferenceError("Content metadata version mismatch")
        file_facet = raw.get("file", {})
        if not isinstance(file_facet, dict):
            raise SourceEvidenceError("OneDrive file facet must be an object")
        mime = file_facet.get("mimeType")
        if mime is not None and not isinstance(mime, str):
            raise SourceEvidenceError("OneDrive file MIME type must be a string")
        attachment = CollectedAttachment(
            reference=fact_reference(fact),
            name=raw.get("name"),
            content_type=mime,
            content_kind=content_kind(mime),
            byte_count=saved.byte_count,
            inline=False,
            saved_bytes=saved,
            location=DocumentLocation(part="saved-bytes"),
        )
        result = record(fact, raw, saved, scope).model_copy(
            update={
                "source_content_kind": ContentKind.BINARY,
            }
        )
        return result, attachment
    if fact.resource_kind == "calendar_event_surface":
        return _surface(fact, evidence, scope), None
    if fact.resource_kind == "calendar_attachment":
        if fact.component_kind == "attachment_content":
            _, saved = evidence.load(fact.evidence_id or "", fact.source_id)
            raw = {"id": fact.resource_identity}
            result = record(fact, raw, saved, scope).model_copy(
                update={
                    "source_content_kind": ContentKind.BINARY,
                }
            )
            return result, _attachment(fact, raw, saved)
        raw, saved = evidence.object(fact)
        return record(fact, raw, saved, scope), _attachment(fact, raw)
    if fact.resource_kind == "calendar_series":
        status = fact.transition_reason
        if status not in _TERMINAL:
            raise SourceReferenceError("Calendar series status is not terminal")
        if status != "acquired":
            saved = None
            if fact.evidence_id:
                _, saved = evidence.load(fact.evidence_id, fact.source_id)
            value = record(fact, {"id": fact.resource_identity}, saved, scope)
            return value.model_copy(
                update={
                    "limitations": (
                        Limitation(
                            f"calendar-series-{status}",
                            "Released series topology limitation.",
                        ),
                    )
                }
            ), None
    raw, saved = evidence.object(fact)
    return record(fact, raw, saved, scope), None


def _surface(fact, evidence, scope):
    """Retain the immutable surface outcome without reading current status."""
    reason = json.loads(fact.transition_reason or "{}")
    if not isinstance(reason, dict):
        raise SourceReferenceError(
            "Calendar surface terminal metadata must be an object"
        )
    status = reason.get("status")
    if status not in _TERMINAL:
        raise SourceReferenceError("Calendar surface status is not terminal")
    if status == "acquired" and not fact.evidence_id:
        raise SourceReferenceError("Acquired Calendar surface lacks evidence")
    saved = None
    if fact.evidence_id:
        _, saved = evidence.load(fact.evidence_id, fact.source_id)
    raw = {"id": fact.resource_identity}
    if status == "acquired" and fact.component_kind == "detail":
        raw, saved = evidence.object(fact)
    raw = {**raw, "status": status, "profile_version": reason.get("profile_version")}
    result = record(fact, raw, saved, scope)
    if status != "acquired":
        result = result.model_copy(
            update={
                "limitations": (
                    Limitation(
                        f"calendar-{status}", "Released Calendar component limitation."
                    ),
                )
            }
        )
    return result


def validate_components(primary, facts, evidence):
    """
    Reject mixed material versions and content bound to other metadata.

    Calendar proof facts can describe a series master with its own version.
    Reconstruction validates their exact evidence separately; they do not
    enrich the primary event's material components.
    """
    if any(f.stream == "outlook_mail" for f in facts):
        from msgloom.sources._release_mail import validate

        validate(primary, facts, evidence)
        return
    if primary is None:
        return
    locator = primary.source_version_locator
    if locator is None:
        raise SourceReferenceError("Primary locator is unavailable")
    for fact in facts:
        child = fact.source_version_locator
        if fact.fact_kind != "component_observation" or child is None:
            continue
        if (
            primary.stream == "outlook_calendar"
            and fact.role != "proof"
            and locator.resource_version is not None
            and child.resource_version is not None
            and locator.resource_version != child.resource_version
        ):
            raise SourceReferenceError("Calendar component version mismatch")
        if primary.stream == "onedrive" and child.kind == "content_capture":
            capture = content_capture(evidence.catalog, fact)
            if capture["planned_metadata_evidence_id"] != primary.evidence_id:
                raise SourceReferenceError(
                    "Content is bound to another metadata capture"
                )


def enrich(parent, components, attachments, facts):
    """Freeze component lineage, outcomes, and detailed source fields."""
    relationships = list(parent.relationships)
    limitations = list(parent.limitations)
    updates = {}
    for value, fact in zip(components, facts, strict=True):
        relationships.append(
            NativeRelationship(
                kind="released_component",
                target=value.source,
            )
        )
        limitations.extend(value.limitations)
        if value.alternate_bodies:
            updates["alternate_bodies"] = value.alternate_bodies
        if (
            fact.resource_kind in {"calendar_event_surface", "message_surface"}
            and fact.component_kind == "detail"
            and (fact.stream != "outlook_mail" or not value.limitations)
        ):
            for field in (
                "subject",
                "body",
                "sender",
                "author",
                "recipients",
                "metadata",
            ):
                updates[field] = getattr(value, field)
    merged = {}
    for attachment in attachments:
        key = attachment.reference.identity
        previous = merged.get(key)
        if previous is None:
            merged[key] = attachment
            continue
        metadata, content = (
            (previous, attachment) if attachment.saved_bytes else (attachment, previous)
        )
        if metadata.saved_bytes or content.saved_bytes is None:
            raise SourceReferenceError("Ambiguous released attachment component")
        merged[key] = metadata.model_copy(
            update={
                "saved_bytes": content.saved_bytes,
                "byte_count": content.byte_count,
                "location": content.location,
            }
        )
    return parent.model_copy(
        update={
            **updates,
            "relationships": tuple(relationships),
            "limitations": tuple(limitations),
            "attachments": tuple(merged.values()),
        }
    )

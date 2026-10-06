"""Map verified release objects into the existing CollectedSelection codec."""

import json
from typing import Any

from msgloom.contracts import VersionRef
from msgloom.preparation.contracts import DocumentLocation, SavedByteReference
from msgloom.preparation.records import (
    NativeRelationship,
    PreparedRecipient,
    PreparedSourceType,
    RecipientRole,
)
from msgloom.sources._mapping import body_descriptor, party, source_time
from msgloom.sources._mapping import recipients as mail_recipients
from msgloom.sources._release_evidence import fact_reference
from msgloom.sources.handoff_models import ReleasedFact
from msgloom.sources.models import CollectedRecord, ContentKind, SourceMetadata

_TYPES = {
    "outlook_mail": PreparedSourceType.OUTLOOK_EMAIL,
    "todo": PreparedSourceType.TODO,
    "contacts": PreparedSourceType.CONTACT,
    "onedrive": PreparedSourceType.ONEDRIVE,
    "outlook_calendar": PreparedSourceType.OUTLOOK_CALENDAR,
}


def record(
    fact: ReleasedFact,
    raw: dict[str, Any],
    saved: SavedByteReference | None,
    scope: VersionRef,
) -> CollectedRecord:
    """Preserve provider fields, hierarchy, and exact provenance."""
    source = fact_reference(fact)
    metadata = []
    for name, value in (
        ("resource_kind", fact.resource_kind),
        ("component_kind", fact.component_kind),
        ("parent_resource_kind", fact.parent_resource_kind),
        ("parent_resource_identity", fact.parent_resource_identity),
        ("scope_kind", fact.scope_kind),
        ("scope_identity", fact.scope_identity),
    ):
        if value is not None:
            metadata.append(SourceMetadata(name=name, value=value))
    for name in (
        "profile_version",
        "status",
        "importance",
        "companyName",
        "jobTitle",
        "eTag",
        "cTag",
        "start",
        "end",
        "type",
        "seriesMasterId",
        "recurrence",
        "isAllDay",
        "isCancelled",
        "isChecked",
        "webUrl",
    ):
        if name in raw and raw[name] is not None:
            value = raw[name]
            metadata.append(
                SourceMetadata(
                    name=name,
                    value=value
                    if isinstance(value, str) and value
                    else json.dumps(value),
                )
            )
    attendees = raw.get("attendees", [])
    recipients = tuple(
        PreparedRecipient(party=value, role=RecipientRole.MEMBER)
        for item in (attendees if isinstance(attendees, list) else [])
        if (value := party(item)) is not None
    )
    return CollectedRecord(
        source=source,
        source_scope=scope,
        source_type=_TYPES[fact.stream],
        semantic_identity=source.identity,
        observed_at=source_time(fact.provider_observed_at, fact.provider_observed_at),
        source_time=source_time(
            raw.get("lastModifiedDateTime"), fact.provider_observed_at
        ),
        subject=next(
            (
                raw[key]
                for key in ("subject", "title", "displayName", "name")
                if isinstance(raw.get(key), str)
            ),
            None,
        ),
        sender=party(raw.get("sender")) if fact.stream == "outlook_mail" else None,
        author=party(
            raw.get("from") if fact.stream == "outlook_mail" else raw.get("organizer")
        ),
        recipients=mail_recipients(raw)
        if fact.stream == "outlook_mail"
        else recipients,
        source_content_kind=ContentKind.JSON,
        source_bytes=saved,
        body=body_descriptor(raw.get("body"), saved),
        alternate_bodies=(),
        attachments=(),
        relationships=(NativeRelationship(kind="source_scope", target=scope),),
        metadata=tuple(metadata),
        source_locations=(DocumentLocation(part="graph-json"),),
        limitations=(),
    )

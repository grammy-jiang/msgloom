"""Outlook-specific mapping for exact saved message observations."""

from __future__ import annotations

import json
from typing import Any

from msgloom.contracts import Limitation, VersionRef
from msgloom.preparation.contracts import DocumentLocation, SavedByteReference
from msgloom.preparation.records import NativeRelationship, PreparedSourceType
from msgloom.sources._catalog import ReadOnlyCatalog, ReplyCandidate, SelectedVersion
from msgloom.sources._io import EvidenceFiles
from msgloom.sources._mapping import (
    body_descriptor,
    content_kind,
    graph_object,
    party,
    recipients,
)
from msgloom.sources._mapping import metadata as make_metadata
from msgloom.sources._mapping import source_time as parse_source_time
from msgloom.sources.models import (
    CollectedAttachment,
    CollectedBody,
    CollectedRecord,
    ContentKind,
    SourceEvidenceError,
    SourceMetadata,
    SourceReferenceError,
)

_JSON_LOCATION = DocumentLocation(part="graph-json")
_BINARY_LOCATION = DocumentLocation(part="saved-bytes")


class OutlookMapper:
    """Map Outlook observations and explicitly capture mutable components."""

    def __init__(self, catalog: ReadOnlyCatalog, files: EvidenceFiles) -> None:
        self._catalog = catalog
        self._files = files

    @staticmethod
    def _base_relationships(scope: VersionRef) -> list[NativeRelationship]:
        return [NativeRelationship(kind="source_scope", target=scope)]

    def map(
        self,
        selected: SelectedVersion,
        scope: VersionRef,
        raw: dict[str, Any] | None,
        saved: SavedByteReference | None,
        evidence_limits: tuple[Limitation, ...],
    ) -> CollectedRecord:
        """Build one record while keeping primary and component lineage distinct."""
        limitations = list(evidence_limits)
        relationships = self._base_relationships(scope)
        body = None
        attachments: tuple[CollectedAttachment, ...] = ()
        alternate_bodies: tuple[CollectedBody, ...] = ()
        if raw is not None:
            body = body_descriptor(raw.get("body"), saved)
            if body is None:
                limitations.append(
                    Limitation(
                        "body-unavailable",
                        "Selected Outlook evidence contains no readable body.",
                    )
                )
            conversation = raw.get("conversationId")
            if isinstance(conversation, str) and conversation:
                relationships.append(
                    NativeRelationship(
                        kind="outlook_conversation",
                        target=VersionRef(
                            "outlook_conversation",
                            f"{selected.source_id}/{conversation}",
                            scope.version,
                        ),
                    )
                )
            self._add_in_reply_to(raw, selected, relationships, limitations)
        if self._catalog.outlook_current(selected):
            attachments = self._outlook_attachments(selected, limitations)
            alternate_bodies = self._outlook_mime(selected, limitations)
            if attachments or alternate_bodies:
                limitations.append(
                    Limitation(
                        "captured-current-component-selection",
                        "Current MIME/attachment associations are captured by the "
                        "composite selection snapshot; A1 does not prove permanent "
                        "ownership by the primary message observation.",
                    )
                )
        elif raw is not None and raw.get("hasAttachments") is True:
            limitations.append(
                Limitation(
                    "historical-attachment-association-unavailable",
                    "A1 does not bind current attachment surfaces to this old "
                    "message observation.",
                )
            )
        source_time = parse_source_time(
            raw.get("receivedDateTime") if raw is not None else None,
            selected.observed_at,
        )
        metadata = tuple(
            item
            for item in (
                make_metadata("internet_message_id", raw.get("internetMessageId"))
                if raw
                else None,
                make_metadata("parent_folder_id", raw.get("parentFolderId"))
                if raw
                else None,
                SourceMetadata(name="observation_kind", value=selected.locator),
            )
            if item is not None
        )
        return CollectedRecord(
            source=selected.source,
            source_scope=scope,
            source_type=PreparedSourceType.OUTLOOK_EMAIL,
            semantic_identity=f"outlook:{selected.source_id}:{selected.provider_id}",
            observed_at=parse_source_time(selected.observed_at, selected.observed_at),
            source_time=source_time,
            subject=(
                raw.get("subject")
                if raw and isinstance(raw.get("subject"), str)
                else None
            ),
            sender=party(raw.get("sender")) if raw else None,
            author=party(raw.get("from")) if raw else None,
            recipients=recipients(raw or {}),
            source_content_kind=ContentKind.JSON,
            source_bytes=saved,
            body=body,
            alternate_bodies=alternate_bodies,
            attachments=attachments,
            relationships=tuple(relationships),
            metadata=metadata,
            source_locations=(_JSON_LOCATION,),
            limitations=tuple(limitations),
        )

    def _add_in_reply_to(
        self,
        raw: dict[str, Any],
        selected: SelectedVersion,
        relationships: list[NativeRelationship],
        limitations: list[Limitation],
    ) -> None:
        headers = raw.get("internetMessageHeaders")
        if not isinstance(headers, list):
            return
        values: list[str] = []
        for header in headers:
            if not isinstance(header, dict):
                continue
            name = header.get("name")
            value = header.get("value")
            if (
                isinstance(name, str)
                and name.lower() == "in-reply-to"
                and isinstance(value, str)
            ):
                values.append(value)
        if len(values) != 1:
            if len(values) > 1:
                limitations.append(
                    Limitation(
                        "ambiguous-in-reply-to",
                        "Multiple In-Reply-To values were saved for this message.",
                    )
                )
            return
        reply_value = values[0]
        candidates, overflow = self._catalog.outlook_reply_candidates(
            selected.source_id
        )
        if overflow:
            limitations.append(
                Limitation(
                    "in-reply-to-query-overflow",
                    "Saved observation scan exceeded the configured query bound; "
                    "reply uniqueness is unknown.",
                )
            )
            return
        verified = tuple(
            candidate.source
            for candidate in candidates
            if self._candidate_matches(candidate, selected.source_id, reply_value)
        )
        if len(verified) == 1:
            relationships.append(
                NativeRelationship(kind="in_reply_to", target=verified[0])
            )
        elif verified:
            limitations.append(
                Limitation(
                    "ambiguous-in-reply-to-target",
                    "Internet-Message-ID resolves to multiple saved target versions.",
                )
            )
        else:
            limitations.append(
                Limitation(
                    "missing-in-reply-to-target",
                    "In-Reply-To target is unavailable in this source scope.",
                )
            )

    def _candidate_matches(
        self,
        candidate: ReplyCandidate,
        source_id: str,
        internet_message_id: str,
    ) -> bool:
        if candidate.evidence_id is None:
            return False
        try:
            evidence = self._catalog.evidence(candidate.evidence_id)
            if evidence.source_id != source_id:
                return False
            payload = json.loads(self._files.read(evidence))
            raw = graph_object(payload, candidate.provider_id)
        except (
            SourceEvidenceError,
            SourceReferenceError,
            json.JSONDecodeError,
        ):
            return False
        return raw.get("internetMessageId") == internet_message_id

    def _surface_rows(
        self,
        selected: SelectedVersion,
        record_limits: list[Limitation],
    ) -> dict[str, Any]:
        rows, overflow = self._catalog.outlook_surfaces(
            selected.source_id,
            selected.provider_id,
        )
        if overflow:
            record_limits.append(
                Limitation(
                    "outlook-surface-inventory-overflow",
                    "Current surface inventory exceeds the configured query bound.",
                )
            )
        return {row["surface"]: row for row in rows}

    def _outlook_mime(
        self,
        selected: SelectedVersion,
        record_limits: list[Limitation],
    ) -> tuple[CollectedBody, ...]:
        surfaces = self._surface_rows(selected, record_limits)
        surface = surfaces.get("mime")
        if surface is None:
            return ()
        if surface["status"] != "acquired" or not surface["evidence_id"]:
            record_limits.append(
                Limitation(
                    "mime-unavailable",
                    "Outlook MIME surface is not acquired.",
                )
            )
            return ()
        try:
            evidence = self._catalog.evidence(surface["evidence_id"])
            if evidence.source_id != selected.source_id:
                raise SourceEvidenceError("MIME evidence belongs to another source")
            self._files.read(evidence)
            saved = self._files.reference(evidence)
        except (SourceEvidenceError, SourceReferenceError):
            record_limits.append(
                Limitation("unavailable-mime", "Saved MIME evidence is unavailable.")
            )
            return ()
        return (
            CollectedBody(
                kind=ContentKind.MIME,
                content=None,
                saved_bytes=saved,
                location=DocumentLocation(part="mime"),
            ),
        )

    def _outlook_attachments(
        self,
        selected: SelectedVersion,
        record_limits: list[Limitation],
    ) -> tuple[CollectedAttachment, ...]:
        surfaces = self._surface_rows(selected, record_limits)
        rows, overflow = self._catalog.outlook_attachments(
            selected.source_id,
            selected.provider_id,
        )
        if overflow:
            record_limits.append(
                Limitation(
                    "outlook-attachment-inventory-overflow",
                    "Attachment inventory exceeds the configured query bound.",
                )
            )
        values: list[CollectedAttachment] = []
        for row in rows:
            values.append(self._attachment(selected, row, surfaces))
        inventory = surfaces.get("attachments")
        if not values and inventory is not None and inventory["status"] != "acquired":
            record_limits.append(
                Limitation(
                    "attachment-inventory-unavailable",
                    "Current attachment inventory is not acquired.",
                )
            )
        return tuple(values)

    def _attachment(
        self,
        selected: SelectedVersion,
        row: Any,
        surfaces: dict[str, Any],
    ) -> CollectedAttachment:
        surface = surfaces.get(f"attachment_raw:{row['attachment_id']}")
        saved = None
        limits: list[Limitation] = []
        metadata_bound = row["latest_evidence_id"] == selected.evidence_id
        if not metadata_bound:
            limits.append(
                Limitation(
                    "attachment-metadata-unbound",
                    "Attachment metadata is not bound to the selected primary "
                    "message evidence.",
                )
            )
        elif (
            surface is not None
            and surface["status"] == "acquired"
            and surface["evidence_id"]
        ):
            try:
                evidence = self._catalog.evidence(surface["evidence_id"])
                if evidence.source_id != selected.source_id:
                    raise SourceEvidenceError(
                        "attachment evidence belongs to another source"
                    )
                self._files.read(evidence)
                saved = self._files.reference(evidence)
            except (SourceEvidenceError, SourceReferenceError):
                limits.append(
                    Limitation(
                        "unavailable-attachment",
                        "Saved attachment evidence is unavailable.",
                    )
                )
        else:
            limits.append(
                Limitation(
                    "attachment-content-unavailable",
                    "Attachment raw-content surface is not acquired.",
                )
            )
        reference = VersionRef(
            "outlook_attachment",
            f"{selected.source.identity}/{row['attachment_id']}",
            row["latest_evidence_id"] or row["latest_observed_at"],
        )
        return CollectedAttachment(
            reference=reference,
            name=row["name"],
            content_type=row["content_type"],
            content_kind=content_kind(row["content_type"]),
            byte_count=row["size"],
            inline=(bool(row["is_inline"]) if row["is_inline"] is not None else None),
            saved_bytes=saved,
            location=_BINARY_LOCATION,
            limitations=tuple(limits),
        )

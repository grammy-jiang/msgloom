"""Map verified A1 evidence into immutable collected-record descriptors."""

from __future__ import annotations

import json
from typing import Any

from msgloom.contracts import Limitation, VersionRef
from msgloom.preparation.contracts import DocumentLocation, SavedByteReference
from msgloom.preparation.records import (
    NativeRelationship,
    PreparedSourceType,
)
from msgloom.sources._catalog import (
    ReadOnlyCatalog,
    SelectedVersion,
    encode_parts,
)
from msgloom.sources._io import EvidenceFiles
from msgloom.sources._mapping import (
    body_descriptor,
    content_kind,
    graph_object,
)
from msgloom.sources._mapping import (
    metadata as make_metadata,
)
from msgloom.sources._mapping import (
    source_time as parse_source_time,
)
from msgloom.sources._outlook import OutlookMapper
from msgloom.sources.models import (
    CollectedAttachment,
    CollectedRecord,
    ContentKind,
    SourceEvidenceError,
    SourceReferenceError,
)

_JSON_LOCATION = DocumentLocation(part="graph-json")
_BINARY_LOCATION = DocumentLocation(part="saved-bytes")


class RecordAssembler:
    """Build provider-neutral records from exact verified A1 associations."""

    def __init__(self, catalog: ReadOnlyCatalog, files: EvidenceFiles) -> None:
        self._catalog = catalog
        self._files = files
        self._outlook_mapper = OutlookMapper(catalog, files)

    def _evidence(
        self, selected: SelectedVersion
    ) -> tuple[
        dict[str, Any] | None,
        SavedByteReference | None,
        tuple[Limitation, ...],
    ]:
        if selected.evidence_id is None:
            return (
                None,
                None,
                (
                    Limitation(
                        "missing-evidence",
                        "Selected observation has no saved evidence.",
                    ),
                ),
            )
        try:
            row = self._catalog.evidence(selected.evidence_id)
            if row.source_id != selected.source_id:
                raise SourceEvidenceError("saved evidence belongs to another source")
            data = self._files.read(row)
            reference = self._files.reference(row)
            payload = json.loads(data)
            raw = graph_object(payload, selected.provider_id)
            return raw, reference, ()
        except (SourceEvidenceError, SourceReferenceError, json.JSONDecodeError) as exc:
            return None, None, (Limitation("unavailable-evidence", str(exc)),)

    def list_onedrive_versions(
        self, source_id: str, limit: int
    ) -> tuple[VersionRef, ...]:
        """Enumerate exact OneDrive item versions from immutable page evidence."""
        values: list[VersionRef] = []
        seen: set[VersionRef] = set()
        for row in self._catalog.onedrive_evidence(source_id):
            try:
                payload = json.loads(self._files.read(row))
            except (SourceEvidenceError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict) or not isinstance(
                payload.get("value"), list
            ):
                continue
            for item in payload["value"]:
                if not isinstance(item, dict):
                    continue
                provider_id = item.get("id")
                if not isinstance(provider_id, str) or not provider_id:
                    continue
                ref = VersionRef(
                    PreparedSourceType.ONEDRIVE.value,
                    encode_parts(source_id, provider_id),
                    encode_parts("evidence", row.observed_at, row.evidence_id),
                )
                if ref in seen:
                    continue
                values.append(ref)
                seen.add(ref)
                if len(values) == limit:
                    return tuple(values)
        return tuple(values)

    def read(self, source: VersionRef) -> CollectedRecord:
        selected = self._catalog.select(source)
        scope = self._catalog.source_scope(selected.source_id)
        source_type = PreparedSourceType(source.kind)
        raw, saved, evidence_limits = self._evidence(selected)
        if source_type is PreparedSourceType.OUTLOOK_EMAIL:
            return self._outlook_mapper.map(
                selected, scope, raw, saved, evidence_limits
            )
        if source_type is PreparedSourceType.TODO:
            return self._todo(selected, scope, raw, saved, evidence_limits)
        if source_type is PreparedSourceType.CONTACT:
            return self._contact(selected, scope, raw, saved, evidence_limits)
        if source_type is PreparedSourceType.ONEDRIVE:
            return self._onedrive(selected, scope, raw, saved, evidence_limits)
        raise SourceReferenceError("unsupported A1 source type")

    @staticmethod
    def _base_relationships(scope: VersionRef) -> list[NativeRelationship]:
        return [NativeRelationship(kind="source_scope", target=scope)]

    def _todo(
        self,
        selected: SelectedVersion,
        scope: VersionRef,
        raw: dict[str, Any] | None,
        saved: SavedByteReference | None,
        evidence_limits: tuple[Limitation, ...],
    ) -> CollectedRecord:
        body = body_descriptor(raw.get("body"), saved) if raw else None
        source_time = parse_source_time(
            raw.get("lastModifiedDateTime") if raw else None,
            selected.observed_at,
        )
        metadata = tuple(
            item
            for item in (
                make_metadata("status", raw.get("status")) if raw else None,
                make_metadata("importance", raw.get("importance")) if raw else None,
                make_metadata("list_id", selected.auxiliary[0]),
            )
            if item is not None
        )
        return CollectedRecord(
            source=selected.source,
            source_scope=scope,
            source_type=PreparedSourceType.TODO,
            semantic_identity=(
                f"todo:{selected.source_id}:{selected.auxiliary[0]}:"
                f"{selected.provider_id}"
            ),
            observed_at=parse_source_time(selected.observed_at, selected.observed_at),
            source_time=source_time,
            subject=(
                raw.get("title") if raw and isinstance(raw.get("title"), str) else None
            ),
            sender=None,
            author=None,
            recipients=(),
            source_content_kind=ContentKind.JSON,
            source_bytes=saved,
            body=body,
            alternate_bodies=(),
            attachments=(),
            relationships=tuple(self._base_relationships(scope)),
            metadata=metadata,
            source_locations=(_JSON_LOCATION,),
            limitations=evidence_limits,
        )

    def _contact(
        self,
        selected: SelectedVersion,
        scope: VersionRef,
        raw: dict[str, Any] | None,
        saved: SavedByteReference | None,
        evidence_limits: tuple[Limitation, ...],
    ) -> CollectedRecord:
        metadata = tuple(
            item
            for item in (
                make_metadata("company_name", raw.get("companyName")) if raw else None,
                make_metadata("job_title", raw.get("jobTitle")) if raw else None,
                make_metadata("scope_key", selected.auxiliary[0]),
            )
            if item is not None
        )
        return CollectedRecord(
            source=selected.source,
            source_scope=scope,
            source_type=PreparedSourceType.CONTACT,
            semantic_identity=(
                f"contact:{selected.source_id}:{selected.auxiliary[0]}:"
                f"{selected.provider_id}"
            ),
            observed_at=parse_source_time(selected.observed_at, selected.observed_at),
            source_time=parse_source_time(
                raw.get("lastModifiedDateTime") if raw else None,
                selected.observed_at,
            ),
            subject=(
                raw.get("displayName")
                if raw and isinstance(raw.get("displayName"), str)
                else None
            ),
            sender=None,
            author=None,
            recipients=(),
            source_content_kind=ContentKind.JSON,
            source_bytes=saved,
            body=None,
            alternate_bodies=(),
            attachments=(),
            relationships=tuple(self._base_relationships(scope)),
            metadata=metadata,
            source_locations=(_JSON_LOCATION,),
            limitations=evidence_limits,
        )

    def _onedrive(
        self,
        selected: SelectedVersion,
        scope: VersionRef,
        raw: dict[str, Any] | None,
        saved_source: SavedByteReference | None,
        evidence_limits: tuple[Limitation, ...],
    ) -> CollectedRecord:
        limitations = list(evidence_limits)
        attachments: tuple[CollectedAttachment, ...] = ()
        capture, capture_overflow = self._catalog.onedrive_content_capture(selected)
        if capture_overflow:
            limitations.append(
                Limitation(
                    "onedrive-content-query-overflow",
                    "Content-capture inventory exceeds the configured query bound.",
                )
            )
        if capture is not None:
            try:
                evidence = self._catalog.evidence(capture["evidence_id"])
                if evidence.source_id != selected.source_id:
                    raise SourceEvidenceError(
                        "OneDrive content evidence belongs to another source"
                    )
                self._files.read(evidence)
                saved = self._files.reference(evidence)
                if (
                    saved.sha256 != capture["content_sha256"]
                    or saved.byte_count != capture["content_bytes"]
                ):
                    raise SourceEvidenceError(
                        "OneDrive content capture integrity association changed"
                    )
                attachments = (
                    CollectedAttachment(
                        reference=VersionRef(
                            "onedrive_content",
                            selected.source.identity,
                            capture["evidence_id"],
                        ),
                        name=(
                            raw.get("name")
                            if raw and isinstance(raw.get("name"), str)
                            else None
                        ),
                        content_type=self._onedrive_content_type(raw),
                        content_kind=content_kind(self._onedrive_content_type(raw)),
                        byte_count=capture["content_bytes"],
                        inline=False,
                        saved_bytes=saved,
                        location=_BINARY_LOCATION,
                    ),
                )
            except (SourceEvidenceError, SourceReferenceError) as exc:
                limitations.append(Limitation("unavailable-onedrive-content", str(exc)))
        elif not capture_overflow and raw is not None and raw.get("file") is not None:
            limitations.append(
                Limitation(
                    "onedrive-content-not-current",
                    "No verified content capture is bound to this exact item version.",
                )
            )
        metadata = tuple(
            item
            for item in (
                make_metadata("web_url", raw.get("webUrl")) if raw else None,
                make_metadata("e_tag", raw.get("eTag")) if raw else None,
                make_metadata("c_tag", raw.get("cTag")) if raw else None,
            )
            if item is not None
        )
        return CollectedRecord(
            source=selected.source,
            source_scope=scope,
            source_type=PreparedSourceType.ONEDRIVE,
            semantic_identity=f"onedrive:{selected.source_id}:{selected.provider_id}",
            observed_at=parse_source_time(selected.observed_at, selected.observed_at),
            source_time=parse_source_time(
                raw.get("lastModifiedDateTime") if raw else None,
                selected.observed_at,
            ),
            subject=(
                raw.get("name") if raw and isinstance(raw.get("name"), str) else None
            ),
            sender=None,
            author=None,
            recipients=(),
            source_content_kind=ContentKind.JSON,
            source_bytes=saved_source,
            body=None,
            alternate_bodies=(),
            attachments=attachments,
            relationships=tuple(self._base_relationships(scope)),
            metadata=metadata,
            source_locations=(_JSON_LOCATION,),
            limitations=tuple(limitations),
        )

    @staticmethod
    def _onedrive_content_type(raw: dict[str, Any] | None) -> str | None:
        if raw is None or not isinstance(raw.get("file"), dict):
            return None
        mime = raw["file"].get("mimeType")
        return mime if isinstance(mime, str) else None

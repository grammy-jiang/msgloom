"""Bounded read-only SQLite access for the existing A1 acquisition schema."""

from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote

from msgloom.contracts import VersionRef
from msgloom.preparation.records import PreparedSourceType
from msgloom.sources._catalog_path import CatalogPath
from msgloom.sources.models import SourceReaderLimits, SourceReferenceError


@dataclass(frozen=True, slots=True)
class EvidenceRow:
    """Credential-free fields required to verify one saved response body."""

    evidence_id: str
    source_id: str
    observed_at: str
    purpose: str | None
    response_body_sha256: str
    response_body_path: str
    response_body_bytes: int


@dataclass(frozen=True, slots=True)
class SelectedVersion:
    """Internal exact source association resolved from immutable A1 rows."""

    source: VersionRef
    source_id: str
    provider_id: str
    observed_at: str
    evidence_id: str | None
    locator: str
    auxiliary: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReplyCandidate:
    """One saved Outlook observation requiring evidence verification."""

    source: VersionRef
    provider_id: str
    evidence_id: str | None


def _pack(*parts: str) -> str:
    return "/".join(quote(part, safe="") for part in parts)


def encode_parts(*parts: str) -> str:
    """Encode stable ref components without creating a fetchable URI."""
    return _pack(*parts)


def _unpack(value: str, count: int) -> tuple[str, ...]:
    parts = tuple(unquote(part) for part in value.split("/"))
    if len(parts) != count or any(not part for part in parts):
        raise SourceReferenceError("malformed saved source identity")
    return parts


class ReadOnlyCatalog:
    """Open short-lived SQLite read-only connections with query deadlines."""

    def __init__(self, path: Path, limits: SourceReaderLimits) -> None:
        self.path = path
        self.limits = limits
        self._safe_path = CatalogPath(path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._safe_path.uri(),
            uri=True,
            timeout=0.0,
        )
        try:
            self._safe_path.verify()
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            deadline = time.monotonic() + self.limits.query_timeout_seconds

            def progress() -> int:
                return int(time.monotonic() >= deadline)

            connection.set_progress_handler(progress, 1_000)
        except Exception:
            connection.close()
            raise
        return connection

    def close(self) -> None:
        """Release the pinned catalog path after all queries drain."""
        self._safe_path.close()

    def source_scope(self, source_id: str) -> VersionRef:
        """Resolve one exact stable source binding without account material."""
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT source_id, bound_at FROM source_bindings "
                "WHERE source_id = ? LIMIT 1",
                (source_id,),
            ).fetchone()
        if row is None:
            raise SourceReferenceError("selected source has no source binding")
        return VersionRef("source_scope", row["source_id"], row["bound_at"])

    def evidence(self, evidence_id: str) -> EvidenceRow:
        """Return only fields needed for local response-byte verification."""
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT evidence_id, source_id, observed_at, purpose, "
                "response_body_sha256, response_body_path, response_body_bytes "
                "FROM raw_http_evidence WHERE evidence_id = ? LIMIT 1",
                (evidence_id,),
            ).fetchone()
        if row is None:
            raise SourceReferenceError("saved evidence reference is unknown")
        return EvidenceRow(**dict(row))

    def list_versions(
        self,
        source_type: PreparedSourceType,
        source_id: str,
        limit: int,
    ) -> tuple[VersionRef, ...]:
        """List exact versions from immutable associations, never latest aliases."""
        if source_type is PreparedSourceType.OUTLOOK_EMAIL:
            sql = (
                "SELECT observation_id, message_id FROM message_observations "
                "WHERE source_id = ? ORDER BY observed_at DESC, observation_id DESC "
                "LIMIT ?"
            )
            params = (source_id, limit)
            make = lambda row: VersionRef(
                source_type.value,
                _pack(source_id, row["message_id"]),
                row["observation_id"],
            )
        elif source_type is PreparedSourceType.TODO:
            sql = (
                "SELECT run_id, evidence_id, list_id, task_id "
                "FROM todo_task_sightings WHERE source_id = ? "
                "ORDER BY observed_at DESC, run_id DESC, list_id, task_id LIMIT ?"
            )
            params = (source_id, limit)
            make = lambda row: VersionRef(
                source_type.value,
                _pack(source_id, row["list_id"], row["task_id"]),
                _pack(row["run_id"], row["evidence_id"]),
            )
        elif source_type is PreparedSourceType.CONTACT:
            sql = (
                "SELECT mode, run_id, evidence_id, scope_key, contact_id, "
                "observed_at, ordinal FROM ("
                "SELECT 'snapshot' AS mode, run_id, evidence_id, scope_key, "
                "contact_id, observed_at, -1 AS ordinal FROM contact_sightings "
                "WHERE source_id = ? UNION ALL "
                "SELECT 'delta' AS mode, run_id, evidence_id, "
                "'folder:' || folder_id AS scope_key, contact_id, observed_at, "
                "ordinal FROM contact_delta_observations "
                "WHERE source_id = ? AND evidence_id IS NOT NULL"
                ") ORDER BY observed_at DESC, run_id DESC, scope_key, contact_id "
                "LIMIT ?"
            )
            params = (source_id, source_id, limit)
            make = lambda row: VersionRef(
                source_type.value,
                _pack(source_id, row["scope_key"], row["contact_id"]),
                (
                    _pack("snapshot", row["run_id"], row["evidence_id"])
                    if row["mode"] == "snapshot"
                    else _pack(
                        "delta",
                        row["run_id"],
                        str(row["ordinal"]),
                        row["evidence_id"],
                    )
                ),
            )
        elif source_type is PreparedSourceType.ONEDRIVE:
            sql = (
                "SELECT item_id, latest_observed_at, latest_evidence_id "
                "FROM onedrive_items WHERE source_id = ? "
                "ORDER BY latest_observed_at DESC, item_id LIMIT ?"
            )
            params = (source_id, limit)
            make = lambda row: VersionRef(
                source_type.value,
                _pack(source_id, row["item_id"]),
                _pack(
                    "current",
                    row["latest_observed_at"],
                    row["latest_evidence_id"] or "missing",
                ),
            )
        else:
            raise SourceReferenceError("source type has no live A1 adapter")
        with closing(self._connect()) as connection:
            rows = connection.execute(sql, params).fetchall()
        return tuple(make(row) for row in rows)

    def onedrive_evidence(self, source_id: str) -> tuple[EvidenceRow, ...]:
        """Return a complete bounded OneDrive page inventory or fail."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT evidence_id, source_id, observed_at, purpose, "
                "response_body_sha256, response_body_path, response_body_bytes "
                "FROM raw_http_evidence WHERE source_id = ? "
                "AND purpose IN ('onedrive-delta-page', "
                "'onedrive-root-children-page') "
                "ORDER BY observed_at DESC, evidence_id DESC LIMIT ?",
                (source_id, self.limits.max_query_rows + 1),
            ).fetchall()
        if len(rows) > self.limits.max_query_rows:
            raise SourceReferenceError(
                "OneDrive evidence inventory exceeds configured query bound"
            )
        return tuple(EvidenceRow(**dict(row)) for row in rows)

    def select(self, source: VersionRef) -> SelectedVersion:
        """Resolve a caller-supplied exact version through immutable A1 rows."""
        try:
            source_type = PreparedSourceType(source.kind)
        except ValueError as exc:
            raise SourceReferenceError("unsupported saved source kind") from exc
        if source_type is PreparedSourceType.OUTLOOK_EMAIL:
            return self._select_outlook(source)
        if source_type is PreparedSourceType.TODO:
            return self._select_todo(source)
        if source_type is PreparedSourceType.CONTACT:
            return self._select_contact(source)
        if source_type is PreparedSourceType.ONEDRIVE:
            return self._select_onedrive(source)
        raise SourceReferenceError("source type has no live A1 adapter")

    def _select_outlook(self, source: VersionRef) -> SelectedVersion:
        source_id, message_id = _unpack(source.identity, 2)
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT observed_at, evidence_id, kind, parent_folder_id, "
                "last_modified_date_time FROM message_observations "
                "WHERE source_id = ? AND message_id = ? AND observation_id = ? "
                "LIMIT 1",
                (source_id, message_id, source.version),
            ).fetchone()
        if row is None:
            raise SourceReferenceError("Outlook source version is unknown")
        return SelectedVersion(
            source,
            source_id,
            message_id,
            row["observed_at"],
            row["evidence_id"],
            row["kind"],
            (
                row["parent_folder_id"] or "",
                row["last_modified_date_time"] or "",
            ),
        )

    def _select_todo(self, source: VersionRef) -> SelectedVersion:
        source_id, list_id, task_id = _unpack(source.identity, 3)
        run_id, evidence_id = _unpack(source.version, 2)
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT observed_at FROM todo_task_sightings "
                "WHERE source_id = ? AND run_id = ? AND list_id = ? "
                "AND task_id = ? AND evidence_id = ? LIMIT 1",
                (source_id, run_id, list_id, task_id, evidence_id),
            ).fetchone()
        if row is None:
            raise SourceReferenceError("To Do source version is unknown")
        return SelectedVersion(
            source,
            source_id,
            task_id,
            row["observed_at"],
            evidence_id,
            "task",
            (list_id, run_id),
        )

    def _select_contact(self, source: VersionRef) -> SelectedVersion:
        source_id, scope_key, contact_id = _unpack(source.identity, 3)
        version = tuple(unquote(part) for part in source.version.split("/"))
        if len(version) == 3 and version[0] == "snapshot":
            _, run_id, evidence_id = version
            sql = (
                "SELECT observed_at FROM contact_sightings "
                "WHERE source_id = ? AND run_id = ? AND scope_key = ? "
                "AND contact_id = ? AND evidence_id = ? LIMIT 1"
            )
            params = (source_id, run_id, scope_key, contact_id, evidence_id)
        elif len(version) == 4 and version[0] == "delta":
            _, run_id, ordinal, evidence_id = version
            if (
                not ordinal.isascii()
                or not ordinal.isdecimal()
                or len(ordinal) > 19
                or (len(ordinal) > 1 and ordinal.startswith("0"))
                or (ordinal_value := int(ordinal)) > 2**63 - 1
            ):
                raise SourceReferenceError("Contact delta ordinal is malformed")
            if not scope_key.startswith("folder:"):
                raise SourceReferenceError("Contact delta scope is malformed")
            sql = (
                "SELECT observed_at FROM contact_delta_observations "
                "WHERE source_id = ? AND run_id = ? AND folder_id = ? "
                "AND contact_id = ? AND ordinal = ? AND evidence_id = ? LIMIT 1"
            )
            params = (
                source_id,
                run_id,
                scope_key.removeprefix("folder:"),
                contact_id,
                ordinal_value,
                evidence_id,
            )
        else:
            raise SourceReferenceError("unsupported Contact source version")
        with closing(self._connect()) as connection:
            row = connection.execute(sql, params).fetchone()
        if row is None:
            raise SourceReferenceError("Contact source version is unknown")
        return SelectedVersion(
            source,
            source_id,
            contact_id,
            row["observed_at"],
            evidence_id,
            "contact",
            (scope_key, run_id),
        )

    def _select_onedrive(self, source: VersionRef) -> SelectedVersion:
        source_id, item_id = _unpack(source.identity, 2)
        version = tuple(unquote(part) for part in source.version.split("/"))
        if len(version) != 3:
            raise SourceReferenceError("unsupported OneDrive source version")
        mode, observed_at, evidence_id = version
        if mode == "evidence":
            row = self.evidence(evidence_id)
            if (
                row.source_id != source_id
                or row.observed_at != observed_at
                or row.purpose
                not in {"onedrive-delta-page", "onedrive-root-children-page"}
            ):
                raise SourceReferenceError("OneDrive evidence version is unknown")
            return SelectedVersion(
                source,
                source_id,
                item_id,
                observed_at,
                evidence_id,
                "item",
            )
        if mode != "current":
            raise SourceReferenceError("unsupported OneDrive source version")
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT latest_observed_at, latest_evidence_id FROM onedrive_items "
                "WHERE source_id = ? AND item_id = ? LIMIT 1",
                (source_id, item_id),
            ).fetchone()
        if (
            row is None
            or row["latest_observed_at"] != observed_at
            or (row["latest_evidence_id"] or "missing") != evidence_id
        ):
            raise SourceReferenceError(
                "OneDrive current-version reference is stale or unknown"
            )
        return SelectedVersion(
            source,
            source_id,
            item_id,
            observed_at,
            None if evidence_id == "missing" else evidence_id,
            "item",
        )

    def outlook_reply_candidates(
        self, source_id: str
    ) -> tuple[tuple[ReplyCandidate, ...], bool]:
        """Return saved observations plus explicit query-overflow state."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT observation_id, message_id, evidence_id "
                "FROM message_observations WHERE source_id = ? "
                "ORDER BY observed_at, observation_id LIMIT ?",
                (source_id, self.limits.max_query_rows + 1),
            ).fetchall()
        overflow = len(rows) > self.limits.max_query_rows
        rows = rows[: self.limits.max_query_rows]
        return (
            tuple(
                ReplyCandidate(
                    source=VersionRef(
                        PreparedSourceType.OUTLOOK_EMAIL.value,
                        _pack(source_id, row["message_id"]),
                        row["observation_id"],
                    ),
                    provider_id=row["message_id"],
                    evidence_id=row["evidence_id"],
                )
                for row in rows
            ),
            overflow,
        )

    def outlook_current(self, selected: SelectedVersion) -> bool:
        """Return whether an Outlook observation is the current projection."""
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT latest_evidence_id FROM messages "
                "WHERE source_id = ? AND message_id = ? LIMIT 1",
                (selected.source_id, selected.provider_id),
            ).fetchone()
        return (
            row is not None
            and selected.evidence_id is not None
            and row["latest_evidence_id"] == selected.evidence_id
        )

    def outlook_surfaces(
        self, source_id: str, message_id: str
    ) -> tuple[tuple[sqlite3.Row, ...], bool]:
        """Read current surfaces with explicit inventory-overflow state."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT surface, status, evidence_id, observed_at, profile_version "
                "FROM message_surfaces WHERE source_id = ? AND message_id = ? "
                "ORDER BY surface LIMIT ?",
                (source_id, message_id, self.limits.max_query_rows + 1),
            ).fetchall()
        return (
            tuple(rows[: self.limits.max_query_rows]),
            len(rows) > self.limits.max_query_rows,
        )

    def outlook_attachments(
        self, source_id: str, message_id: str
    ) -> tuple[tuple[sqlite3.Row, ...], bool]:
        """Read current attachment metadata with explicit overflow state."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT attachment_id, attachment_type, name, content_type, size, "
                "is_inline, latest_observed_at, latest_evidence_id "
                "FROM attachments WHERE source_id = ? AND message_id = ? "
                "ORDER BY attachment_id LIMIT ?",
                (source_id, message_id, self.limits.max_query_rows + 1),
            ).fetchall()
        return (
            tuple(rows[: self.limits.max_query_rows]),
            len(rows) > self.limits.max_query_rows,
        )

    def onedrive_content_capture(
        self, selected: SelectedVersion
    ) -> tuple[sqlite3.Row | None, bool]:
        """Return exact content association and explicit query overflow."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT evidence_id, content_sha256, content_bytes, "
                "planned_metadata_observed_at, planned_metadata_evidence_id, "
                "planned_e_tag, response_e_tag, observed_at "
                "FROM onedrive_content_captures "
                "WHERE source_id = ? AND item_id = ? "
                "ORDER BY observed_at DESC LIMIT ?",
                (
                    selected.source_id,
                    selected.provider_id,
                    self.limits.max_query_rows + 1,
                ),
            ).fetchall()
        overflow = len(rows) > self.limits.max_query_rows
        if overflow:
            return None, True
        matches = [
            row
            for row in rows
            if row["planned_metadata_observed_at"] == selected.observed_at
            and row["planned_metadata_evidence_id"] == selected.evidence_id
            and row["planned_e_tag"]
            and row["response_e_tag"] == row["planned_e_tag"]
        ]
        if len(matches) != 1:
            return None, False
        return matches[0], False

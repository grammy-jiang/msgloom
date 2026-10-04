"""Bounded Teams queries over the existing read-only A1 catalog."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import unquote

from msgloom.contracts import VersionRef
from msgloom.preparation.records import PreparedSourceType
from msgloom.sources._catalog import encode_parts
from msgloom.sources.models import SourceReaderLimits, SourceReferenceError

_CHAT = PreparedSourceType.TEAMS_CHAT_MESSAGE
_CHANNEL = PreparedSourceType.TEAMS_CHANNEL_MESSAGE
_TEAMS_TYPES = frozenset({_CHAT, _CHANNEL})


class _CatalogAccess(Protocol):
    """Expose the existing deadline-bound connection and configured limits."""

    limits: SourceReaderLimits

    def _connect(self) -> sqlite3.Connection:
        """Open one pinned read-only SQLite connection."""
        ...


@dataclass(frozen=True, slots=True)
class TeamsMessageSelection:
    """One exact immutable Teams message observation."""

    source: VersionRef
    source_type: PreparedSourceType
    source_id: str
    observation_id: int
    scope_key_sha256: str
    location: str
    message_id: str
    chat_id: str | None
    team_id: str | None
    channel_id: str | None
    root_message_id: str | None
    observed_at: str
    evidence_id: str
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class TeamsComponentRows:
    """Bounded additive component rows captured for one message version."""

    attachments: tuple[dict[str, Any], ...]
    deletions: tuple[dict[str, Any], ...]
    references: tuple[dict[str, Any], ...]
    hosted: tuple[dict[str, Any], ...]
    topology: tuple[dict[str, Any], ...]
    coverage: tuple[dict[str, Any], ...]
    reply_target: VersionRef | None


def is_teams_source_type(source_type: PreparedSourceType) -> bool:
    """Return whether source_type belongs to the frozen Teams core."""
    return source_type in _TEAMS_TYPES


def decode_json(value: object, expected: type[list | dict], label: str) -> Any:
    """Decode one SQLite JSON field without accepting non-finite numbers."""
    if isinstance(value, expected):
        return value
    if not isinstance(value, str):
        raise SourceReferenceError(f"Teams {label} JSON is invalid")
    try:
        decoded = json.loads(
            value,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
        )
    except (json.JSONDecodeError, ValueError):
        raise SourceReferenceError(f"Teams {label} JSON is invalid") from None
    if not isinstance(decoded, expected):
        raise SourceReferenceError(f"Teams {label} JSON is invalid")
    return decoded


def scope_digest(scope: Sequence[object]) -> str:
    """Return the persistence-compatible digest for one exact scope tuple."""
    try:
        data = json.dumps(
            list(scope),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    except (TypeError, ValueError):
        raise SourceReferenceError("Teams saved scope is invalid") from None
    return hashlib.sha256(data).hexdigest()


def _unpack(value: str) -> tuple[str, ...]:
    parts = tuple(unquote(part) for part in value.split("/"))
    if any(not part for part in parts):
        raise SourceReferenceError("malformed Teams saved source identity")
    return parts


def _row_id(value: str) -> int:
    valid = (
        value.isascii()
        and value.isdecimal()
        and len(value) <= 19
        and (len(value) == 1 or not value.startswith("0"))
    )
    if not valid:
        raise SourceReferenceError("Teams source version is malformed")
    parsed = int(value)
    if not 1 <= parsed <= 2**63 - 1:
        raise SourceReferenceError("Teams source version is malformed")
    return parsed


class TeamsCatalogQueries:
    """Read Teams rows through the existing pinned, deadline-bound catalog."""

    def __init__(self, catalog: _CatalogAccess) -> None:
        self._catalog = catalog

    def list_versions(
        self,
        source_type: PreparedSourceType,
        source_id: str,
        limit: int,
    ) -> tuple[VersionRef, ...]:
        """List exact immutable Teams message captures deterministically."""
        self._require_type(source_type)
        if not source_id.strip():
            raise ValueError("source_id must be non-empty")
        if isinstance(limit, bool) or limit < 1:
            raise ValueError("limit must be positive")
        if limit > self._catalog.limits.max_list_results:
            raise ValueError("limit exceeds configured listing bound")
        location = (
            "location = 'chat'"
            if source_type == _CHAT
            else "location IN ('channel-root', 'channel-reply')"
        )
        with closing(self._catalog._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM teams_message_observations "
                f"WHERE source_id = ? AND {location} "
                "ORDER BY observed_at DESC, observation_id DESC LIMIT ?",
                (source_id, limit),
            ).fetchall()
        return tuple(self._version(source_type, row) for row in rows)

    def select(self, source: VersionRef) -> TeamsMessageSelection:
        """Resolve an exact caller-supplied Teams version and validate scope."""
        try:
            source_type = PreparedSourceType(source.kind)
        except ValueError as exc:
            raise SourceReferenceError("unsupported Teams saved source kind") from exc
        self._require_type(source_type)
        identity = _unpack(source.identity)
        version = _unpack(source.version)
        if len(version) != 2:
            raise SourceReferenceError("Teams source version is malformed")
        with closing(self._catalog._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM teams_message_observations "
                "WHERE observation_id = ? AND evidence_id = ? LIMIT 2",
                (_row_id(version[0]), version[1]),
            ).fetchall()
        if len(rows) != 1:
            raise SourceReferenceError("Teams source version is unknown")
        selected = self._selection(source_type, source, rows[0])
        if identity != self._identity_parts(selected):
            raise SourceReferenceError("Teams source identity does not match version")
        return selected

    def components(self, selected: TeamsMessageSelection) -> TeamsComponentRows:
        """Read all relevant components under the configured row ceiling."""
        return TeamsComponentRows(
            attachments=self._bounded(
                "teams_message_attachments",
                "message_observation_id = ? AND source_id = ? AND scope_key_sha256 = ?",
                (
                    selected.observation_id,
                    selected.source_id,
                    selected.scope_key_sha256,
                ),
                "ordinal",
                "attachment",
            ),
            deletions=self._bounded(
                "teams_message_deletions",
                "source_id = ? AND scope_key_sha256 = ?",
                (selected.source_id, selected.scope_key_sha256),
                "observed_at, deletion_id",
                "deletion",
            ),
            references=self._bounded(
                "teams_reference_resolution_observations",
                "source_id = ? AND trigger_scope_sha256 = ? "
                "AND trigger_evidence_id = ?",
                (
                    selected.source_id,
                    selected.scope_key_sha256,
                    selected.evidence_id,
                ),
                "attachment_ordinal, observed_at, observation_id",
                "reference resolution",
            ),
            hosted=self._bounded(
                "teams_hosted_content_observations",
                "source_id = ? AND trigger_scope_sha256 = ? "
                "AND trigger_evidence_id = ?",
                (
                    selected.source_id,
                    selected.scope_key_sha256,
                    selected.evidence_id,
                ),
                "observed_at, observation_id",
                "hosted content",
            ),
            topology=self._topology(selected),
            coverage=self._coverage(selected),
            reply_target=self._reply_target(selected),
        )

    @staticmethod
    def _require_type(source_type: PreparedSourceType) -> None:
        if not is_teams_source_type(source_type):
            raise SourceReferenceError("unsupported Teams saved source kind")

    def _version(
        self,
        source_type: PreparedSourceType,
        row: sqlite3.Row | dict[str, Any],
    ) -> VersionRef:
        selected = self._selection(
            source_type,
            VersionRef(source_type.value, "validation", "validation"),
            row,
        )
        return VersionRef(
            source_type.value,
            encode_parts(*self._identity_parts(selected)),
            encode_parts(str(selected.observation_id), selected.evidence_id),
        )

    def _selection(
        self,
        source_type: PreparedSourceType,
        source: VersionRef,
        row: sqlite3.Row | dict[str, Any],
    ) -> TeamsMessageSelection:
        raw = decode_json(row["raw"], dict, "message raw")
        parts = self._scope_parts(source_type, row)
        scope = decode_json(row["scope_key"], list, "message scope")
        expected = ["message", *parts]
        if scope != expected or row["scope_key_sha256"] != scope_digest(expected):
            raise SourceReferenceError("Teams saved message scope is inconsistent")
        if raw.get("id") != row["message_id"]:
            raise SourceReferenceError(
                "Teams saved message raw identity is inconsistent"
            )
        return TeamsMessageSelection(
            source=source,
            source_type=source_type,
            source_id=row["source_id"],
            observation_id=row["observation_id"],
            scope_key_sha256=row["scope_key_sha256"],
            location=row["location"],
            message_id=row["message_id"],
            chat_id=row["chat_id"],
            team_id=row["team_id"],
            channel_id=row["channel_id"],
            root_message_id=row["root_message_id"],
            observed_at=row["observed_at"],
            evidence_id=row["evidence_id"],
            raw=raw,
        )

    @staticmethod
    def _identity_parts(selected: TeamsMessageSelection) -> tuple[str, ...]:
        values = [selected.source_id, selected.location]
        if selected.location == "chat":
            values.extend((selected.chat_id or "", selected.message_id))
        elif selected.location == "channel-root":
            values.extend(
                (
                    selected.team_id or "",
                    selected.channel_id or "",
                    selected.message_id,
                )
            )
        else:
            values.extend(
                (
                    selected.team_id or "",
                    selected.channel_id or "",
                    selected.root_message_id or "",
                    selected.message_id,
                )
            )
        return tuple(values)

    @staticmethod
    def _scope_parts(
        source_type: PreparedSourceType,
        row: sqlite3.Row | dict[str, Any],
    ) -> list[str]:
        location = row["location"]
        if source_type == _CHAT:
            if (
                location != "chat"
                or not row["chat_id"]
                or not row["message_id"]
                or any(
                    row[name] is not None
                    for name in ("team_id", "channel_id", "root_message_id")
                )
            ):
                raise SourceReferenceError("Teams chat message scope is invalid")
            return ["chat", row["chat_id"], row["message_id"]]
        if location not in {"channel-root", "channel-reply"}:
            raise SourceReferenceError("Teams channel message location is invalid")
        required = (row["team_id"], row["channel_id"], row["message_id"])
        if row["chat_id"] is not None or any(not value for value in required):
            raise SourceReferenceError("Teams channel message scope is invalid")
        if location == "channel-root":
            if row["root_message_id"] is not None:
                raise SourceReferenceError("Teams channel root scope is invalid")
            return [location, *required]
        if not row["root_message_id"]:
            raise SourceReferenceError("Teams channel reply scope is invalid")
        return [
            location,
            row["team_id"],
            row["channel_id"],
            row["root_message_id"],
            row["message_id"],
        ]

    def _bounded(
        self,
        table: str,
        where: str,
        params: tuple[object, ...],
        order: str,
        label: str,
    ) -> tuple[dict[str, Any], ...]:
        limit = self._catalog.limits.max_query_rows
        sql = f"SELECT * FROM {table} WHERE {where} ORDER BY {order} LIMIT ?"
        with closing(self._catalog._connect()) as connection:
            rows = connection.execute(sql, (*params, limit + 1)).fetchall()
        if len(rows) > limit:
            raise SourceReferenceError(
                f"Teams {label} inventory exceeds configured query bound"
            )
        return tuple(dict(row) for row in rows)

    def _topology(self, selected: TeamsMessageSelection) -> tuple[dict[str, Any], ...]:
        if selected.location == "chat":
            where = (
                "source_id = ? AND ((resource_kind IN ('chat', 'chat-member') "
                "AND json_extract(scope_key, '$[1]') = ?) OR "
                "(resource_kind = 'pin' AND json_extract(scope_key, '$[1]') = ? "
                "AND json_extract(scope_key, '$[2]') = ?))"
            )
            params = (
                selected.source_id,
                selected.chat_id,
                selected.chat_id,
                selected.message_id,
            )
        else:
            where = (
                "source_id = ? AND ((resource_kind IN ('team', 'team-membership') "
                "AND json_extract(scope_key, '$[1]') = ?) OR "
                "(resource_kind IN "
                "('channel', 'shared-with-team', 'channel-membership') "
                "AND json_extract(scope_key, '$[1]') = ? "
                "AND json_extract(scope_key, '$[2]') = ?))"
            )
            params = (
                selected.source_id,
                selected.team_id,
                selected.team_id,
                selected.channel_id,
            )
        return self._bounded(
            "teams_topology_observations",
            where,
            params,
            "observed_at, observation_id",
            "topology",
        )

    def _coverage(self, selected: TeamsMessageSelection) -> tuple[dict[str, Any], ...]:
        canonical = (
            "source_id = ? AND json_extract(scope_key, '$[0]') = 'coverage' "
            "AND json_extract(scope_key, '$[1]') = scope_kind AND "
        )
        if selected.location == "chat":
            where = canonical + (
                "scope_kind IN ('chat', 'chat-messages') "
                "AND json_array_length(scope_key) = 3 "
                "AND json_extract(scope_key, '$[2]') = ?"
            )
            params = (selected.source_id, selected.chat_id)
        else:
            where = canonical + (
                "((scope_kind = 'team' AND json_array_length(scope_key) = 3 "
                "AND json_extract(scope_key, '$[2]') = ?) OR "
                "(scope_kind = 'channel' "
                "AND json_array_length(scope_key) IN (4, 5) "
                "AND json_extract(scope_key, '$[2]') = ? "
                "AND json_extract(scope_key, '$[3]') = ?) OR "
                "(scope_kind IN ('channel-resource-link', 'channel-messages') "
                "AND json_array_length(scope_key) = 4 "
                "AND json_extract(scope_key, '$[2]') = ? "
                "AND json_extract(scope_key, '$[3]') = ?))"
            )
            params = (
                selected.source_id,
                selected.team_id,
                selected.team_id,
                selected.channel_id,
                selected.team_id,
                selected.channel_id,
            )
        return self._bounded(
            "teams_coverage_observations",
            where,
            params,
            "observed_at, observation_id",
            "coverage",
        )

    def _reply_target(self, selected: TeamsMessageSelection) -> VersionRef | None:
        if selected.location != "channel-reply":
            return None
        rows = self._bounded(
            "teams_message_observations",
            "source_id = ? AND location = 'channel-root' AND team_id = ? "
            "AND channel_id = ? AND message_id = ? AND observed_at <= ?",
            (
                selected.source_id,
                selected.team_id,
                selected.channel_id,
                selected.root_message_id,
                selected.observed_at,
            ),
            "observed_at DESC, observation_id DESC",
            "reply target",
        )
        return None if not rows else self._version(_CHANNEL, rows[0])


__all__ = [
    "TeamsCatalogQueries",
    "TeamsComponentRows",
    "TeamsMessageSelection",
    "decode_json",
    "is_teams_source_type",
    "scope_digest",
]

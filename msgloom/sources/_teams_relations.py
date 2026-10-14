"""Resolve Teams source-native message-reference relationships from saved A1 facts."""

from __future__ import annotations

import json
from contextlib import closing
from typing import Any

from msgloom.contracts import Limitation, VersionRef
from msgloom.preparation.records import NativeRelationship, PreparedSourceType
from msgloom.sources._catalog import ReadOnlyCatalog, encode_parts
from msgloom.sources._teams_catalog import TeamsMessageSelection, decode_json
from msgloom.sources.models import SourceReferenceError


def _message_reference_id(raw: dict[str, Any]) -> str | None:
    """Decode one provider messageReference without widening its semantics."""
    content = raw.get("content")
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return None
    if not isinstance(content, dict):
        return None
    message_id = content.get("messageId")
    return message_id if isinstance(message_id, str) and message_id else None


def _candidate(selected: TeamsMessageSelection, message_id: str) -> VersionRef:
    if selected.chat_id is None:
        raise SourceReferenceError("Teams chat relation lacks chat identity")
    return VersionRef(
        "teams_chat_message_candidate",
        encode_parts(selected.source_id, "chat", selected.chat_id, message_id),
        "candidate",
    )


def _exact_target(
    catalog: ReadOnlyCatalog,
    selected: TeamsMessageSelection,
    message_id: str,
) -> VersionRef | None:
    """Resolve the newest target capture already observable at reply capture time."""
    if selected.chat_id is None:
        return None
    limit = catalog.limits.max_query_rows
    with closing(catalog._connect()) as connection:
        rows = connection.execute(
            "SELECT * FROM teams_message_observations "
            "WHERE source_id=? AND location='chat' AND chat_id=? AND message_id=? "
            "AND observed_at<=? ORDER BY observed_at DESC, observation_id DESC LIMIT ?",
            (
                selected.source_id,
                selected.chat_id,
                message_id,
                selected.observed_at,
                limit + 1,
            ),
        ).fetchall()
    if len(rows) > limit:
        raise SourceReferenceError("Teams message-reference target query exceeds bound")
    if not rows:
        return None
    row = rows[0]
    return VersionRef(
        PreparedSourceType.TEAMS_CHAT_MESSAGE.value,
        encode_parts(selected.source_id, "chat", selected.chat_id, message_id),
        encode_parts(str(row["observation_id"]), row["evidence_id"]),
    )


def message_reference_relationships(
    catalog: ReadOnlyCatalog,
    selected: TeamsMessageSelection,
    attachments: tuple[dict[str, Any], ...],
) -> tuple[tuple[NativeRelationship, ...], tuple[Limitation, ...]]:
    """Preserve every chat messageReference and confirm only saved exact targets."""
    if selected.location != "chat":
        return (), ()
    relationships: list[NativeRelationship] = []
    limitations: list[Limitation] = []
    for row in attachments:
        if row.get("kind") != "message-reference":
            continue
        raw = decode_json(row.get("raw"), dict, "attachment raw")
        message_id = _message_reference_id(raw)
        if message_id is None:
            limitations.append(
                Limitation(
                    "teams-message-reference-invalid",
                    "A saved Teams messageReference has no valid message identity.",
                )
            )
            continue
        relationships.append(
            NativeRelationship(
                kind="teams_chat_message_reference",
                target=_candidate(selected, message_id),
            )
        )
        target = _exact_target(catalog, selected, message_id)
        if target is None:
            limitations.append(
                Limitation(
                    "teams-message-reference-target-unavailable",
                    "The referenced Teams chat message was not saved before this capture.",
                )
            )
            continue
        relationships.append(
            NativeRelationship(kind="teams_chat_reply_to", target=target)
        )
    return tuple(relationships), tuple(limitations)


__all__ = ["message_reference_relationships"]

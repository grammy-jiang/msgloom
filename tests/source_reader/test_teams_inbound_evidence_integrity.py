"""Require Teams saved history to verify actual inbound notification bytes."""

import asyncio
import hashlib
import sqlite3
from pathlib import Path

import pytest

from msgloom.sources import SavedSourceReader, SavedSourceReaderConfig
from msgloom.sources.models import SourceEvidenceError
from tests.source_reader.test_teams_saved_history import _add_history
from tests.source_reader.test_teams_saved_source import _build_fixture


@pytest.mark.parametrize(
    ("evidence_id", "origin", "method"),
    (
        ("delete", "inbound-webhook", "POST"),
        ("gap-chat", "inbound-webhook", "POST"),
        ("gap-chat", "local-gap", "LOCAL"),
    ),
)
def test_saved_notification_history_checks_inbound_bytes(
    tmp_path: Path, evidence_id: str, origin: str, method: str
) -> None:
    """An intact empty response cannot authenticate a changed inbound request."""
    fixture = _build_fixture(tmp_path)
    _add_history(fixture)
    with sqlite3.connect(fixture.database) as connection:
        path, digest, size = connection.execute(
            "SELECT response_body_path, response_body_sha256, response_body_bytes "
            "FROM raw_http_evidence WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()
        request_path = Path(path)
        empty = fixture.evidence_root / "inbound-empty-response.bin"
        empty.write_bytes(b"")
        connection.execute(
            "UPDATE raw_http_evidence SET origin = ?, request_method = ?, "
            "request_body_path = ?, request_body_sha256 = ?, request_body_bytes = ?, "
            "response_url = NULL, response_status = NULL, response_headers = ?, "
            "response_body_path = ?, response_body_sha256 = ?, response_body_bytes = 0 "
            "WHERE evidence_id = ?",
            (
                origin,
                method,
                str(request_path),
                digest,
                size,
                "{}",
                str(empty),
                hashlib.sha256(b"").hexdigest(),
                evidence_id,
            ),
        )

    async def exercise() -> None:
        reader = SavedSourceReader(
            SavedSourceReaderConfig(
                catalog_path=fixture.database, evidence_roots=(fixture.evidence_root,)
            )
        )
        try:
            before = await reader.read(fixture.chat_a)
            if before.body is None or before.body.content != "before edit":
                pytest.fail("Valid request history changed the earlier message body")
            if "teams-history-incomplete" not in {
                limitation.code for limitation in before.limitations
            }:
                pytest.fail("Saved gap lost its incomplete-history limitation")
            request_path.write_bytes(b"altered notification or gap")
            with pytest.raises(SourceEvidenceError):
                await reader.read(fixture.chat_a)
        finally:
            await reader.close()

    asyncio.run(exercise())

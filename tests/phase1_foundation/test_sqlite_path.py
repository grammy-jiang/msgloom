"""Verify that persistence opens the exact file a SQLite URL names."""

from __future__ import annotations

import asyncio
import stat
from pathlib import Path
from urllib.parse import quote

import pytest
from sqlalchemy.engine import URL

from msgloom.persistence import Phase1Persistence, sqlite_file_path

RESERVED = "phase1?reserved #%.sqlite3"


def _uri(path: Path, **query: str) -> str:
    return URL.create(
        "sqlite",
        database=f"file:{quote(str(path), safe='/')}",
        query={"uri": "true", **query},
    ).render_as_string(hide_password=False)


def test_plain_and_uri_urls_name_the_same_file(tmp_path: Path) -> None:
    """Plain and URI-form URLs resolve to the configured file identity."""
    exact = tmp_path / "state" / RESERVED
    if sqlite_file_path(f"sqlite:///{tmp_path / 'plain.sqlite3'}") != (
        tmp_path / "plain.sqlite3"
    ):
        pytest.fail("plain SQLite URL changed its file path")
    if sqlite_file_path(_uri(exact)) != exact:
        pytest.fail("URI-form SQLite URL lost reserved filename characters")
    localhost = f"sqlite:///file://localhost{quote(str(exact), safe='/')}?uri=true"
    if sqlite_file_path(localhost) != exact:
        pytest.fail("SQLite localhost URI authority was not accepted")


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://localhost/phase1",
        "sqlite://",
        "sqlite:///:memory:",
        "sqlite:///file:memdb?uri=true&mode=memory",
        "sqlite:///relative.sqlite3?uri=true",
        "sqlite:///file://remote/tmp/phase1.sqlite3?uri=true",
        "sqlite:///file:?uri=true",
        "sqlite:///file:%00?uri=true",
    ],
)
def test_non_file_or_malformed_urls_are_rejected(url: str) -> None:
    """Only a durable local file database is accepted."""
    with pytest.raises(ValueError):
        sqlite_file_path(url)


def test_uri_database_opens_exact_path_without_cwd_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Persistence creates only the real parent and never a relative file: tree."""
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    exact = tmp_path / "state" / RESERVED

    async def exercise() -> None:
        persistence = await Phase1Persistence.open(_uri(exact))
        await persistence.close()

    asyncio.run(exercise())
    if not exact.is_file():
        pytest.fail("URI-form persistence did not create the exact database file")
    if stat.S_IMODE(exact.parent.stat().st_mode) != 0o700:
        pytest.fail("database parent directory is not owner-only")
    if stat.S_IMODE(exact.stat().st_mode) != 0o600:
        pytest.fail("database file is not owner-only")
    if any(workdir.iterdir()):
        pytest.fail("URI-form persistence created paths in the working directory")
    if (tmp_path / "state" / "phase1").exists():
        pytest.fail("reserved '?' was treated as a URI query delimiter")

"""Resolve the file that a SQLite persistence URL names."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote

from sqlalchemy.engine import make_url
from sqlalchemy.util import asbool


def sqlite_file_path(database_url: str) -> Path:
    """
    Return the filesystem path named by a file-backed SQLite URL.

    A plain ``sqlite:///path`` URL names ``path`` directly. When the URL query
    sets ``uri`` true, SQLAlchemy passes the database component to SQLite as a
    URI filename. The path is then the percent-decoded ``file:`` component
    without its fragment, and an authority must be empty or ``localhost`` as
    SQLite requires. The ``uri`` flag uses SQLAlchemy's own boolean coercion,
    so this function and the driver always agree on the file identity.

    :raises ValueError: for a non-SQLite backend, an in-memory database, or a
        malformed URI filename.
    """
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        raise ValueError("Phase 1 persistence currently requires SQLite")
    database = url.database
    if not database or database == ":memory:":
        raise ValueError("Phase 1 durable persistence requires a file database")
    if not asbool(url.query.get("uri", False)):
        return Path(database)
    if url.query.get("mode") == "memory":
        raise ValueError("Phase 1 durable persistence requires a file database")
    if not database.startswith("file:"):
        raise ValueError("SQLite URI database must use the file scheme")
    target = database.removeprefix("file:").split("#", 1)[0]
    if target.startswith("//"):
        authority, slash, rest = target[2:].partition("/")
        if authority not in ("", "localhost") or not slash:
            raise ValueError("SQLite URI database authority is invalid")
        target = "/" + rest
    path = unquote(target)
    if not path or "\x00" in path:
        raise ValueError("SQLite URI database path is invalid")
    return Path(path)

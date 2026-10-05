"""Mark the exact release-entry SQL boundary in qualification subprocesses."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import Engine, event

_MARKER_ENV = "MSGLOOM_QUALIFICATION_RELEASE_MARKER"
_RELEASE_INSERT = "insert into acquisition_release_entries"


@event.listens_for(Engine, "before_cursor_execute")
def _mark_release_entry_insert(
    _connection,
    _cursor,
    statement,
    _parameters,
    _context,
    _executemany,
) -> None:
    """
    Persist proof before SQLite executes the fixture-owned failing insert.
    """
    marker = os.environ.get(_MARKER_ENV)
    if not marker:
        return
    normalized = " ".join(statement.lower().split())
    if _RELEASE_INSERT not in normalized:
        return
    Path(marker).write_text(statement)

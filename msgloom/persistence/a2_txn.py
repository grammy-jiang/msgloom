"""
Best-effort rollback shared by the A2 research SQLite transaction helpers.

CANDIDATE/RESEARCH. The helper serves :mod:`msgloom.persistence.a2_schema`
and :mod:`msgloom.persistence.a2_sqlite_store`. It is used on every failure
path of a transaction, including a failed ``COMMIT`` and a
``BaseException`` such as ``KeyboardInterrupt``.

Failure handling: a rollback must never replace the error that caused it.
The helper therefore swallows every ``Exception`` raised while it checks or
rolls back, for example when the connection is already closed or SQLite
already ended the transaction. A ``BaseException`` raised by the rollback
itself still propagates, because the process asked to stop.
"""

from __future__ import annotations

import sqlite3


def rollback_quietly(connection: sqlite3.Connection) -> None:
    """
    Roll back an open transaction and hide any secondary error.

    Does nothing when no transaction is open. The caller re-raises its own
    original exception after this call returns.
    """
    try:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
    except Exception:  # noqa: BLE001 - must not mask the original error
        return

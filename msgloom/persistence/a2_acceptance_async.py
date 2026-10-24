"""
Awaited facade for accepted-result writes (C0-12c).

CANDIDATE/RESEARCH. Nothing here runs against a real database. Tests use
disposable files under ``tmp_path``.

:class:`AcceptanceAsync` sends :func:`accept_result` and :func:`get_accepted`
through :meth:`Phase1Persistence.run_bounded`. That public method owns the
worker slot limit, the cancel drain and the close accounting. This module
adds no semaphore, no thread start and no access to private attributes.

Ownership: the facade holds a database path, never a connection. SQLite
connections belong to the thread that creates them. Each call therefore
opens :func:`connect_existing` inside the worker operation, runs one
function and closes the connection in ``finally``. No connection crosses a
thread.

Cancellation: the caller waits until the worker thread ends. The
transaction of :func:`accept_result` then is fully committed or fully rolled
back. A cancelled caller reads the row back, or replays the same receipt. A
replay of an identical receipt is idempotent.

Failure handling: errors from :func:`accept_result` propagate unchanged.
``close`` stays on :class:`Phase1Persistence`. After it starts, a new call
raises :exc:`RuntimeError` before it opens any connection.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path

from msgloom.a2_kedro.contracts.identity import StageIdentity
from msgloom.persistence.a2_acceptance_models import AcceptedStage
from msgloom.persistence.a2_schema import connect_existing
from msgloom.persistence.a2_store import (
    Accepted,
    PublisherReceipt,
    accept_result,
    get_accepted,
)
from msgloom.persistence.async_store import Phase1Persistence


def _accept_once(
    path: Path, identity: StageIdentity, receipt: PublisherReceipt
) -> Accepted:
    """Open, accept and close inside one worker thread."""
    connection = connect_existing(path)
    try:
        return accept_result(connection, identity, receipt)
    finally:
        connection.close()


def _read_once(path: Path, logical_key: str) -> AcceptedStage | None:
    """Open, read one verified record and close inside one worker thread."""
    connection = connect_existing(path)
    try:
        return get_accepted(connection, logical_key)
    finally:
        connection.close()


class AcceptanceAsync:
    """Await accepted-result writes through the shared persistence gate."""

    def __init__(self, persistence: Phase1Persistence, database_path: Path) -> None:
        self._persistence = persistence
        self._path = database_path

    async def accept(
        self, identity: StageIdentity, receipt: PublisherReceipt
    ) -> Accepted:
        """
        Accept one published stage; see :func:`accept_result` for outcomes.

        Raises :exc:`RuntimeError` when persistence is closing or closed.
        """
        return await self._persistence.run_bounded(
            partial(_accept_once, self._path, identity, receipt)
        )

    async def get(self, logical_key: str) -> AcceptedStage | None:
        """Return the verified stored record for ``logical_key``, if any."""
        return await self._persistence.run_bounded(
            partial(_read_once, self._path, logical_key)
        )

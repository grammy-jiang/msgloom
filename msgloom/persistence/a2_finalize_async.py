"""
Awaited facade for the version 2 Workset finalizer (C0-14e).

CANDIDATE/RESEARCH. Nothing here runs against a real database. Tests use
disposable files under ``tmp_path``.

:class:`FinalizeAsync` sends :func:`finalize_a2_intake_workset_v2` through
:meth:`Phase1Persistence.run_bounded`. That public method owns the worker
slot limit, the cancel drain and the close accounting. This module adds no
semaphore, no thread start and no access to private attributes.

Ownership: the facade holds a database path and a receipt store root, never
a connection or a store. SQLite connections belong to the thread that
creates them. Each call therefore builds its :class:`ReceiptStore` and opens
:func:`connect_existing` inside the worker operation, runs the finalizer
once and closes the connection in ``finally``. No handle crosses a thread.

Cancellation: the caller waits until the worker thread ends. The row then
is fully terminal with its proof file, or unchanged (the finalizer rolls
back every failure before ``COMMIT``). A cancelled caller reads the row
back, or replays the identical request. A replay of a request that already
finished returns ``replayed``. A replay after a rollback returns
``finalized``. A proof file left by a failed ``COMMIT`` is the exact proof
of the same receipt, so the retry accepts it. When the worker fails while
the caller waits, the caller sees that error instead of the cancellation.

Failure handling: errors from the finalizer propagate unchanged
(:exc:`A2FinalizeError`, :exc:`A2FinalizeConflict`, :exc:`A2ReceiptError`).
They carry fixed reason codes and never carry a value, a path or record
text. ``close`` stays on :class:`Phase1Persistence`. After it starts, a new
call raises :exc:`RuntimeError` before it opens any connection or touches
any file.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path

from msgloom.persistence.a2_receipt_store import ReceiptStore
from msgloom.persistence.a2_schema import connect_existing
from msgloom.persistence.a2_workset_finalize import (
    FinalizeRequest,
    FinalizeResult,
    finalize_a2_intake_workset_v2,
)
from msgloom.persistence.async_store import Phase1Persistence


def _finalize_once(path: Path, root: Path, request: FinalizeRequest) -> FinalizeResult:
    """Build the store, open, finalize and close inside one worker thread."""
    store = ReceiptStore(root)
    connection = connect_existing(path)
    try:
        return finalize_a2_intake_workset_v2(connection, store, request)
    finally:
        connection.close()


class FinalizeAsync:
    """Await v2 Workset finalization through the shared persistence gate."""

    def __init__(
        self, persistence: Phase1Persistence, database_path: Path, store_root: Path
    ) -> None:
        self._persistence = persistence
        self._path = database_path
        self._root = store_root

    async def finalize(self, request: FinalizeRequest) -> FinalizeResult:
        """
        Finish one pending Workset; see :func:`finalize_a2_intake_workset_v2`.

        Returns ``finalized`` or ``replayed``. Raises :exc:`RuntimeError`
        when persistence is closing or closed.
        """
        return await self._persistence.run_bounded(
            partial(_finalize_once, self._path, self._root, request)
        )

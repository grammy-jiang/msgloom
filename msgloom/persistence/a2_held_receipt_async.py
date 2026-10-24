"""
Awaited facades for held-index and receipt-store operations (C0-13a).

CANDIDATE/RESEARCH. Nothing here runs against a real database. Tests use
disposable files under ``tmp_path``.

:class:`HeldAsync` wraps the held-index functions of
:mod:`msgloom.persistence.a2_held_store`. :class:`ReceiptAsync` wraps the
methods of :class:`msgloom.persistence.a2_receipt_store.ReceiptStore`. Both
send each call through :meth:`Phase1Persistence.run_bounded`. That public
method owns the worker slot limit, the cancel drain and the close
accounting. This module adds no semaphore, no thread start and no access
to private attributes.

Wrapped held operations: ``put_held``, ``put_many``, ``get_held``,
``list_held`` and ``held_status``. :func:`ensure_held_index` is a DDL step
for an operator and is not wrapped.

Wrapped receipt operations: ``put_receipt_proof``, ``get_receipt_proof``,
``claim_history`` and ``append_claim``.

Ownership: a facade holds a path, never a connection or a store. SQLite
connections belong to the thread that creates them. Each held call opens
:func:`connect_existing` inside the worker operation, runs one function and
closes the connection in ``finally``. Each receipt call builds its
:class:`ReceiptStore` inside the worker operation. No handle crosses a
thread.

Cancellation: the caller waits until the worker thread ends. A held write
then is fully committed or fully rolled back. A receipt write is one
published file or no file. A cancelled caller reads the state back or
replays the same request. An identical replay is idempotent.

Failure handling: errors from the stores propagate unchanged. They carry
short reason codes and never carry a path or record text. ``close`` stays
on :class:`Phase1Persistence`. After it starts, a new call raises
:exc:`RuntimeError` before it opens any connection or touches any file.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import partial
from pathlib import Path

from msgloom.a2_kedro.contracts.held import HeldReason, InputDisposition
from msgloom.a2_kedro.contracts.receipt import CompletionReceipt
from msgloom.contracts import ResultRef
from msgloom.persistence.a2_acceptance_models import AcceptedStage
from msgloom.persistence.a2_held_store import (
    HeldCursor,
    HeldPage,
    HeldStatus,
    get_held,
    held_status,
    list_held,
    put_held,
    put_many,
)
from msgloom.persistence.a2_held_store import PutOutcome as HeldOutcome
from msgloom.persistence.a2_receipt_store import (
    ClaimEntry,
    ReceiptProof,
    ReceiptStore,
    StoredClaim,
)
from msgloom.persistence.a2_receipt_store import PutOutcome as ReceiptOutcome
from msgloom.persistence.a2_schema import connect_existing
from msgloom.persistence.async_store import Phase1Persistence


def _put_held_once(
    path: Path, workset: ResultRef, item: InputDisposition
) -> HeldOutcome:
    """Open, store one record and close inside one worker thread."""
    connection = connect_existing(path)
    try:
        return put_held(connection, workset, item)
    finally:
        connection.close()


def _put_many_once(
    path: Path, workset: ResultRef, items: tuple[InputDisposition, ...]
) -> tuple[HeldOutcome, ...]:
    """Open, store one all-or-nothing batch and close in one worker thread."""
    connection = connect_existing(path)
    try:
        return put_many(connection, workset, items)
    finally:
        connection.close()


def _get_held_once(
    path: Path, workset: ResultRef, workset_index: int
) -> InputDisposition | None:
    """Open, read one verified record and close inside one worker thread."""
    connection = connect_existing(path)
    try:
        return get_held(connection, workset, workset_index)
    finally:
        connection.close()


def _list_held_once(
    path: Path,
    workset: ResultRef,
    limit: int,
    after: HeldCursor | None,
    reason: HeldReason | None,
) -> HeldPage:
    """Open, read one bounded page and close inside one worker thread."""
    connection = connect_existing(path)
    try:
        return list_held(connection, workset, limit=limit, after=after, reason=reason)
    finally:
        connection.close()


def _status_once(path: Path, workset: ResultRef) -> HeldStatus:
    """Open, count by closed reason and close inside one worker thread."""
    connection = connect_existing(path)
    try:
        return held_status(connection, workset)
    finally:
        connection.close()


class HeldAsync:
    """Await held-index calls through the shared persistence gate."""

    def __init__(self, persistence: Phase1Persistence, database_path: Path) -> None:
        self._persistence = persistence
        self._path = database_path

    async def put(self, workset: ResultRef, item: InputDisposition) -> HeldOutcome:
        """
        Store one held record; an identical replay returns ``replayed``.

        Raises :exc:`RuntimeError` when persistence is closing or closed.
        """
        return await self._persistence.run_bounded(
            partial(_put_held_once, self._path, workset, item)
        )

    async def put_batch(
        self, workset: ResultRef, items: Sequence[InputDisposition]
    ) -> tuple[HeldOutcome, ...]:
        """Store a batch in one transaction: all rows or none."""
        return await self._persistence.run_bounded(
            partial(_put_many_once, self._path, workset, tuple(items))
        )

    async def get(
        self, workset: ResultRef, workset_index: int
    ) -> InputDisposition | None:
        """Return the verified record at ``workset_index``, if any."""
        return await self._persistence.run_bounded(
            partial(_get_held_once, self._path, workset, workset_index)
        )

    async def page(
        self,
        workset: ResultRef,
        *,
        limit: int,
        after: HeldCursor | None = None,
        reason: HeldReason | None = None,
    ) -> HeldPage:
        """Return one bounded page of closed rows; see :func:`list_held`."""
        return await self._persistence.run_bounded(
            partial(_list_held_once, self._path, workset, limit, after, reason)
        )

    async def status(self, workset: ResultRef) -> HeldStatus:
        """Return counts by closed reason and repair class. Never text."""
        return await self._persistence.run_bounded(
            partial(_status_once, self._path, workset)
        )


def _put_proof_once(
    root: Path,
    proof: ReceiptProof,
    receipt: CompletionReceipt,
    accepted: Mapping[str, AcceptedStage],
) -> ReceiptOutcome:
    """Build the store and write the proof inside one worker thread."""
    return ReceiptStore(root).put_receipt_proof(proof, receipt, accepted)


def _get_proof_once(root: Path, workset: ResultRef) -> ReceiptProof | None:
    """Build the store and read the proof inside one worker thread."""
    return ReceiptStore(root).get_receipt_proof(workset)


def _history_once(
    root: Path, workset: ResultRef, expected_head_sha256: str | None
) -> tuple[StoredClaim, ...]:
    """Build the store and read the claim chain inside one worker thread."""
    return ReceiptStore(root).claim_history(
        workset, expected_head_sha256=expected_head_sha256
    )


def _append_once(
    root: Path,
    workset: ResultRef,
    entry: ClaimEntry,
    expected_seq: int,
    expected_head_sha256: str | None,
) -> ReceiptOutcome:
    """Build the store and append one claim inside one worker thread."""
    return ReceiptStore(root).append_claim(
        workset, entry, expected_seq, expected_head_sha256=expected_head_sha256
    )


class ReceiptAsync:
    """Await receipt-proof and claim-history calls through the gate."""

    def __init__(self, persistence: Phase1Persistence, store_root: Path) -> None:
        self._persistence = persistence
        self._root = store_root

    async def put_proof(
        self,
        proof: ReceiptProof,
        receipt: CompletionReceipt,
        accepted: Mapping[str, AcceptedStage],
    ) -> ReceiptOutcome:
        """
        Verify and store one receipt proof; an identical replay replays.

        Raises :exc:`RuntimeError` when persistence is closing or closed.
        """
        return await self._persistence.run_bounded(
            partial(_put_proof_once, self._root, proof, receipt, accepted)
        )

    async def get_proof(self, workset: ResultRef) -> ReceiptProof | None:
        """Return the stored proof after its integrity check, if any."""
        return await self._persistence.run_bounded(
            partial(_get_proof_once, self._root, workset)
        )

    async def history(
        self, workset: ResultRef, *, expected_head_sha256: str | None = None
    ) -> tuple[StoredClaim, ...]:
        """Return the verified claim chain, oldest first."""
        return await self._persistence.run_bounded(
            partial(_history_once, self._root, workset, expected_head_sha256)
        )

    async def append(
        self,
        workset: ResultRef,
        entry: ClaimEntry,
        expected_seq: int,
        *,
        expected_head_sha256: str | None = None,
    ) -> ReceiptOutcome:
        """Append ``entry`` at ``expected_seq``; never rewrite history."""
        return await self._persistence.run_bounded(
            partial(
                _append_once,
                self._root,
                workset,
                entry,
                expected_seq,
                expected_head_sha256,
            )
        )

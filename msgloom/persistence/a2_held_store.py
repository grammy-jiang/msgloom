"""
Bounded, workset-scoped index of A2-held occurrences (C0-13).

CANDIDATE/RESEARCH. A held record says A2 could not prepare one exact
selected occurrence. The record contract is
:class:`msgloom.a2_kedro.contracts.held.InputDisposition`. This module
stores one row per ``(workset, workset_index)`` and answers bounded queries.
Nothing here runs against a real database. Tests use ``tmp_path`` files.

Pending schema integration: schema 5 (``a2_schema.py``) has no held-index
table, and that module is not edited here. The table
``a2_held_index_pending`` is therefore created only by the explicit,
idempotent :func:`ensure_held_index`. No store function creates it. The
function refuses a file that holds ``phase1_*`` tables unless the caller
sets ``pending_integration_ack``. It then also requires exact schema 5. The
table name has no ``phase1_`` prefix, so :func:`classify_schema` still
accepts the file. A later schema revision must move this table into
``a2_schema.py`` (see ``docs/notes/a2-v2-db-store.md``).

Queries: every function takes a workset ref. :func:`list_held` also takes a
hard row limit (1 to :data:`MAX_LIMIT`, never clamped) and an optional
keyset cursor bound to the workset. Rows sort by ``workset_index``, which is
unique inside a workset, so the order is deterministic and a page never
repeats or skips a row.

Writes: :func:`put_held` is idempotent. The same record replays. Another
record for the same index, or the same selection at another index, raises
:exc:`A2HeldConflict` and changes nothing. A batch is all or nothing.

Privacy: :func:`held_status` reads only closed columns and counts. It never
selects ``record_json`` or any version text, so it cannot return body or
identifier text. Errors carry short reason codes only.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    canonical_model_bytes,
    decode_canonical_json,
    sha256_hex,
)
from msgloom.a2_kedro.contracts.held import HeldReason, InputDisposition
from msgloom.contracts import ResultRef
from msgloom.persistence.a2_schema import hex64_check, require_schema5
from msgloom.persistence.a2_txn import rollback_quietly

PutOutcome = Literal["inserted", "replayed"]
TABLE = "a2_held_index_pending"
#: Largest page a caller may request. A larger value is refused.
MAX_LIMIT = 500
#: Largest batch for one atomic write.
MAX_BATCH = 1024
#: Largest stored record, so a row stays small.
MAX_HELD_RECORD_BYTES = 8 * 1024
_WORKSET = ("preparation_intake_workset", "1")
_REASONS = ", ".join(f"'{reason.value}'" for reason in HeldReason)

DDL = " ".join(
    f"""CREATE TABLE {TABLE} (
        workset_id TEXT NOT NULL CHECK (typeof(workset_id) = 'text'
            AND length(CAST(workset_id AS BLOB)) BETWEEN 1 AND 2048),
        workset_index INTEGER NOT NULL CHECK (typeof(workset_index) = 'integer'
            AND workset_index BETWEEN 0 AND 1023),
        selected_id TEXT NOT NULL CHECK (typeof(selected_id) = 'text'
            AND length(CAST(selected_id AS BLOB)) BETWEEN 1 AND 2048),
        selection_sha256 TEXT NOT NULL CHECK ({hex64_check("selection_sha256")}),
        reason TEXT NOT NULL CHECK (reason IN ({_REASONS})),
        repair_class TEXT NOT NULL CHECK (repair_class = 'operator_repair'),
        is_baseline INTEGER NOT NULL CHECK (is_baseline IN (0, 1)),
        record_sha256 TEXT NOT NULL CHECK ({hex64_check("record_sha256")}),
        record_json TEXT NOT NULL CHECK (typeof(record_json) = 'text'
            AND length(CAST(record_json AS BLOB))
            BETWEEN 1 AND {MAX_HELD_RECORD_BYTES}),
        PRIMARY KEY (workset_id, workset_index),
        UNIQUE (workset_id, selected_id)
    )""".split()
)


class A2HeldError(A2ContractError):
    """A held-index call was refused. ``reason`` is a short code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class A2HeldConflict(A2HeldError):
    """Another record holds the index or the selection. Names fields only."""

    def __init__(self, fields: tuple[str, ...]) -> None:
        super().__init__("held-conflict")
        self.fields = fields


@dataclass(frozen=True, slots=True)
class HeldCursor:
    """Keyset position: the last ``workset_index`` the caller has seen."""

    workset_id: str
    after_index: int


@dataclass(frozen=True, slots=True)
class HeldRow:
    """Closed columns of one held row. No record text, no version text."""

    workset_index: int
    selected_id: str
    selection_sha256: str
    reason: HeldReason
    repair_class: str
    is_baseline: bool


@dataclass(frozen=True, slots=True)
class HeldPage:
    """One bounded page. ``next_cursor`` is ``None`` on the last page."""

    rows: tuple[HeldRow, ...]
    next_cursor: HeldCursor | None


@dataclass(frozen=True, slots=True)
class HeldStatus:
    """Privacy-safe summary: closed reasons, repair classes and counts only."""

    total: int
    baseline: int
    incremental: int
    by_reason: tuple[tuple[str, int], ...]
    by_repair_class: tuple[tuple[str, int], ...]


def _workset_id(workset: ResultRef) -> str:
    if not isinstance(workset, ResultRef):
        raise A2HeldError("workset-ref-required")
    if (workset.kind, workset.schema_version) != _WORKSET:
        raise A2HeldError("workset-ref-invalid")
    return workset.result_id


def _checked(db: sqlite3.Connection) -> None:
    """Fail closed unless the pending table exists with the exact DDL."""
    try:
        row = db.execute(
            "SELECT sql FROM sqlite_schema WHERE type = 'table' AND name = ?",
            (TABLE,),
        ).fetchone()
    except sqlite3.Error:
        raise A2HeldError("database-error") from None
    if row is None:
        raise A2HeldError("held-index-missing")
    if " ".join(str(row[0]).split()) != DDL:
        raise A2HeldError("held-index-definition-mismatch")


@contextmanager
def _immediate(db: sqlite3.Connection) -> Iterator[None]:
    if db.in_transaction:
        raise A2HeldError("open-transaction")
    try:
        db.execute("BEGIN IMMEDIATE")
    except sqlite3.Error:
        raise A2HeldError("lock-failed") from None
    try:
        yield
    except sqlite3.Error:
        rollback_quietly(db)
        raise A2HeldError("database-error") from None
    except BaseException:
        rollback_quietly(db)
        raise
    try:
        db.execute("COMMIT")
    except sqlite3.Error:
        rollback_quietly(db)
        raise A2HeldError("commit-failed") from None
    except BaseException:
        rollback_quietly(db)
        raise


def ensure_held_index(
    db: sqlite3.Connection, *, pending_integration_ack: bool = False
) -> Literal["created", "present"]:
    """
    Create the pending held-index table once. Idempotent.

    PENDING SCHEMA INTEGRATION. A file with any ``phase1_*`` table is
    refused unless ``pending_integration_ack`` is true, and then it must be
    exact schema 5. An existing table must match :data:`DDL` exactly.
    """
    with _immediate(db):
        names = [
            str(row[0])
            for row in db.execute("SELECT name FROM sqlite_schema WHERE type = 'table'")
        ]
        if any(name.lower().startswith("phase1_") for name in names):
            if not pending_integration_ack:
                raise A2HeldError("phase1-database-refused")
            require_schema5(db)
        if TABLE in names:
            _checked(db)
            return "present"
        db.execute(DDL)
    return "created"


def _stored(workset_id: str, item: InputDisposition) -> tuple[object, ...]:
    data = canonical_model_bytes(item, max_bytes=MAX_HELD_RECORD_BYTES)
    return (
        workset_id,
        item.workset_index,
        item.selected.result_id,
        item.selection_sha256,
        item.reason.value,
        item.repair_class,
        int(item.entry is None),
        sha256_hex(data),
        data.decode(),
    )


def _differs(known: InputDisposition, proposed: InputDisposition) -> tuple[str, ...]:
    fields = type(known).model_fields
    return tuple(n for n in fields if getattr(known, n) != getattr(proposed, n))


def _load(row: tuple[str, str], key: tuple[str, int]) -> InputDisposition:
    try:
        data = row[1].encode()
        if sha256_hex(data) != row[0]:
            raise A2HeldError("stored-record-corrupt")
        decode_canonical_json(data, max_bytes=MAX_HELD_RECORD_BYTES)
        record = InputDisposition.model_validate_json(data)
    except ValueError:
        raise A2HeldError("stored-record-corrupt") from None
    if record.workset_index != key[1]:
        raise A2HeldError("stored-record-corrupt")
    return record


def _put_one(
    db: sqlite3.Connection, workset_id: str, item: InputDisposition
) -> PutOutcome:
    if not isinstance(item, InputDisposition):
        raise A2HeldError("disposition-required")
    row = _stored(workset_id, item)
    same_index = db.execute(
        f"SELECT record_sha256, record_json FROM {TABLE} "
        "WHERE workset_id = ? AND workset_index = ?",
        (workset_id, item.workset_index),
    ).fetchone()
    if same_index is not None:
        known = _load(same_index, (workset_id, item.workset_index))
        if same_index[0] == row[7]:
            return "replayed"
        raise A2HeldConflict(_differs(known, item) or ("record",))
    same_selection = db.execute(
        f"SELECT 1 FROM {TABLE} WHERE workset_id = ? AND selected_id = ?",
        (workset_id, item.selected.result_id),
    ).fetchone()
    if same_selection is not None:
        raise A2HeldConflict(("selected", "workset_index"))
    db.execute(f"INSERT INTO {TABLE} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", row)
    return "inserted"


def put_held(
    db: sqlite3.Connection, workset: ResultRef, item: InputDisposition
) -> PutOutcome:
    """
    Store one held record. An identical replay returns ``replayed``.

    Raises :exc:`A2HeldConflict` when another record holds the index or the
    selection. The stored row never changes.
    """
    return put_many(db, workset, (item,))[0]


def put_many(
    db: sqlite3.Connection, workset: ResultRef, items: Sequence[InputDisposition]
) -> tuple[PutOutcome, ...]:
    """Store up to :data:`MAX_BATCH` records in one all-or-nothing batch."""
    workset_id = _workset_id(workset)
    if not 1 <= len(items) <= MAX_BATCH:
        raise A2HeldError("batch-size")
    with _immediate(db):
        _checked(db)
        outcomes: list[PutOutcome] = []
        for item in items:
            outcomes.append(_put_one(db, workset_id, item))
    return tuple(outcomes)


def get_held(
    db: sqlite3.Connection, workset: ResultRef, workset_index: int
) -> InputDisposition | None:
    """Return the verified record at ``workset_index``, if any."""
    workset_id = _workset_id(workset)
    _checked(db)
    row = db.execute(
        f"SELECT record_sha256, record_json FROM {TABLE} "
        "WHERE workset_id = ? AND workset_index = ?",
        (workset_id, workset_index),
    ).fetchone()
    if row is None:
        return None
    return _load(row, (workset_id, workset_index))


def list_held(
    db: sqlite3.Connection,
    workset: ResultRef,
    *,
    limit: int,
    after: HeldCursor | None = None,
    reason: HeldReason | None = None,
) -> HeldPage:
    """
    Return one page of closed rows ordered by ``workset_index``.

    ``limit`` is required and must be 1 to :data:`MAX_LIMIT`. ``after`` must
    come from a page of the same workset. ``reason`` filters on one closed
    reason. The query reads ``limit + 1`` rows to find the next cursor.
    """
    workset_id = _workset_id(workset)
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise A2HeldError("limit-required")
    if not 1 <= limit <= MAX_LIMIT:
        raise A2HeldError("limit-out-of-range")
    start = -1
    if after is not None:
        if not isinstance(after, HeldCursor) or after.workset_id != workset_id:
            raise A2HeldError("cursor-foreign")
        if not -1 <= after.after_index <= 1023:
            raise A2HeldError("cursor-invalid")
        start = after.after_index
    _checked(db)
    where, args = "workset_id = ? AND workset_index > ?", [workset_id, start]
    if reason is not None:
        where += " AND reason = ?"
        args.append(HeldReason(reason).value)
    found = db.execute(
        "SELECT workset_index, selected_id, selection_sha256, reason, "
        f"repair_class, is_baseline FROM {TABLE} WHERE {where} "
        "ORDER BY workset_index LIMIT ?",
        (*args, limit + 1),
    ).fetchall()
    rows = tuple(
        HeldRow(r[0], r[1], r[2], HeldReason(r[3]), r[4], bool(r[5]))
        for r in found[:limit]
    )
    more = len(found) > limit
    cursor = HeldCursor(workset_id, rows[-1].workset_index) if more else None
    return HeldPage(rows, cursor)


def held_status(db: sqlite3.Connection, workset: ResultRef) -> HeldStatus:
    """
    Return counts by closed reason and repair class. Never returns text.

    The query selects only the closed ``reason`` and ``repair_class``
    columns, the baseline flag and a count. At most
    ``len(HeldReason) * 2`` groups come back, so the result is bounded.
    """
    workset_id = _workset_id(workset)
    _checked(db)
    groups = db.execute(
        f"SELECT reason, repair_class, is_baseline, count(*) FROM {TABLE} "
        "WHERE workset_id = ? GROUP BY reason, repair_class, is_baseline "
        "ORDER BY reason, repair_class, is_baseline",
        (workset_id,),
    ).fetchall()
    reasons: dict[str, int] = {}
    classes: dict[str, int] = {}
    baseline = 0
    for reason, repair, is_baseline, number in groups:
        reasons[reason] = reasons.get(reason, 0) + number
        classes[repair] = classes.get(repair, 0) + number
        baseline += number if is_baseline else 0
    total = sum(reasons.values())
    return HeldStatus(
        total=total,
        baseline=baseline,
        incremental=total - baseline,
        by_reason=tuple(sorted(reasons.items())),
        by_repair_class=tuple(sorted(classes.items())),
    )

"""
I0-02 ``scope-status`` command for A2 v2 (CANDIDATE/RESEARCH).

``--db PATH --workset ID --expected N`` (plus ``--expects-batch`` and
``--expected-intake-held N``) opens the ``a2c0_*`` research store with
SQLite URI ``mode=ro`` and maps the last receipt of the workset through the
pure C0-18 layer in :mod:`msgloom.cli.a2_scope_status`. That layer stays
free of storage, files and environment. This module holds the only I/O.

The command prints one JSON line with a fixed key set (:func:`render_status`).
Scope hash: digest of the workset id. Cursor digest: receipt
``acceptance_index_sha256``. Pending: ``incomplete + missing``. Held:
``held + intake_held``. Exit 0 is ok for any state, 2 is a usage error and
3 is a missing or unreadable store (basename only). A first argument that
does not start with ``--`` keeps the older ``STATE`` table mode.

CANDIDATE/RESEARCH: nothing calls this module yet.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from msgloom.a2_kedro.contracts.codec import (
    decode_model_bytes,
    domain_sha256,
    sha256_hex,
)
from msgloom.a2_kedro.contracts.receipt import CompletionReceipt
from msgloom.cli.a2_scope_status import (
    EXIT_INVALID,
    ScopeInputError,
    ScopeProgress,
    ScopeState,
    ScopeStatus,
    ScopeStatusError,
    status_from_error,
    status_from_receipt,
)
from msgloom.cli.a2_scope_status import main as table_main
from msgloom.contracts import ResultRef
from msgloom.persistence.a2_sqlite_ddl import MARKER

EXIT_STORE = 3
_WORKSET_ID = re.compile(r"^[a-z][a-z-]{0,31}:[0-9a-f]{64}$")
_BASENAME = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class ScopeStoreError(ScopeStatusError):
    """The research store is missing, foreign, corrupt or unreadable."""

    message = "scope store is unavailable"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ScopeInputError  # never echo an argument value


def _parse(argv: Sequence[str]) -> argparse.Namespace:
    parser = _Parser(prog="scope-status", add_help=False, allow_abbrev=False)
    parser.add_argument("--db", required=True)
    parser.add_argument("--workset", required=True)
    parser.add_argument("--expected", required=True, type=int)
    parser.add_argument("--expected-intake-held", type=int, default=0)
    parser.add_argument("--expects-batch", action="store_true")
    args = parser.parse_args(argv)
    if not _WORKSET_ID.fullmatch(args.workset):
        raise ScopeInputError
    return args


def render_status(
    status: ScopeStatus, receipt: CompletionReceipt | None, digest: str | None
) -> dict[str, str | int | None]:
    """
    Return the allowlisted output fields for ``status``.

    The keys are the whole output allowlist. Each value is read by name, so
    an unknown attribute of a subclass or receipt is never copied.
    """
    if not isinstance(status, ScopeStatus):
        raise ScopeInputError
    return {
        "scope_hash": status.scope_id,
        "state": status.state.value,
        "cursor_digest": receipt.acceptance_index_sha256 if receipt else None,
        "pending_count": status.incomplete + status.missing,
        "held_count": status.held + status.intake_held,
        "last_receipt": digest,
        "last_receipt_status": receipt.status.value if receipt else None,
    }


def _last_receipt(path: Path, workset: str) -> tuple[CompletionReceipt, str] | None:
    # The URI ``mode=ro`` makes SQLite refuse every write on this handle.
    try:
        if not path.is_file():
            raise ScopeStoreError
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            meta = db.execute("SELECT value FROM a2c0_meta WHERE key = 'marker'")
            if (row := meta.fetchone()) is None or row[0] != MARKER:
                raise ScopeStoreError
            row = db.execute(
                "SELECT receipt_sha256, receipt_json FROM a2c0_receipt "
                "WHERE workset_id = ? ORDER BY rowid DESC LIMIT 1",
                (workset,),
            ).fetchone()
        finally:
            db.close()
        if row is None:
            return None
        data = row[1].encode()
        if sha256_hex(data) != row[0]:
            raise ScopeStoreError
        return decode_model_bytes(CompletionReceipt, data, max_bytes=1 << 20), row[0]
    except (sqlite3.Error, ValueError) as error:  # not a typed error
        raise ScopeStoreError from error


def scope_status(args: argparse.Namespace) -> dict[str, str | int | None]:
    """Return the allowlisted fields for the scope that ``args`` names."""
    scope_id = domain_sha256("a2.scope-status.scope@1", args.workset)
    expected = args.expected
    try:
        progress = ScopeProgress(
            scope_id=scope_id,
            workset=ResultRef(args.workset, "preparation_intake_workset", "1"),
            expected_occurrences=expected,
            expects_batch=args.expects_batch,
            expected_intake_held=args.expected_intake_held,
        )
    except ValueError as error:  # includes pydantic validation errors
        raise ScopeInputError from error
    if (found := _last_receipt(Path(args.db), args.workset)) is None:
        none = ScopeStatus(
            scope_id=scope_id,
            state=ScopeState.INCOMPLETE,
            occurrences=expected,
            missing=expected,
            batches=int(args.expects_batch),
            limitation_codes=("occurrence_missing",),
        )
        return render_status(none, None, None)
    try:
        status = status_from_receipt(progress, found[0])
    except ScopeStatusError as error:
        status = status_from_error(scope_id, error)  # no state: input error
    return render_status(status, *found)


def _fail(text: str, code: int) -> int:
    sys.stderr.write(f"a2 scope status: {text}\n")
    return code


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run ``scope-status`` and return its exit code (0, 2 or 3).

    Arguments that do not start with ``--`` keep the older table mode: one
    state name prints its table line and code, anything else returns 2.
    Otherwise one store is read read-only and one JSON line is printed.
    Error text is fixed. It holds no argument value, id or stored value,
    only a safe basename of the store file.
    """
    tokens = list(sys.argv[1:] if argv is None else argv)
    if not tokens or not tokens[0].startswith("--"):
        return table_main(tokens)
    try:
        args = _parse(tokens)
    except ScopeStatusError:
        return _fail("usage error", EXIT_INVALID)
    try:
        fields = scope_status(args)
    except ScopeStoreError:
        name = Path(args.db).name
        label = name if _BASENAME.fullmatch(name) else "store"
        return _fail(f"store unavailable: {label}", EXIT_STORE)
    except ScopeStatusError:
        return _fail("usage error", EXIT_INVALID)
    sys.stdout.write(json.dumps(fields) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

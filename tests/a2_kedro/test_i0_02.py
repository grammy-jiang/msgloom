"""I0-02: ``scope-status`` CLI. Every database lives in tmp_path."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import canonical_model_bytes, sha256_hex
from msgloom.a2_kedro.contracts.receipt import CompletionReceipt
from msgloom.cli import a2_scope_status_cli as a2_scope_status
from msgloom.cli.a2_scope_status import ScopeState, ScopeStatus
from msgloom.cli.a2_scope_status_cli import main, render_status
from msgloom.contracts import Limitation, TerminalStatus
from msgloom.persistence.a2_sqlite_store import A2ResearchStore
from tests.a2_kedro.helpers import WORKSET_REF, check, workset
from tests.a2_kedro.helpers_c0_18 import (
    SCOPE,
    complete_receipt,
    held_ref,
    open_root,
    prepared_ref,
    receipt,
    terminal,
)

INCOMPLETE = TerminalStatus.INCOMPLETE
KEYS = {
    "scope_hash",
    "state",
    "cursor_digest",
    "pending_count",
    "held_count",
    "last_receipt",
    "last_receipt_status",
}
EMAIL = "alice.canary@example.com"
SUBJECT = "Subject: Q3 salary review for Bob"
CANARIES = (EMAIL, SUBJECT, "Bob", "salary", "example.com")


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "a2.sqlite"
    A2ResearchStore.create(path).close()
    return path


def add_receipt(path: Path, value: CompletionReceipt) -> str:
    """Insert ``value`` directly (no proofs) and return its row digest."""
    data = canonical_model_bytes(value, max_bytes=1 << 20)
    digest = sha256_hex(data)
    with sqlite3.connect(path) as con:
        con.execute(
            "INSERT INTO a2c0_receipt (workset_id, policy_version, status, "
            "receipt_sha256, receipt_json) VALUES (?, ?, ?, ?, ?)",
            (
                value.workset.result_id,
                value.policy_version,
                value.status.value,
                digest,
                data.decode(),
            ),
        )
    con.close()
    return digest


def argv(path: Path, expected: int = 2, *more: str) -> list[str]:
    ws = WORKSET_REF.result_id
    return ["--db", str(path), "--workset", ws, "--expected", str(expected), *more]


def run(capsys: pytest.CaptureFixture[str], args: list[str]) -> tuple[int, str, str]:
    code = main(args)
    out = capsys.readouterr()
    return code, out.out, out.err


def no_canary(*texts: str) -> None:
    for text in texts:
        for canary in CANARIES:
            check(canary not in text, "canary text reached the output")


def test_happy_path_prints_exactly_the_allowlisted_keys(
    db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    value = complete_receipt()
    digest = add_receipt(db, value)
    code, out, err = run(capsys, argv(db))
    check(code == 0 and err == "", "exit 0 and empty stderr")
    check(out.count("\n") == 1, "one output line")
    fields = json.loads(out)
    check(set(fields) == KEYS, "exactly the allowlisted keys")
    check(fields["state"] == "complete", "state")
    check(fields["pending_count"] == 0 and fields["held_count"] == 0, "counts")
    check(fields["last_receipt"] == digest, "last receipt digest")
    check(fields["last_receipt_status"] == "complete", "last receipt status")
    check(fields["cursor_digest"] == value.acceptance_index_sha256, "cursor")
    check(fields["scope_hash"] != SCOPE, "scope hash is derived from the workset")
    check(len(fields["scope_hash"]) == 64, "scope hash is a digest")


def test_pending_and_held_counts(db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ws = workset(3)
    add_receipt(
        db,
        receipt(
            (
                terminal(ws, 0, prepared_ref("1")),
                terminal(ws, 1, held_ref("2"), INCOMPLETE),
            ),
            status=INCOMPLETE,
        ),
    )
    code, out, _ = run(capsys, argv(db, 3))
    fields = json.loads(out)
    check(code == 0, "an open scope still exits 0")
    check(fields["state"] == "held", "held state")
    check(fields["held_count"] == 1, "held count")
    check(fields["pending_count"] == 1, "one occurrence has no root yet")


def test_scope_without_receipt_is_all_pending(
    db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, err = run(capsys, argv(db, 4))
    fields = json.loads(out)
    check(code == 0 and err == "", "exit 0")
    check(set(fields) == KEYS, "same keys")
    check(fields["pending_count"] == 4 and fields["held_count"] == 0, "counts")
    check(fields["last_receipt"] is None, "no receipt")
    check(fields["cursor_digest"] is None, "no cursor")


def test_pii_canary_never_reaches_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / EMAIL.split("@")[0] / "a2.sqlite"
    path.parent.mkdir()
    A2ResearchStore.create(path).close()
    ws = workset(2)
    canary_root = open_root(ws, 0, (Limitation("partial", f"{EMAIL} {SUBJECT}"),))
    add_receipt(
        path,
        receipt(
            (canary_root, terminal(ws, 1, prepared_ref("2"))),
            status=INCOMPLETE,
            policy_version=f"policy {EMAIL} {SUBJECT}",
        ),
    )
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO a2c0_meta VALUES (?, ?)", (EMAIL, SUBJECT))
    con.close()
    code, out, err = run(capsys, argv(path))
    check(code == 0, "exit 0")
    no_canary(out, err)
    check(str(tmp_path) not in out + err, "no filesystem path in output")
    check(set(json.loads(out)) == KEYS, "allowlisted keys only")


def test_unknown_status_fields_are_not_printed(
    db: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Extra(ScopeStatus):
        contact: str = EMAIL
        subject: str = SUBJECT

    def fake(progress: Any, _receipt: Any) -> Extra:
        return Extra(scope_id=progress.scope_id, state=ScopeState.INCOMPLETE)

    value = complete_receipt()
    add_receipt(db, value)
    monkeypatch.setattr(a2_scope_status, "status_from_receipt", fake)
    code, out, err = run(capsys, argv(db))
    check(code == 0, "exit 0")
    no_canary(out, err)
    check(set(json.loads(out)) == KEYS, "allowlisted keys only")
    direct = render_status(
        Extra(scope_id=SCOPE, state=ScopeState.INCOMPLETE), value, "0" * 64
    )
    check(set(direct) == KEYS, "render_status keeps the allowlist")
    no_canary(json.dumps(direct))


def test_render_status_refuses_a_non_status() -> None:
    with pytest.raises(a2_scope_status.ScopeInputError):
        render_status({"state": "complete"}, None, None)  # type: ignore[arg-type]


def test_missing_store_exits_3_with_basename_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hidden = tmp_path / "bob@example.com-dir"
    code, out, err = run(capsys, argv(hidden / "gone.sqlite"))
    check(code == 3 and out == "", "exit 3 and empty stdout")
    check("gone.sqlite" in err, "basename is named")
    check("bob@example.com-dir" not in err, "parent directory is not named")
    check(str(tmp_path) not in err, "no path leak")
    check(not hidden.exists(), "a missing store is not created")


@pytest.mark.parametrize("content", [b"not a database at all" * 20, None])
def test_foreign_or_corrupt_store_exits_3(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: bytes | None
) -> None:
    path = tmp_path / "other.sqlite"
    if content is None:
        with sqlite3.connect(path) as con:
            con.execute("CREATE TABLE t (secret TEXT)")
            con.execute("INSERT INTO t VALUES (?)", (EMAIL,))
        con.close()
    else:
        path.write_bytes(content)
    code, out, err = run(capsys, argv(path))
    check(code == 3 and out == "", "exit 3")
    no_canary(err)


def test_tampered_receipt_exits_3(db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add_receipt(db, complete_receipt())
    with sqlite3.connect(db) as con:
        con.execute("UPDATE a2c0_receipt SET receipt_sha256 = ?", ("a" * 64,))
    con.close()
    code, out, _ = run(capsys, argv(db))
    check(code == 3 and out == "", "digest mismatch is an unreadable store")


@pytest.mark.parametrize(
    "bad",
    [
        ["--db"],
        ["--unknown", EMAIL],
        ["--db", "x", "--workset", "w", "--expected", EMAIL],
        ["--db", "x", "--workset", EMAIL, "--expected", "1"],
        ["--db", "x", "--workset", WORKSET_REF.result_id, "--expected", "0"],
        ["--db", "x", "--workset", WORKSET_REF.result_id, "--expected", "-1"],
        ["--db", "x", "--workset", WORKSET_REF.result_id, "--expected", "99999"],
        ["--db", "x", "--workset", WORKSET_REF.result_id, "--expect", "1"],
        ["--help"],
    ],
)
def test_bad_arguments_exit_2(
    capsys: pytest.CaptureFixture[str], bad: list[str]
) -> None:
    code, out, err = run(capsys, bad)
    check(code == 2 and out == "", "exit 2 and empty stdout")
    check(err == "a2 scope status: usage error\n", "fixed message")


def test_receipt_for_another_workset_is_a_usage_error(
    db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    add_receipt(db, complete_receipt())
    code, out, _ = run(capsys, argv(db, 1))
    check(code == 2 and out == "", "more roots than expected is an input error")


def test_run_is_read_only(db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add_receipt(db, complete_receipt())
    before = (db.read_bytes(), db.stat().st_mtime_ns, sorted(db.parent.iterdir()))
    for _ in range(2):
        code, _, _ = run(capsys, argv(db))
        check(code == 0, "exit 0")
    after = (db.read_bytes(), db.stat().st_mtime_ns, sorted(db.parent.iterdir()))
    check(before == after, "bytes, mtime and directory listing are unchanged")


def test_connection_is_opened_read_only(
    db: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    add_receipt(db, complete_receipt())
    seen: list[str] = []
    real = sqlite3.connect

    def spy(target: str, *args: Any, **kwargs: Any) -> sqlite3.Connection:
        seen.append(target)
        return real(target, *args, **kwargs)

    monkeypatch.setattr(a2_scope_status.sqlite3, "connect", spy)
    run(capsys, argv(db))
    check(len(seen) == 1 and seen[0].endswith("?mode=ro"), "mode=ro URI")
    check(seen[0].startswith("file:"), "SQLite URI form")


@pytest.mark.parametrize("old", [[], ["status"], ["complete", "busy"]])
def test_older_table_mode_is_kept(
    capsys: pytest.CaptureFixture[str], old: list[str]
) -> None:
    code, out, err = run(capsys, old)
    check(code == 2 and err == "", "exit 2")
    check(out == "a2 scope status: invalid state\n", "fixed text")
    code, out, _ = run(capsys, ["held"])
    check(code == 22 and out == "a2 scope held: exit=22\n", "table line")

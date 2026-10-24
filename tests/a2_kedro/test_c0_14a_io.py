"""C0-14a review fixes: full writes, directory fsync, head anchor (tmp_path only)."""

from __future__ import annotations

import os
import stat
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from msgloom.persistence import a2_receipt_store as module
from msgloom.persistence.a2_receipt_store import (
    GENESIS,
    MAX_CLAIM_BYTES,
    MAX_PROOF_BYTES,
    A2ReceiptConflict,
    CoverageItem,
    ReceiptStore,
    build_receipt_proof,
    seal_proof,
)
from tests.a2_kedro.helpers import WORKSET_REF, check, hexd
from tests.a2_kedro.test_c0_14a import (
    BATCH_REF,
    bound,
    entry,
    expect,
    make_receipt,
    prepared,
    stage_for,
)

REAL_WRITE, REAL_READ, REAL_FSYNC = os.write, os.read, os.fsync
POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="directory fsync")

# Golden digests, computed by a separate hashlib + json script from the
# documented domain strings and canonical form, not by production helpers.
GOLD_ROOT_RECORD = "c5cefd237b70a7cdea3387801604c5f284a7fc84c94d5af32771bf649093b516"
GOLD_TRANSITION_ITEM = (
    "692cbe52f80ddd6fa68d044e665de8bedd8262fad650a9fcef6f09a50d66bbde"
)
GOLD_CLAIM = "9d137f89b400904118df6a0ea8a2bdc1dc2d08921cba7d037fe4173c16110180"
GOLD_PROOF = "323e67ad4a91249cb116d197ca2d9e7f57a64d40b98123103437ccda732ee5da"


class Env:
    """A store in ``tmp_path`` plus black-box helpers that use the public API."""

    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path / "proofs"
        self.root.mkdir()
        self.store = ReceiptStore(self.root)
        self.receipt, self.accepted = make_receipt()
        self.good = build_receipt_proof(self.receipt, self.accepted)

    def files(self) -> list[Path]:
        return sorted(p for p in self.root.rglob("*") if p.is_file())

    def put(self) -> str:
        return self.store.put_receipt_proof(self.good, self.receipt, self.accepted)

    def append(self, seq: int, **kwargs: Any) -> str:
        item = kwargs.pop("item", entry(attempt=f"a{seq}"))
        return self.store.append_claim(WORKSET_REF, item, seq, **kwargs)

    def history(self, **kwargs: Any) -> Any:
        return self.store.claim_history(WORKSET_REF, **kwargs)

    def workset_dir(self) -> Path:
        return next(p for p in self.root.iterdir() if p.is_dir())


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return Env(tmp_path)


def test_golden_digests_match_an_independent_computation(env: Env) -> None:
    root_stage = stage_for(prepared("1"), "a")
    check(root_stage.record_sha256() == GOLD_ROOT_RECORD, "root record digest")
    check(env.good.items[0].item_sha256 == GOLD_ROOT_RECORD, "root item digest")
    check(env.good.items[2].item_sha256 == GOLD_TRANSITION_ITEM, "transition item")
    check(env.append(0, item=entry()) == "inserted", "append")
    check(env.history()[0].entry_sha256 == GOLD_CLAIM, "claim digest")
    items = [
        CoverageItem(
            role="root",
            position=0,
            item_id=prepared("1").result_id,
            item_sha256=hexd("a"),
        ),
        CoverageItem(
            role="transition",
            position=0,
            item_id=BATCH_REF.result_id,
            item_sha256=hexd("b"),
        ),
    ]
    sealed = seal_proof(WORKSET_REF, hexd("9"), "policy-1", items)
    check(sealed.proof_sha256 == GOLD_PROOF, "proof digest")


def patch_write(monkeypatch: pytest.MonkeyPatch, fake: Callable[..., int]) -> None:
    monkeypatch.setattr(os, "write", fake)


def test_short_writes_still_publish_the_whole_file(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def half(fd: int, data: Any) -> int:
        raw = bytes(data)
        calls.append(len(raw))
        return REAL_WRITE(fd, raw[: max(1, len(raw) // 2)])

    patch_write(monkeypatch, half)
    check(env.put() == "inserted", "proof written in pieces")
    check(env.append(0) == "inserted", "claim written in pieces")
    monkeypatch.undo()
    check(len(calls) > 2, "the loop wrote more than once")
    check(env.store.get_receipt_proof(WORKSET_REF) == env.good, "whole proof")
    check(len(env.history()) == 1, "whole claim")
    check(env.put() == "replayed", "stored bytes equal a fresh encoding")


def zero_write(_fd: int, _data: Any) -> int:
    return 0


def failing_write(_fd: int, _data: Any) -> int:
    raise OSError("disk full")


def lying_write(fd: int, data: Any) -> int:
    raw = bytes(data)
    REAL_WRITE(fd, raw[: len(raw) // 2])
    return len(raw)  # claims a full write that never happened


def excess_write(fd: int, data: Any) -> int:
    return REAL_WRITE(fd, bytes(data)) + 1


def half_then_zero() -> Callable[[int, Any], int]:
    state = {"calls": 0}

    def fake(fd: int, data: Any) -> int:
        state["calls"] += 1
        if state["calls"] == 1:
            raw = bytes(data)
            return REAL_WRITE(fd, raw[: len(raw) // 2])
        return 0

    return fake


@pytest.mark.parametrize(
    "fake",
    [zero_write, failing_write, lying_write, excess_write, half_then_zero()],
    ids=["zero", "raises", "lying", "excess", "half-then-zero"],
)
def test_failed_writes_publish_nothing_and_retry_works(
    env: Env, monkeypatch: pytest.MonkeyPatch, fake: Callable[..., int]
) -> None:
    patch_write(monkeypatch, fake)
    expect("write-failed", env.put)
    expect("write-failed", lambda: env.append(0))
    monkeypatch.undo()
    check(not env.files(), "no final file and no temporary file")
    check(env.store.get_receipt_proof(WORKSET_REF) is None, "no proof")
    check(env.history() == (), "no claim")
    check(env.put() == "inserted", "proof retry")
    check(env.append(0) == "inserted", "claim retry")
    check(len(env.history()) == 1, "history verifies")


class FsyncLog:
    """Record each fsync as ``file`` or ``dir``; fail chosen directory calls."""

    def __init__(self, fail_dir_calls: tuple[int, ...] = ()) -> None:
        self.events: list[str] = []
        self.fail = fail_dir_calls

    def __call__(self, fd: int) -> None:
        kind = "dir" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file"
        self.events.append(kind)
        if kind == "dir" and self.events.count("dir") in self.fail:
            raise OSError("fsync refused")
        REAL_FSYNC(fd)


@POSIX_ONLY
def test_directories_are_flushed_after_mkdir_and_link(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = FsyncLog()
    monkeypatch.setattr(os, "fsync", log)
    check(env.put() == "inserted", "insert")
    check(log.events == ["dir", "file", "dir"], f"order {log.events}")
    log.events.clear()
    check(env.put() == "replayed", "replay")
    check(log.events[-1] == "dir", "a replay flushes the directory again")


@POSIX_ONLY
@pytest.mark.parametrize("failing_call", [1, 2], ids=["after-mkdir", "after-link"])
def test_directory_fsync_failure_is_write_failed(
    env: Env, monkeypatch: pytest.MonkeyPatch, failing_call: int
) -> None:
    monkeypatch.setattr(os, "fsync", FsyncLog((failing_call,)))
    expect("write-failed", env.put)
    monkeypatch.setattr(os, "fsync", FsyncLog((failing_call,)))
    expect("write-failed", lambda: env.append(0))
    monkeypatch.undo()
    check(not [p for p in env.files() if p.name.startswith(".tmp-")], "no temp")
    # A complete file may remain after a failed directory flush. A retry
    # flushes the directory and then reports a replay or a fresh insert.
    check(env.put() in ("inserted", "replayed"), "proof retry")
    check(env.append(0) in ("inserted", "replayed"), "claim retry")
    check(env.store.get_receipt_proof(WORKSET_REF) == env.good, "whole proof")
    check(len(env.history()) == 1, "whole claim")


def test_tail_truncation_is_detected_only_with_an_anchor(env: Env) -> None:
    for seq in range(3):
        env.append(seq)
    head = env.history()[-1].entry_sha256
    check(env.history(expected_head_sha256=head)[-1].seq == 2, "anchor matches")
    victim = env.workset_dir() / "claim-00002.json"
    victim.unlink()
    expect("claim-head-mismatch", lambda: env.history(expected_head_sha256=head))
    different = entry("released", attempt="other")
    expect(
        "claim-head-mismatch",
        lambda: env.append(2, item=different, expected_head_sha256=head),
    )
    check(not victim.exists(), "a refused append wrote nothing")
    check(len(env.history()) == 2, "no anchor: shorter chain still verifies")
    check(env.append(2, item=different) == "inserted", "no anchor: old behavior")


def test_anchor_covers_empty_history_and_matching_appends(env: Env) -> None:
    check(env.history(expected_head_sha256=GENESIS) == (), "empty matches genesis")
    expect("claim-head-mismatch", lambda: env.history(expected_head_sha256=hexd("1")))
    expect("claim-head-mismatch", lambda: env.append(0, expected_head_sha256=hexd("1")))
    check(not env.files(), "nothing written by a refused append")
    check(env.append(0, expected_head_sha256=GENESIS) == "inserted", "first")
    head = env.history()[0].entry_sha256
    check(env.append(1, expected_head_sha256=head) == "inserted", "second")
    expect("claim-head-mismatch", lambda: env.history(expected_head_sha256=GENESIS))
    # Deleting every claim leaves an empty history that a non-genesis anchor refuses.
    for path in env.workset_dir().glob("claim-*.json"):
        path.unlink()
    expect("claim-head-mismatch", lambda: env.history(expected_head_sha256=head))


def test_short_reads_are_looped(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    env.put()
    for seq in range(2):
        env.append(seq)

    def tiny(fd: int, size: int) -> bytes:
        return REAL_READ(fd, min(size, 7))

    monkeypatch.setattr(os, "read", tiny)
    check(env.store.get_receipt_proof(WORKSET_REF) == env.good, "proof")
    check(len(env.history()) == 2, "claims")
    check(env.put() == "replayed", "replay compares whole bytes")
    (env.workset_dir() / "claim-00001.json").write_bytes(b"y" * (MAX_CLAIM_BYTES + 1))
    bound("stored-too-large", env.history)


def test_oversize_payload_is_a_bound_error(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "MAX_PROOF_BYTES", 10)
    bound("payload-too-large", env.put)
    monkeypatch.setattr(module, "MAX_CLAIM_BYTES", 10)
    bound("payload-too-large", lambda: env.append(0))
    monkeypatch.undo()
    check(MAX_PROOF_BYTES > 10 and MAX_CLAIM_BYTES > 10, "limits restored")
    check(not env.files(), "nothing written")


def run_threads(calls: list[Callable[[], str]]) -> list[str]:
    barrier, out = threading.Barrier(len(calls)), []

    def work(call: Callable[[], str]) -> None:
        barrier.wait()
        try:
            out.append(call())
        except A2ReceiptConflict:
            out.append("conflict")

    threads = [threading.Thread(target=work, args=(call,)) for call in calls]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return sorted(out)


def test_concurrent_identical_proofs_are_idempotent(env: Env) -> None:
    outcomes = run_threads([env.put] * 6)
    check(outcomes == ["inserted"] + ["replayed"] * 5, f"outcomes {outcomes}")
    check(env.store.get_receipt_proof(WORKSET_REF) == env.good, "one proof")
    check(len(env.files()) == 1, "one file, no temporary file")


def test_concurrent_different_proofs_have_one_winner(env: Env) -> None:
    other, other_accepted = make_receipt(policy="policy-2")
    other_proof = build_receipt_proof(other, other_accepted)

    def mine() -> str:
        return env.put()

    def theirs() -> str:
        return env.store.put_receipt_proof(other_proof, other, other_accepted)

    outcomes = run_threads([mine, theirs, mine, theirs])
    check(outcomes.count("inserted") == 1, f"one winner {outcomes}")
    winner = env.store.get_receipt_proof(WORKSET_REF)
    check(winner in (env.good, other_proof), "the stored proof is one of them")
    check(len(env.files()) == 1, "one file")


def symlinks_supported(tmp_path: Path) -> bool:
    if not hasattr(os, "symlink") or not hasattr(os, "O_NOFOLLOW"):
        return False
    try:
        os.symlink(tmp_path, tmp_path / "probe-link")
    except (OSError, NotImplementedError):
        return False
    return True


def test_symlink_inside_workset_directory_is_refused(env: Env, tmp_path: Path) -> None:
    if not symlinks_supported(tmp_path):
        pytest.skip("symlinks or O_NOFOLLOW unsupported")
    env.put()
    env.append(0)
    directory = env.workset_dir()
    for name in ("receipt-proof.json", "claim-00000.json"):
        target = tmp_path / ("copy-" + name)
        target.write_bytes((directory / name).read_bytes())
        (directory / name).unlink()
        (directory / name).symlink_to(target)
    expect("read-failed", lambda: env.store.get_receipt_proof(WORKSET_REF))
    expect("read-failed", env.history)
    expect("read-failed", lambda: env.append(0))
    expect("read-failed", env.put)

"""C0-14a: bounded receipt coverage proof and claim history (tmp_path only)."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.receipt import (
    CompletionReceipt,
    TerminalRoot,
    TransitionBatch,
)
from msgloom.contracts import ResultRef, TerminalStatus, VersionRef
from msgloom.persistence import a2_receipt_store as module
from msgloom.persistence.a2_acceptance_models import AcceptedStage
from msgloom.persistence.a2_receipt_store import (
    MAX_CLAIM_BYTES,
    MAX_CLAIMS,
    MAX_COVERAGE_ITEMS,
    MAX_PROOF_BYTES,
    A2ReceiptBoundError,
    A2ReceiptConflict,
    A2ReceiptError,
    ClaimEntry,
    CoverageItem,
    ReceiptProof,
    ReceiptStore,
    build_receipt_proof,
    seal_proof,
)
from tests.a2_kedro.helpers import (
    WORKSET_REF,
    accepted_ref,
    check,
    hexd,
    proof,
    selection_for,
    transition_for,
)

COMPLETE = TerminalStatus.COMPLETE
CANARY = "alice@example.test"
BATCH_REF = accepted_ref("5", "prepared_transitions", "2")
OTHER_WS = ResultRef("intake-workset:" + hexd("8"), "preparation_intake_workset", "1")


def prepared(char: str) -> ResultRef:
    return accepted_ref(char, "prepared", "2")


def stage_for(ref: ResultRef, char: str = "a") -> AcceptedStage:
    return AcceptedStage(
        logical_key=ref.result_id,
        output=ref,
        canonical_sha256=hexd(char),
        canonical_byte_count=10,
        semantic_data_id="d-" + ref.result_id[-4:],
        stage_metadata_sha256=hexd("b"),
        lineage_digest=hexd("c"),
        status=COMPLETE,
        limitations_digest=hexd("d"),
        writer=proof(),
    )


def make_receipt(
    *, baseline: bool = False, transitions: bool = True, policy: str = "policy-1"
) -> tuple[CompletionReceipt, dict[str, AcceptedStage]]:
    refs = [prepared("1"), prepared("2")]
    roots = []
    for i, ref in enumerate(refs):
        where: dict[str, Any] = {"selection": selection_for(i + 1)}
        if baseline:
            where = {
                "baseline_selection": ResultRef(f"sel-{i}", "collected_selection", "1"),
                "baseline_source": VersionRef("mail", f"m{i}", "v1"),
            }
        roots.append(
            TerminalRoot(
                workset_selection_index=i,
                result=ref,
                disposition="prepared",
                status=COMPLETE,
                **where,
            )
        )
    batch = None
    if transitions:
        pair = (transition_for(3, "c"), transition_for(4, "d"))
        batch = TransitionBatch(transitions=pair, result=BATCH_REF, status=COMPLETE)
    receipt = CompletionReceipt.build(
        workset=WORKSET_REF,
        status=COMPLETE,
        policy_version=policy,
        roots=tuple(roots),
        transition_batch=batch,
    )
    accepted = {ref.result_id: stage_for(ref, "ab"[i]) for i, ref in enumerate(refs)}
    if transitions:
        accepted[BATCH_REF.result_id] = stage_for(BATCH_REF, "e")
    return receipt, accepted


def entry(
    event: str = "claimed", attempt: str = "a1", result: ResultRef | None = None
) -> ClaimEntry:
    values: dict[str, Any] = {"event": event, "proof": proof(attempt), "result": result}
    return ClaimEntry.model_validate(values)


def tweak(item: CoverageItem, **changes: Any) -> CoverageItem:
    return CoverageItem.model_validate({**item.model_dump(), **changes})


def expect(reason: str, call: Any, error: type[A2ReceiptError] = A2ReceiptError) -> Any:
    with pytest.raises(error) as caught:
        call()
    got = caught.value.reason
    check(got == reason, f"expected {reason}, got {got}")
    return caught.value


def bound(reason: str, call: Any) -> None:
    expect(reason, call, A2ReceiptBoundError)


@dataclass
class Case:
    store: ReceiptStore
    receipt: CompletionReceipt
    accepted: dict[str, AcceptedStage]
    good: ReceiptProof

    def files(self) -> list[str]:
        return sorted(p.name for p in self.store._root.rglob("*") if p.is_file())

    def reseal(self, items: list[CoverageItem], **changes: Any) -> ReceiptProof:
        fields: dict[str, Any] = {
            "workset": self.good.workset,
            "receipt_sha256": self.good.receipt_sha256,
            "policy_version": self.good.policy_version,
        }
        return seal_proof(items=items, **{**fields, **changes})

    def put(self, built: ReceiptProof, accepted: Any = None) -> str:
        accepted = self.accepted if accepted is None else accepted
        return self.store.put_receipt_proof(built, self.receipt, accepted)

    def refuse(self, built: ReceiptProof, reason: str, accepted: Any = None) -> None:
        expect(reason, lambda: self.put(built, accepted))
        check(not self.files(), "a refused proof leaves no file")

    def path(self, name: str = module._PROOF_FILE) -> Path:
        return self.store._directory(WORKSET_REF) / name


@pytest.fixture
def case(tmp_path: Path) -> Case:
    (tmp_path / "proofs").mkdir()
    receipt, accepted = make_receipt()
    good = build_receipt_proof(receipt, accepted)
    return Case(ReceiptStore(tmp_path / "proofs"), receipt, accepted, good)


def test_incremental_proof_covers_roots_then_transitions(case: Case) -> None:
    check(case.store.get_receipt_proof(WORKSET_REF) is None, "absent")
    check(case.store.claim_history(WORKSET_REF) == (), "empty history")
    check(not list(case.store._root.iterdir()), "reads create nothing")
    items = case.good.items
    order = [(i.role, i.position) for i in items]
    want = [("root", 0), ("root", 1), ("transition", 0), ("transition", 1)]
    check(order == want, "coverage order")
    check(items[0].item_id == prepared("1").result_id, "id reference")
    check(
        items[0].item_sha256 == case.accepted[items[0].item_id].record_sha256(), "sha"
    )
    check(case.put(case.good) == "inserted", "insert")
    check(case.put(case.good) == "replayed", "replay")
    check(case.store.get_receipt_proof(WORKSET_REF) == case.good, "round trip")
    check(len(case.files()) == 1, "one file and no temporary file")


def test_baseline_proof_uses_baseline_role(case: Case) -> None:
    receipt, accepted = make_receipt(baseline=True, transitions=False)
    built = build_receipt_proof(receipt, accepted)
    check([i.role for i in built.items] == ["baseline", "baseline"], "roles")
    check(case.store.put_receipt_proof(built, receipt, accepted) == "inserted", "put")


def test_missing_item_is_refused(case: Case) -> None:
    items = list(case.good.items)
    for cut in (items[:-1], items[1:], items[:2], []):
        case.refuse(case.reseal(cut), "coverage-missing")


def test_extra_item_is_refused(case: Case) -> None:
    a, b, t0, t1 = case.good.items
    extra_root = tweak(a, position=2, item_id=prepared("3").result_id)
    case.refuse(case.reseal([a, b, extra_root, t0, t1]), "coverage-extra")
    case.refuse(case.reseal([a, b, t0, t1, tweak(t1, position=2)]), "coverage-extra")
    # A baseline item cannot stand in for an incremental root.
    case.refuse(case.reseal([tweak(a, role="baseline")]), "coverage-missing")


def test_duplicate_and_out_of_order_items_are_refused(case: Case) -> None:
    a, b, t0, t1 = case.good.items
    expect("coverage-duplicate", lambda: case.reseal([a, a, t0, t1]))
    expect("coverage-duplicate", lambda: case.reseal([a, b, t0, t0]))
    expect("coverage-order", lambda: case.reseal([b, a, t0, t1]))
    expect("coverage-order", lambda: case.reseal([t0, t1, a, b]))
    expect("coverage-order", lambda: case.reseal([a, b, t1, t0]))
    expect("coverage-role-mix", lambda: case.reseal([a, tweak(b, role="baseline")]))
    check(not case.files(), "nothing written")


def test_digest_and_id_tamper_are_refused(case: Case) -> None:
    for index, item in enumerate(case.good.items):
        for field, reason in (
            ("item_sha256", "coverage-digest-mismatch"),
            ("item_id", "coverage-id-mismatch"),
        ):
            value = hexd("f") if field == "item_sha256" else prepared("f").result_id
            items = list(case.good.items)
            items[index] = tweak(item, **{field: value})
            case.refuse(case.reseal(items), reason)
    same = list(case.good.items)
    case.refuse(case.reseal(same, receipt_sha256=hexd("f")), "proof-receipt-mismatch")
    case.refuse(case.reseal(same, policy_version="policy-2"), "proof-receipt-mismatch")
    case.refuse(case.reseal(same, workset=OTHER_WS), "proof-workset-mismatch")


def test_accepted_record_changes_break_the_proof(case: Case) -> None:
    key, batch_key = prepared("1").result_id, BATCH_REF.result_id
    changed = {**case.accepted, key: stage_for(prepared("1"), "c")}
    case.refuse(case.good, "coverage-digest-mismatch", changed)
    missing = {k: v for k, v in case.accepted.items() if k != batch_key}
    case.refuse(case.good, "accepted-result-missing", missing)
    wrong_kind = {**case.accepted, key: stage_for(accepted_ref("1", "zones", "1"))}
    case.refuse(case.good, "accepted-result-mismatch", wrong_kind)
    expect("accepted-result-missing", lambda: build_receipt_proof(case.receipt, {}))


def test_conflicting_second_proof_keeps_the_first(case: Case) -> None:
    case.put(case.good)
    before = case.path().read_bytes()
    other, other_accepted = make_receipt(policy="policy-2")
    built = build_receipt_proof(other, other_accepted)
    error = expect(
        "receipt-proof-conflict",
        lambda: case.store.put_receipt_proof(built, other, other_accepted),
        A2ReceiptConflict,
    )
    check(error.fields == ("proof",), "field names only")
    check(case.path().read_bytes() == before, "stored proof unchanged")


def test_stored_proof_tamper_fails_closed(case: Case) -> None:
    case.put(case.good)
    good = case.path().read_bytes()
    victim = case.good.items[0].item_sha256.encode()
    variants = {
        "digest": good.replace(victim, hexd("0").encode(), 1),
        "space": good.replace(b'{"items"', b'{ "items"', 1),
        "truncated": good[:-7],
        "junk": b"\xff\xfe",
        "empty": b"",
    }
    for name, data in variants.items():
        check(data != good, f"variant {name} must differ")
        case.path().write_bytes(data)
        expect(
            "stored-proof-corrupt", lambda: case.store.get_receipt_proof(WORKSET_REF)
        )
    case.path().write_bytes(b"x" * (MAX_PROOF_BYTES + 1))
    bound("stored-too-large", lambda: case.store.get_receipt_proof(WORKSET_REF))


def test_item_bound_fails_closed(case: Case) -> None:
    item = case.good.items[0]
    many = [item] * (MAX_COVERAGE_ITEMS + 1)
    bound("coverage-too-many", lambda: case.reseal(many))
    with pytest.raises(ValueError):
        tweak(item, position=1024)


def test_claim_history_is_chained_and_append_only(case: Case) -> None:
    store = case.store
    sequence = [entry(), entry("published", result=prepared("1")), entry("released")]
    for seq, item in enumerate(sequence):
        check(store.append_claim(WORKSET_REF, item, seq) == "inserted", "append")
    history = store.claim_history(WORKSET_REF)
    check([c.seq for c in history] == [0, 1, 2], "sequence")
    check(history[0].prev_sha256 == module.GENESIS, "genesis")
    check(history[1].prev_sha256 == history[0].entry_sha256, "chain 1")
    check(history[2].prev_sha256 == history[1].entry_sha256, "chain 2")
    check([c.entry for c in history] == sequence, "raw entries kept")
    check(store.append_claim(WORKSET_REF, sequence[1], 1) == "replayed", "replay")
    check(len(store.claim_history(WORKSET_REF)) == 3, "replay appends nothing")


def test_claim_rewrite_and_gap_are_refused(case: Case) -> None:
    store = case.store
    store.append_claim(WORKSET_REF, entry(), 0)
    before = case.files(), case.path("claim-00000.json").read_bytes()
    for other in (
        entry(attempt="a2"),
        entry("released"),
        entry("published", result=prepared("1")),
    ):
        error = expect(
            "claim-history-rewrite",
            lambda other=other: store.append_claim(WORKSET_REF, other, 0),
            A2ReceiptConflict,
        )
        check(error.fields == ("entry",), "field names only")
    expect("claim-gap", lambda: store.append_claim(WORKSET_REF, entry(), 2))
    bound(
        "claim-history-too-long", lambda: store.append_claim(WORKSET_REF, entry(), -1)
    )
    after = case.files(), case.path("claim-00000.json").read_bytes()
    check(before == after, "history unchanged by refused writes")


def test_claim_entry_shape_is_strict() -> None:
    key = prepared("1").result_id
    for event, result in (
        ("published", None),
        ("claimed", prepared("1")),
        ("published", ResultRef("raw-id", "prepared", "2")),
        ("published", ResultRef(key, "prepared", "1")),
    ):
        with pytest.raises(ValueError):
            ClaimEntry.model_validate(
                {"event": event, "proof": proof(), "result": result}
            )


def test_claim_history_tamper_is_detected(case: Case) -> None:
    store = case.store
    for seq in range(3):
        store.append_claim(WORKSET_REF, entry(attempt=f"a{seq}"), seq)
    middle, last = case.path("claim-00001.json"), case.path("claim-00002.json")
    good = middle.read_bytes()

    def broken() -> None:
        expect("claim-history-corrupt", lambda: store.claim_history(WORKSET_REF))

    middle.write_bytes(good.replace(b"a1", b"a9"))
    broken()
    expect("claim-history-corrupt", lambda: store.append_claim(WORKSET_REF, entry(), 3))
    middle.write_bytes(good)
    check(len(store.claim_history(WORKSET_REF)) == 3, "restored history verifies")
    middle.write_bytes(last.read_bytes())
    broken()
    middle.unlink()
    broken()
    middle.write_bytes(b"y" * (MAX_CLAIM_BYTES + 1))
    bound("stored-too-large", lambda: store.claim_history(WORKSET_REF))
    middle.write_bytes(good)
    case.path("claim-extra.json").write_bytes(good)
    broken()


def test_claim_count_bound_fails_closed(case: Case) -> None:
    store = case.store
    for seq in range(MAX_CLAIMS):
        store.append_claim(WORKSET_REF, entry(attempt=f"a{seq}"), seq)
    check(len(store.claim_history(WORKSET_REF)) == MAX_CLAIMS, "full history")
    bound(
        "claim-history-too-long",
        lambda: store.append_claim(WORKSET_REF, entry(), MAX_CLAIMS),
    )
    case.path(f"claim-{MAX_CLAIMS:05d}.json").write_bytes(b"{}")
    bound("claim-history-too-long", lambda: store.claim_history(WORKSET_REF))


@pytest.mark.parametrize("failure", [OSError("disk"), KeyboardInterrupt()])
def test_failed_publish_leaves_nothing_partial(
    case: Case, monkeypatch: pytest.MonkeyPatch, failure: BaseException
) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise failure

    monkeypatch.setattr(module.os, "link", boom)
    expected = A2ReceiptError if isinstance(failure, OSError) else KeyboardInterrupt
    with pytest.raises(expected):
        case.put(case.good)
    with pytest.raises(expected):
        case.store.append_claim(WORKSET_REF, entry(), 0)
    monkeypatch.undo()
    check(not case.files(), "no final or temporary file after a failure")
    check(case.store.get_receipt_proof(WORKSET_REF) is None, "no proof")
    check(case.store.claim_history(WORKSET_REF) == (), "no claim")
    case.path().parent.mkdir(exist_ok=True)
    case.path(".tmp-deadbeef").write_bytes(b"half")  # a crash leftover
    check(case.put(case.good) == "inserted", "retry works")
    check(case.store.append_claim(WORKSET_REF, entry(), 0) == "inserted", "retry")
    check(len(case.store.claim_history(WORKSET_REF)) == 1, "temporary ignored")


def race(store: ReceiptStore, entries: list[ClaimEntry]) -> list[str]:
    barrier, out = threading.Barrier(len(entries)), []

    def work(item: ClaimEntry) -> None:
        barrier.wait()
        try:
            out.append(store.append_claim(WORKSET_REF, item, 0))
        except A2ReceiptConflict:
            out.append("conflict")

    threads = [threading.Thread(target=work, args=(e,)) for e in entries]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return sorted(out)


def test_concurrent_appenders_of_one_sequence(case: Case, tmp_path: Path) -> None:
    same = race(case.store, [entry()] * 4)
    check(same == ["inserted", "replayed", "replayed", "replayed"], "same entry")
    (tmp_path / "second").mkdir()
    second = ReceiptStore(tmp_path / "second")
    check(
        race(second, [entry(attempt="x1"), entry(attempt="x2")]).count("inserted") == 1,
        "one wins",
    )
    check(len(second.claim_history(WORKSET_REF)) == 1, "one entry stored")


def test_errors_never_echo_values_or_paths(case: Case, tmp_path: Path) -> None:
    receipt, accepted = make_receipt(policy=CANARY)
    built = build_receipt_proof(receipt, accepted)
    case.store.put_receipt_proof(built, receipt, accepted)
    private = entry(attempt=CANARY)
    case.store.append_claim(WORKSET_REF, private, 0)
    other, other_accepted = make_receipt(policy=CANARY + "2")
    other_proof = build_receipt_proof(other, other_accepted)
    short = case.reseal(list(built.items[:1]), policy_version=CANARY)
    item = case.good.items[0]
    calls = [
        lambda: case.store.put_receipt_proof(other_proof, other, other_accepted),
        lambda: case.store.append_claim(WORKSET_REF, entry(attempt=CANARY + "2"), 0),
        lambda: case.store.append_claim(WORKSET_REF, private, 5),
        lambda: case.store.put_receipt_proof(short, receipt, accepted),
        lambda: seal_proof(WORKSET_REF, CANARY, "p", [item]),
    ]
    errors: list[BaseException] = []
    for call in calls:
        with pytest.raises(A2ReceiptError) as caught:
            call()
        errors.append(caught.value)
    case.path().write_bytes(case.path().read_bytes()[:-5])
    case.path("claim-00000.json").write_bytes(b'{"x":"' + CANARY.encode() + b'"}')
    for read in (case.store.get_receipt_proof, case.store.claim_history):
        with pytest.raises(A2ReceiptError) as caught:
            read(WORKSET_REF)
        errors.append(caught.value)
    for error in errors:
        text = f"{error!s} {error!r} {getattr(error, 'fields', '')}"
        for secret in (CANARY, str(tmp_path), hexd("1"), "a2-accepted"):
            check(secret not in text, "error text leaked a value")
    names = [*case.files(), case.path().parent.name]
    check(all(CANARY not in name for name in names), "no value in a name")


def test_store_root_must_be_a_real_directory(tmp_path: Path) -> None:
    (tmp_path / "file").write_text("x")
    (tmp_path / "link").symlink_to(tmp_path)
    for bad in (tmp_path / "missing", tmp_path / "file", tmp_path / "link"):
        expect("store-root-invalid", lambda bad=bad: ReceiptStore(bad))
    store = ReceiptStore(tmp_path)
    target = tmp_path / "elsewhere"
    target.mkdir()
    store._directory(WORKSET_REF).symlink_to(target)
    expect("store-root-invalid", lambda: store.claim_history(WORKSET_REF))
    expect("store-root-invalid", lambda: store.append_claim(WORKSET_REF, entry(), 0))
    check(not list(target.iterdir()), "nothing written through a symlink")

"""C0-22: stage storage budgets, retention and the decision record check."""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import os
import re
import sqlite3
import stat
from collections.abc import Callable
from itertools import takewhile
from pathlib import Path

import pytest

import msgloom.persistence.a2_acceptance_models as models
import msgloom.persistence.a2_held_store as held_store
import msgloom.persistence.a2_receipt_store as receipt_store
import msgloom.persistence.a2_sqlite_ddl as research_ddl
import msgloom.persistence.a2_sqlite_store as research_store
import msgloom.persistence.a2_stage_budgets as budgets
from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.held import HeldReason, InputDisposition
from msgloom.a2_kedro.contracts.schema_ids import STAGE_SCHEMAS
from msgloom.contracts import ResultSchemaRegistry
from msgloom.persistence import a2_schema, a2_store
from msgloom.persistence.a2_acceptance_models import MAX_PAYLOAD_BYTES
from msgloom.persistence.a2_receipt_io import create_once
from msgloom.persistence.a2_schema_migration import create_backup
from msgloom.persistence.a2_stage_budgets import (
    DEFAULT_POLICY,
    A2BudgetConfigError,
    A2BudgetExceeded,
    A2StageBudgetError,
    ArtifactBudget,
    RetentionAction,
    StageBudgetPolicy,
    check_artifact,
    retention_action,
)
from msgloom.persistence.errors import IncompatibleSchemaError
from msgloom.persistence.store import Phase1Store
from tests.a2_kedro.helpers import (
    WORKSET_REF,
    hexd,
    proof,
    result_for,
    root_for,
    stage_identity,
    workset,
)
from tests.persistence.test_a2_schema_constraints import put
from tests.persistence.test_a2_schema_fixtures import (
    GATE,
    build_schema4,
    build_schema5,
    raw,
    snapshot,
)

KIND = "zones"
CANARY = "CANARY-PII-c022-bob@example.invalid"
ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/decisions/a2-v2-storage-budgets.md"
PERSISTENCE = Path(budgets.__file__).parent


def check(condition: bool, message: str) -> None:
    """Fail the test with ``message`` unless ``condition`` holds."""
    if not condition:
        pytest.fail(message)


def small_policy(
    *, entries: int = 3, workset_bytes: int = 100, payload: int = 40
) -> StageBudgetPolicy:
    """Return a tiny policy that covers every approved kind."""
    return StageBudgetPolicy(
        artifacts=tuple(
            ArtifactBudget(kind, payload, 10, 20) for kind in STAGE_SCHEMAS
        ),
        max_entries_per_workset=entries,
        max_bytes_per_workset=workset_bytes,
    )


def reason_of(call, *args: object) -> str:  # type: ignore[no-untyped-def]
    """Return the reason code of the budget error ``call`` raises."""
    try:
        call(*args)
    except A2BudgetExceeded as error:
        return error.reason
    pytest.fail("expected A2BudgetExceeded")


def test_default_policy_is_finite_and_covers_every_kind() -> None:
    kinds = {budget.kind for budget in DEFAULT_POLICY.artifacts}
    check(kinds == set(STAGE_SCHEMAS), "every approved kind needs a budget")
    for budget in DEFAULT_POLICY.artifacts:
        check(0 < budget.max_payload_bytes <= MAX_PAYLOAD_BYTES, budget.kind)
        check(
            budget.max_payload_bytes <= DEFAULT_POLICY.max_bytes_per_workset,
            budget.kind,
        )
        check(0 < budget.payload_days < budget.digest_days, budget.kind)


def test_policy_is_frozen_and_errors_are_contract_errors() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        DEFAULT_POLICY.max_entries_per_workset = 1  # type: ignore[misc]
    check(issubclass(A2BudgetExceeded, A2ContractError), "must be contract error")
    check(issubclass(A2BudgetConfigError, A2ContractError), "must be contract error")


def test_unknown_and_historical_kind_is_refused() -> None:
    check(reason_of(check_artifact, "mystery", 1, 0, 0) == "unknown-kind", "kind")
    check(reason_of(retention_action, "mystery", 1) == "unknown-kind", "kind")
    with pytest.raises(A2BudgetConfigError):
        ArtifactBudget("prepared_v1_history", 10, 1, 2)


@pytest.mark.parametrize(
    "args",
    [(0, 0, 0), (-1, 0, 0), (1, -1, 0), (1, 0, -1), (True, 0, 0), (1.5, 0, 0)],
)
def test_invalid_measurements_are_refused(args: tuple[object, ...]) -> None:
    with pytest.raises(A2BudgetExceeded):
        check_artifact(KIND, *args)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [0, -1, MAX_PAYLOAD_BYTES + 1, True, 1.5])
def test_artifact_budget_rejects_bad_payload_limit(bad: object) -> None:
    with pytest.raises(A2BudgetConfigError):
        ArtifactBudget(KIND, bad, 1, 2)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("payload", "digest"),
    [(0, 5), (-1, 5), (1, 0), (1, -3), (5, 5), (6, 5), (1, 3651)],
)
def test_artifact_budget_rejects_bad_retention_ages(payload: int, digest: int) -> None:
    with pytest.raises(A2BudgetConfigError):
        ArtifactBudget(KIND, 10, payload, digest)


@pytest.mark.parametrize("entries", [0, -1, True, 1_000_001, 1.5, "3"])
def test_policy_rejects_bad_entry_limit(entries: object) -> None:
    with pytest.raises(A2BudgetConfigError):
        small_policy(entries=entries)  # type: ignore[arg-type]


@pytest.mark.parametrize("total", [0, -1, (1 << 40) + 1, 100.0, True, "100"])
def test_policy_rejects_bad_workset_byte_limit(total: object) -> None:
    with pytest.raises(A2BudgetConfigError):
        small_policy(workset_bytes=total, payload=1)  # type: ignore[arg-type]


def test_policy_rejects_list_and_foreign_artifact_elements() -> None:
    good = small_policy().artifacts
    for bad in (list(good), (*good[:-1], None), (*good[:-1], 3), good[:-1], ()):
        with pytest.raises(A2BudgetConfigError):
            StageBudgetPolicy(bad, 3, 100)  # type: ignore[arg-type]
    with pytest.raises(A2BudgetConfigError):
        StageBudgetPolicy(good + good[:1], 3, 100)


def test_int_subclasses_are_refused() -> None:
    class Loud(int):
        pass

    with pytest.raises(A2BudgetConfigError):
        small_policy(entries=Loud(3))
    with pytest.raises(A2StageBudgetError):
        retention_action("zones", Loud(3), small_policy())


def test_policy_rejects_artifact_limit_above_workset_limit() -> None:
    with pytest.raises(A2BudgetConfigError) as caught:
        small_policy(workset_bytes=39, payload=40)
    check(caught.value.reason == "artifact-limit-above-workset-limit", "reason")


@pytest.mark.parametrize("age", [-1, True, 1.5])
def test_retention_rejects_bad_age(age: object) -> None:
    with pytest.raises(A2BudgetExceeded):
        retention_action(KIND, age, small_policy())  # type: ignore[arg-type]


def test_policy_limits_at_limit_and_over() -> None:
    for budget in DEFAULT_POLICY.artifacts:
        limit = budget.max_payload_bytes
        check_artifact(budget.kind, limit, 0, 0)
        reason = reason_of(check_artifact, budget.kind, limit + 1, 0, 0)
        check(reason == "payload-too-large", f"{budget.kind}: {reason}")
    entries = DEFAULT_POLICY.max_entries_per_workset
    used = DEFAULT_POLICY.max_bytes_per_workset
    small_policy(entries=1_000_000, workset_bytes=1 << 40)  # upper bounds pass
    ArtifactBudget(KIND, 10, 1, budgets.MAX_RETENTION_DAYS)  # age bound passes
    check_artifact(KIND, 1, entries - 1, used - 1)
    got = reason_of(check_artifact, KIND, 1, entries, 0)
    check(got == "workset-entries-exceeded", got)
    got = reason_of(check_artifact, KIND, 1, 0, used)
    check(got == "workset-bytes-exceeded", got)


def test_retention_boundaries_for_every_kind() -> None:
    keep, drop = RetentionAction.KEEP, RetentionAction.DROP_PAYLOAD_KEEP_DIGEST
    for b in DEFAULT_POLICY.artifacts:
        cases = [(b.payload_days - 1, keep), (b.payload_days, drop)]
        cases += [(b.digest_days - 1, drop), (b.digest_days, RetentionAction.DELETE)]
        for age, action in cases:
            check(retention_action(b.kind, age) is action, f"{b.kind} age {age}")


def test_budget_errors_never_echo_the_input() -> None:
    calls = ((check_artifact, (CANARY, 1, 0, 0)), (retention_action, (CANARY, 1)))
    for call, args in calls:
        with pytest.raises(A2BudgetExceeded) as caught:
            call(*args)  # type: ignore[arg-type]
        check(CANARY not in str(caught.value) + repr(caught.value), "input echoed")
        check(str(caught.value) == caught.value.reason == "unknown-kind", "text")


def at_and_over(insert: Callable[[int, int], object], limit: int) -> None:
    """Insert row 1 at ``limit`` (accepted) and row 2 at ``limit + 1`` (refused)."""
    insert(1, limit)
    with pytest.raises(sqlite3.IntegrityError):
        insert(2, limit + 1)


def test_accepted_stage_bytes_at_limit_and_over(tmp_path: Path) -> None:
    db = raw(build_schema5(tmp_path / "a2.sqlite"))
    if a2_schema.acquire_claim(db, proof("w1")) is None:
        pytest.fail("fixture claim must be acquired")

    def put_stage(n: int, **changes: object) -> None:
        put(db, logical_key="a2-accepted:" + hexd(str(n)), **changes)

    at_and_over(
        lambda n, size: put_stage(n, canonical_byte_count=size),
        models.MAX_PAYLOAD_BYTES,
    )
    at_and_over(
        lambda n, size: put_stage(n + 2, record_json="x" * size),
        models.MAX_RECORD_BYTES,
    )


def held_db(tmp_path: Path) -> sqlite3.Connection:
    db = raw(tmp_path / "held.sqlite")
    held_store.ensure_held_index(db)
    return db


def put_held_row(db: sqlite3.Connection, index: int, record_json: str = "{}") -> None:
    reason = HeldReason.PARSER_UNSUPPORTED.value
    db.execute(
        f"INSERT INTO {held_store.TABLE} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (WORKSET_REF.result_id, index, f"s{index}", hexd("1"), reason)
        + ("operator_repair", 0, hexd("2"), record_json),
    )


def test_held_bytes_and_rows_at_limit_and_over(tmp_path: Path) -> None:
    found = re.search(r"workset_index BETWEEN 0 AND (\d+)", held_store.DDL)
    last = int(found[1]) if found else -1
    db = held_db(tmp_path)
    at_and_over(
        lambda n, size: put_held_row(db, n, "x" * size),
        held_store.MAX_HELD_RECORD_BYTES,
    )
    at_and_over(lambda _n, index: put_held_row(db, index), last)


def test_held_batch_and_page_at_limit_and_over(tmp_path: Path) -> None:
    item = InputDisposition.from_root(
        root_for(workset(selected=2), 0),
        HeldReason.PARSER_UNSUPPORTED,
        configuration_version="config-1",
        code_version="code-1",
    )
    db = held_db(tmp_path)
    # One record repeated: the first inserts and the rest replay.
    done = held_store.put_many(db, WORKSET_REF, [item] * held_store.MAX_BATCH)
    check(len(done) == held_store.MAX_BATCH, "full batch is accepted")
    with pytest.raises(held_store.A2HeldError, match="batch-size"):
        held_store.put_many(db, WORKSET_REF, [item] * (held_store.MAX_BATCH + 1))
    held_store.list_held(db, WORKSET_REF, limit=held_store.MAX_LIMIT)
    with pytest.raises(held_store.A2HeldError, match="limit-out-of-range"):
        held_store.list_held(db, WORKSET_REF, limit=held_store.MAX_LIMIT + 1)


def research_limit(column: str) -> int:
    found = re.search(rf"length\({column}\) <= (\d+)", "".join(research_ddl.STATEMENTS))
    return int(found[1]) if found else -1


def test_research_bytes_at_limit_and_over(tmp_path: Path) -> None:
    path = tmp_path / "research.sqlite"
    research_store.A2ResearchStore.create(path).close()
    db = raw(path)
    sql = "INSERT INTO a2c0_receipt VALUES (?, 'p1', 'complete', ?, ?)"
    at_and_over(
        lambda n, size: db.execute(sql, (f"w{n}", hexd("a"), "x" * size)),
        research_store.MAX_RECEIPT_BYTES,
    )

    def insert(n: int, size: int) -> None:
        key = "a2-accepted:" + hexd(str(n))
        db.execute(
            "INSERT INTO a2c0_accepted_stage VALUES (?, ?, 'k', '1', 'complete', ?, ?)",
            (key, key, hexd("a"), "x" * size),
        )

    at_and_over(insert, research_limit("record_json"))


def mode_of(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_staging_backup_and_receipt_files_are_0600(tmp_path: Path) -> None:
    target = tmp_path / "stage" / "live.sqlite"
    Phase1Store(f"sqlite:///{target}", ResultSchemaRegistry.phase1()).close()
    check(mode_of(target) == 0o600, f"file mode {mode_of(target):o}")
    check(mode_of(target.parent) == 0o700, f"dir mode {mode_of(target.parent):o}")
    source = build_schema4(tmp_path / "live.sqlite")
    (tmp_path / "backups").mkdir()
    backup, _digest = create_backup(source, tmp_path / "backups")
    check(mode_of(backup) == 0o600, f"backup mode {mode_of(backup):o}")
    check(create_once(tmp_path, "claim-00000.json", b"{}"), "new file")
    check(mode_of(tmp_path / "claim-00000.json") == 0o600, "receipt file mode")


def test_second_writer_is_refused_while_the_first_holds_the_lock(
    tmp_path: Path,
) -> None:
    path = build_schema5(tmp_path / "a2.sqlite")
    holder = raw(path)
    if a2_schema.acquire_claim(holder, proof("w1")) is None:
        pytest.fail("fixture claim must be acquired")
    identity = stage_identity()
    result = result_for(identity, attempt="w1")
    published = a2_store.PublisherReceipt(result, proof("w1"))
    writer = sqlite3.connect(path, isolation_level=None, timeout=0.05)
    holder.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(a2_store.A2AcceptError, match="lock-failed"):
            a2_store.accept_result(writer, identity, published)
    finally:
        holder.execute("ROLLBACK")
    outcome = a2_store.accept_result(writer, identity, published).outcome
    check(outcome == "inserted", "the writer succeeds after the lock is free")
    writer.close()
    holder.close()


def test_schema4_reader_refuses_schema5_and_leaves_it_unchanged(
    tmp_path: Path,
) -> None:
    path = build_schema5(tmp_path / "five.sqlite")
    before = snapshot(path)
    with pytest.raises(IncompatibleSchemaError):
        Phase1Store(f"sqlite:///{path}", ResultSchemaRegistry.phase1())
    check(snapshot(path) == before, "refused open changed the file")


def test_migration_keeps_recorded_schema4_history(tmp_path: Path) -> None:
    key = "preparation_proof_legacy_terminal:r"
    path = build_schema4(tmp_path / "four.sqlite", legacy_keys=(key,))
    db = raw(path)
    with pytest.raises(a2_schema.A2SchemaError, match="migration-required"):
        a2_schema.require_schema5(db)
    before = snapshot(path)
    a2_schema.migrate_schema4_to_v5(db, GATE)
    check(a2_schema.classify_schema(db) is a2_schema.SchemaState.SCHEMA5, "schema 5")
    db.close()
    after = snapshot(path)
    for row in (r for r in before if len(r) == 4):  # type, name, table, sql
        check(row in after, f"schema 4 object changed: {row[1]}")
    check((key, "scope-x") in after, "legacy history row must stay")


def table_after(header: str) -> list[list[str]]:
    """Return the body rows of the table whose first header cell is ``header``."""
    lines = DOC.read_text(encoding="utf-8").splitlines()
    start = next((n for n, s in enumerate(lines) if s.startswith(f"| {header} |")), -1)
    check(start >= 0, f"decision record has no table headed {header!r}")
    body = list(takewhile(lambda line: line.startswith("|"), lines[start + 2 :]))
    return [[c.strip() for c in line.strip("|").split("|")] for line in body]


def code_value(name: str) -> int:
    """Resolve a documented ``module.NAME`` (or a DDL literal) to its code value."""
    if name == "a2_held_store.DDL.workset_index_max":
        found = re.search(r"workset_index BETWEEN 0 AND (\d+)", held_store.DDL)
        return int(found[1]) if found else -1
    if name == "a2_sqlite_ddl.record_json_max":
        return research_limit("record_json")
    module, _, attr = name.partition(".")
    target: object = importlib.import_module("msgloom.persistence." + module)
    for part in attr.split("."):
        target = getattr(target, part)
    return int(target)  # type: ignore[call-overload]


def test_doc_budget_table_matches_code_names_and_values() -> None:
    documented = {row[0].strip("`"): row[1] for row in table_after("Name")}
    for name, value in documented.items():
        check(code_value(name) == int(value), f"{name}: doc {value} != code")
    for file in PERSISTENCE.glob("a2_*.py"):
        for const in re.findall(
            r"^(MAX_\w+) *=", file.read_text("utf-8"), re.MULTILINE
        ):
            check(f"{file.stem}.{const}" in documented, f"{file.stem}.{const} missing")


def test_doc_per_kind_table_matches_default_policy() -> None:
    documented = {
        row[0].strip("`"): tuple(int(cell) for cell in row[1:])
        for row in table_after("Kind")
    }
    actual = {
        b.kind: (b.max_payload_bytes, b.payload_days, b.digest_days)
        for b in DEFAULT_POLICY.artifacts
    }
    check(documented == actual, "per-kind table differs from DEFAULT_POLICY")


def test_doc_enforcement_and_test_references_resolve() -> None:
    this_file = Path(__file__).read_text(encoding="utf-8")
    for row in table_after("Name"):
        for name, symbol in re.findall(r"`(\w+\.py)(?::(\w+))?", row[2]):
            file = PERSISTENCE / name
            check(file.is_file(), f"{name} is not a persistence module")
            check(symbol in file.read_text(encoding="utf-8"), f"{name} lacks {symbol}")
        for name in re.findall(r"`(test_\w+)`", row[3]):
            check(f"def {name}(" in this_file, f"missing test {name}")
        for rel in re.findall(r"`(tests/[\w/]+\.py)`", row[3]):
            check((ROOT / rel).is_file(), f"missing {rel}")


GAP_IDS = """GAP-WORKSET-COUNT GAP-WORKSET-BYTES GAP-KIND-LIMITS GAP-RETENTION-JOB
GAP-WORKSET-COUNT-GLOBAL GAP-RESEARCH-STORE-MODE GAP-BACKUP-DIR-MODE
GAP-BACKUP-RETENTION GAP-RECEIPT-DIR-MODE GAP-HISTORICAL-VERSION
GAP-RECORD-JSON-BYTES"""


def test_gap_every_unenforced_budget_is_listed_with_a_task() -> None:
    section = DOC.read_text(encoding="utf-8").split("## Not enforced yet", 1)[-1]
    expected = set(GAP_IDS.split())
    gaps = {i.split(":", 1)[0]: i for i in re.split(r"\n- (?=GAP-)", section)[1:]}
    check(set(gaps) == expected, f"gap list differs: {set(gaps) ^ expected}")
    for gap, text in gaps.items():
        check(re.search(r"Task: C0-\d+", text) is not None, f"{gap} has no task")


def test_gap_no_store_uses_the_policy_and_schema5_has_no_workset_column() -> None:
    for file in PERSISTENCE.glob("*.py"):
        text = file.read_text(encoding="utf-8")
        used = "a2_stage_budgets" in text or "retention_action" in text
        check(
            file.name == "a2_stage_budgets.py" or not used, f"{file.name} uses policy"
        )
    check("policy" not in inspect.signature(a2_store.accept_result).parameters, "param")
    db = sqlite3.connect(":memory:")
    for kind, _name, sql in a2_schema.A2_OBJECTS:
        if kind == "table":
            db.execute(sql)
    columns = {r[1] for r in db.execute("PRAGMA table_info(phase1_a2_accepted_stages)")}
    db.close()
    check(not any("workset" in column for column in columns), "workset column exists")


def test_gap_file_and_directory_modes_follow_the_umask(tmp_path: Path) -> None:
    source = build_schema4(tmp_path / "live.sqlite")
    backups = tmp_path / "backups"
    backups.mkdir()
    os.chmod(backups, 0o755)
    create_backup(source, backups)
    (tmp_path / "receipts").mkdir()
    old = os.umask(0)
    try:
        path = tmp_path / "research.sqlite"
        research_store.A2ResearchStore.create(path).close()
        store = receipt_store.ReceiptStore(tmp_path / "receipts")
        directory = store._directory(WORKSET_REF, create=True)
    finally:
        os.umask(old)
    check(mode_of(backups) == 0o755, "create_backup now sets the directory mode")
    check(mode_of(path) & 0o077 != 0, "research store file mode is now forced")
    check(mode_of(directory) & 0o077 != 0, "receipt directory mode is now forced")

"""C0-17c: v2 adapter and handler dispatch. Synthetic data, no providers."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import canonical_json_bytes
from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    Limitation,
    ResultRef,
    SemanticDataRef,
    StageResult,
    TerminalStatus,
)
from msgloom.triage_input import TriageInputCodec, build_triage_input
from msgloom.triage_input import adapter_v2 as adapter
from msgloom.triage_input.adapter_v2 import (
    AdapterError,
    InputTooLargeError,
    InputUnreadableError,
    LimitationOverflowError,
    LossyProjectionError,
    MixedVersionsError,
    UnsupportedVersionError,
    UpstreamStateError,
    V1ReadError,
    admit_upstream,
    classify_upstream,
    project_to_v1,
    read_triage_input,
    summarize_v2,
)
from msgloom.triage_input.codec_v2 import (
    DigestMismatchError,
    OversizedInputError,
    TriageInputV2Codec,
    TriageInputV2Error,
    UnknownVersionError,
    seal_snapshot,
)
from msgloom.triage_pipeline import TriageHandler, TriageReplayPlan
from tests.a2_kedro.helpers import check
from tests.a2_kedro.test_c0_17a import (
    SECRET,
    edit,
    incomplete_data,
    load,
    snapshot_data,
)
from tests.triage_input.helpers import config, record, selection
from tests.triage_pipeline.helpers import handler, open_store, save_selection, setup
from tests.triage_pipeline.test_handler import request

V2CODEC = TriageInputV2Codec()
#: Pinned from the handler before C0-17c. The v1 path must not change.
V1_GOLDEN_RESULT = (
    "triage:6fcb4ff23a80df75bdded71be1e5fa007aae86298246cfd83af135411c25e1c6"
)
V1_GOLDEN_SHA = "83930ce7fc9c13ba7cf0e03a0205d3afe0e7e0832c814825aebc2d21ecfb241c"


def v2_bytes(data: dict[str, Any] | None = None) -> bytes:
    return V2CODEC.encode(seal_snapshot(load(data or snapshot_data())))


def raw(data: dict[str, Any]) -> bytes:
    return canonical_json_bytes(data, max_bytes=2**31)


def refuses(call: Any, error: type[Exception]) -> Exception:
    """Check ``call`` raises exactly ``error`` with a fixed, clean message."""
    with pytest.raises(error) as caught:
        call()
    found = caught.value
    check(type(found) is error, f"expected {error.__name__}")
    check(found.__cause__ is None and found.__context__ is None, "no chain")
    check(SECRET not in str(found), "message has no input value")
    return found


# -- reading -----------------------------------------------------------------


def test_v2_payload_is_read_by_the_v2_codec_with_all_state() -> None:
    for make in (snapshot_data, incomplete_data):
        payload = v2_bytes(make())
        result = read_triage_input(payload)
        check(result.version == "2", "version")
        check(result.value == V2CODEC.decode(payload), "same as v2 codec")
    summary = summarize_v2(read_triage_input(v2_bytes(incomplete_data())).value)  # type: ignore[arg-type]
    check(summary.complete is False, "incomplete kept")
    check(summary.limitations == (Limitation("coverage_incomplete", "unit"),), "lims")
    check(summary.coverage_failures == 1, "failure kept")
    check(summary.held_sources == 1 and summary.selected_sources == 3, "held kept")
    check(summary.pending_parts == 2, "parts kept")


def test_v1_payload_stays_readable_and_unchanged(tmp_path: Path) -> None:
    v1 = build_triage_input(selection((record("one"),)), config())
    payload = TriageInputCodec().encode(v1)
    path = tmp_path / "v1.json"
    path.write_bytes(payload)
    result = read_triage_input(path.read_bytes())
    check(result.version == "1", "version")
    check(result.value == v1, "v1 value equals the v1 codec value")
    check(TriageInputCodec().encode(result.value) == payload, "byte identical")  # type: ignore[arg-type]


# -- negatives ---------------------------------------------------------------


def test_unknown_version_is_typed() -> None:
    good = json.loads(v2_bytes())
    refuses(
        lambda: read_triage_input(raw(edit(good, "header.version", "3"))),
        UnknownVersionError,
    )
    for text in ("2", "3", ""):
        refuses(
            lambda text=text: read_triage_input(raw({"schema_version": text})),
            UnsupportedVersionError,
        )
    refuses(lambda: read_triage_input(raw({"other": 1})), UnsupportedVersionError)


def test_tampered_digest_is_rejected() -> None:
    data = json.loads(v2_bytes())
    for field in ("binding_sha256", "configuration_sha256", "snapshot_sha256"):
        refuses(
            lambda f=field: read_triage_input(raw(edit(data, f, "1" * 64))),
            DigestMismatchError,
        )
    changed = edit(data, "units.0.occurrence_count", 13)
    refuses(lambda: read_triage_input(raw(changed)), DigestMismatchError)


def test_mixed_v1_and_v2_payload_is_rejected() -> None:
    both = edit(json.loads(v2_bytes()), "schema_version", "1")
    refuses(lambda: read_triage_input(raw(both)), MixedVersionsError)
    v1 = json.loads(
        TriageInputCodec().encode(
            build_triage_input(selection((record("a"),)), config())
        )
    )
    v1["header"] = json.loads(v2_bytes())["header"]
    refuses(lambda: read_triage_input(raw(v1)), MixedVersionsError)
    # A v2 snapshot that binds a v1 reference is not accepted either.
    old_ref = edit(
        json.loads(v2_bytes()), "binding.prepared.0.result.schema_version", "1"
    )
    refuses(lambda: read_triage_input(raw(old_ref)), UnknownVersionError)


def test_oversize_is_rejected_before_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    padded = b'{"header":{}}' + b" " * (V2CODEC.max_bytes + 1)
    refuses(lambda: read_triage_input(padded), OversizedInputError)
    monkeypatch.setattr(adapter, "MAX_TRIAGE_INPUT_BYTES", 64)
    refuses(lambda: read_triage_input(b" " * 65), InputTooLargeError)


def test_malformed_input_is_rejected_without_echo() -> None:
    for bad in (b"", b"\xff\xfe", b"not json", b"[1]", b'"x"', b"null", b"{"):
        refuses(lambda b=bad: read_triage_input(b), InputUnreadableError)
    refuses(lambda: read_triage_input(b'{"schema_version":"1"}'), V1ReadError)
    with pytest.raises(TriageInputV2Error) as caught:
        read_triage_input(b'{"header":{"kind":"%s"}}' % SECRET.encode())
    check(SECRET not in str(caught.value), "v2 codec error has no input value")
    check(issubclass(LossyProjectionError, AdapterError), "typed family")


def test_no_lossy_projection_ever() -> None:
    for make, expected in (
        (snapshot_data, {"v2-references", "held-sources", "baseline-context-role"}),
        (
            incomplete_data,
            {
                "v2-references",
                "held-sources",
                "baseline-context-role",
                "limitations",
                "coverage-failures",
                "incomplete-state",
            },
        ),
    ):
        snapshot = read_triage_input(v2_bytes(make())).value
        found = refuses(lambda s=snapshot: project_to_v1(s), LossyProjectionError)  # type: ignore[arg-type]
        check(set(found.reasons) == expected, f"reasons {found.reasons}")  # type: ignore[attr-defined]


# -- upstream dispatch -------------------------------------------------------


def ref(char: str, kind: str, version: str) -> ResultRef:
    return ResultRef(f"id-{char}", kind, version)


def stage(
    reference: ResultRef,
    *,
    status: TerminalStatus = TerminalStatus.COMPLETE,
    limitations: tuple[Limitation, ...] = (),
    data: bool = True,
) -> StageResult:
    return StageResult(
        result_id=reference.result_id,
        kind=reference.kind,
        schema_version=reference.schema_version,
        execution=ExecutionIdentity("upstream"),
        attempt=AttemptIdentity("attempt"),
        input_refs=(),
        source_versions=(),
        prepared_versions=(),
        topic_versions=(),
        configuration_version="cfg",
        code_version="code",
        status=status,
        acceptable=True,
        semantic_data_ref=(
            SemanticDataRef(
                reference.result_id + ":d",
                reference.kind,
                reference.schema_version,
                "a" * 64,
                10,
            )
            if data
            else None
        ),
        limitations=limitations,
    )


def family(version: str) -> tuple[ResultRef, ...]:
    return tuple(
        ref(k[0], k, version) for k in ("prepared", "filter_result", "group_result")
    )


def test_classify_and_admit_upstream() -> None:
    check(classify_upstream(()) is None, "empty")
    check(classify_upstream(family("1")) == "1", "v1")
    check(classify_upstream(family("2")) == "2", "v2")
    check(
        classify_upstream((ref("x", "triage", "9"), *family("1"))) == "1",
        "other kinds ignored",
    )
    v1 = tuple((r, stage(r)) for r in family("1"))
    check(admit_upstream(v1) is None, "v1 is not held")
    limit = Limitation("body_missing", "synthetic")
    v2 = [(r, stage(r)) for r in family("2")]
    v2[0] = (
        v2[0][0],
        stage(v2[0][0], status=TerminalStatus.INCOMPLETE, limitations=(limit,)),
    )
    hold = admit_upstream(v2)
    check(
        hold is not None and hold.status is TerminalStatus.INCOMPLETE, "held incomplete"
    )
    check(hold is not None and limit in hold.limitations, "limitation carried")
    check(
        hold is not None and hold.limitations[-1].code == adapter.HOLD_CODE,
        "hold marker",
    )
    complete = admit_upstream([(r, stage(r)) for r in family("2")])
    check(
        complete is not None and len(complete.limitations) == 1, "only the hold marker"
    )


def test_upstream_negatives() -> None:
    mixed = (
        ref("a", "prepared", "1"),
        ref("b", "filter_result", "2"),
        ref("c", "group_result", "2"),
    )
    refuses(lambda: classify_upstream(mixed), MixedVersionsError)
    refuses(
        lambda: classify_upstream((ref("a", "prepared", "3"),)), UnsupportedVersionError
    )
    refuses(
        lambda: classify_upstream(
            (ref("a", "prepared", "1"), ref("b", "prepared", "3"))
        ),
        UnsupportedVersionError,
    )
    limit = Limitation("body_missing", "synthetic")
    prepared = family("2")[0]
    bad = (
        stage(
            prepared, status=TerminalStatus.INCOMPLETE
        ),  # incomplete without limitation
        stage(prepared, limitations=(limit,)),  # complete with limitation
        stage(prepared, data=False),
        replace(
            stage(prepared),
            semantic_data_ref=SemanticDataRef("d", "prepared", "1", "a" * 64, 1),
        ),
    )
    for saved in bad:
        refuses(lambda s=saved: admit_upstream([(prepared, s)]), UpstreamStateError)
    many = tuple(Limitation(f"code_{i:03d}", "x") for i in range(64))
    heavy = stage(prepared, status=TerminalStatus.INCOMPLETE, limitations=many)
    refuses(lambda: admit_upstream([(prepared, heavy)]), LimitationOverflowError)


# -- handler -----------------------------------------------------------------


def test_handler_v1_is_byte_identical_to_the_pre_adapter_run(tmp_path: Path) -> None:
    asyncio.run(_v1_run(tmp_path))


async def _v1_run(tmp_path: Path) -> None:
    store = await open_store(tmp_path / "a3.sqlite")
    selected, producer, candidate = setup(allocations=2)
    await save_selection(store, selected)
    triage, runner = handler(store, producer, candidate)
    outcome = await triage.run(request(producer))
    check(outcome.status is TerminalStatus.COMPLETE, "v1 complete")
    check(outcome.limitations == () and outcome.failures == (), "v1 clean")
    check(runner.calls == 1, "one fake runner call")
    final = outcome.result_refs[0]
    check(final.result_id == V1_GOLDEN_RESULT, "v1 result id unchanged")
    saved = await store.get_result(final.result_id)
    check(saved is not None and saved.semantic_data_ref is not None, "saved")
    check(saved.semantic_data_ref.sha256 == V1_GOLDEN_SHA, "v1 bytes unchanged")  # type: ignore[union-attr]


class _OnlyResults:
    """Persistence double. Any call but ``get_result`` fails the test."""

    def __init__(self, results: dict[str, StageResult]) -> None:
        self.results = results

    async def get_result(self, result_id: str) -> StageResult | None:
        return self.results.get(result_id)

    def __getattr__(self, name: str) -> Any:
        pytest.fail(f"unexpected persistence call: {name}")


@dataclass(frozen=True)
class V2Case:
    """One v2 handler fixture. ``request`` is the exact admitted request."""

    triage: TriageHandler
    runner: Any
    saved: dict[str, StageResult]
    plan: TriageReplayPlan
    request: Any


def v2_handler(
    results: dict[str, StageResult] | None = None,
    *,
    versions: tuple[str, str, str] = ("2", "2", "2"),
) -> V2Case:
    _selected, producer, _candidate = setup()
    plan = producer.plan
    renamed = tuple(
        tuple(ResultRef(f"{SECRET}-{kind}", kind, v) for _ in old)
        for (kind, old), v in zip(
            (
                ("prepared", plan.prepared_results),
                ("filter_result", plan.filter_results),
                ("group_result", plan.group_results),
            ),
            versions,
            strict=True,
        )
    )
    plan = replace(
        plan,
        prepared_results=renamed[0],
        filter_results=renamed[1],
        group_results=renamed[2],
    )
    producer = replace(producer, plan=plan)
    saved = (
        results
        if results is not None
        else {r.result_id: stage(r) for group in renamed for r in group}
    )
    runner = type("Runner", (), {"calls": 0})()
    triage = TriageHandler(_OnlyResults(saved), producer, runner)  # type: ignore[arg-type]
    return V2Case(triage, runner, saved, plan, request(producer))


def test_handler_holds_v2_upstream_with_limitations_and_no_effects() -> None:
    limit = Limitation("body_missing", "synthetic")
    first = v2_handler()
    prepared = first.plan.prepared_results[0]
    first.saved[prepared.result_id] = stage(
        prepared, status=TerminalStatus.INCOMPLETE, limitations=(limit,)
    )
    case = v2_handler(first.saved)
    outcome = asyncio.run(case.triage.run(case.request))
    check(outcome.status is TerminalStatus.INCOMPLETE, "incomplete, not complete")
    check(limit in outcome.limitations, "upstream limitation carried")
    check(outcome.limitations[-1].code == adapter.HOLD_CODE, "hold marker last")
    check(outcome.result_refs == () and outcome.failures == (), "no result, no failure")
    check(case.runner.calls == 0, "no provider call")


def test_handler_fails_closed_on_bad_v2_upstream() -> None:
    cases = (
        (("1", "2", "2"), MixedVersionsError),
        (("2", "9", "2"), UnsupportedVersionError),
    )
    for versions, error in cases:
        case = v2_handler(versions=versions)
        outcome = asyncio.run(case.triage.run(case.request))
        check(outcome.status is TerminalStatus.FAILED, "failed")
        check(outcome.failures[0].code == "triage_input_invalid", "typed failure")
        check(outcome.failures[0].detail == error.__name__, "typed error name only")
        check(SECRET not in repr(outcome), "no input value in outcome")
    case = v2_handler()
    prepared = case.plan.prepared_results[0]
    case.saved[prepared.result_id] = stage(prepared, status=TerminalStatus.INCOMPLETE)
    outcome = asyncio.run(case.triage.run(case.request))
    check(outcome.status is TerminalStatus.FAILED, "silent incomplete is refused")
    check(outcome.failures[0].detail == UpstreamStateError.__name__, "state error")
    check(SECRET not in repr(outcome), "no input value in outcome")

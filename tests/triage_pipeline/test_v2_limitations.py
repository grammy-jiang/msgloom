"""C0-17g: A3 limitations and terminal proof for upstream triage_input@2.

Synthetic data only. Expected codes and detail text are written by hand.
The fake store keeps results in memory. Historical bytes live in ``tmp_path``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ClaimToken,
    ExecutionIdentity,
    Limitation,
    OperationRequest,
    PhaseCapability,
    ResultRef,
    SemanticDataRef,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.triage import SourceDisposition, SourceDispositionKind, TriageCandidate
from msgloom.triage_input import build_triage_input
from msgloom.triage_input.codec_v2 import seal_snapshot
from msgloom.triage_input.models_v2 import TriageInputSnapshot as V2Snapshot
from msgloom.triage_pipeline import finalize_mixin, limitations
from msgloom.triage_pipeline.common import RUN_STATE, RunState
from msgloom.triage_pipeline.finalize_mixin import _TriageFinalizeMixin
from msgloom.triage_pipeline.limitations import (
    KnownLimitationError,
    V2ProvenanceError,
    merge_trusted_source_limitations,
    v2_input_limitations,
    verify_v2_provenance,
)
from tests.a2_kedro.helpers import check, hexd
from tests.a2_kedro.test_c0_17a import incomplete_data, load, rref, snapshot_data
from tests.triage_input.helpers import config, record, selection

A_ID = "a2-accepted:" + hexd("a")
C_ID = "a2-accepted:" + hexd("c")


def sealed(data: dict[str, Any]) -> V2Snapshot:
    return seal_snapshot(load(data))


def clean_data() -> dict[str, Any]:
    """Complete snapshot, no held source: source c is active in the unit."""
    data = snapshot_data()
    data["held"] = []
    data["units"][0]["prepared"] = [rref("a"), rref("b"), rref("c")]
    return data


def incomplete() -> V2Snapshot:
    return sealed(incomplete_data())


def held_only() -> V2Snapshot:
    return sealed(snapshot_data())


def clean() -> V2Snapshot:
    return sealed(clean_data())


def v1_snapshot():
    return build_triage_input(selection((record("one"),)), config())


def refuses(call: Any, code: str) -> V2ProvenanceError:
    """Check ``call`` raises ``V2ProvenanceError`` with ``code``, no chain."""
    with pytest.raises(V2ProvenanceError) as caught:
        call()
    found = caught.value
    check(found.code == code, f"expected {code}, got {found.code}")
    check(isinstance(found, KnownLimitationError), "typed known-limitation base")
    check(found.__cause__ is None, "no chain")
    return found


# -- limitation derivation: positive -------------------------------------------


def test_incomplete_snapshot_yields_stable_codes_with_provenance() -> None:
    snap = incomplete()
    got = v2_input_limitations(snap)
    origin = f"snapshot_sha256={snap.snapshot_sha256}"
    check(
        [item.code for item in got]
        == [
            "triage-v2-coverage-failure",
            "triage-v2-held-source",
            "triage-v2-input-incomplete",
            "triage-v2-upstream-coverage_incomplete",
        ],
        "stable sorted codes",
    )
    coverage, held, whole, upstream = got
    check(
        coverage.detail
        == f"unit_id={hexd('7')} reason=part-count-exceeded remaining=7 "
        f"remaining_sha256={hexd('5')} {origin}",
        "coverage provenance",
    )
    check(
        held.detail == f"source={C_ID} filter={'a2-accepted:' + hexd('c')} "
        f"reasons=filter-excluded,filter-unknown {origin}",
        "held provenance",
    )
    check(
        whole.detail == f"{origin} binding_sha256={snap.binding_sha256}",
        "snapshot and binding digest",
    )
    check(upstream == Limitation(upstream.code, "unit"), "original detail kept")
    check(got == v2_input_limitations(snap), "deterministic")
    check(got == tuple(sorted(got, key=lambda x: (x.code, x.detail))), "ordered")


def test_held_source_alone_yields_one_held_limitation() -> None:
    snap = held_only()
    check(snap.complete is True, "fixture is a complete snapshot")
    got = v2_input_limitations(snap)
    check([item.code for item in got] == ["triage-v2-held-source"], "held only")
    check(A_ID not in got[0].detail and C_ID in got[0].detail, "names held source")
    check(snap.snapshot_sha256 in got[0].detail, "carries snapshot digest")


def test_expected_digest_that_matches_is_accepted() -> None:
    snap = incomplete()
    got = verify_v2_provenance(snap, snap.snapshot_sha256)
    check(got == snap, "same verified snapshot")


# -- limitation derivation: negative -------------------------------------------


def test_clean_complete_snapshot_has_no_limitation() -> None:
    check(v2_input_limitations(clean()) == (), "complete and no held source")


def test_missing_provenance_fails_closed() -> None:
    for value in (None, {}, "text", object(), v1_snapshot()):
        refuses(
            lambda value=value: v2_input_limitations(value), "v2-provenance-missing"
        )
    unvalidated = V2Snapshot.model_construct()
    refuses(lambda: v2_input_limitations(unvalidated), "v2-provenance-missing")
    blank = cast(V2Snapshot, incomplete().model_copy(update={"snapshot_sha256": ""}))
    refuses(lambda: v2_input_limitations(blank), "v2-provenance-missing")


def test_forged_digest_fails_closed() -> None:
    snap = incomplete()
    forged = snap.model_copy(update={"snapshot_sha256": hexd("f")})
    refuses(lambda: v2_input_limitations(forged), "v2-provenance-forged")
    other = snap.model_copy(update={"binding_sha256": hexd("e")})
    refuses(lambda: v2_input_limitations(other), "v2-provenance-forged")
    config_change = snap.configuration.model_copy(update={"max_part_bytes": 8192})
    edited = snap.model_copy(update={"configuration": config_change})
    refuses(lambda: v2_input_limitations(edited), "v2-provenance-forged")


def test_expected_digest_that_differs_is_forged() -> None:
    snap = incomplete()
    refuses(lambda: verify_v2_provenance(snap, hexd("9")), "v2-provenance-forged")


def test_dropping_incomplete_or_held_state_is_not_accepted() -> None:
    snap = incomplete()
    as_complete = snap.model_copy(update={"complete": True})
    refuses(lambda: v2_input_limitations(as_complete), "v2-provenance-invalid")
    no_held = snap.model_copy(update={"held": ()})
    refuses(lambda: v2_input_limitations(no_held), "v2-provenance-invalid")


def test_limitation_overflow_raises_instead_of_truncating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(limitations, "MAX_PROPAGATED_LIMITATIONS", 3)
    with pytest.raises(KnownLimitationError) as caught:
        v2_input_limitations(incomplete())
    check(caught.value.code == "v2-limitation-overflow", "overflow code")
    check(not isinstance(caught.value, V2ProvenanceError), "not a provenance error")


# -- finalize: terminal status -------------------------------------------------

BASE = (Limitation("working-context-missing", "synthetic"),)


def test_v1_terminal_state_is_unchanged() -> None:
    state = _TriageFinalizeMixin._terminal_state(v1_snapshot(), BASE)
    check(state == (TerminalStatus.COMPLETE, BASE), "v1 stays complete as given")
    empty = _TriageFinalizeMixin._terminal_state(v1_snapshot())
    check(empty == (TerminalStatus.COMPLETE, ()), "v1 empty limitations")


def test_v2_terminal_state_positive_and_negative() -> None:
    mixin = _TriageFinalizeMixin
    status, merged = mixin._terminal_state(clean(), BASE)
    check((status, merged) == (TerminalStatus.COMPLETE, BASE), "clean v2 completes")
    for snap in (incomplete(), held_only()):
        status, merged = mixin._terminal_state(snap, BASE)
        check(status is TerminalStatus.INCOMPLETE, "INCOMPLETE or held blocks proof")
        check(merged[: len(BASE)] == BASE, "base limitations first")
        check(merged[len(BASE) :] == v2_input_limitations(snap), "v2 limitations")
    status, merged = mixin._terminal_state(
        held_only(), v2_input_limitations(held_only())
    )
    check(merged == v2_input_limitations(held_only()), "no duplicate limitation")


def test_terminal_state_refuses_bad_input_and_overflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mixin = _TriageFinalizeMixin
    refuses(lambda: mixin._terminal_state(None), "v2-provenance-missing")
    refuses(lambda: mixin._terminal_state({"complete": True}), "v2-provenance-missing")
    forged = incomplete().model_copy(update={"snapshot_sha256": hexd("f")})
    refuses(lambda: mixin._terminal_state(forged), "v2-provenance-forged")
    monkeypatch.setattr(finalize_mixin, "MAX_PROPAGATED_LIMITATIONS", 1)
    with pytest.raises(KnownLimitationError) as caught:
        mixin._terminal_state(held_only(), BASE)
    check(caught.value.code == "v2-limitation-overflow", "merged overflow")


# -- finalize: saved result ----------------------------------------------------


@dataclass
class Store:
    """In-memory persistence double. It refuses to rewrite a result id."""

    results: dict[str, StageResult] = field(default_factory=dict)

    def semantic_reference(
        self, data_id: str, kind: str, version: str, value: object
    ) -> SemanticDataRef:
        return SemanticDataRef(data_id, kind, version, sha256(b"x").hexdigest(), 1)

    async def append_result_with_data(
        self, result: StageResult, data: object, *, claim: object
    ) -> None:
        if result.result_id in self.results:
            raise ValueError("result id already saved")
        self.results[result.result_id] = result


class Probe(_TriageFinalizeMixin):
    def __init__(self, store: Store) -> None:
        self._persistence = cast(Any, store)
        self._config = cast(
            Any,
            SimpleNamespace(
                configuration_version="cfg",
                code_version="code",
                rule_config=SimpleNamespace(version=VersionRef("rule", "r", "v1")),
                versions=SimpleNamespace(
                    prompt=VersionRef("prompt", "p", "v1"),
                    model=VersionRef("model", "m", "v1"),
                ),
                trusted_policy=SimpleNamespace(
                    models={VersionRef("model", "m", "v1"): "synthetic-model"}
                ),
                semantic_fingerprint=lambda: "fingerprint",
            ),
        )


REQUEST = OperationRequest(
    execution=ExecutionIdentity("exec-1"),
    caller="synthetic-app",
    capability=PhaseCapability.TRIAGE,
    target_inputs=(),
    authority_ref="synthetic-authority",
    parameters=(),
)
CLAIM = ClaimToken(
    "claim-key",
    "secret",
    ClaimKind.TRIAGE,
    ExecutionIdentity("exec-1"),
    AttemptIdentity("attempt"),
)


def finalize_args() -> tuple[Any, ...]:
    """Arguments of ``_save_triage`` after ``request``."""
    ref = ResultRef("input-result", "triage_input", "1")
    return (
        AttemptIdentity("attempt"),
        CLAIM,
        SimpleNamespace(topics=(), dispositions=()),
        (),
        ResultRef("rule-result", "triage_rules", "1"),
        ResultRef("context-result", "working_context", "1"),
        ref,
        (),
        SimpleNamespace(),
    )


def run_save(call: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setattr(
        finalize_mixin, "snapshot_ref", lambda _c: VersionRef("wc", "s", "v1")
    )

    async def main() -> Any:
        RUN_STATE.set(
            RunState(acceptance_deadline=asyncio.get_running_loop().time() + 60)
        )
        return await call()

    return asyncio.run(main())


def only(store: Store) -> StageResult:
    check(len(store.results) == 1, "exactly one result saved")
    return next(iter(store.results.values()))


def test_v1_save_is_identical_to_the_current_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plain, via_v2 = Store(), Store()
    first = run_save(
        lambda: Probe(plain)._save_triage(REQUEST, *finalize_args(), limitations=BASE),
        monkeypatch,
    )
    outcome = run_save(
        lambda: Probe(via_v2)._save_triage_v2(
            v1_snapshot(), REQUEST, *finalize_args(), limitations=BASE
        ),
        monkeypatch,
    )
    check(only(plain) == only(via_v2), "saved v1 result is identical")
    check(only(plain).status is TerminalStatus.COMPLETE, "v1 saves COMPLETE")
    check(outcome.status is TerminalStatus.COMPLETE, "v1 outcome COMPLETE")
    check(outcome.result_refs == (first,), "same result ref")
    check(outcome.limitations == BASE, "v1 outcome limitations")


def test_v1_source_limitation_merge_is_unchanged() -> None:
    """Hand-pinned output of the unchanged v1 merge for one gapped source."""
    gap = Limitation("time_unknown", "synthetic")
    source = record("src").model_copy(update={"limitations": (gap,)})
    candidate = TriageCandidate(
        topics=(),
        dispositions=(
            SourceDisposition(
                source_ref=source.source,
                kind=SourceDispositionKind.NO_REPORTABLE_CONTENT,
                reason="nothing",
            ),
        ),
    )
    merged, operation = merge_trusted_source_limitations(candidate, (source,))
    check(operation == (gap,), "known gap is propagated to the operation")
    check(len(merged.dispositions) == 1, "one disposition")
    check(
        merged.dispositions[0].kind is SourceDispositionKind.REVIEW_REQUIRED,
        "gapped source needs review",
    )
    check(
        merged.dispositions[0].reason
        == "Known incomplete source evidence requires review",
        "pinned reason",
    )


@pytest.mark.parametrize(
    ("name", "maker"), [("incomplete", incomplete), ("held", held_only)]
)
def test_v2_incomplete_or_held_never_saves_a_complete_proof(
    name: str, maker: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store()
    snap = maker()
    outcome = run_save(
        lambda: Probe(store)._save_triage_v2(
            snap, REQUEST, *finalize_args(), limitations=BASE
        ),
        monkeypatch,
    )
    saved = only(store)
    check(saved.status is TerminalStatus.INCOMPLETE, f"{name}: saved INCOMPLETE")
    check(outcome.status is TerminalStatus.INCOMPLETE, f"{name}: outcome INCOMPLETE")
    check(saved.limitations == outcome.limitations, "outcome equals saved")
    check(saved.limitations[0] == BASE[0], "base limitation kept")
    check(
        saved.limitations[1:] == v2_input_limitations(snap),
        "provenance limitations saved",
    )
    check(saved.acceptable is True, "incomplete result stays acceptable")


def test_v2_clean_snapshot_saves_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Store()
    outcome = run_save(
        lambda: Probe(store)._save_triage_v2(
            clean(), REQUEST, *finalize_args(), limitations=BASE
        ),
        monkeypatch,
    )
    check(only(store).status is TerminalStatus.COMPLETE, "clean v2 completes")
    check(only(store).limitations == BASE, "no extra limitation")
    check(outcome.status is TerminalStatus.COMPLETE, "outcome COMPLETE")


def test_forged_or_missing_v2_provenance_saves_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forged = incomplete().model_copy(update={"snapshot_sha256": hexd("f")})
    for bad, code in (
        (forged, "v2-provenance-forged"),
        (None, "v2-provenance-missing"),
    ):
        store = Store()

        def call(bad: Any = bad, store: Store = store) -> Any:
            return Probe(store)._save_triage_v2(bad, REQUEST, *finalize_args())

        with pytest.raises(V2ProvenanceError) as caught:
            run_save(call, monkeypatch)
        check(caught.value.code == code, f"expected {code}")
        check(store.results == {}, "fail closed: nothing written")
    store = Store()
    snap = incomplete()
    with pytest.raises(V2ProvenanceError) as caught:
        run_save(
            lambda: Probe(store)._save_triage_v2(
                snap,
                REQUEST,
                *finalize_args(),
                expected_snapshot_sha256=hexd("9"),
            ),
            monkeypatch,
        )
    check(caught.value.code == "v2-provenance-forged", "expected digest enforced")
    check(store.results == {}, "digest mismatch writes nothing")


def test_historical_result_bytes_are_not_mutated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history = tmp_path / "historical-result.bin"
    history.write_bytes(b'{"status":"complete","limitations":[]}\n')
    before = history.read_bytes()
    old = StageResult(
        result_id="triage:historical",
        kind="triage",
        schema_version="1",
        execution=ExecutionIdentity("old"),
        attempt=AttemptIdentity("old"),
        input_refs=(),
        source_versions=(),
        prepared_versions=(),
        topic_versions=(),
        configuration_version="cfg",
        code_version="code",
        status=TerminalStatus.COMPLETE,
        acceptable=True,
    )
    store = Store({old.result_id: old})
    for snap in (incomplete(), held_only(), clean(), v1_snapshot()):
        run_save(
            lambda snap=snap: Probe(store)._save_triage_v2(
                snap, REQUEST, *finalize_args()
            ),
            monkeypatch,
        )
        store.results.pop(next(k for k in store.results if k != old.result_id))
    check(history.read_bytes() == before, "historical file bytes unchanged")
    check(store.results == {old.result_id: old}, "historical result unchanged")
    # A repeat of the same result id is refused, never overwritten.
    run_save(
        lambda: Probe(store)._save_triage_v2(clean(), REQUEST, *finalize_args()),
        monkeypatch,
    )
    with pytest.raises(ValueError, match="already saved"):
        run_save(
            lambda: Probe(store)._save_triage_v2(clean(), REQUEST, *finalize_args()),
            monkeypatch,
        )
    check(old in store.results.values(), "historical result still present")

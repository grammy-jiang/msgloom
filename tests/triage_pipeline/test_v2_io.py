"""C0-17e: A3 io_mixin loads prepared@2 and prepared@1. Synthetic data only."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.results import (
    FilterResult,
    GroupResult,
    Prepared,
)
from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    Failure,
    Limitation,
    ResultRef,
    SemanticDataRef,
    StageResult,
    TerminalStatus,
)
from msgloom.preparation import PreparedRecord
from msgloom.triage_input import io_v2
from msgloom.triage_input.adapter_v2 import (
    AdapterError,
    LossyProjectionError,
    MixedVersionsError,
    UnsupportedVersionError,
    UpstreamStateError,
)
from msgloom.triage_input.codec_v2 import (
    DigestMismatchError,
    DuplicateKeyError,
    ExtraFieldError,
    HistoricalVersionError,
    InvalidValueError,
    MalformedInputError,
    NonCanonicalError,
    OversizedInputError,
    SchemaViolationError,
    TriageInputV2Error,
    UnknownKindError,
    UnknownVersionError,
)
from msgloom.triage_input.io_v2 import decode_v2, load_values
from msgloom.triage_pipeline.io_mixin import _TriageIOMixin
from tests.a2_kedro.helpers import check
from tests.a2_kedro.result_fixtures import (
    SENTINEL,
    filter_data,
    group_data,
    make,
    prepared_data,
    ref,
)
from tests.triage_input.helpers import record

LIMIT = {"code": "time_unknown", "detail": "synthetic"}
INCOMPLETE = {"status": "incomplete", "sent_at": None, "limitations": [LIMIT]}


@dataclass
class Loader:
    """Persistence double. It returns what the test stored, by data id."""

    values: dict[str, object] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)

    async def load_semantic_data(self, reference: SemanticDataRef) -> object:
        self.calls.append(reference.data_id)
        return self.values[reference.data_id]


@dataclass(frozen=True)
class Entry:
    ref: ResultRef
    saved: StageResult


def stage(reference: ResultRef, semantic: SemanticDataRef | None, **kw: Any) -> Any:
    status = kw.pop("status", TerminalStatus.COMPLETE)
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
        semantic_data_ref=semantic,
        limitations=kw.pop("limitations", ()),
        failures=kw.pop("failures", ()),
    )


def semantic_of(reference: ResultRef, payload: bytes, **kw: Any) -> SemanticDataRef:
    return SemanticDataRef(
        f"{reference.result_id}:d",
        reference.kind,
        kw.get("data_version", reference.schema_version),
        kw.get("sha", sha256(payload).hexdigest()),
        kw.get("size", len(payload)),
    )


def entry(
    kind: str, payload: bytes, char: str = "1", version: str = "2", **kw: Any
) -> Entry:
    """Return a saved result whose semantic reference describes ``payload``."""
    reference = ref(char, kind, version)
    semantic = semantic_of(reference, payload, **kw)
    extra: dict[str, Any] = {}
    if kw.get("incomplete"):
        extra = {
            "status": TerminalStatus.INCOMPLETE,
            "limitations": (Limitation("time_unknown", "synthetic"),),
        }
    return Entry(reference, stage(reference, semantic, **extra))


def encoded(cls: Any, data: dict[str, Any]) -> bytes:
    return make(cls, data).encode()


def load(
    entries: tuple[Entry, ...], values: dict[int, object], expected: type
) -> tuple[Any, Loader]:
    loader = Loader(
        {e.saved.semantic_data_ref.data_id: values[i] for i, e in enumerate(entries)}  # type: ignore[union-attr]
    )
    refs = tuple(e.ref for e in entries)
    by_id = {e.ref.result_id: e.saved for e in entries}
    return asyncio.run(load_values(loader, refs, by_id, expected)), loader


def refuses(call: Any, error: type[Exception]) -> Exception:
    """Check ``call`` raises exactly ``error``, clean of chain and payload."""
    with pytest.raises(error) as caught:
        call()
    found = caught.value
    check(type(found) is error, f"expected {error.__name__}, got {type(found)}")
    check(found.__cause__ is None and found.__context__ is None, "no chain")
    text = str(found) + repr(found)
    check(SENTINEL not in text and "alice" not in text, "no payload text")
    return found


# -- positive ----------------------------------------------------------------


def test_v1_loading_is_unchanged() -> None:
    first, second = record("one"), record("two")
    refs = (ResultRef("id-a", "prepared", "1"), ResultRef("id-b", "prepared", "1"))
    datas = [
        SemanticDataRef(f"{r.result_id}:d", "prepared", "1", "a" * 64, 5) for r in refs
    ]
    by_id = {r.result_id: stage(r, d) for r, d in zip(refs, datas, strict=True)}
    loader = Loader({datas[0].data_id: first, datas[1].data_id: second})
    got = asyncio.run(load_values(loader, refs, by_id, PreparedRecord))
    check(got == (first, second), "v1 values in plan order")
    check(loader.calls == [datas[0].data_id, datas[1].data_id], "one load per ref")
    check(asyncio.run(load_values(loader, (), {}, PreparedRecord)) == (), "empty")
    with pytest.raises(TypeError, match="unexpected type"):
        asyncio.run(
            load_values(
                Loader({datas[0].data_id: "x"}), refs[:1], by_id, PreparedRecord
            )
        )
    by_id[refs[0].result_id] = stage(refs[0], None)
    with pytest.raises(ValueError, match="semantic reference is missing"):
        asyncio.run(load_values(loader, refs[:1], by_id, PreparedRecord))


def test_io_mixin_delegates_to_the_loader() -> None:
    class Probe(_TriageIOMixin):
        def __init__(self, loader: Loader) -> None:
            self._persistence = loader  # type: ignore[assignment]

    payload = encoded(Prepared, prepared_data())
    item = entry("prepared", payload)
    loader = Loader({item.saved.semantic_data_ref.data_id: payload})  # type: ignore[union-attr]
    got = asyncio.run(
        Probe(loader)._load_values(
            (item.ref,), {item.ref.result_id: item.saved}, Prepared
        )
    )
    check(got == (Prepared.decode(payload),), "mixin returns the v2 record")


def test_v2_records_are_read_from_bytes_and_from_models() -> None:
    cases = (
        (Prepared, prepared_data(), "prepared"),
        (FilterResult, filter_data(), "filter_result"),
        (GroupResult, group_data(), "group_result"),
    )
    for cls, data, kind in cases:
        payload = encoded(cls, data)
        item = entry(kind, payload)
        as_bytes, _ = load((item,), {0: payload}, cls)
        as_model, _ = load((item,), {0: make(cls, data)}, cls)
        check(as_bytes == as_model == (cls.decode(payload),), f"{kind} read")
        check(isinstance(as_bytes[0], cls), f"{kind} type")


def test_v2_limitations_and_incomplete_state_are_preserved() -> None:
    payload = encoded(Prepared, prepared_data(**INCOMPLETE))
    item = entry("prepared", payload, incomplete=True)
    got, loader = load((item,), {0: payload}, Prepared)
    check(got[0].status is TerminalStatus.INCOMPLETE, "incomplete kept")
    check(got[0].limitations == (Limitation("time_unknown", "synthetic"),), "kept")
    check(len(loader.calls) == 1, "loaded once")
    # The saved result and the record must agree on both facts.
    complete = entry("prepared", payload)
    refuses(lambda: load((complete,), {0: payload}, Prepared), UpstreamStateError)
    quiet = encoded(Prepared, prepared_data())
    refuses(
        lambda: load(
            (entry("prepared", quiet, incomplete=True),), {0: quiet}, Prepared
        ),
        UpstreamStateError,
    )


def test_saved_result_with_failures_is_refused() -> None:
    payload = encoded(Prepared, prepared_data())
    item = entry("prepared", payload)
    failed = Entry(
        item.ref,
        stage(
            item.ref,
            item.saved.semantic_data_ref,
            failures=(Failure("upstream_failed", "synthetic"),),
        ),
    )
    refuses(lambda: load((failed,), {0: payload}, Prepared), UpstreamStateError)


# -- dispatch ----------------------------------------------------------------


def test_unknown_mixed_and_cross_version_refs_are_refused_before_loading() -> None:
    payload = encoded(Prepared, prepared_data())
    v1_ref = ResultRef("id-v1", "prepared", "1")
    two = entry("prepared", payload, "2")
    old = Entry(
        v1_ref, stage(v1_ref, SemanticDataRef("d1", "prepared", "1", "a" * 64, 1))
    )
    three = entry("prepared", payload, "3", "3")
    cases: tuple[tuple[Any, type[Exception], type], ...] = (
        ((two, old), MixedVersionsError, Prepared),
        ((three,), UnsupportedVersionError, Prepared),
        ((three, old), UnsupportedVersionError, PreparedRecord),
        ((two,), LossyProjectionError, PreparedRecord),
        ((old,), HistoricalVersionError, Prepared),
    )
    for entries, error, expected in cases:
        loader = Loader({e.saved.semantic_data_ref.data_id: payload for e in entries})  # type: ignore[union-attr]
        refs = tuple(e.ref for e in entries)
        by_id = {e.ref.result_id: e.saved for e in entries}
        refuses(
            lambda a=(loader, refs, by_id, expected): asyncio.run(load_values(*a)),
            error,
        )
        check(loader.calls == [], "nothing loaded")
    found = refuses(
        lambda: asyncio.run(
            load_values(
                Loader(), (two.ref,), {two.ref.result_id: two.saved}, PreparedRecord
            )
        ),
        LossyProjectionError,
    )
    check(found.reasons == ("v2-references",), "fixed reason")  # type: ignore[attr-defined]
    check(issubclass(LossyProjectionError, AdapterError), "typed family")


def test_wrong_kind_for_the_expected_type_is_refused() -> None:
    payload = encoded(FilterResult, filter_data())
    item = entry("filter_result", payload)
    refuses(lambda: load((item,), {0: payload}, Prepared), InvalidValueError)


# -- payload limits ----------------------------------------------------------


def test_oversized_source_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = encoded(Prepared, prepared_data())
    huge = entry("prepared", payload, size=io_v2.MAX_SOURCE_BYTES + 1)
    refuses(lambda: load((huge,), {0: payload}, Prepared), OversizedInputError)
    got = Loader({huge.saved.semantic_data_ref.data_id: payload})  # type: ignore[union-attr]
    refuses(
        lambda: asyncio.run(
            load_values(got, (huge.ref,), {huge.ref.result_id: huge.saved}, Prepared)
        ),
        OversizedInputError,
    )
    check(got.calls == [], "declared size stops the load")
    monkeypatch.setattr(io_v2, "MAX_SOURCE_BYTES", len(payload) - 1)
    lying = entry("prepared", payload, size=1)
    refuses(lambda: load((lying,), {0: payload}, Prepared), OversizedInputError)


def test_bad_bytes_are_refused_with_typed_errors() -> None:
    good = encoded(Prepared, prepared_data())
    data = json.loads(good)
    spaced = json.dumps(data, sort_keys=True).encode()
    twice = good[:-1] + b',"rule_version":"rule-2"}'
    extra = json.dumps(
        {**data, SENTINEL: SENTINEL}, sort_keys=True, separators=(",", ":")
    ).encode()
    floaty = json.dumps(
        {**data, "sent_at": 1.5}, sort_keys=True, separators=(",", ":")
    ).encode()
    cases: tuple[tuple[bytes, type[Exception]], ...] = (
        (spaced, NonCanonicalError),
        (twice, DuplicateKeyError),
        (extra, ExtraFieldError),
        (floaty, NonCanonicalError),
        (b"\xff\xfe", MalformedInputError),
        (b"not json", MalformedInputError),
        (b"[1]", MalformedInputError),
    )
    for payload, error in cases:
        item = entry("prepared", payload)
        refuses(lambda i=item, p=payload: load((i,), {0: p}, Prepared), error)
    short = json.dumps(
        {**data, "parts": []}, sort_keys=True, separators=(",", ":")
    ).encode()
    refuses(
        lambda: load((entry("prepared", short),), {0: short}, Prepared),
        SchemaViolationError,
    )


def test_digest_and_byte_count_must_match_the_saved_reference() -> None:
    payload = encoded(Prepared, prepared_data(rule_version=SENTINEL))
    bads: tuple[dict[str, Any], ...] = ({"sha": "0" * 64}, {"size": len(payload) + 1})
    for bad in bads:
        item = entry("prepared", payload, **bad)
        refuses(lambda i=item: load((i,), {0: payload}, Prepared), DigestMismatchError)
    # A changed payload under the original reference is also a mismatch.
    original = entry("prepared", payload)
    changed = encoded(Prepared, prepared_data(rule_version="other-rule"))
    refuses(lambda: load((original,), {0: changed}, Prepared), DigestMismatchError)


def test_header_pairs_and_mixed_markers_are_refused() -> None:
    data = json.loads(encoded(Prepared, prepared_data()))

    def raw(value: dict[str, Any]) -> bytes:
        return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

    def header(**kw: str) -> dict[str, Any]:
        return {**data, "header": {**data["header"], **kw}}

    cases: tuple[tuple[bytes, type[Exception]], ...] = (
        (raw(header(version="3")), UnknownVersionError),
        (raw(header(version="1")), HistoricalVersionError),
        (raw(header(kind=SENTINEL)), UnknownKindError),
        (raw(header(kind="filter_result")), UnknownKindError),
        (raw({**data, "schema_version": "1"}), MixedVersionsError),
        (raw({k: v for k, v in data.items() if k != "header"}), SchemaViolationError),
        (
            raw(
                {
                    **{k: v for k, v in data.items() if k != "header"},
                    "schema_version": "1",
                }
            ),
            HistoricalVersionError,
        ),
        (raw({**data, "header": "x"}), SchemaViolationError),
    )
    for payload, error in cases:
        item = entry("prepared", payload)
        refuses(lambda i=item, p=payload: load((i,), {0: p}, Prepared), error)
    semantic = semantic_of(ref("1", "prepared", "2"), b"{}")
    refuses(lambda: decode_v2(b"{}", dict, semantic), InvalidValueError)  # type: ignore[type-var]


def test_wrong_value_types_from_persistence_are_refused() -> None:
    payload = encoded(Prepared, prepared_data())
    item = entry("prepared", payload)
    wrong: tuple[object, ...] = (
        "text",
        {"header": {}},
        record("one"),
        make(FilterResult, filter_data()),
        None,
        7,
    )
    for value in wrong:
        refuses(lambda v=value: load((item,), {0: v}, Prepared), InvalidValueError)
    # A model changed without validation cannot match the saved digest.
    broken = make(Prepared, prepared_data()).model_copy(update={"parts": ()})
    refuses(lambda: load((item,), {0: broken}, Prepared), DigestMismatchError)
    # Semantic data of another version in the saved result is an upstream fault.
    other = entry("prepared", payload, data_version="1")
    refuses(lambda: load((other,), {0: payload}, Prepared), UpstreamStateError)


def test_missing_semantic_reference_and_error_families() -> None:
    check(issubclass(DigestMismatchError, TriageInputV2Error), "codec family")
    check(issubclass(MixedVersionsError, AdapterError), "adapter family")
    reference = ref("1", "prepared", "2")
    by_id = {reference.result_id: stage(reference, None)}
    with pytest.raises(ValueError, match="semantic reference is missing"):
        asyncio.run(load_values(Loader(), (reference,), by_id, Prepared))

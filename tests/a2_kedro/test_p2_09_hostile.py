"""P2-09 hostile-input checks: no input text reaches a decision or an error."""

from __future__ import annotations

import pytest

from msgloom.a2_kedro.contracts.parse import ParserReceipt
from msgloom.a2_kedro.parsers.failure_policy import (
    FailureDecision,
    FailurePolicyError,
    check_formats,
    classify_exception,
    decide,
    decide_from_receipt,
    parse_outcome,
    parse_reason,
)
from tests.a2_kedro.helpers import check
from tests.a2_kedro.test_p2_09 import HOSTILE, SECRET

#: Distinctive marker (>= 8 chars) that no policy text can contain.
MARKER = "ZQ-LEAK-7431"

#: Hostile inputs with the marker embedded, so short and empty inputs
#: are checked against a long substring instead of an empty prefix.
MARKED = tuple(
    variant
    for item in HOSTILE
    for variant in (item + MARKER, MARKER + item, item[:3] + MARKER + item[3:])
)


def all_decision_text(d: FailureDecision) -> str:
    return " ".join(
        [repr(d), str(d), d.outcome.value, d.reason.value, d.held_reason.value]
    )


def test_marker_is_distinctive_and_marked_inputs_are_not_formats() -> None:
    check(len(MARKER) >= 8, "marker is long enough")
    check(all(MARKER in m for m in MARKED), "marker is in every variant")
    check(len(MARKED) == 3 * len(HOSTILE), "three variants per input")
    check("" in HOSTILE, "the empty input is still covered")


@pytest.mark.parametrize("hostile", MARKED, ids=range(len(MARKED)))
def test_hostile_formats_never_reach_decisions(hostile: str) -> None:
    for declared, detected in ((hostile, "pdf"), ("pdf", hostile), (hostile, hostile)):
        got = check_formats(declared, detected)
        if got is None:
            pytest.fail("hostile text must not pass")
        text = all_decision_text(got)
        check(len(text) < 600, "decision text is small")
        check(text.isascii() and text.isprintable(), "decision text is plain")
        check(MARKER not in text, "no marker copied")
        check(SECRET not in text, "no secret copied")


@pytest.mark.parametrize("hostile", HOSTILE, ids=range(len(HOSTILE)))
def test_short_and_empty_hostile_formats_are_held(hostile: str) -> None:
    got = check_formats(hostile, hostile)
    if got is None:
        pytest.fail("hostile text must not pass")
    check(got.outcome.value == "unknown", "unknown detection is held")


@pytest.mark.parametrize("hostile", MARKED, ids=range(len(MARKED)))
def test_hostile_text_never_reaches_errors(hostile: str) -> None:
    calls = (
        lambda: parse_reason(hostile),
        lambda: parse_outcome(hostile),
        lambda: decide(hostile, hostile),
        lambda: decide("partial", hostile),
        lambda: decide(hostile, "size_limit"),
        lambda: check_formats(1, hostile),
        lambda: check_formats(hostile, 1),
        lambda: decide_from_receipt(hostile),  # type: ignore[arg-type]
    )
    for call in calls:
        with pytest.raises(FailurePolicyError) as info:
            call()
        message = str(info.value)
        check(len(message) < 80, "error text is short")
        check(message.isascii() and message.isprintable(), "error text is plain")
        check(MARKER not in message, "no marker copied")
        check(MARKER not in repr(info.value), "no marker in repr")
        check(info.value.__cause__ is None, "no chained cause")
        check(
            info.value.__context__ is None or info.value.__suppress_context__,
            "no visible chained context",
        )


@pytest.mark.parametrize(
    "error",
    [
        ValueError(SECRET),
        KeyError(SECRET),
        RuntimeError("A" * 100_000, SECRET),
        UnicodeDecodeError("utf-8", b"\xff", 0, 1, SECRET),
        OSError(2, SECRET, SECRET),
        TimeoutError(SECRET),
        ValueError(MARKER),
    ],
)
def test_parser_exception_becomes_unknown_without_its_text(error: Exception) -> None:
    d = classify_exception(error)
    check(d.outcome.value == "unknown", "exception is unknown")
    check(d.reason.value == "parser_failed", "reason is parser_failed")
    check(d.held_reason.value == "proof_missing", "held reason")
    check(SECRET not in all_decision_text(d), "no exception text in decision")
    check(MARKER not in all_decision_text(d), "no marker in decision")
    check(d == decide("unknown", "parser_failed"), "same as the table pair")


def test_classify_exception_rejects_non_exceptions() -> None:
    for bad in (KeyboardInterrupt(), "boom", None):
        with pytest.raises(FailurePolicyError):
            classify_exception(bad)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad",
    [*HOSTILE, "Size_Limit", "size-limit", "size_limit ", "complete", "ok"],
    ids=range(len(HOSTILE) + 5),
)
def test_parse_reason_rejects_text_outside_the_closed_set(bad: str) -> None:
    with pytest.raises(FailurePolicyError) as info:
        parse_reason(bad)
    check(SECRET not in str(info.value), "error has no input")
    check(str(info.value) == "reason is not in the closed set", "fixed text")


@pytest.mark.parametrize("bad", [None, 1, b"size_limit", ["size_limit"], 1.5])
def test_parse_reason_rejects_other_types(bad: object) -> None:
    with pytest.raises(FailurePolicyError):
        parse_reason(bad)


def test_parse_reason_rejects_str_subclass_with_odd_behavior() -> None:
    class Sneaky(str):
        def __hash__(self) -> int:
            return hash("size_limit")

    with pytest.raises(FailurePolicyError):
        parse_reason(Sneaky("size_limit"))


@pytest.mark.parametrize("bad", ["complete", "Partial", "", None, 3, "\ud800"])
def test_parse_outcome_rejects_unknown_values(bad: object) -> None:
    with pytest.raises(FailurePolicyError):
        parse_outcome(bad)


@pytest.mark.parametrize(
    "detected",
    [None, "unknown", "application/pdf", *HOSTILE],
    ids=range(len(HOSTILE) + 3),
)
def test_unknown_detected_format_is_unknown_even_if_declared_is_valid(
    detected: object,
) -> None:
    got = check_formats("pdf", detected)
    if got is None:
        pytest.fail("unknown detection must be held")
    check(got.outcome.value == "unknown", "outcome is unknown")
    check(got.reason.value == "detected_format_unknown", "reason")
    check(got.held_reason.value == "parser_unsupported", "held reason")
    check(check_formats(None, detected) == got, "no declared value, same result")
    check(check_formats(detected, detected) == got, "echoed claim, same result")


@pytest.mark.parametrize(
    "declared", ["application/x-evil", *HOSTILE], ids=range(len(HOSTILE) + 1)
)
def test_unknown_declared_text_is_a_mismatch_not_trusted(declared: str) -> None:
    got = check_formats(declared, "pdf")
    if got is None:
        pytest.fail("odd declared text must not pass")
    check(got.outcome.value == "mime_mismatch", "outcome is mime_mismatch")


@pytest.mark.parametrize("bad", [1, b"pdf", ["pdf"], object()])
def test_non_text_formats_are_rejected(bad: object) -> None:
    with pytest.raises(FailurePolicyError):
        check_formats(bad, "pdf")
    with pytest.raises(FailurePolicyError):
        check_formats("pdf", bad)


def _unchecked_receipt(outcome: str, limit: str) -> ParserReceipt:
    return ParserReceipt.model_construct(
        worker="w",
        worker_version="1",
        outcome=outcome,
        limit_hit=limit,
        input_bytes=10,
        part_count=1,
    )


@pytest.mark.parametrize("limit", ["bytes", "parts", "pages", "cells", "time", "x"])
def test_unchecked_complete_receipt_with_a_limit_is_rejected(limit: str) -> None:
    with pytest.raises(FailurePolicyError) as info:
        decide_from_receipt(_unchecked_receipt("complete", limit))
    check(str(info.value) == "complete receipt must not carry a limit", "fixed text")


def test_unchecked_receipts_with_odd_state_are_rejected() -> None:
    for outcome, limit in (("partial", "none"), ("done", "none"), ("", "bytes")):
        with pytest.raises(FailurePolicyError):
            decide_from_receipt(_unchecked_receipt(outcome, limit))
    check(decide_from_receipt(_unchecked_receipt("complete", "none")) is None, "ok")


@pytest.mark.parametrize(
    "bad", [None, "complete", 1, b"x", {"outcome": "complete"}, object()]
)
def test_non_receipt_input_is_rejected_with_fixed_text(bad: object) -> None:
    with pytest.raises(FailurePolicyError) as info:
        decide_from_receipt(bad)  # type: ignore[arg-type]
    check(str(info.value) == "receipt must be a ParserReceipt", "fixed text")


def test_duck_typed_receipt_is_rejected() -> None:
    class Fake:
        outcome = "complete"
        limit_hit = "none"

    with pytest.raises(FailurePolicyError):
        decide_from_receipt(Fake())  # type: ignore[arg-type]

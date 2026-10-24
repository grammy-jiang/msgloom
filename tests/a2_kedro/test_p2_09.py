"""P2-09 parser failure policy: closed reasons, MIME mismatch, held mapping."""

from __future__ import annotations

import dataclasses
import itertools
from typing import get_args

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.held import HeldReason
from msgloom.a2_kedro.contracts.parse import ParserReceipt, PartFormat
from msgloom.a2_kedro.parsers import failure_policy as fp
from msgloom.a2_kedro.parsers.failure_policy import (
    PARSER_AVAILABLE_FORMATS,
    UNSUPPORTED_FORMATS,
    FailureDecision,
    FailureOutcome,
    FailurePolicyError,
    FailureReason,
    check_formats,
    decide,
    decide_from_receipt,
    held_reason_for,
    parse_reason,
    to_disposition,
)
from tests.a2_kedro.helpers import CODE, CONFIG, check, root_for, workset

# --- expected values, written by hand from the rules ---------------------

OUTCOMES = ("unknown", "partial", "unsupported", "mime_mismatch")
REASONS = (
    "detected_format_unknown",
    "parser_failed",
    "no_parser_result",
    "size_limit",
    "part_limit",
    "page_limit",
    "cell_limit",
    "time_limit",
    "truncated_input",
    "format_not_supported",
    "encoding_not_supported",
    "encrypted_content",
    "detected_format_differs",
)
HELD_VALUES = (
    "role_unverifiable",
    "source_evidence_unavailable",
    "parser_unsupported",
    "input_limit",
    "proof_missing",
)

#: The only defined pairs. Every other pair must be rejected.
DEFINED = {
    ("unknown", "detected_format_unknown"): "parser_unsupported",
    ("unknown", "parser_failed"): "proof_missing",
    ("unknown", "no_parser_result"): "proof_missing",
    ("partial", "size_limit"): "input_limit",
    ("partial", "part_limit"): "input_limit",
    ("partial", "page_limit"): "input_limit",
    ("partial", "cell_limit"): "input_limit",
    ("partial", "time_limit"): "input_limit",
    ("partial", "truncated_input"): "source_evidence_unavailable",
    ("unsupported", "format_not_supported"): "parser_unsupported",
    ("unsupported", "encoding_not_supported"): "parser_unsupported",
    ("unsupported", "encrypted_content"): "parser_unsupported",
    ("mime_mismatch", "detected_format_differs"): "parser_unsupported",
}

SECRET = "alice.private@example.invalid"
KNOWN = ("rfc822", "html", "plain_text", "pdf", "docx", "xlsx", "csv")
NO_PARSER = ("image", "pptx")
ALL_FORMATS = (*KNOWN, *NO_PARSER)

HOSTILE = (
    SECRET,
    "A" * 1_000_000,
    "pdf\x00",
    "pdf\n",
    " pdf",
    "PDF",
    "pdf\u202e",
    "\ud800",
    "\udc00pdf",
    "\x1b[31mpdf",
    "",
    "рdf",
)


def receipt(outcome: str, limit: str) -> ParserReceipt:
    return ParserReceipt(
        worker="w",
        worker_version="1",
        outcome=outcome,  # type: ignore[arg-type]
        limit_hit=limit,  # type: ignore[arg-type]
        input_bytes=10,
        part_count=1,
    )


# --- (1) closed vocabulary ----------------------------------------------


def test_enums_hold_exactly_the_expected_members() -> None:
    check([m.value for m in FailureOutcome] == list(OUTCOMES), "outcomes are closed")
    check([m.value for m in FailureReason] == list(REASONS), "reasons are closed")
    check("complete" not in OUTCOMES, "there is no success outcome")


def test_held_reasons_are_the_existing_contract_vocabulary() -> None:
    check(tuple(h.value for h in HeldReason) == HELD_VALUES, "held vocab moved")
    for held in DEFINED.values():
        check(held in HELD_VALUES, "mapping targets an existing held reason")


@pytest.mark.parametrize("name", REASONS)
def test_parse_reason_accepts_each_exact_code(name: str) -> None:
    check(parse_reason(name).value == name, "exact code is accepted")


def test_policy_error_is_a_contract_error() -> None:
    check(issubclass(FailurePolicyError, A2ContractError), "shared error base")


# --- (2) MIME mismatch ---------------------------------------------------


@pytest.mark.parametrize(
    ("declared", "detected"),
    [
        ("pdf", "html"),
        ("html", "pdf"),
        ("plain_text", "docx"),
        ("xlsx", "csv"),
        ("pdf", "image"),  # mismatch wins over unsupported
        ("pptx", "pdf"),
    ],
)
def test_mismatch_is_held_and_never_trusts_declared(
    declared: str, detected: str
) -> None:
    got = check_formats(declared, detected)
    if got is None:
        pytest.fail("mismatch must produce a decision")
    check(got.outcome.value == "mime_mismatch", "outcome is mime_mismatch")
    check(got.reason.value == "detected_format_differs", "reason is differs")
    check(got.held_reason.value == "parser_unsupported", "held reason")
    check(not got.is_complete, "mismatch is not complete")


def test_swapping_declared_and_detected_changes_nothing_but_trust() -> None:
    forward = check_formats("pdf", "html")
    backward = check_formats("html", "pdf")
    check(forward == backward, "both orders hold as mismatch")


@pytest.mark.parametrize("fmt", KNOWN)
def test_agreeing_known_formats_pass(fmt: str) -> None:
    check(check_formats(fmt, fmt) is None, "agreement is not a failure")
    check(check_formats(None, fmt) is None, "absent declared value passes")


@pytest.mark.parametrize("fmt", NO_PARSER)
def test_agreeing_format_without_parser_is_unsupported(fmt: str) -> None:
    for declared in (fmt, None):
        got = check_formats(declared, fmt)
        if got is None:
            pytest.fail("format without parser must be held")
        check(got.outcome.value == "unsupported", "outcome is unsupported")
        check(got.reason.value == "format_not_supported", "reason")
        check(got.held_reason.value == "parser_unsupported", "held reason")


def test_every_part_format_is_in_exactly_one_of_allowlist_or_remainder() -> None:
    members = set(get_args(PartFormat))
    check(members == set(ALL_FORMATS), "a new PartFormat needs a decision here")
    check(PARSER_AVAILABLE_FORMATS <= members, "allowlist has only real members")
    check(
        PARSER_AVAILABLE_FORMATS.isdisjoint(UNSUPPORTED_FORMATS),
        "no format is in both sets",
    )
    check(
        PARSER_AVAILABLE_FORMATS | UNSUPPORTED_FORMATS == members,
        "every member is in one set",
    )
    check(PARSER_AVAILABLE_FORMATS == set(KNOWN), "allowlist is the hand-written list")
    check(UNSUPPORTED_FORMATS == set(NO_PARSER), "remainder is the hand-written list")


def test_format_outside_the_allowlist_is_unsupported_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A new PartFormat member must be held until a parser task lists it.
    monkeypatch.setattr(fp, "_KNOWN_FORMATS", fp._KNOWN_FORMATS | {"future_fmt"})
    for declared in ("future_fmt", None):
        got = check_formats(declared, "future_fmt")
        if got is None:
            pytest.fail("a format outside the allowlist must be held")
        check(got.outcome.value == "unsupported", "outcome is unsupported")
        check(got.reason.value == "format_not_supported", "reason")
    # Removing a listed format from the allowlist holds it too.
    monkeypatch.setattr(
        fp, "PARSER_AVAILABLE_FORMATS", PARSER_AVAILABLE_FORMATS - {"csv"}
    )
    held = check_formats("csv", "csv")
    check(held is not None and held.outcome.value == "unsupported", "csv held")


# --- (3) distinct outcomes, each held with a reason ----------------------


def test_unknown_partial_unsupported_are_distinct_and_held() -> None:
    unknown = decide("unknown", "parser_failed")
    partial = decide("partial", "size_limit")
    unsupported = decide("unsupported", "format_not_supported")
    check(len({unknown.outcome, partial.outcome, unsupported.outcome}) == 3, "distinct")
    check(len({unknown, partial, unsupported}) == 3, "distinct decisions")
    check(unknown.held_reason.value == "proof_missing", "unknown is held")
    check(partial.held_reason.value == "input_limit", "partial is held")
    check(unsupported.held_reason.value == "parser_unsupported", "unsupported held")


def test_decision_is_deterministic() -> None:
    check(decide("partial", "page_limit") == decide("partial", "page_limit"), "equal")
    check(
        hash(decide("partial", "page_limit")) == hash(decide("partial", "page_limit")),
        "equal hash",
    )


def test_decision_is_frozen() -> None:
    d = decide("unknown", "parser_failed")
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.outcome = FailureOutcome.PARTIAL  # type: ignore[misc]
    check(not hasattr(d, "__dict__"), "slots: no instance dict")
    # CPython raises TypeError here for a frozen slots dataclass.
    with pytest.raises((AttributeError, TypeError)):
        d.extra = 1  # type: ignore[attr-defined]


def test_hand_built_decision_must_match_the_table() -> None:
    ok = FailureDecision(
        FailureOutcome.PARTIAL, FailureReason.SIZE_LIMIT, HeldReason.INPUT_LIMIT
    )
    check(ok == decide("partial", "size_limit"), "valid hand-built decision")
    with pytest.raises(FailurePolicyError):  # wrong held reason
        FailureDecision(
            FailureOutcome.PARTIAL, FailureReason.SIZE_LIMIT, HeldReason.PROOF_MISSING
        )
    with pytest.raises(FailurePolicyError):  # undefined pair
        FailureDecision(
            FailureOutcome.PARTIAL,
            FailureReason.PARSER_FAILED,
            HeldReason.PROOF_MISSING,
        )
    with pytest.raises(FailurePolicyError):  # not a policy member
        FailureDecision(
            "partial",  # type: ignore[arg-type]
            FailureReason.SIZE_LIMIT,
            HeldReason.INPUT_LIMIT,
        )


def test_decision_requires_a_held_reason_member_not_equal_text() -> None:
    for text in ("input_limit", "INPUT_LIMIT", None, 1):
        with pytest.raises(FailurePolicyError) as info:
            FailureDecision(
                FailureOutcome.PARTIAL,
                FailureReason.SIZE_LIMIT,
                text,  # type: ignore[arg-type]
            )
        check(str(info.value) == "held reason must be a HeldReason member", "text")

    class Loose(str):
        pass

    with pytest.raises(FailurePolicyError):
        FailureDecision(
            FailureOutcome.PARTIAL,
            FailureReason.SIZE_LIMIT,
            Loose("input_limit"),  # type: ignore[arg-type]
        )


# --- (4) partial is never complete ---------------------------------------


@pytest.mark.parametrize(("outcome", "reason"), sorted(DEFINED))
def test_no_decision_is_complete(outcome: str, reason: str) -> None:
    d = decide(outcome, reason)
    check(d.is_complete is False, "failure is never complete")
    want = "partial" if outcome == "partial" else None
    check(d.receipt_outcome == want, "only partial keeps a partial receipt")


@pytest.mark.parametrize(
    ("limit", "reason"),
    [
        ("bytes", "size_limit"),
        ("parts", "part_limit"),
        ("pages", "page_limit"),
        ("cells", "cell_limit"),
        ("time", "time_limit"),
    ],
)
def test_partial_receipt_maps_to_partial_decision(limit: str, reason: str) -> None:
    d = decide_from_receipt(receipt("partial", limit))
    if d is None:
        pytest.fail("partial receipt must be held")
    check(d.outcome.value == "partial", "outcome stays partial")
    check(d.reason.value == reason, "reason follows the limit")
    check(d.held_reason.value == "input_limit", "held reason")
    check(not d.is_complete, "partial is not promoted")


def test_complete_receipt_has_no_failure() -> None:
    check(decide_from_receipt(receipt("complete", "none")) is None, "no failure")


def test_receipt_cannot_claim_complete_with_a_limit_or_partial_without() -> None:
    with pytest.raises(ValidationError):
        receipt("complete", "pages")
    with pytest.raises(ValidationError):
        receipt("partial", "none")


def test_no_policy_name_builds_a_success() -> None:
    names = [n for n in dir(fp) if not n.startswith("_")]
    for name in names:
        check("complete" not in name.lower(), name)
    check(not hasattr(FailureOutcome, "COMPLETE"), "no COMPLETE member")


# --- (5) totality --------------------------------------------------------


def test_every_outcome_reason_pair_is_defined_or_rejected() -> None:
    seen = 0
    for outcome, reason in itertools.product(OUTCOMES, REASONS):
        seen += 1
        want = DEFINED.get((outcome, reason))
        if want is None:
            with pytest.raises(FailurePolicyError) as info:
                decide(outcome, reason)
            check(
                str(info.value) == "reason is not defined for this outcome",
                "fixed rejection text",
            )
            continue
        got = decide(outcome, reason)
        check(got.held_reason.value == want, f"held reason of {outcome}/{reason}")
        check(got.outcome.value == outcome, "outcome kept")
        check(got.reason.value == reason, "reason kept")
    check(seen == 4 * 13, "all 52 pairs were visited")
    check(len(DEFINED) == 13, "13 pairs are defined")


def test_every_reason_is_used_by_exactly_one_outcome() -> None:
    for reason in REASONS:
        owners = [o for (o, r) in DEFINED if r == reason]
        check(len(owners) == 1, f"{reason} has one owning outcome")


def test_held_reason_for_rejects_wire_text_and_non_members() -> None:
    with pytest.raises(FailurePolicyError):
        held_reason_for("partial", "size_limit")  # type: ignore[arg-type]
    with pytest.raises(FailurePolicyError):
        held_reason_for(FailureOutcome.PARTIAL, "size_limit")  # type: ignore[arg-type]


def test_every_decision_has_an_input_disposition() -> None:
    root = root_for(workset())
    for (outcome, reason), held in sorted(DEFINED.items()):
        record = to_disposition(
            root,
            decide(outcome, reason),
            configuration_version=CONFIG,
            code_version=CODE,
        )
        check(record.reason.value == held, f"held record for {outcome}/{reason}")
        check(record.repair_class == "operator_repair", "explicit repair class")
        record.validate_against(root)


def test_to_disposition_rejects_a_non_decision() -> None:
    root = root_for(workset())
    with pytest.raises(FailurePolicyError):
        to_disposition(
            root,
            "proof_missing",  # type: ignore[arg-type]
            configuration_version=CONFIG,
            code_version=CODE,
        )


# --- (6) hostile input: see test_p2_09_hostile.py ---


def test_module_has_no_logging_or_io_imports() -> None:
    source = fp.__doc__ or ""
    check("pure python" in source.lower(), "module states that it is pure")
    for name in ("logging", "open", "print", "Path", "subprocess", "socket"):
        check(name not in vars(fp), f"module does not bind {name}")

"""
Typed parser failure policy (P2-09): every parser failure becomes a held outcome.

The policy is pure Python. It does no I/O and no logging. It reads no
message text, so no decision, repr or error can carry content.

Outcomes (:class:`FailureOutcome`) are four distinct failure kinds:

* ``UNKNOWN``: the format or the parse result cannot be proved.
* ``PARTIAL``: a parser worker stopped at a limit and kept some evidence.
* ``UNSUPPORTED``: the format, encoding or content has no parser.
* ``MIME_MISMATCH``: the declared format differs from the detected format.

There is no ``COMPLETE`` outcome here. A failure is never a success and a
``PARTIAL`` decision is never complete (:attr:`FailureDecision.is_complete`
is always false). The policy has no way to build a success.

Reasons (:class:`FailureReason`) are a closed set of content-free codes.
Wire text that is not exactly one code is rejected (:func:`parse_reason`).
The reason table (``_TABLE``) lists every defined ``(outcome, reason)``
pair and the :class:`~msgloom.a2_kedro.contracts.held.HeldReason` it maps
to. Any other pair is rejected with :exc:`FailurePolicyError`. The table is
total in this sense: each pair is defined or explicitly rejected.

Held mapping: the existing closed ``HeldReason`` vocabulary is reused and
not extended. It has no dedicated codes for mismatch, unknown or partial,
so the finer detail stays in the policy outcome and reason, and the held
reason is the closest existing code (see ``_TABLE``).

Format check: :func:`check_formats` never trusts the declared format. The
detected format decides. A declared value that is not the detected value
is a mismatch, also when the declared value is not a known format.

PII: errors use fixed text. A declared or detected value is never copied
into a reason, a decision or an error. :func:`classify_exception` ignores
the exception message and its arguments.

CANDIDATE/RESEARCH, PROVISIONAL: reason names and the unsupported format
list are not frozen.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final, get_args

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.held import HeldReason, InputDisposition
from msgloom.a2_kedro.contracts.parse import (
    LimitHit,
    ParserReceipt,
    PartFormat,
    WorkerOutcome,
)
from msgloom.a2_kedro.contracts.source import FrozenRoot

#: Formats that have no parser yet. Provisional; a parser task removes one.
UNSUPPORTED_FORMATS: Final[frozenset[str]] = frozenset({"image", "pptx"})

_KNOWN_FORMATS: Final[frozenset[str]] = frozenset(get_args(PartFormat))


class FailurePolicyError(A2ContractError):
    """Raised for an invalid policy input. The message is fixed text."""


class FailureOutcome(StrEnum):
    """Closed failure kinds. There is no success member."""

    UNKNOWN = "unknown"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    MIME_MISMATCH = "mime_mismatch"


class FailureReason(StrEnum):
    """Closed, content-free reason codes."""

    DETECTED_FORMAT_UNKNOWN = "detected_format_unknown"
    PARSER_FAILED = "parser_failed"
    NO_PARSER_RESULT = "no_parser_result"
    SIZE_LIMIT = "size_limit"
    PART_LIMIT = "part_limit"
    PAGE_LIMIT = "page_limit"
    CELL_LIMIT = "cell_limit"
    TIME_LIMIT = "time_limit"
    TRUNCATED_INPUT = "truncated_input"
    FORMAT_NOT_SUPPORTED = "format_not_supported"
    ENCODING_NOT_SUPPORTED = "encoding_not_supported"
    ENCRYPTED_CONTENT = "encrypted_content"
    DETECTED_FORMAT_DIFFERS = "detected_format_differs"


O, R, H = FailureOutcome, FailureReason, HeldReason

#: Every defined pair and its held reason. Any other pair is rejected.
_TABLE: Final[dict[tuple[FailureOutcome, FailureReason], HeldReason]] = {
    (O.UNKNOWN, R.DETECTED_FORMAT_UNKNOWN): H.PARSER_UNSUPPORTED,
    (O.UNKNOWN, R.PARSER_FAILED): H.PROOF_MISSING,
    (O.UNKNOWN, R.NO_PARSER_RESULT): H.PROOF_MISSING,
    (O.PARTIAL, R.SIZE_LIMIT): H.INPUT_LIMIT,
    (O.PARTIAL, R.PART_LIMIT): H.INPUT_LIMIT,
    (O.PARTIAL, R.PAGE_LIMIT): H.INPUT_LIMIT,
    (O.PARTIAL, R.CELL_LIMIT): H.INPUT_LIMIT,
    (O.PARTIAL, R.TIME_LIMIT): H.INPUT_LIMIT,
    (O.PARTIAL, R.TRUNCATED_INPUT): H.SOURCE_EVIDENCE_UNAVAILABLE,
    (O.UNSUPPORTED, R.FORMAT_NOT_SUPPORTED): H.PARSER_UNSUPPORTED,
    (O.UNSUPPORTED, R.ENCODING_NOT_SUPPORTED): H.PARSER_UNSUPPORTED,
    (O.UNSUPPORTED, R.ENCRYPTED_CONTENT): H.PARSER_UNSUPPORTED,
    (O.MIME_MISMATCH, R.DETECTED_FORMAT_DIFFERS): H.PARSER_UNSUPPORTED,
}

#: Receipt limit name to partial reason. ``none`` is not a limit.
_LIMIT_REASONS: Final[dict[str, FailureReason]] = {
    "bytes": R.SIZE_LIMIT,
    "parts": R.PART_LIMIT,
    "pages": R.PAGE_LIMIT,
    "cells": R.CELL_LIMIT,
    "time": R.TIME_LIMIT,
}


def held_reason_for(outcome: FailureOutcome, reason: FailureReason) -> HeldReason:
    """Return the held reason of a defined pair; reject any other pair."""
    if not isinstance(outcome, FailureOutcome) or not isinstance(reason, FailureReason):
        raise FailurePolicyError("outcome and reason must be policy members")
    held = _TABLE.get((outcome, reason))
    if held is None:
        raise FailurePolicyError("reason is not defined for this outcome")
    return held


def parse_reason(value: object) -> FailureReason:
    """
    Return the reason for exact wire text; reject anything else.

    Matching is exact and case-sensitive. Padding, other types and unknown
    text raise :exc:`FailurePolicyError` and are never echoed.
    """
    if isinstance(value, FailureReason):
        return value
    if type(value) is not str:
        raise FailurePolicyError("reason must be text")
    try:
        return FailureReason(value)
    except ValueError:
        raise FailurePolicyError("reason is not in the closed set") from None


def parse_outcome(value: object) -> FailureOutcome:
    """Return the outcome for exact wire text; reject anything else."""
    if isinstance(value, FailureOutcome):
        return value
    if type(value) is not str:
        raise FailurePolicyError("outcome must be text")
    try:
        return FailureOutcome(value)
    except ValueError:
        raise FailurePolicyError("outcome is not in the closed set") from None


@dataclass(frozen=True, slots=True)
class FailureDecision:
    """
    One checked failure: outcome, reason and the held reason it maps to.

    Construction re-checks the pair, so a hand-built decision cannot carry
    an undefined pair or a wrong held reason. The decision holds only enum
    members, so its ``repr`` shows no content.
    """

    outcome: FailureOutcome
    reason: FailureReason
    held_reason: HeldReason

    def __post_init__(self) -> None:
        if held_reason_for(self.outcome, self.reason) != self.held_reason:
            raise FailurePolicyError("held reason differs from the policy table")

    @property
    def is_complete(self) -> bool:
        """Always false: a failure is never a completed parse."""
        return False

    @property
    def receipt_outcome(self) -> WorkerOutcome | None:
        """Return ``partial`` for kept partial evidence, else ``None``."""
        return "partial" if self.outcome is FailureOutcome.PARTIAL else None


def decide(outcome: object, reason: object) -> FailureDecision:
    """
    Build the decision for an outcome and a reason (members or wire text).

    Raise :exc:`FailurePolicyError` for text outside the closed sets and
    for a pair that the table does not define.
    """
    out, why = parse_outcome(outcome), parse_reason(reason)
    return FailureDecision(out, why, held_reason_for(out, why))


def decide_from_receipt(receipt: ParserReceipt) -> FailureDecision | None:
    """
    Return the decision for a worker receipt, or ``None`` when complete.

    A ``partial`` receipt maps to ``PARTIAL`` with the reason of its limit.
    ``ParserReceipt`` already rejects ``partial`` with ``limit_hit`` of
    ``none`` and ``complete`` with a limit, so a limit always maps.
    """
    if receipt.outcome == "complete":
        return None
    limit: LimitHit = receipt.limit_hit
    why = _LIMIT_REASONS.get(limit)
    if why is None:
        raise FailurePolicyError("partial receipt has no limit")
    return decide(FailureOutcome.PARTIAL, why)


def _format_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise FailurePolicyError(f"{label} format must be text or None")
    return value


def check_formats(declared: object, detected: object) -> FailureDecision | None:
    """
    Compare the declared and the detected format; return a failure or ``None``.

    Order of rules, first match wins:

    1. A detected value that is absent or not a known format is ``UNKNOWN``.
    2. A declared value that is present and not equal to the detected value
       is ``MIME_MISMATCH``. The declared value is never trusted.
    3. A detected format with no parser is ``UNSUPPORTED``.

    ``None`` means the formats agree and have a parser. A non-text value
    raises :exc:`FailurePolicyError`. No value is copied to the result.
    """
    claim = _format_text(declared, "declared")
    found = _format_text(detected, "detected")
    if found is None or found not in _KNOWN_FORMATS:
        return decide(FailureOutcome.UNKNOWN, FailureReason.DETECTED_FORMAT_UNKNOWN)
    if claim is not None and claim != found:
        return decide(
            FailureOutcome.MIME_MISMATCH, FailureReason.DETECTED_FORMAT_DIFFERS
        )
    if found in UNSUPPORTED_FORMATS:
        return decide(FailureOutcome.UNSUPPORTED, FailureReason.FORMAT_NOT_SUPPORTED)
    return None


def classify_exception(error: Exception) -> FailureDecision:
    """
    Map a parser exception to ``UNKNOWN`` / ``PARSER_FAILED``.

    Only the fact of a failure is used. The exception type, message and
    arguments are ignored, because a parser error can quote message text.
    Callers must not catch ``BaseException`` for this call.
    """
    if not isinstance(error, Exception):
        raise FailurePolicyError("a parser failure must be an exception")
    return decide(FailureOutcome.UNKNOWN, FailureReason.PARSER_FAILED)


def to_disposition(
    root: FrozenRoot,
    decision: FailureDecision,
    *,
    configuration_version: str,
    code_version: str,
) -> InputDisposition:
    """
    Build the held record for ``decision``; there is no success path.

    The record copies its source fields from the verified ``root`` and
    carries only the closed held reason of the decision.
    """
    if not isinstance(decision, FailureDecision):
        raise FailurePolicyError("decision must be a FailureDecision")
    return InputDisposition.from_root(
        root,
        decision.held_reason,
        configuration_version=configuration_version,
        code_version=code_version,
    )

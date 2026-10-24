"""
Read-only scoped progress status for A2 v2 (CANDIDATE/RESEARCH).

This module is a pure mapping layer. Its input is an already-typed A2
contract object (:class:`CompletionReceipt`, :class:`InputDisposition` or
a :class:`ScopeStatusError`) plus the small :class:`ScopeProgress` that
names the frozen scope. Its output is a frozen :class:`ScopeStatus`, a
stable process exit code and a one-line text.

The :class:`ScopeProgress` also names the frozen workset reference. A
receipt for another workset raises :exc:`ScopeInputError` before any count
is read, so a foreign receipt never gives ``COMPLETE``. The scope id is a
digest, never free text, so an address or a path cannot enter a status.

Boundaries: no database is opened, nothing is written, the environment is
never read and no persistence module is imported. A caller that wants a
status from storage must load typed objects first. The status holds only a
closed state, the scope id, counts and limitation codes. The text line
holds none of the scope id, identity values, paths or limitation detail.

Completion rule: ``COMPLETE`` is reported only when the receipt covers
every expected occurrence, every root and the batch are COMPLETE, no
occurrence is missing, nothing is held and the receipt itself says
COMPLETE. The status is recomputed from the roots. A receipt status that
claims more is ignored. Anything else is never ``COMPLETE``.

Exit codes follow ``msgloom/cli/runner.py``: 0 is success and 4 is a
failed operation (reused here for claim loss). That module keeps 2 for
invalid input and 3 for an untrusted authority, so this table avoids both.
The other values are new, provisional and documented in
:data:`EXIT_CODES`.

CANDIDATE/RESEARCH: nothing calls this module yet.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Mapping, Sequence
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, ClassVar

from pydantic import Field, model_validator

from msgloom.a2_kedro.contracts.codec import A2ContractError, A2Model, Digest
from msgloom.a2_kedro.contracts.held import KIND as HELD_KIND
from msgloom.a2_kedro.contracts.held import InputDisposition
from msgloom.a2_kedro.contracts.receipt import CompletionReceipt, TerminalRoot
from msgloom.contracts import ResultRef, TerminalStatus

COMPLETE, INCOMPLETE = TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE
#: Provisional bound; it equals the receipt root bound.
MAX_OCCURRENCES = 1024
#: Provisional bound on distinct limitation codes in one status.
MAX_CODES = 64
#: A limitation code that may appear in a status or in the text line.
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
#: A scope id is a lowercase SHA-256 digest (same pattern as ``Digest``).
_SCOPE_DIGEST = re.compile(r"^[0-9a-f]{64}$")
#: Fixed stand-ins; they keep unsafe or excess codes out of the status.
UNSAFE_CODE = "limitation_code_unsafe"
TRUNCATED_CODE = "limitation_codes_truncated"


class ScopeState(StrEnum):
    """
    Closed states of one scope. ``HELD`` and ``BUSY`` are INCOMPLETE.

    The wire names are provisional until a CLI decision confirms them.
    """

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    HELD = "held"
    BUSY = "busy"
    BLOCKED_SOURCE = "blocked_source"
    BLOCKED_REFERENCE = "blocked_reference"
    BLOCKED_CATALOG = "blocked_catalog"
    CLAIM_LOST = "claim_lost"

    @property
    def terminal_status(self) -> TerminalStatus:
        """Return the contract status that this state reports."""
        return _TERMINAL[self]


_TERMINAL: Mapping[ScopeState, TerminalStatus] = MappingProxyType(
    {
        ScopeState.COMPLETE: COMPLETE,
        ScopeState.INCOMPLETE: INCOMPLETE,
        ScopeState.HELD: INCOMPLETE,
        ScopeState.BUSY: INCOMPLETE,
        ScopeState.BLOCKED_SOURCE: TerminalStatus.BLOCKED,
        ScopeState.BLOCKED_REFERENCE: TerminalStatus.BLOCKED,
        ScopeState.BLOCKED_CATALOG: TerminalStatus.BLOCKED,
        ScopeState.CLAIM_LOST: TerminalStatus.FAILED,
    }
)

#: Process exit codes, one per state. Only 0 and 4 are shared with
#: ``runner.py`` and only those two are stable. The values 20 to 32 are
#: PROVISIONAL, as are the state wire names and the limitation codes
#: ``occurrence_missing``, ``batch_missing`` and ``intake_held``. A script
#: must not rely on them until a CLI decision confirms them.
EXIT_CODES: Mapping[ScopeState, int] = MappingProxyType(
    {
        ScopeState.COMPLETE: 0,
        ScopeState.CLAIM_LOST: 4,
        ScopeState.INCOMPLETE: 20,
        ScopeState.BUSY: 21,
        ScopeState.HELD: 22,
        ScopeState.BLOCKED_SOURCE: 30,
        ScopeState.BLOCKED_REFERENCE: 31,
        ScopeState.BLOCKED_CATALOG: 32,
    }
)
#: Exit code for a bad command line of :func:`main` (as in ``runner.py``).
EXIT_INVALID = 2


class ScopeStatusError(Exception):
    """
    Base of every typed status error. The message is fixed.

    A subclass names its ``state`` and a safe ``code``. No subclass takes
    an argument, so no identifier or detail can enter the message.
    """

    state: ClassVar[ScopeState | None] = None
    code: ClassVar[str] = "scope_status_invalid"
    message: ClassVar[str] = "scope status input is invalid"

    def __init__(self) -> None:
        super().__init__(self.message)


class ScopeInputError(ScopeStatusError):
    """A status input has the wrong type, shape or coverage."""


class BlockedSourceError(ScopeStatusError):
    """The source evidence for the scope is not available."""

    state = ScopeState.BLOCKED_SOURCE
    code = "blocked_source"
    message = "scope is blocked: source unavailable"


class BlockedReferenceError(ScopeStatusError):
    """A result reference that the scope needs cannot be resolved."""

    state = ScopeState.BLOCKED_REFERENCE
    code = "blocked_reference"
    message = "scope is blocked: reference unresolved"


class BlockedCatalogError(ScopeStatusError):
    """The catalog identity of the scope is unavailable or differs."""

    state = ScopeState.BLOCKED_CATALOG
    code = "blocked_catalog"
    message = "scope is blocked: catalog unavailable"


class BusyScopeError(ScopeStatusError):
    """Another claim is active for the scope. The result is INCOMPLETE."""

    state = ScopeState.BUSY
    code = "claim_active"
    message = "scope is busy: another claim is active"


class ClaimLostError(ScopeStatusError):
    """The claim of this attempt was lost. The result is FAILED."""

    state = ScopeState.CLAIM_LOST
    code = "claim_lost"
    message = "scope claim was lost"


class HeldTerminalError(ScopeStatusError):
    """An A2-held terminal root cannot be COMPLETE. It stays INCOMPLETE."""

    state = ScopeState.HELD
    code = "a2_held_terminal"
    message = "A2 held terminal root is never complete"


class ScopeProgress(A2Model):
    """The frozen scope that a receipt must cover, as a workset and counts."""

    scope_id: Digest
    workset: ResultRef
    expected_occurrences: Annotated[int, Field(ge=0, le=MAX_OCCURRENCES)]
    expects_batch: bool = False
    expected_intake_held: Annotated[int, Field(ge=0, le=MAX_OCCURRENCES)] = 0

    @model_validator(mode="after")
    def _not_empty(self) -> ScopeProgress:
        if not (
            self.expected_occurrences or self.expects_batch or self.expected_intake_held
        ):
            raise A2ContractError("scope has no frozen work")
        return self


class ScopeStatus(A2Model):
    """Frozen status of one scope: state, counts and limitation codes."""

    scope_id: Digest
    state: ScopeState
    occurrences: Annotated[int, Field(ge=0, le=MAX_OCCURRENCES)] = 0
    complete: Annotated[int, Field(ge=0, le=MAX_OCCURRENCES)] = 0
    incomplete: Annotated[int, Field(ge=0, le=MAX_OCCURRENCES)] = 0
    held: Annotated[int, Field(ge=0, le=MAX_OCCURRENCES)] = 0
    missing: Annotated[int, Field(ge=0, le=MAX_OCCURRENCES)] = 0
    intake_held: Annotated[int, Field(ge=0, le=MAX_OCCURRENCES)] = 0
    batches: Annotated[int, Field(ge=0, le=1)] = 0
    batches_complete: Annotated[int, Field(ge=0, le=1)] = 0
    limitation_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _shape(self) -> ScopeStatus:
        if self.batches_complete > self.batches:
            raise A2ContractError("batch complete count exceeds batch count")
        parts = self.complete + self.incomplete + self.held + self.missing
        if self.state is not ScopeState.COMPLETE and parts == 0 == self.occurrences:
            return self._codes_only()
        if parts != self.occurrences:
            raise A2ContractError("status counts do not add up")
        self._codes_only()
        if self.state is not ScopeState.COMPLETE:
            return self
        clean = (self.incomplete, self.held, self.missing, self.intake_held)
        if any(clean) or self.limitation_codes:
            raise A2ContractError("COMPLETE status has open work")
        if self.batches_complete != self.batches or not (
            self.occurrences or self.batches
        ):
            raise A2ContractError("COMPLETE status does not cover the scope")
        return self

    def _codes_only(self) -> ScopeStatus:
        codes = self.limitation_codes
        if len(codes) > MAX_CODES or list(codes) != sorted(set(codes)):
            raise A2ContractError("limitation codes are not sorted and unique")
        if not all(_SAFE_CODE.fullmatch(code) for code in codes):
            raise A2ContractError("limitation code is not a safe code")
        return self

    @property
    def terminal_status(self) -> TerminalStatus:
        """Return the contract status that the state reports."""
        return self.state.terminal_status


def exit_code(status: ScopeStatus) -> int:
    """Return the stable process exit code for ``status``."""
    if not isinstance(status, ScopeStatus):
        raise ScopeInputError
    return EXIT_CODES[status.state]


def status_line(status: ScopeStatus) -> str:
    """
    Return one ASCII line for ``status``.

    The line holds the state, counts and limitation codes. It never holds
    the scope id, an identity, a path or a limitation detail.
    """
    if not isinstance(status, ScopeStatus):
        raise ScopeInputError
    codes = ",".join(status.limitation_codes) or "none"
    return (
        f"a2 scope {status.state.value}: occurrences={status.occurrences}"
        f" complete={status.complete} incomplete={status.incomplete}"
        f" held={status.held} missing={status.missing}"
        f" intake_held={status.intake_held}"
        f" batches={status.batches} batches_complete={status.batches_complete}"
        f" limitations={codes}"
    )


def _scope_id(scope_id: object) -> str:
    if type(scope_id) is not str or not _SCOPE_DIGEST.fullmatch(scope_id):
        raise ScopeInputError
    return scope_id


def status_from_error(scope_id: str, error: ScopeStatusError) -> ScopeStatus:
    """
    Map a typed status error to its status with zero counts.

    :exc:`ScopeInputError` and the bare base have no state. They raise
    :exc:`ScopeInputError`, because a malformed input has no status.
    """
    _scope_id(scope_id)
    if not isinstance(error, ScopeStatusError) or error.state is None:
        raise ScopeInputError
    return ScopeStatus(
        scope_id=scope_id, state=error.state, limitation_codes=(error.code,)
    )


def status_from_held(scope_id: str, held: InputDisposition) -> ScopeStatus:
    """Return the HELD status for one A2 held record (never COMPLETE)."""
    _scope_id(scope_id)
    if not isinstance(held, InputDisposition):
        raise ScopeInputError
    return ScopeStatus(
        scope_id=scope_id,
        state=ScopeState.HELD,
        occurrences=1,
        held=1,
        limitation_codes=(held.reason.value,),
    )


def _is_held(root: TerminalRoot) -> bool:
    return root.disposition == "held" or root.result.kind == HELD_KIND


def _safe_codes(roots: Sequence[TerminalRoot], extra: set[str]) -> tuple[str, ...]:
    # Detail text is never read. A code outside the safe pattern becomes a
    # fixed stand-in, so a free-text code cannot reach the output.
    codes = set(extra)
    for root in roots:
        for item in root.limitations:
            codes.add(item.code if _SAFE_CODE.fullmatch(item.code) else UNSAFE_CODE)
    ordered = sorted(codes)
    if len(ordered) <= MAX_CODES:
        return tuple(ordered)
    return tuple(sorted([*ordered[: MAX_CODES - 1], TRUNCATED_CODE]))


def status_from_receipt(
    progress: ScopeProgress, receipt: CompletionReceipt
) -> ScopeStatus:
    """
    Return the status of ``progress`` as covered by ``receipt``.

    A receipt with fewer roots than expected leaves the missing
    occurrences open, so the state is INCOMPLETE. A receipt for another
    workset, a receipt that names an occurrence outside the scope, other
    intake-held entries or an unexpected batch raises
    :exc:`ScopeInputError`. The workset check comes first. A root that claims
    held and COMPLETE raises :exc:`HeldTerminalError`.
    """
    if not isinstance(progress, ScopeProgress):
        raise ScopeInputError
    if not isinstance(receipt, CompletionReceipt):
        raise ScopeInputError
    roots = receipt.roots
    batch = receipt.transition_batch
    expected = progress.expected_occurrences
    if (
        receipt.workset != progress.workset
        or type(receipt.intake_held_count) is not int
        or len(roots) > expected
        or receipt.intake_held_count != progress.expected_intake_held
        or (batch is not None and not progress.expects_batch)
        or [r.workset_selection_index for r in roots] != list(range(len(roots)))
    ):
        raise ScopeInputError
    statuses = [root.status for root in roots] + ([batch.status] if batch else [])
    if any(item not in (COMPLETE, INCOMPLETE) for item in statuses):
        raise ScopeInputError
    if any(_is_held(r) and r.status is COMPLETE for r in roots):
        raise HeldTerminalError
    held = sum(_is_held(root) for root in roots)
    done = sum(r.status is COMPLETE and not _is_held(r) for r in roots)
    missing = expected - len(roots)
    extra: set[str] = set()
    if missing:
        extra.add("occurrence_missing")
    if progress.expects_batch and batch is None:
        extra.add("batch_missing")
    if batch is not None and batch.status is not COMPLETE:
        extra.add("batch_incomplete")
    if receipt.status is not COMPLETE:
        extra.add("receipt_incomplete")
    if receipt.intake_held_count:
        extra.add("intake_held")
    codes = _safe_codes(roots, extra)
    open_work = bool(codes or held or missing)
    if held:
        state = ScopeState.HELD
    else:
        state = ScopeState.INCOMPLETE if open_work else ScopeState.COMPLETE
    return ScopeStatus(
        scope_id=progress.scope_id,
        state=state,
        occurrences=expected,
        complete=done,
        incomplete=len(roots) - held - done,
        held=held,
        missing=missing,
        intake_held=receipt.intake_held_count,
        batches=int(progress.expects_batch),
        batches_complete=int(batch is not None and batch.status is COMPLETE),
        limitation_codes=codes,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """
    Print the table line for one state name and return its exit code.

    This entry reads no file, no environment value and no storage. It
    exists so a script can pin the exit code table of a built process.
    One argument is required; an unknown or missing state returns 2.
    """
    tokens = list(sys.argv[1:] if argv is None else argv)
    try:
        state = ScopeState(tokens[0]) if len(tokens) == 1 else None
    except ValueError:
        state = None
    if state is None:
        sys.stdout.write("a2 scope status: invalid state\n")
        return EXIT_INVALID
    code = EXIT_CODES[state]
    sys.stdout.write(f"a2 scope {state.value}: exit={code}\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())

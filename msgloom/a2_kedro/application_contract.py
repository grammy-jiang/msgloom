"""
Public ``async def prepare(...)`` contract surface for the A2 v2 design.

``prepare`` is the single trusted entry point that an Application layer
calls. It does three things and nothing else:

1. It checks the input and the authority pin before any work starts. A
   missing or mismatched pin returns ``REJECTED`` and never calls the
   worker.
2. It runs one injected preparation worker under a deadline. The deadline
   uses :func:`asyncio.timeout` on the caller's running loop.
3. It maps the result into a closed :class:`PrepareStatus`.

``prepare`` never creates, runs or closes an event loop. It must be
awaited from a running loop. The caller owns that loop.

Cancellation: :exc:`asyncio.CancelledError` always propagates to the
caller. This module never swallows it and never maps it to a status. The
caller owns structured cancellation and the bridge-closed protocol.

Messages: an outcome holds only a closed status and a closed reason. It
never holds ``str(exc)``, a path, an address or a subject.

CANDIDATE/RESEARCH, PROVISIONAL: nothing here is wired into a CLI, a
Kedro graph, SQLite or a provider. See ``docs/notes/a2-v2-contract-c0-15.md``.
"""

from __future__ import annotations

import asyncio
import math
from enum import StrEnum
from typing import Protocol

from pydantic import model_validator

from msgloom.a2_kedro.contracts.codec import A2ContractError, A2Model, Digest, Text
from msgloom.a2_kedro.contracts.schema_ids import RECEIPT_SCHEMA
from msgloom.contracts import ResultRef

#: Identity of the saved Workset that a prepare call may target.
WORKSET_KIND = "preparation_intake_workset"
WORKSET_VERSION = "1"

#: Provisional deadline ceiling in seconds. P1 profiling must replace it.
MAX_TIMEOUT_SECONDS = 3600.0


class PrepareStatus(StrEnum):
    """Closed status of one ``prepare`` call that returned normally."""

    PREPARED = "prepared"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    FAILED = "failed"


class PrepareReason(StrEnum):
    """Closed, content-free reason that accompanies a status."""

    OK = "ok"
    INVALID_REQUEST = "invalid_request"
    INVALID_WORKSET = "invalid_workset"
    INVALID_TIMEOUT = "invalid_timeout"
    PIN_MISSING = "pin_missing"
    PIN_MISMATCH = "pin_mismatch"
    DEADLINE_EXCEEDED = "deadline_exceeded"
    CONTRACT_VIOLATION = "contract_violation"
    BAD_WORKER_RESULT = "bad_worker_result"
    UNEXPECTED_ERROR = "unexpected_error"


class AuthorityPin(A2Model):
    """Trusted pins that bind one prepare call to frozen inputs."""

    workset: ResultRef
    workset_sha256: Digest
    configuration_version: Text
    code_version: Text
    partition_policy_version: Text


class PrepareRequest(A2Model):
    """
    Caller input for one prepare call.

    ``pin`` is the pin the caller claims. ``None`` means the caller sent
    none. The trusted pin comes from a separate argument of
    :func:`prepare`.
    """

    workset: ResultRef
    pin: AuthorityPin | None = None


class PrepareOutcome(A2Model):
    """Closed result of one ``prepare`` call that returned normally."""

    status: PrepareStatus
    reason: PrepareReason
    receipt: ResultRef | None = None

    @model_validator(mode="after")
    def _consistent(self) -> PrepareOutcome:
        prepared = self.status is PrepareStatus.PREPARED
        if prepared != (self.receipt is not None):
            raise A2ContractError("only a prepared outcome carries a receipt")
        if prepared != (self.reason is PrepareReason.OK):
            raise A2ContractError("reason ok belongs to a prepared outcome")
        return self


class PrepareWorker(Protocol):
    """
    Injected async callable that does the actual preparation.

    It returns the ``a2_completion_receipt@2`` reference it produced. It
    must not create or run an event loop.
    """

    async def __call__(self, request: PrepareRequest, /) -> ResultRef:
        """Prepare the pinned Workset and return the receipt reference."""
        ...


def _rejected(reason: PrepareReason) -> PrepareOutcome:
    return PrepareOutcome(status=PrepareStatus.REJECTED, reason=reason)


def _valid_timeout(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value) and 0 < value <= MAX_TIMEOUT_SECONDS


def _is_workset(ref: object) -> bool:
    return isinstance(ref, ResultRef) and (ref.kind, ref.schema_version) == (
        WORKSET_KIND,
        WORKSET_VERSION,
    )


def preflight(
    request: object, authority: object, timeout_seconds: object
) -> PrepareReason:
    """
    Check input and pins without doing any work.

    Return :attr:`PrepareReason.OK` when the call may start. Otherwise
    return the first closed rejection reason. The order is: request shape,
    Workset identity, deadline, missing pin, pin mismatch.
    """
    if not isinstance(request, PrepareRequest):
        return PrepareReason.INVALID_REQUEST
    if not _is_workset(request.workset):
        return PrepareReason.INVALID_WORKSET
    if not _valid_timeout(timeout_seconds):
        return PrepareReason.INVALID_TIMEOUT
    if not isinstance(authority, AuthorityPin) or request.pin is None:
        return PrepareReason.PIN_MISSING
    if not _is_workset(authority.workset):
        return PrepareReason.INVALID_WORKSET
    if request.pin != authority or request.workset != authority.workset:
        return PrepareReason.PIN_MISMATCH
    return PrepareReason.OK


def _is_receipt(ref: object) -> bool:
    return (
        isinstance(ref, ResultRef)
        and (
            ref.kind,
            ref.schema_version,
        )
        == RECEIPT_SCHEMA
    )


async def prepare(
    request: PrepareRequest,
    *,
    authority: AuthorityPin | None,
    worker: PrepareWorker,
    timeout_seconds: float,
) -> PrepareOutcome:
    """
    Run one pinned preparation under a deadline and classify the result.

    Await this from a running loop. It never creates a loop.

    :param request: caller input with the claimed pin.
    :param authority: trusted pin from the Application layer. ``None``
        rejects the call.
    :param worker: injected async preparation callable.
    :param timeout_seconds: finite deadline, above 0 and at most
        :data:`MAX_TIMEOUT_SECONDS`.
    :returns: a :class:`PrepareOutcome`. Pre-flight problems return
        ``REJECTED`` and the worker is never called. A deadline returns
        ``TIMED_OUT``. A worker error returns ``FAILED``.
    :raises asyncio.CancelledError: always, when the caller cancels.
    """
    reason = preflight(request, authority, timeout_seconds)
    if reason is not PrepareReason.OK:
        return _rejected(reason)
    scope = asyncio.timeout(float(timeout_seconds))
    try:
        async with scope:
            receipt = await worker(request)
    except asyncio.CancelledError:
        raise
    except TimeoutError:
        # A TimeoutError that this scope did not raise belongs to the
        # worker. It is a failure, not a deadline.
        if scope.expired():
            return PrepareOutcome(
                status=PrepareStatus.TIMED_OUT,
                reason=PrepareReason.DEADLINE_EXCEEDED,
            )
        return _failed(PrepareReason.UNEXPECTED_ERROR)
    except A2ContractError:
        return _failed(PrepareReason.CONTRACT_VIOLATION)
    except Exception:  # noqa: BLE001 - classified into a closed reason
        return _failed(PrepareReason.UNEXPECTED_ERROR)
    if not _is_receipt(receipt):
        return _failed(PrepareReason.BAD_WORKER_RESULT)
    return PrepareOutcome(
        status=PrepareStatus.PREPARED,
        reason=PrepareReason.OK,
        receipt=receipt,
    )


def _failed(reason: PrepareReason) -> PrepareOutcome:
    return PrepareOutcome(status=PrepareStatus.FAILED, reason=reason)

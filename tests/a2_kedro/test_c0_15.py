"""C0-15 prepare contract: pre-flight, classification and loop ownership."""

from __future__ import annotations

import asyncio
import functools
import inspect
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro import application_contract as contract
from msgloom.a2_kedro.application_contract import (
    MAX_TIMEOUT_SECONDS,
    AuthorityPin,
    PrepareOutcome,
    PrepareReason,
    PrepareRequest,
    PrepareStatus,
    prepare,
)
from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.contracts import ResultRef
from tests.a2_kedro.helpers import check, hexd


def sync(test: Callable[..., Coroutine[Any, Any, None]]) -> Callable[..., None]:
    """Run an async test on a fresh loop; avoids an async plugin dependency."""

    @functools.wraps(test)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        asyncio.run(test(*args, **kwargs))

    return wrapper


WS = ResultRef("ws-1", "preparation_intake_workset", "1")
RECEIPT = ResultRef("rc-1", "a2_completion_receipt", "2")
SECRET = "alice@example.com /home/alice/secret.eml"


def pin(**changes: Any) -> AuthorityPin:
    data: dict[str, Any] = {
        "workset": WS,
        "workset_sha256": hexd("a"),
        "configuration_version": "config-1",
        "code_version": "code-1",
        "partition_policy_version": "partition-1",
    }
    data.update(changes)
    return AuthorityPin(**data)


def request(claimed: AuthorityPin | None = None, ws: ResultRef = WS) -> PrepareRequest:
    return PrepareRequest(workset=ws, pin=claimed)


class Worker:
    """Injected fake worker; counts calls and runs a scripted behavior."""

    def __init__(self, result: Any = RECEIPT, error: BaseException | None = None):
        self.result = result
        self.error = error
        self.calls = 0
        self.loop: asyncio.AbstractEventLoop | None = None

    async def __call__(self, req: PrepareRequest) -> ResultRef:
        self.calls += 1
        self.loop = asyncio.get_running_loop()
        if self.error is not None:
            raise self.error
        return self.result


async def run(
    worker: Any,
    req: Any = None,
    authority: Any = ...,
    timeout: Any = 5.0,
) -> PrepareOutcome:
    trusted = pin() if authority is ... else authority
    return await prepare(
        req if req is not None else request(pin()),
        authority=trusted,
        worker=worker,
        timeout_seconds=timeout,
    )


@sync
async def test_positive_path_returns_receipt() -> None:
    worker = Worker()
    out = await run(worker)
    check(out.status is PrepareStatus.PREPARED, "status")
    check(out.reason is PrepareReason.OK, "reason")
    check(out.receipt == RECEIPT, "receipt")
    check(worker.calls == 1, "worker called once")


def test_prepare_is_a_coroutine_function() -> None:
    check(inspect.iscoroutinefunction(prepare), "prepare must be async def")


@sync
async def test_missing_authority_rejected_before_work() -> None:
    worker = Worker()
    out = await run(worker, authority=None)
    check(out.status is PrepareStatus.REJECTED, "status")
    check(out.reason is PrepareReason.PIN_MISSING, "reason")
    check(worker.calls == 0, "worker must not run")


@sync
async def test_missing_claimed_pin_rejected_before_work() -> None:
    worker = Worker()
    out = await run(worker, req=request(None))
    check(out.reason is PrepareReason.PIN_MISSING, "reason")
    check(out.status is PrepareStatus.REJECTED, "status")
    check(worker.calls == 0, "worker must not run")


@pytest.mark.parametrize(
    "changes",
    [
        {"workset_sha256": hexd("b")},
        {"configuration_version": "config-2"},
        {"code_version": "code-2"},
        {"partition_policy_version": "partition-2"},
        {"workset": ResultRef("ws-2", "preparation_intake_workset", "1")},
    ],
)
@sync
async def test_mismatched_pin_rejected_before_work(changes: dict[str, Any]) -> None:
    worker = Worker()
    claimed = pin(**changes)
    out = await run(worker, req=request(claimed, ws=claimed.workset))
    check(out.status is PrepareStatus.REJECTED, "status")
    check(out.reason is PrepareReason.PIN_MISMATCH, "reason")
    check(worker.calls == 0, "worker must not run")


@sync
async def test_request_workset_must_match_trusted_workset() -> None:
    worker = Worker()
    other = ResultRef("ws-2", "preparation_intake_workset", "1")
    out = await run(worker, req=request(pin(), ws=other))
    check(out.reason is PrepareReason.PIN_MISMATCH, "reason")
    check(worker.calls == 0, "worker must not run")


@pytest.mark.parametrize(
    "ref",
    [
        ResultRef("ws-1", "collected_selection", "1"),
        ResultRef("ws-1", "preparation_intake_workset", "2"),
    ],
)
@sync
async def test_wrong_workset_identity_rejected(ref: ResultRef) -> None:
    worker = Worker()
    out = await run(worker, req=request(pin(workset=ref), ws=ref))
    check(out.status is PrepareStatus.REJECTED, "status")
    check(out.reason is PrepareReason.INVALID_WORKSET, "reason")
    check(worker.calls == 0, "worker must not run")


@sync
async def test_wrong_request_type_rejected() -> None:
    worker = Worker()
    out = await prepare(
        {"workset": WS},  # type: ignore[arg-type]
        authority=pin(),
        worker=worker,
        timeout_seconds=1.0,
    )
    check(out.reason is PrepareReason.INVALID_REQUEST, "reason")
    check(worker.calls == 0, "worker must not run")


@pytest.mark.parametrize(
    "timeout",
    [0, -1, 0.0, float("nan"), float("inf"), True, "1", None, MAX_TIMEOUT_SECONDS + 1],
)
@sync
async def test_invalid_timeout_rejected(timeout: Any) -> None:
    worker = Worker()
    out = await run(worker, timeout=timeout)
    check(out.status is PrepareStatus.REJECTED, "status")
    check(out.reason is PrepareReason.INVALID_TIMEOUT, "reason")
    check(worker.calls == 0, "worker must not run")


@sync
async def test_timeout_is_classified_not_raised() -> None:
    async def slow(req: PrepareRequest) -> ResultRef:
        await asyncio.sleep(30)
        return RECEIPT

    out = await run(slow, timeout=0.01)
    check(out.status is PrepareStatus.TIMED_OUT, "status")
    check(out.reason is PrepareReason.DEADLINE_EXCEEDED, "reason")
    check(out.receipt is None, "no receipt on timeout")


@sync
async def test_worker_own_timeout_error_is_failure_not_deadline() -> None:
    out = await run(Worker(error=TimeoutError(SECRET)))
    check(out.status is PrepareStatus.FAILED, "status")
    check(out.reason is PrepareReason.UNEXPECTED_ERROR, "reason")


@sync
async def test_contract_error_is_classified() -> None:
    out = await run(Worker(error=A2ContractError(SECRET)))
    check(out.status is PrepareStatus.FAILED, "status")
    check(out.reason is PrepareReason.CONTRACT_VIOLATION, "reason")


@pytest.mark.parametrize(
    "error", [RuntimeError(SECRET), ValueError(SECRET), OSError(SECRET)]
)
@sync
async def test_failure_is_classified_without_pii(error: Exception) -> None:
    out = await run(Worker(error=error))
    check(out.status is PrepareStatus.FAILED, "status")
    check(out.reason is PrepareReason.UNEXPECTED_ERROR, "reason")
    text = out.model_dump_json() + repr(out)
    check("alice" not in text and "secret" not in text, "PII leaked")
    check(out.receipt is None, "no receipt on failure")


@pytest.mark.parametrize(
    "bad",
    [
        None,
        "rc-1",
        ResultRef("rc-1", "a2_completion_receipt", "1"),
        ResultRef("rc-1", "prepared", "2"),
    ],
)
@sync
async def test_bad_worker_result_fails_closed(bad: Any) -> None:
    out = await run(Worker(result=bad))
    check(out.status is PrepareStatus.FAILED, "status")
    check(out.reason is PrepareReason.BAD_WORKER_RESULT, "reason")


@sync
async def test_cancellation_propagates_to_caller() -> None:
    started = asyncio.Event()
    cleaned = asyncio.Event()

    async def blocked(req: PrepareRequest) -> ResultRef:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()
        return RECEIPT

    task = asyncio.create_task(run(blocked))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    check(task.cancelled(), "task must end cancelled, not completed")
    check(cleaned.is_set(), "worker cleanup must run")


@sync
async def test_cancelled_error_from_worker_is_not_swallowed() -> None:
    with pytest.raises(asyncio.CancelledError):
        await run(Worker(error=asyncio.CancelledError()))


@sync
async def test_uses_callers_loop_and_creates_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("prepare must not create or run an event loop")

    monkeypatch.setattr(asyncio, "run", forbidden)
    monkeypatch.setattr(asyncio, "new_event_loop", forbidden)
    monkeypatch.setattr(asyncio, "Runner", forbidden)
    worker = Worker()
    out = await run(worker)
    check(out.status is PrepareStatus.PREPARED, "status")
    check(worker.loop is asyncio.get_running_loop(), "must use caller loop")


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit(1)])
@sync
async def test_process_exit_signals_are_not_classified(error: BaseException) -> None:
    with pytest.raises(type(error)):
        await run(Worker(error=error))


def test_source_has_no_loop_creation() -> None:
    source = Path(contract.__file__).read_text(encoding="utf-8")
    for name in ("asyncio.run(", "new_event_loop", "run_until_complete", "Runner("):
        check(name not in source, f"forbidden loop call: {name}")


def test_outcome_rejects_inconsistent_combinations() -> None:
    with pytest.raises(ValidationError):
        PrepareOutcome(
            status=PrepareStatus.PREPARED, reason=PrepareReason.OK, receipt=None
        )
    with pytest.raises(ValidationError):
        PrepareOutcome(
            status=PrepareStatus.FAILED,
            reason=PrepareReason.OK,
            receipt=RECEIPT,
        )
    with pytest.raises(ValidationError):
        PrepareOutcome(status=PrepareStatus.FAILED, reason=PrepareReason.OK)


def test_status_enum_is_closed() -> None:
    check(
        {s.value for s in PrepareStatus}
        == {"prepared", "rejected", "timed_out", "failed"},
        "status set changed",
    )

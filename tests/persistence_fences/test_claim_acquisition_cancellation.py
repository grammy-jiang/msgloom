"""Keep ownership of claims committed before cancelled acquisition returns."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ClaimToken,
    ExecutionIdentity,
    ExternalEffectState,
    TerminalStatus,
)
from msgloom.persistence import ClaimUnavailableError, Phase1Persistence


@pytest.mark.parametrize("kind", (ClaimKind.PREPARE, ClaimKind.REPORT_SUBMIT))
def test_cancelled_acquisition_finishes_committed_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: ClaimKind
) -> None:
    """A committed token must not disappear before its owner can release it."""

    async def exercise() -> None:
        store = await Phase1Persistence.open(f"sqlite:///{tmp_path / 'claim.db'}")
        loop = asyncio.get_running_loop()
        entered = asyncio.Event()
        release = threading.Event()
        original = store._store.acquire_claim

        def acquire(*args: object) -> ClaimToken:
            token = original(*args)  # type: ignore[arg-type]
            loop.call_soon_threadsafe(entered.set)
            if not release.wait(5):
                raise RuntimeError("acquisition barrier timed out")
            return token

        monkeypatch.setattr(store._store, "acquire_claim", acquire)
        task = asyncio.create_task(
            store.acquire_claim(
                "cancelled",
                kind,
                ExecutionIdentity("owner"),
                AttemptIdentity("attempt"),
            )
        )
        try:
            await asyncio.wait_for(entered.wait(), 5)
            task.cancel()
            loop.call_soon(task.cancel)
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            inspection = await store.inspect_claim("cancelled")
            if inspection.current_token is not None:
                pytest.fail("cancelled acquisition leaked its committed claim")
            attempt = inspection.attempts[0]
            if attempt.terminal_status is not TerminalStatus.CANCELLED:
                pytest.fail("cancelled acquisition did not record terminal history")
            if attempt.external_effect is not ExternalEffectState.NOT_STARTED:
                pytest.fail("unreturned acquisition recorded an external effect")
            if attempt.finished_at is None:
                pytest.fail("cancelled acquisition did not finish its attempt")
        finally:
            release.set()
            await store.close()

    asyncio.run(exercise())


def test_cancelled_rejected_acquisition_preserves_existing_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An acquisition failure must not release another caller's claim."""

    async def exercise() -> None:
        store = await Phase1Persistence.open(f"sqlite:///{tmp_path / 'claim.db'}")
        owner = await store.acquire_claim(
            "busy",
            ClaimKind.PREPARE,
            ExecutionIdentity("owner"),
            AttemptIdentity("owner-attempt"),
        )
        loop = asyncio.get_running_loop()
        entered = asyncio.Event()
        release = threading.Event()
        original = store._store.acquire_claim

        def acquire(*args: object) -> ClaimToken:
            loop.call_soon_threadsafe(entered.set)
            if not release.wait(5):
                raise RuntimeError("acquisition barrier timed out")
            return original(*args)  # type: ignore[arg-type]

        monkeypatch.setattr(store._store, "acquire_claim", acquire)
        task = asyncio.create_task(
            store.acquire_claim(
                "busy",
                ClaimKind.PREPARE,
                ExecutionIdentity("other"),
                AttemptIdentity("other-attempt"),
            )
        )
        try:
            await asyncio.wait_for(entered.wait(), 5)
            task.cancel()
            release.set()
            with pytest.raises(ClaimUnavailableError):
                await task
            inspection = await store.inspect_claim("busy")
            if inspection.current_token != owner or len(inspection.attempts) != 1:
                pytest.fail("failed acquisition changed the existing claim")
        finally:
            release.set()
            await store.close()

    asyncio.run(exercise())


def test_repeated_cancellation_drains_cleanup_before_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repeated cancellation and close cannot overtake accepted cleanup."""

    async def exercise() -> None:
        url = f"sqlite:///{tmp_path / 'claim.db'}"
        store = await Phase1Persistence.open(url)
        loop = asyncio.get_running_loop()
        committed = asyncio.Event()
        cleaning = asyncio.Event()
        release_acquire = threading.Event()
        release_cleanup = threading.Event()
        original_acquire = store._store.acquire_claim
        original_finish = store._store.finish_claim

        def acquire(*args: object) -> ClaimToken:
            token = original_acquire(*args)  # type: ignore[arg-type]
            loop.call_soon_threadsafe(committed.set)
            if not release_acquire.wait(5):
                raise RuntimeError("acquisition barrier timed out")
            return token

        def finish(*args: object) -> None:
            loop.call_soon_threadsafe(cleaning.set)
            if not release_cleanup.wait(5):
                raise RuntimeError("cleanup barrier timed out")
            original_finish(*args)  # type: ignore[arg-type]

        monkeypatch.setattr(store._store, "acquire_claim", acquire)
        monkeypatch.setattr(store._store, "finish_claim", finish)
        task = asyncio.create_task(
            store.acquire_claim(
                "cancelled",
                ClaimKind.REPORT_SUBMIT,
                ExecutionIdentity("owner"),
                AttemptIdentity("attempt"),
            )
        )
        try:
            await asyncio.wait_for(committed.wait(), 5)
            task.cancel()
            release_acquire.set()
            await asyncio.wait_for(cleaning.wait(), 5)
            task.cancel()
            closing = asyncio.create_task(store.close())
            turn = loop.create_future()
            loop.call_soon(turn.set_result, None)
            await turn
            task.cancel()
            if task.done() or closing.done():
                pytest.fail("cancellation or disposal overtook cleanup")
            release_cleanup.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            await closing
            reopened = await Phase1Persistence.open(url)
            try:
                state = await reopened.inspect_claim("cancelled")
                if state.current_token is not None:
                    pytest.fail("repeated cancellation interrupted terminal cleanup")
                if state.attempts[0].terminal_status is not TerminalStatus.CANCELLED:
                    pytest.fail("terminal history did not survive close")
            finally:
                await reopened.close()
        finally:
            release_acquire.set()
            release_cleanup.set()
            await store.close()

    asyncio.run(exercise())


def test_cancelled_acquisition_cannot_finish_replacement_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cleanup of an expired unreturned token must retain a replacement."""

    async def exercise() -> None:
        url = f"sqlite:///{tmp_path / 'claim.db'}"
        store = await Phase1Persistence.open(url)
        competitor = await Phase1Persistence.open(url)
        loop = asyncio.get_running_loop()
        committed = asyncio.Event()
        release = threading.Event()
        original = store._store.acquire_claim

        def acquire(*args: object) -> ClaimToken:
            token = original(*args)  # type: ignore[arg-type]
            loop.call_soon_threadsafe(committed.set)
            if not release.wait(5):
                raise RuntimeError("acquisition barrier timed out")
            return token

        monkeypatch.setattr(store._store, "acquire_claim", acquire)
        task = asyncio.create_task(
            store.acquire_claim(
                "reclaimed",
                ClaimKind.PREPARE,
                ExecutionIdentity("old"),
                AttemptIdentity("old-attempt"),
                lease_seconds=0,
            )
        )
        try:
            await asyncio.wait_for(committed.wait(), 5)
            replacement = await competitor.acquire_claim(
                "reclaimed",
                ClaimKind.PREPARE,
                ExecutionIdentity("new"),
                AttemptIdentity("new-attempt"),
            )
            task.cancel()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            state = await competitor.inspect_claim("reclaimed")
            if state.current_token != replacement:
                pytest.fail("cancelled acquisition released its replacement")
            old = next(
                item
                for item in state.attempts
                if item.token.execution == ExecutionIdentity("old")
            )
            if old.terminal_status is not TerminalStatus.INCOMPLETE:
                pytest.fail("cancellation replaced reclaim terminal history")
        finally:
            release.set()
            await store.close()
            await competitor.close()

    asyncio.run(exercise())

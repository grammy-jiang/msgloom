#!/usr/bin/env python3
"""Reproduce the Phase 1 sync-thread versus aiosqlite persistence spike."""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import tempfile
import threading
import time
from collections.abc import Callable
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from statistics import median
from typing import Any

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

_WRITE_COUNT = 80
_CONTENDED_COUNT = 60
_HEARTBEAT_SECONDS = 0.002
_LOCK_SECONDS = 0.15

metadata = MetaData()
writes = Table(
    "writes",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("owner", String, nullable=False),
)
claims = Table(
    "claims",
    metadata,
    Column("claim_key", String, primary_key=True),
    Column("owner", String, nullable=False),
)


def _sync_url(path: Path) -> str:
    return f"sqlite:///{path}"


def _async_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path}"


@contextmanager
def _sync_transaction(engine: Any):
    """Use the same explicit writer transaction as the production store."""
    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            yield connection
            connection.exec_driver_sql("COMMIT")
        except BaseException:
            connection.exec_driver_sql("ROLLBACK")
            raise


@asynccontextmanager
async def _async_transaction(engine: Any):
    """Match the synchronous transaction boundary for a fair comparison."""
    async with engine.connect() as connection:
        await connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            yield connection
            await connection.exec_driver_sql("COMMIT")
        except BaseException:
            await connection.exec_driver_sql("ROLLBACK")
            raise


def _sync_insert(engine: Any, row_id: int, owner: str) -> None:
    with _sync_transaction(engine) as connection:
        connection.execute(writes.insert().values(id=row_id, owner=owner))


async def _drain_thread[T](operation: Callable[[], T]) -> T:
    task = asyncio.create_task(asyncio.to_thread(operation))
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    if task.cancelled():
        raise asyncio.CancelledError
    error = task.exception()
    if error is not None:
        raise error
    result = task.result()
    if cancelled:
        raise asyncio.CancelledError
    return result


async def _heartbeat(stop: asyncio.Event) -> float:
    loop = asyncio.get_running_loop()
    target = loop.time() + _HEARTBEAT_SECONDS
    worst = 0.0
    while not stop.is_set():
        await asyncio.sleep(max(0.0, target - loop.time()))
        now = loop.time()
        worst = max(worst, now - target)
        target += _HEARTBEAT_SECONDS
    return worst


async def _with_heartbeat(operation: Callable[[], Any]) -> tuple[float, float]:
    stop = asyncio.Event()
    heartbeat = asyncio.create_task(_heartbeat(stop))
    started = time.perf_counter()
    try:
        await operation()
    finally:
        elapsed = time.perf_counter() - started
        stop.set()
    worst = await heartbeat
    return elapsed, worst


async def _sync_sequential(path: Path) -> None:
    engine = create_engine(
        _sync_url(path),
        connect_args={"autocommit": True, "timeout": 5.0},
    )
    metadata.create_all(engine)
    try:
        for row_id in range(_WRITE_COUNT):
            await asyncio.to_thread(_sync_insert, engine, row_id, "sync")
    finally:
        engine.dispose()


async def _async_sequential(path: Path) -> None:
    engine = create_async_engine(
        _async_url(path), connect_args={"autocommit": True, "timeout": 5.0}
    )
    async with _async_transaction(engine) as connection:
        await connection.run_sync(metadata.create_all)
    try:
        for row_id in range(_WRITE_COUNT):
            async with _async_transaction(engine) as connection:
                await connection.execute(
                    writes.insert().values(id=row_id, owner="async")
                )
    finally:
        await engine.dispose()


async def _sync_contended(path: Path) -> float:
    engines = [
        create_engine(
            _sync_url(path),
            connect_args={"autocommit": True, "timeout": 5.0},
        )
        for _ in range(2)
    ]
    metadata.create_all(engines[0])

    def writer(engine: Any, owner: str, offset: int) -> None:
        for index in range(_CONTENDED_COUNT // 2):
            _sync_insert(engine, offset + index, owner)

    started = time.perf_counter()
    try:
        await asyncio.gather(
            asyncio.to_thread(writer, engines[0], "left", 0),
            asyncio.to_thread(
                writer,
                engines[1],
                "right",
                _CONTENDED_COUNT // 2,
            ),
        )
    finally:
        for engine in engines:
            engine.dispose()
    return time.perf_counter() - started


async def _async_contended(path: Path) -> float:
    engines = [
        create_async_engine(
            _async_url(path), connect_args={"autocommit": True, "timeout": 5.0}
        )
        for _ in range(2)
    ]
    async with _async_transaction(engines[0]) as connection:
        await connection.run_sync(metadata.create_all)

    async def writer(engine: Any, owner: str, offset: int) -> None:
        for index in range(_CONTENDED_COUNT // 2):
            async with _async_transaction(engine) as connection:
                await connection.execute(
                    writes.insert().values(id=offset + index, owner=owner)
                )

    started = time.perf_counter()
    try:
        await asyncio.gather(
            writer(engines[0], "left", 0),
            writer(engines[1], "right", _CONTENDED_COUNT // 2),
        )
    finally:
        for engine in engines:
            await engine.dispose()
    return time.perf_counter() - started


async def _sync_claim_race(path: Path) -> list[str]:
    engines = [
        create_engine(
            _sync_url(path),
            connect_args={"autocommit": True, "timeout": 5.0},
        )
        for _ in range(2)
    ]
    metadata.create_all(engines[0])

    def claim(engine: Any, owner: str) -> str:
        try:
            with _sync_transaction(engine) as connection:
                connection.execute(
                    claims.insert().values(claim_key="scope", owner=owner)
                )
        except IntegrityError:
            return "blocked"
        return "acquired"

    try:
        return sorted(
            await asyncio.gather(
                asyncio.to_thread(claim, engines[0], "left"),
                asyncio.to_thread(claim, engines[1], "right"),
            )
        )
    finally:
        for engine in engines:
            engine.dispose()


async def _async_claim_race(path: Path) -> list[str]:
    engines = [
        create_async_engine(
            _async_url(path), connect_args={"autocommit": True, "timeout": 5.0}
        )
        for _ in range(2)
    ]
    async with _async_transaction(engines[0]) as connection:
        await connection.run_sync(metadata.create_all)

    async def claim(engine: Any, owner: str) -> str:
        try:
            async with _async_transaction(engine) as connection:
                await connection.execute(
                    claims.insert().values(claim_key="scope", owner=owner)
                )
        except IntegrityError:
            return "blocked"
        return "acquired"

    try:
        return sorted(
            await asyncio.gather(
                claim(engines[0], "left"),
                claim(engines[1], "right"),
            )
        )
    finally:
        for engine in engines:
            await engine.dispose()


async def _sync_cancel(path: Path) -> tuple[float, bool]:
    engine = create_engine(
        _sync_url(path),
        connect_args={"autocommit": True, "timeout": 5.0},
    )
    metadata.create_all(engine)
    lock = sqlite3.connect(path, isolation_level=None)
    lock.execute("BEGIN IMMEDIATE")
    started = threading.Event()

    def blocked_write() -> None:
        started.set()
        _sync_insert(engine, 1, "cancelled-sync")

    task = asyncio.create_task(_drain_thread(blocked_write))
    await asyncio.to_thread(started.wait, 2)

    async def release() -> None:
        await asyncio.sleep(_LOCK_SECONDS)
        lock.execute("COMMIT")

    releaser = asyncio.create_task(release())
    began_cancel = time.perf_counter()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    elapsed = time.perf_counter() - began_cancel
    await releaser
    lock.close()
    with engine.connect() as connection:
        durable = connection.execute(writes.select()).first() is not None
    engine.dispose()
    return elapsed, durable


async def _async_cancel(path: Path) -> tuple[float, bool]:
    engine = create_async_engine(
        _async_url(path), connect_args={"autocommit": True, "timeout": 5.0}
    )
    async with _async_transaction(engine) as connection:
        await connection.run_sync(metadata.create_all)
    lock = sqlite3.connect(path, isolation_level=None)
    lock.execute("BEGIN IMMEDIATE")

    async def blocked_write() -> None:
        async with _async_transaction(engine) as connection:
            await connection.execute(
                writes.insert().values(id=1, owner="cancelled-async")
            )

    task = asyncio.create_task(blocked_write())
    await asyncio.sleep(0.01)

    async def release() -> None:
        await asyncio.sleep(_LOCK_SECONDS)
        lock.execute("COMMIT")

    releaser = asyncio.create_task(release())
    began_cancel = time.perf_counter()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    elapsed = time.perf_counter() - began_cancel
    await releaser
    lock.close()
    async with engine.connect() as connection:
        durable = (await connection.execute(writes.select())).first() is not None
    await engine.dispose()
    return elapsed, durable


async def _one_run(root: Path, run: int) -> dict[str, Any]:
    def path(name: str) -> Path:
        return root / f"run-{run}-{name}.sqlite3"

    sync_seq, sync_heartbeat = await _with_heartbeat(
        lambda: _sync_sequential(path("sync-sequential"))
    )
    async_seq, async_heartbeat = await _with_heartbeat(
        lambda: _async_sequential(path("async-sequential"))
    )
    sync_cancel, sync_durable = await _sync_cancel(path("sync-cancel"))
    async_cancel, async_durable = await _async_cancel(path("async-cancel"))
    return {
        "run": run,
        "sync": {
            "sequential_writes_s": sync_seq,
            "max_heartbeat_delay_s": sync_heartbeat,
            "contended_writes_s": await _sync_contended(path("sync-contended")),
            "claim_race": await _sync_claim_race(path("sync-claim")),
            "cancellation_return_s": sync_cancel,
            "cancelled_write_durable": sync_durable,
        },
        "async": {
            "sequential_writes_s": async_seq,
            "max_heartbeat_delay_s": async_heartbeat,
            "contended_writes_s": await _async_contended(path("async-contended")),
            "claim_race": await _async_claim_race(path("async-claim")),
            "cancellation_return_s": async_cancel,
            "cancelled_write_durable": async_durable,
        },
    }


def _summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for mode in ("sync", "async"):
        summary[mode] = {}
        for metric in (
            "sequential_writes_s",
            "max_heartbeat_delay_s",
            "contended_writes_s",
            "cancellation_return_s",
        ):
            values = [float(run[mode][metric]) for run in runs]
            summary[mode][metric] = {
                "median": median(values),
                "min": min(values),
                "max": max(values),
            }
    return summary


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.runs < 1:
        raise ValueError("--runs must be positive")

    with tempfile.TemporaryDirectory(prefix="msgloom-p1-spike-") as directory:
        runs = [
            await _one_run(Path(directory), index + 1) for index in range(args.runs)
        ]
    payload = {
        "benchmark": "phase1-persistence-spike",
        "write_count": _WRITE_COUNT,
        "contended_write_count": _CONTENDED_COUNT,
        "heartbeat_interval_s": _HEARTBEAT_SECONDS,
        "writer_lock_hold_s": _LOCK_SECONDS,
        "runs": runs,
        "summary": _summary(runs),
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.write_text(rendered)


if __name__ == "__main__":
    asyncio.run(main())

"""Isolated Q0 probe: Kedro 1.7.0 orchestrates trusted async-backed datasets.

Execute ONLY in a disposable virtualenv with:
    DO_NOT_TRACK=1 KEDRO_DISABLE_TELEMETRY=1 python -I scripts/research/q0_kedro_runtime_probe.py

No msgloom imports, filesystem writes, provider access, production DB, or network.
This is not a business-store acceptance or bounded-production-worker proof.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
import socket
import sys
import threading
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

os.environ["DO_NOT_TRACK"] = "1"
os.environ["KEDRO_DISABLE_TELEMETRY"] = "1"

NETWORK_ATTEMPTS = 0


def _deny_network(*_args: object, **_kwargs: object) -> None:
    global NETWORK_ATTEMPTS
    NETWORK_ATTEMPTS += 1
    raise RuntimeError("Q0 network denied")


socket.create_connection = _deny_network  # type: ignore[assignment]
socket.socket.connect = _deny_network  # type: ignore[method-assign]
socket.socket.connect_ex = _deny_network  # type: ignore[method-assign]

from kedro import __version__ as kedro_version
from kedro.io import AbstractDataset, DataCatalog, DatasetError, MemoryDataset
from kedro.pipeline import Pipeline, node
from kedro.runner import SequentialRunner

logging.disable(logging.CRITICAL)


class SafeBoundaryError(Exception):
    """No untrusted payload or original exception text is included."""


@dataclass(frozen=True)
class Source:
    identity: str
    content: str


@dataclass(frozen=True)
class ParseRequest:
    content: str


@dataclass(frozen=True)
class Parsed:
    content: str


@dataclass(frozen=True)
class Normalized:
    content: str
    identity: str


@dataclass(frozen=True)
class Accepted:
    key: str
    payload_digest: str


@dataclass
class ProbeService:
    parser_delay: float = 0.0
    cpu_delay: float = 0.0
    fail_parse: bool = False
    fail_publish: bool = False
    claim_valid: bool = True
    accepted: dict[str, Accepted] = field(default_factory=dict)
    publish_count: int = 0
    parse_count: int = 0

    async def parse(self, request: ParseRequest) -> Parsed:
        await asyncio.sleep(self.parser_delay)
        self.parse_count += 1
        if self.fail_parse:
            raise RuntimeError("PRIVATE_CANARY_PARSER_EXCEPTION")
        return Parsed(content=request.content.strip())

    async def publish(self, content: Normalized) -> Accepted:
        await asyncio.sleep(0)
        if not self.claim_valid:
            raise RuntimeError("PRIVATE_CANARY_STALE_CLAIM")
        if self.fail_publish:
            raise RuntimeError("PRIVATE_CANARY_PUBLISH_EXCEPTION")
        key = f"q0:{content.identity}:normalized:v1:code-v1"
        digest = hashlib.sha256(content.content.encode()).hexdigest()
        candidate = Accepted(key=key, payload_digest=digest)
        old = self.accepted.get(key)
        if old is not None:
            if old != candidate:
                raise RuntimeError("PRIVATE_CANARY_OUTPUT_CONFLICT")
            return old
        self.accepted[key] = candidate
        self.publish_count += 1
        return candidate


@dataclass
class ServiceBridge:
    loop: asyncio.AbstractEventLoop
    owner_thread: int
    stopped: threading.Event
    deadline: float
    calls: int = 0

    def call(self, awaitable: Any) -> Any:
        if threading.get_ident() == self.owner_thread:
            awaitable.close()
            raise SafeBoundaryError("wrong-thread")
        if self.stopped.is_set() or monotonic() >= self.deadline:
            awaitable.close()
            raise SafeBoundaryError("operation-stopped")
        fut = asyncio.run_coroutine_threadsafe(awaitable, self.loop)
        self.calls += 1
        try:
            result = fut.result(timeout=max(0.01, self.deadline - monotonic()))
            if self.stopped.is_set() or monotonic() >= self.deadline:
                raise SafeBoundaryError("operation-stopped")
            return result
        except Exception:  # noqa: BLE001 - boundary redacts any provider error
            fut.cancel()
            # No "from e"; private body/error messages must not leak.
            raise SafeBoundaryError("trusted-service-failed") from None


class SourceDataset(AbstractDataset[Source, Source]):
    def __init__(self, source: Source) -> None:
        self.source = source

    def load(self) -> Source:
        return self.source

    def save(self, data: Source) -> None:
        del data
        raise SafeBoundaryError("source-is-read-only")

    def _describe(self) -> dict[str, str]:
        return {"kind": "frozen-exact-input"}


class ParseServiceDataset(AbstractDataset[ParseRequest, Parsed]):
    def __init__(self, bridge: ServiceBridge, service: ProbeService) -> None:
        self.bridge = bridge
        self.service = service
        self.output: Parsed | None = None

    def save(self, data: ParseRequest) -> None:
        self.output = self.bridge.call(self.service.parse(data))

    def load(self) -> Parsed:
        if self.output is None:
            raise SafeBoundaryError("parser-result-missing")
        return self.output

    def _describe(self) -> dict[str, str]:
        return {"kind": "isolated-parser-adapter"}


class SemanticStageDataset(AbstractDataset[Normalized, Accepted]):
    def __init__(self, bridge: ServiceBridge, service: ProbeService) -> None:
        self.bridge = bridge
        self.service = service
        self.output: Accepted | None = None

    def save(self, data: Normalized) -> None:
        self.output = self.bridge.call(self.service.publish(data))

    def load(self) -> Accepted:
        if self.output is None:
            raise SafeBoundaryError("stage-result-missing")
        return self.output

    def _describe(self) -> dict[str, str]:
        return {"kind": "claim-fenced-stage-adapter"}


def build_pipeline_and_catalog(
    source: Source, service: ProbeService, bridge: ServiceBridge
) -> tuple[Pipeline, DataCatalog]:
    def make_request(data: Source) -> ParseRequest:
        return ParseRequest(content=data.content)

    def normalize(parsed: Parsed, src: Source) -> Normalized:
        if bridge.stopped.is_set() or monotonic() >= bridge.deadline:
            raise SafeBoundaryError("operation-stopped")
        until = monotonic() + service.cpu_delay
        while monotonic() < until:
            # Cooperative cancellation is essential: Python threads cannot
            # be forcibly stopped by the awaiting Application coroutine.
            if bridge.stopped.is_set() or monotonic() >= bridge.deadline:
                raise SafeBoundaryError("operation-stopped")
        return Normalized(content=parsed.content.casefold(), identity=src.identity)

    def emit(normalized: Normalized) -> Normalized:
        return normalized

    def finish(accepted: Accepted) -> dict[str, str]:
        return {"stage_key": accepted.key, "sha256": accepted.payload_digest}

    pipeline = Pipeline(
        [
            node(
                make_request, "frozen_input", "parsed_service", name="dispatch_parser"
            ),
            node(
                normalize,
                ["parsed_service", "frozen_input"],
                "normalized",
                name="normalize_source",
            ),
            node(emit, "normalized", "saved_stage", name="commit_stage"),
            node(finish, "saved_stage", "manifest", name="build_manifest"),
        ]
    )
    catalog = DataCatalog(
        {
            "frozen_input": SourceDataset(source),
            "parsed_service": ParseServiceDataset(bridge, service),
            "normalized": MemoryDataset(copy_mode="assign"),
            "saved_stage": SemanticStageDataset(bridge, service),
            "manifest": MemoryDataset(copy_mode="assign"),
        }
    )
    # Prevent the runner from implicitly materializing extra MemoryDatasets.
    if set(pipeline.datasets()) != set(catalog.keys()):
        raise SafeBoundaryError("unexpected-dataset")
    return pipeline, catalog


async def run_case(
    source: Source,
    service: ProbeService,
    *,
    budget: float = 1.0,
) -> tuple[dict[str, str] | None, float, int, bool]:
    loop = asyncio.get_running_loop()
    event = threading.Event()
    bridge = ServiceBridge(
        loop=loop,
        owner_thread=threading.get_ident(),
        stopped=event,
        deadline=monotonic() + budget,
    )
    pipeline, catalog = build_pipeline_and_catalog(source, service, bridge)

    def _execute() -> dict[str, str]:
        out = SequentialRunner(is_async=False).run(pipeline, catalog)
        return out["manifest"].load()

    started = monotonic()
    worker = asyncio.create_task(asyncio.to_thread(_execute))
    try:
        value = await asyncio.shield(worker)
        return value, monotonic() - started, bridge.calls, False
    except asyncio.CancelledError:
        event.set()
        # Unlike task.cancel() on asyncio.to_thread, this does not detach
        # the underlying thread. We await the bounded real worker.
        while not worker.done():
            try:
                await asyncio.shield(worker)
            except asyncio.CancelledError:
                continue
            except Exception:  # noqa: BLE001 - drained worker failed
                break
        try:
            worker.result()
        except (Exception, asyncio.CancelledError):  # noqa: BLE001 - drained
            return None, monotonic() - started, bridge.calls, True
        return None, monotonic() - started, bridge.calls, True
    finally:
        event.set()


async def verify() -> dict[str, Any]:
    source = Source("message-1", "  Confidential Example  ")
    service = ProbeService()
    result, elapsed, calls, cancelled = await run_case(source, service)
    assert result is not None and not cancelled
    assert len(service.accepted) == service.publish_count == 1
    assert len(result["sha256"]) == 64 and calls == 2

    again, _, _, _ = await run_case(source, service)
    assert again == result and service.publish_count == 1

    try:
        await run_case(Source("message-1", "CHANGED"), service)
    except (SafeBoundaryError, DatasetError):
        pass
    else:
        raise AssertionError("same-key conflicting output was accepted")
    assert service.publish_count == 1

    failures: dict[str, bool] = {}
    for label, flags in (
        ("parser_failure", {"fail_parse": True}),
        ("stage_failure", {"fail_publish": True}),
        ("stale_claim", {"claim_valid": False}),
    ):
        bad = ProbeService(**flags)
        try:
            await run_case(source, bad)
        except (SafeBoundaryError, DatasetError) as exc:
            assert "PRIVATE_CANARY" not in str(exc)
        else:
            raise AssertionError(label + " unexpectedly succeeded")
        failures[label] = not bad.accepted

    slow = ProbeService(parser_delay=0.16)
    task = asyncio.create_task(run_case(source, slow))
    await asyncio.sleep(0.02)
    task.cancel()
    _, cancel_drain, _, was_cancelled = await task
    assert was_cancelled and not slow.accepted
    assert cancel_drain < 0.5, cancel_drain

    deadline = ProbeService(parser_delay=0.16)
    try:
        await run_case(source, deadline, budget=0.025)
    except (SafeBoundaryError, DatasetError):
        pass
    else:
        raise AssertionError("expired operation unexpectedly succeeded")
    assert not deadline.accepted

    heartbeats = 0

    async def tick() -> None:
        nonlocal heartbeats
        for _ in range(8):
            await asyncio.sleep(0.012)
            heartbeats += 1

    heartbeat_service = ProbeService(parser_delay=0.14)
    finished, _ = await asyncio.gather(run_case(source, heartbeat_service), tick())
    assert finished[0] is not None and heartbeats == 8

    cpu = ProbeService(cpu_delay=0.12)
    cpu_task = asyncio.create_task(run_case(source, cpu))
    await asyncio.sleep(0.025)
    cpu_task.cancel()
    _, cpu_drain, _, cpu_cancelled = await cpu_task
    assert cpu_cancelled and not cpu.accepted and cpu_drain < 0.5

    # Unlike the ordinary quiet probe, exercise Kedro's actual exception
    # logging path. Trusted dataset facades must redact exceptions *before*
    # DataCatalog wraps them; external payloads never become dataset names.
    capture = io.StringIO()
    recorder = logging.StreamHandler(capture)
    kedro_logger = logging.getLogger("kedro")
    old_handlers = list(kedro_logger.handlers)
    old_propagate = kedro_logger.propagate
    old_level = kedro_logger.level
    try:
        kedro_logger.handlers = [recorder]
        kedro_logger.propagate = False
        kedro_logger.setLevel(logging.DEBUG)
        logging.disable(logging.NOTSET)
        private = Source("message-redacted", "PRIVATE_CANARY_USER_BODY")
        try:
            await run_case(private, ProbeService(fail_parse=True))
        except (SafeBoundaryError, DatasetError) as exc:
            assert "PRIVATE_CANARY" not in str(exc)
        else:
            raise AssertionError("expected redacted failure")
    finally:
        logging.disable(logging.CRITICAL)
        kedro_logger.handlers = old_handlers
        kedro_logger.propagate = old_propagate
        kedro_logger.setLevel(old_level)
    assert "PRIVATE_CANARY" not in capture.getvalue()

    assert NETWORK_ATTEMPTS == 0, NETWORK_ATTEMPTS
    return {
        "kedro_version": kedro_version,
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "scenarios": [
            "full_etl_catalog_load_parse_save",
            "replay_idempotent",
            "same_key_conflicting_digest_rejected",
            *failures,
            "cancel_worker_drain",
            "deadline_no_late_publication",
            "application_loop_heartbeat",
            "cooperative_cpu_node_cancel",
            "redacted_failure_logging",
            "no_network",
        ],
        "scenarios_passed": 12,
        "dataset_bridge_calls_normal": calls,
        "case_success_s": round(elapsed, 4),
        "cancellation_drain_s": round(cancel_drain, 4),
        "cpu_cancellation_drain_s": round(cpu_drain, 4),
        "event_loop_heartbeats": heartbeats,
        "socket_connection_attempts": NETWORK_ATTEMPTS,
        "safe_kedro_log_chars": len(capture.getvalue()),
        "service_stages_published": service.publish_count,
        "note": "synthetic service only; production persistence not proven",
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(verify()), sort_keys=True))

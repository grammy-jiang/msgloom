"""Isolated Q0 probe: Kedro 1.7.0 orchestrates trusted async-backed datasets.

Execute ONLY in a disposable virtualenv with:
    DO_NOT_TRACK=1 KEDRO_DISABLE_TELEMETRY=1 python -I scripts/research/q0_kedro_runtime_probe.py

No msgloom imports, filesystem writes, provider access, production DB, or network.
This is not a business-store acceptance or bounded-production-worker proof.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import hashlib
import io
import json
import logging
import os
import socket
import sys
import threading
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from time import monotonic
from types import SimpleNamespace
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
socket.socket.sendto = _deny_network  # type: ignore[method-assign]
socket.getaddrinfo = _deny_network  # type: ignore[assignment]

# Kedro's framework.project may configure Rich logging and print during import.
# This program intentionally keeps stdout as one machine-readable JSON record.
with contextlib.redirect_stdout(io.StringIO()):
    from kedro import __version__ as kedro_version
    from kedro.io import AbstractDataset, DataCatalog, DatasetError, MemoryDataset
    from kedro.io.core import AbstractVersionedDataset
    from kedro.pipeline import Pipeline, node
    from kedro.runner import SequentialRunner

logging.disable(logging.CRITICAL)


class SafeBoundaryError(Exception):
    """No untrusted payload or original exception text is included."""


class ProbeCheckError(Exception):
    """A failed Q0 check remains active even under python -O."""


def require(condition: bool, label: str) -> None:
    if not condition:
        raise ProbeCheckError("Q0 failed: " + label)


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
    publish_delay: float = 0.0
    publish_ack_delay: float = 0.0
    node_failure: str | None = None
    fail_parse: bool = False
    fail_publish: bool = False
    claim_valid: bool = True
    accepted: dict[str, Accepted] = field(default_factory=dict)
    publish_count: int = 0
    parse_count: int = 0
    failures: dict[str, int] = field(default_factory=dict)
    enter_publish: asyncio.Event = field(default_factory=asyncio.Event)
    committed: asyncio.Event = field(default_factory=asyncio.Event)
    parse_done: asyncio.Event = field(default_factory=asyncio.Event)
    enter_cpu: threading.Event = field(default_factory=threading.Event)

    def fail(self, reason: str) -> None:
        self.failures[reason] = self.failures.get(reason, 0) + 1

    async def parse(self, request: ParseRequest) -> Parsed:
        try:
            await asyncio.sleep(self.parser_delay)
            self.parse_count += 1
            if self.fail_parse:
                self.fail("parser")
                raise RuntimeError("PRIVATE_CANARY_PARSER_EXCEPTION")
            return Parsed(content=request.content.strip())
        finally:
            self.parse_done.set()

    async def publish(self, content: Normalized, stopped: threading.Event) -> Accepted:
        self.enter_publish.set()
        await asyncio.sleep(self.publish_delay)
        if stopped.is_set():
            self.fail("cancelled_before_commit")
            raise SafeBoundaryError("operation-stopped")
        if not self.claim_valid:
            self.fail("claim")
            raise RuntimeError("PRIVATE_CANARY_STALE_CLAIM")
        if self.fail_publish:
            self.fail("publisher")
            raise RuntimeError("PRIVATE_CANARY_PUBLISH_EXCEPTION")
        key = f"q0:{content.identity}:normalized:v1:code-v1"
        digest = hashlib.sha256(content.content.encode()).hexdigest()
        candidate = Accepted(key=key, payload_digest=digest)
        old = self.accepted.get(key)
        if old is not None:
            if old != candidate:
                self.fail("conflict")
                raise RuntimeError("PRIVATE_CANARY_OUTPUT_CONFLICT")
            return old
        self.accepted[key] = candidate
        self.publish_count += 1
        self.committed.set()
        await asyncio.sleep(self.publish_ack_delay)
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
        settled = threading.Event()

        async def fenced() -> Any:
            try:
                return await awaitable
            finally:
                settled.set()

        fut = asyncio.run_coroutine_threadsafe(fenced(), self.loop)
        self.calls += 1
        try:
            result = fut.result(timeout=max(0.01, self.deadline - monotonic()))
            if self.stopped.is_set() or monotonic() >= self.deadline:
                raise SafeBoundaryError("operation-stopped")
            return result
        except concurrent.futures.TimeoutError:
            fut.cancel()
            require(settled.wait(0.5), "service_timeout_cleanup")
            raise SafeBoundaryError("trusted-service-deadline") from None
        except Exception:  # noqa: BLE001 - redacted async-service boundary
            fut.cancel()
            require(settled.wait(0.5), "service_failure_cleanup")
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
        self.output = self.bridge.call(self.service.publish(data, self.bridge.stopped))

    def load(self) -> Accepted:
        if self.output is None:
            raise SafeBoundaryError("stage-result-missing")
        return self.output

    def _describe(self) -> dict[str, str]:
        return {"kind": "claim-fenced-stage-adapter"}


def require_catalog_closed(pipeline: Pipeline, catalog: DataCatalog) -> None:
    if set(pipeline.datasets()) != set(catalog.keys()):
        raise SafeBoundaryError("unexpected-dataset")


def build_pipeline_and_catalog(
    source: Source, service: ProbeService, bridge: ServiceBridge
) -> tuple[Pipeline, DataCatalog]:
    def make_request(data: Source) -> ParseRequest:
        return ParseRequest(content=data.content)

    def normalize(parsed: Parsed, src: Source) -> Normalized:
        if bridge.stopped.is_set() or monotonic() >= bridge.deadline:
            raise SafeBoundaryError("operation-stopped")
        if service.node_failure == "unsafe":
            raise RuntimeError("PRIVATE_CANARY_UNSAFE_NODE_FAILURE")
        if service.node_failure == "safe":
            raise SafeBoundaryError("node-transform-failed")
        service.enter_cpu.set()
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
    require_catalog_closed(pipeline, catalog)
    return pipeline, catalog


async def run_case(
    source: Source,
    service: ProbeService,
    *,
    budget: float = 1.0,
) -> tuple[dict[str, str], float, int]:
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
        return value, monotonic() - started, bridge.calls
    except asyncio.CancelledError:
        event.set()
        # asyncio.to_thread cannot be interrupted. Drain the real worker
        # before propagating CancelledError to the caller, so it cannot
        # accidentally interpret cancellation as a successful manifest.
        with contextlib.suppress(Exception):
            await asyncio.shield(worker)
        require(worker.done(), "worker_fully_drained_after_cancel")
        raise
    finally:
        event.set()


async def verify() -> dict[str, Any]:
    cases: list[str] = []
    source = Source("message-1", "  Confidential Example  ")
    service = ProbeService()
    result, elapsed, calls = await run_case(source, service)
    require(len(service.accepted) == service.publish_count == 1, "publish_once")
    require(len(result["sha256"]) == 64 and calls == 2, "typed_io_bridge")
    cases.append("full_etl_catalog_load_parse_save")

    again, _, _ = await run_case(source, service)
    require(again == result and service.publish_count == 1, "replay_idempotence")
    cases.append("replay_idempotent")

    try:
        await run_case(Source("message-1", "CHANGED"), service)
    except (SafeBoundaryError, DatasetError):
        pass
    else:
        raise ProbeCheckError("same-key conflicting output was accepted")
    require(service.publish_count == 1, "conflict_published_second_copy")
    require(service.failures.get("conflict") == 1, "wrong_conflict_failure")
    cases.append("same_key_conflicting_digest_rejected")

    for label, flags, reason in (
        ("parser_failure", {"fail_parse": True}, "parser"),
        ("stage_failure", {"fail_publish": True}, "publisher"),
        ("stale_claim", {"claim_valid": False}, "claim"),
    ):
        bad = ProbeService(**flags)
        try:
            await run_case(source, bad)
        except (SafeBoundaryError, DatasetError) as exc:
            require("PRIVATE_CANARY" not in str(exc), label + "_exception_redacted")
        else:
            raise ProbeCheckError(label + " unexpectedly succeeded")
        require(not bad.accepted, label + "_accepted_bad_data")
        require(bad.failures.get(reason) == 1, label + "_wrong_reason")
        cases.append(label)

    # Runner's permissive runtime catch-all is forbidden for trusted datasets.
    temp = ProbeService()
    loop = asyncio.get_running_loop()
    bridge = ServiceBridge(
        loop=loop,
        owner_thread=threading.get_ident(),
        stopped=threading.Event(),
        deadline=monotonic() + 1,
    )
    pipeline, catalog = build_pipeline_and_catalog(source, temp, bridge)
    require(set(pipeline.datasets()) == set(catalog.keys()), "catalog_allowlist")
    unregistered = Pipeline(
        [node(lambda x: x, "frozen_input", "undeclared", name="q0_bad_catalog")]
    )
    try:
        require_catalog_closed(unregistered, catalog)
    except SafeBoundaryError as exc:
        require(str(exc) == "unexpected-dataset", "catalog_wrong_error")
    else:
        raise ProbeCheckError("bad catalog accepted")
    cases.append("reject_unregistered_catalog_dataset")

    # An active async parse is not preempted by coroutine cancellation. Its
    # worker must still be drained and no later stage may be published.
    slow = ProbeService(parser_delay=0.16)
    task = asyncio.create_task(run_case(source, slow))
    await asyncio.sleep(0.02)
    require(task.cancel(), "parse_cancel_sent")
    cancel_started = monotonic()
    try:
        await task
    except asyncio.CancelledError:
        pass
    else:
        raise ProbeCheckError("parse cancellation lost")
    cancel_drain = monotonic() - cancel_started
    require(slow.parse_done.is_set(), "parse_coroutine_not_settled")
    require(not slow.accepted, "parser_cancel_no_publish")
    require(cancel_drain < 0.5, "parser_cancel_drained")
    cases.append("cancel_parser_drain_no_late_stage")

    deadline = ProbeService(parser_delay=0.16)
    try:
        await run_case(source, deadline, budget=0.025)
    except (SafeBoundaryError, DatasetError):
        pass
    else:
        raise ProbeCheckError("expired operation unexpectedly succeeded")
    require(deadline.parse_done.is_set(), "expired_coroutine_not_settled")
    require(not deadline.accepted, "deadline_no_accepted_effect")
    cases.append("deadline_drains_service_future")

    # Cancellation *inside* a write before the atomic acceptance point.
    before = ProbeService(publish_delay=0.14)
    before_task = asyncio.create_task(run_case(source, before))
    await asyncio.wait_for(before.enter_publish.wait(), timeout=0.6)
    require(before_task.cancel(), "precommit_cancel_sent")
    try:
        await before_task
    except asyncio.CancelledError:
        pass
    else:
        raise ProbeCheckError("precommit cancellation lost")
    require(not before.accepted, "precommit_write_after_cancel")
    require(
        before.failures.get("cancelled_before_commit") == 1,
        "precommit_stop_not_checked",
    )
    cases.append("cancel_inside_publish_before_commit")

    # Claim is valid on entry but becomes invalid while the write awaits.
    revoked = ProbeService(publish_delay=0.14)
    revocation_task = asyncio.create_task(run_case(source, revoked))
    await asyncio.wait_for(revoked.enter_publish.wait(), timeout=0.6)
    revoked.claim_valid = False
    try:
        await revocation_task
    except (SafeBoundaryError, DatasetError):
        pass
    else:
        raise ProbeCheckError("revoked mid-flight claim accepted")
    require(revoked.failures.get("claim") == 1, "midflight_claim_not_rechecked")
    require(not revoked.accepted, "midflight_revoked_claim_wrote")
    cases.append("midflight_claim_revocation_rejected")

    # At the commit boundary the stage may already be accepted while its
    # acknowledgement has not reached the Kedro worker. Cancellation must
    # remain visible (not falsely successful); recovery must read back.
    committed = ProbeService(publish_ack_delay=0.14)
    commit_task = asyncio.create_task(run_case(source, committed))
    await asyncio.wait_for(committed.committed.wait(), timeout=0.6)
    require(commit_task.cancel(), "postcommit_cancel_sent")
    try:
        await commit_task
    except asyncio.CancelledError:
        pass
    else:
        raise ProbeCheckError("postcommit cancellation lost")
    require(len(committed.accepted) == committed.publish_count == 1, "commit_missing")
    recovery_manifest, _, _ = await run_case(source, committed)
    require(recovery_manifest == result, "postcommit_reconciliation_wrong_result")
    require(committed.publish_count == 1, "postcommit_reconcile_double_commit")
    cases.append("cancel_after_commit_requires_readback_reconcile")

    # Compare time between actual ticks while a CPU-busy node is active.
    heartbeat_service = ProbeService(cpu_delay=0.23)
    heartbeat_task = asyncio.create_task(run_case(source, heartbeat_service))
    wait_limit = monotonic() + 0.5
    while not heartbeat_service.enter_cpu.is_set() and monotonic() < wait_limit:
        await asyncio.sleep(0.002)
    require(heartbeat_service.enter_cpu.is_set(), "heartbeat_cpu_did_not_start")
    tick_gaps: list[float] = []
    during_cpu = 0
    prev = monotonic()
    for _ in range(8):
        await asyncio.sleep(0.012)
        now = monotonic()
        tick_gaps.append(now - prev)
        prev = now
        if not heartbeat_task.done():
            during_cpu += 1
    heartbeat_result, _, _ = await heartbeat_task
    max_gap = max(tick_gaps)
    require(heartbeat_result == result, "heartbeat_result")
    require(during_cpu >= 5, "heartbeat_did_not_overlap_work")
    require(max_gap < 0.08, "event_loop_blocked_by_cpu")
    cases.append("event_loop_heartbeat_under_cpu")

    cpu = ProbeService(cpu_delay=0.15)
    cpu_task = asyncio.create_task(run_case(source, cpu))
    wait_limit = monotonic() + 0.5
    while not cpu.enter_cpu.is_set() and monotonic() < wait_limit:
        await asyncio.sleep(0.002)
    require(cpu.enter_cpu.is_set(), "cpu_cancel_phase_not_reached")
    cpu_task.cancel()
    cpu_cancel_started = monotonic()
    try:
        await cpu_task
    except asyncio.CancelledError:
        pass
    else:
        raise ProbeCheckError("cpu cancellation lost")
    cpu_drain = monotonic() - cpu_cancel_started
    require(not cpu.accepted and cpu_drain < 0.5, "cpu_cancel_cleanup")
    cases.append("cooperative_cpu_node_cancel")

    # Prove the redaction probe would FAIL on Kedro's real Node.run ERROR
    # logger if a raw exception leaked. Then check sanitized node error and
    # provider-dataset error against that positive logging control.
    async def capture_failure(mode: str) -> tuple[str, str]:
        capture = io.StringIO()
        handler = logging.StreamHandler(capture)
        logger = logging.getLogger("kedro")
        old_handlers, old_propagate, old_level = (
            logger.handlers[:],
            logger.propagate,
            logger.level,
        )
        try:
            logger.handlers = [handler]
            logger.propagate = False
            logger.setLevel(logging.DEBUG)
            logging.disable(logging.NOTSET)
            vulnerable_input = Source("redaction-test", "PRIVATE_CANARY_USER_BODY")
            if mode == "parser":
                synthetic = ProbeService(fail_parse=True)
            else:
                synthetic = ProbeService(node_failure=mode)
            try:
                await run_case(vulnerable_input, synthetic)
            except (SafeBoundaryError, DatasetError, RuntimeError) as exc:
                error_message = str(exc)
            else:
                raise ProbeCheckError("redaction control did not fail: " + mode)
        finally:
            logging.disable(logging.CRITICAL)
            logger.handlers = old_handlers
            logger.propagate = old_propagate
            logger.setLevel(old_level)
        require(bool(capture.getvalue()), "kedro_log_capture_empty_" + mode)
        return capture.getvalue(), error_message

    unsafe_logs, unsafe_error = await capture_failure("unsafe")
    require("PRIVATE_CANARY_UNSAFE_NODE_FAILURE" in unsafe_logs, "positive_log_control")
    require("PRIVATE_CANARY" in unsafe_error, "positive_exception_control")
    safe_logs, safe_error = await capture_failure("safe")
    require("node-transform-failed" in safe_logs, "safe_node_error_not_logged")
    require("PRIVATE_CANARY" not in safe_logs + safe_error, "node_error_leak")
    cases.append("node_failure_log_redaction_with_positive_control")
    parser_logs, parser_error = await capture_failure("parser")
    require("PRIVATE_CANARY" not in parser_logs + parser_error, "parser_error_leak")
    cases.append("dataset_failure_log_redaction")

    from kedro_telemetry.api import send_telemetry_event
    from kedro_telemetry.plugin import _check_for_telemetry_consent

    original_connections = NETWORK_ATTEMPTS
    require(
        _check_for_telemetry_consent(None) is False, "telemetry_consent_not_disabled"
    )
    require(not send_telemetry_event("q0_nonidentifying_probe"), "telemetry_sent")
    require(NETWORK_ATTEMPTS == original_connections, "telemetry_network_attempted")
    cases.append("kedro_telemetry_opt_out")

    # A positive control for the socket deny mechanism, with no real network.
    try:
        socket.create_connection(("127.0.0.1", 9), timeout=0.01)
    except RuntimeError as exc:
        require(str(exc) == "Q0 network denied", "wrong_socket_denial")
    else:
        raise ProbeCheckError("network denial mechanism did not intercept")
    require(NETWORK_ATTEMPTS == original_connections + 1, "socket_monkeypatch_inert")
    cases.append("network_interception_positive_control")

    # Exercise the exact 1.7 wheel's core path guard, not just a copy of it.
    path_holder = SimpleNamespace(_filepath=PurePosixPath("/q0-only/fixture.txt"))
    unsafe_versions = (
        "",
        ".",
        "..",
        "../secret",
        "../../secret",
        "/tmp/x",
        "a/b",
        "a\\b",
    )
    safe_versions = ("v1", "2026-10-23", "date_20261023T000000")
    for version in unsafe_versions:
        try:
            AbstractVersionedDataset._get_versioned_path(path_holder, version)
        except DatasetError:
            pass
        else:
            raise ProbeCheckError("unsafe version path accepted")
    for version in safe_versions:
        result_path = AbstractVersionedDataset._get_versioned_path(path_holder, version)
        require(result_path.parent.name == version, "safe_version_rejected")
    cases.append("exact_wheel_version_path_guard")

    # Failure-instrumentation positive control must survive Python -O.
    try:
        require(False, "negative_control")
    except ProbeCheckError:
        pass
    else:
        raise ProbeCheckError("test gate vanished under optimization")
    cases.append("runtime_checks_survive_python_optimized")

    return {
        "kedro_version": kedro_version,
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "scenarios": cases,
        "scenarios_passed": len(cases),
        "dataset_bridge_calls_normal": calls,
        "case_success_s": round(elapsed, 4),
        "parser_cancel_drain_s": round(cancel_drain, 4),
        "cpu_cancel_drain_s": round(cpu_drain, 4),
        "heartbeat_max_gap_s": round(max_gap, 5),
        "heartbeat_ticks_during_cpu": during_cpu,
        "positive_node_log_chars": len(unsafe_logs),
        "redacted_node_log_chars": len(safe_logs),
        "redacted_dataset_log_chars": len(parser_logs),
        "socket_connection_attempts_during_runtime": original_connections,
        "socket_control_interceptions": NETWORK_ATTEMPTS - original_connections,
        "claims_changed_at_runtime": revoked.failures["claim"],
        "postcommit_cancel_observed_accepted": committed.publish_count,
        "service_stages_published": service.publish_count,
        "note": "synthetic store, no Phase1Persistence; postcommit requires readback",
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(verify()), sort_keys=True))

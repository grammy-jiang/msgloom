"""Focused regressions for the awaited parser process boundary."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from typing import Any, cast
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

import msgloom.preparation.isolation.runner as isolation_runner
from msgloom.preparation import (
    DocumentFormat,
    ParserConfig,
    ParserIdentity,
    ParserLimits,
    ParserRequest,
    SavedByteReference,
)
from msgloom.preparation.isolation import (
    ParserIsolationError,
    ParserIsolationUnavailable,
    ParserOutputError,
    ParserTimeoutError,
)
from msgloom.preparation.isolation.registry import RegistryEntry, TrustedRegistry
from msgloom.preparation.isolation.runner import _parse_isolated, _read_output
from msgloom.preparation.isolation.wire import decode_output

_FIXTURE = Path(__file__).with_name("fixture_backend.py")
_IDENTITY = ParserIdentity(
    "msgloom.synthetic-fixture",
    "1",
    "synthetic-safe-fixture-1",
)
_REGISTRY = TrustedRegistry(
    (
        RegistryEntry(
            formats=(DocumentFormat.TEXT,),
            module="fixture_backend",
            identity=_IDENTITY,
            fixture_file=_FIXTURE,
        ),
    )
)


def _request(
    content: bytes = b"synthetic content",
    *,
    settings: tuple[tuple[str, str], ...] = (),
    wall_time: float = 5.0,
    output_bytes: int = 64 * 1024,
) -> ParserRequest:
    return ParserRequest(
        source=SavedByteReference(
            reference="blob:synthetic-parser-isolation",
            sha256=hashlib.sha256(content).hexdigest(),
            byte_count=len(content),
        ),
        detected_format=DocumentFormat.TEXT,
        parser=_IDENTITY,
        config=ParserConfig(profile="synthetic", settings=settings),
        limits=ParserLimits(
            wall_time_seconds=wall_time,
            memory_bytes=256 * 1024 * 1024,
            decompressed_bytes=1024 * 1024,
            output_bytes=output_bytes,
            container_members=64,
        ),
    )


def test_parse_isolated_returns_exact_provenance_and_keeps_loop_responsive() -> None:
    """Synchronous parser work runs outside the caller event-loop thread."""

    async def exercise() -> None:
        request = _request(
            settings=(("mode", "sleep"), ("seconds", "0.25")),
        )
        ticks = 0
        done = asyncio.Event()

        async def heartbeat() -> None:
            nonlocal ticks
            while not done.is_set():
                ticks += 1
                await asyncio.sleep(0.01)

        heartbeat_task = asyncio.create_task(heartbeat())
        try:
            output = await _parse_isolated(request, b"synthetic content", _REGISTRY)
        finally:
            done.set()
            await heartbeat_task
        if output.provenance.source != request.source:
            pytest.fail("Expected exact saved-byte provenance")
        if output.provenance.parser != request.parser:
            pytest.fail("Expected exact parser provenance")
        if ticks < 10:
            pytest.fail(f"Event loop heartbeat stalled; observed only {ticks} ticks")

    asyncio.run(exercise())


def test_prelaunch_identity_hash_and_count_checks_fail_closed() -> None:
    """Tampered bytes and unregistered parser identity never reach a worker."""
    content = b"synthetic content"
    request = _request(content)
    bad_count = replace(
        request,
        source=replace(request.source, byte_count=request.source.byte_count + 1),
    )
    with pytest.raises(ValueError, match="byte count"):
        asyncio.run(_parse_isolated(bad_count, content, _REGISTRY))

    bad_hash = replace(
        request,
        source=replace(request.source, sha256="00" * 32),
    )
    with pytest.raises(ValueError, match="byte hash"):
        asyncio.run(_parse_isolated(bad_hash, content, _REGISTRY))

    bad_identity = replace(
        request,
        parser=ParserIdentity("untrusted.request.module", "1", "synthetic"),
    )
    with pytest.raises(ParserIsolationError, match="trusted registry"):
        asyncio.run(_parse_isolated(bad_identity, content, _REGISTRY))


def test_sandbox_hides_host_paths_environment_and_external_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Worker sees only the allowlisted environment and isolated namespaces."""
    monkeypatch.setenv("MSGLOOM_SYNTHETIC_SECRET", "must-not-cross-boundary")
    request = _request(settings=(("mode", "probe"),))
    output = asyncio.run(_parse_isolated(request, b"synthetic content", _REGISTRY))
    text = cast(Any, output.blocks[0]).text
    expected = (
        "forbidden_path=0;secret=0;external_route=0;home=/nonexistent;"
        "keys=HOME,LC_CTYPE,PATH,PWD,PYTHONDONTWRITEBYTECODE,"
        "PYTHONNOUSERSITE,PYTHONPATH,PYTHONUTF8"
    )
    if text != expected:
        pytest.fail(f"Unexpected sandbox probe result: {text}")


def test_timeout_kills_and_reaps_worker_descendants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wall timeout cannot leave a fixture descendant running."""
    spawned: list[int] = []
    _capture_subprocess_pid(monkeypatch, spawned)
    request = _request(
        settings=(("mode", "spawn"), ("token", "synthetic-timeout")),
        wall_time=5.0,
    )

    async def exercise() -> set[int]:
        task = asyncio.create_task(
            _parse_isolated(request, b"synthetic content", _REGISTRY)
        )
        descendants = await _wait_for_descendants(spawned, minimum=3, seconds=4.0)
        if len(descendants) < 3:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            pytest.fail(
                f"Fixture descendant did not start before timeout; "
                f"spawned={spawned}, descendants={descendants}"
            )
        with pytest.raises(ParserTimeoutError, match="wall-time"):
            await task
        return descendants

    descendants = asyncio.run(exercise())
    _require_processes_gone(descendants)


def test_cancellation_kills_and_reaps_worker_descendants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caller cancellation is propagated only after child cleanup completes."""
    spawned: list[int] = []
    _capture_subprocess_pid(monkeypatch, spawned)

    async def exercise() -> set[int]:
        request = _request(
            settings=(("mode", "spawn"), ("token", "synthetic-cancel")),
            wall_time=10,
        )
        task = asyncio.create_task(
            _parse_isolated(request, b"synthetic content", _REGISTRY)
        )
        descendants = await _wait_for_descendants(spawned, minimum=3, seconds=5.0)
        if len(descendants) < 3:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            pytest.fail(
                f"Fixture descendant did not start before cancellation; "
                f"spawned={spawned}, descendants={descendants}"
            )
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return descendants

    descendants = asyncio.run(exercise())
    _require_processes_gone(descendants)


def test_required_linux_isolation_unavailable_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Missing required bubblewrap support cannot fall back in-process."""
    monkeypatch.setattr(isolation_runner, "_BWRAP", tmp_path / "missing-bwrap")
    request = _request()
    with pytest.raises(ParserIsolationUnavailable, match="bubblewrap"):
        asyncio.run(_parse_isolated(request, b"synthetic content", _REGISTRY))


@pytest.mark.parametrize(
    "payload",
    [
        (
            b'{"provenance":{},"provenance":{},"blocks":[],'
            b'"mime_parts":[],"limitations":[]}'
        ),
        (b'{"provenance":{},"blocks":[],"mime_parts":[],"limitations":[],"extra":1}'),
        (b'{"provenance":{},"blocks":[],"mime_parts":[],"limitations":[NaN]}'),
    ],
)
def test_wire_decoder_rejects_duplicate_unknown_and_nonfinite_json(
    payload: bytes,
) -> None:
    """Strict JSON decoding rejects ambiguous or extended wire payloads."""
    with pytest.raises((TypeError, ValueError)):
        decode_output(payload)


def test_worker_rejects_output_larger_than_request_ceiling() -> None:
    """A trusted parser cannot make IPC output exceed the caller ceiling."""
    request = _request(
        settings=(("mode", "large"), ("size", "20000")),
        output_bytes=2048,
    )
    with pytest.raises(ParserIsolationError, match="process failed"):
        asyncio.run(_parse_isolated(request, b"synthetic content", _REGISTRY))


def test_output_reader_rejects_symlink_oversize_and_malformed_json(
    tmp_path: Path,
) -> None:
    """Host reads only bounded regular files and strictly validates JSON."""
    target = tmp_path / "target"
    target.write_bytes(b"{}")
    link = tmp_path / "result.json"
    link.symlink_to(target)
    with pytest.raises(ParserOutputError, match="safe regular file"):
        _read_output(link, 128)

    link.unlink()
    link.write_bytes(b"x" * 129)
    with pytest.raises(ParserOutputError, match="output-byte ceiling"):
        _read_output(link, 128)

    link.write_bytes(b'{"provenance":{},"blocks":[],"mime_parts":[],"limitations":[]}')
    payload = _read_output(link, 1024)
    with pytest.raises((TypeError, ValueError)):
        decode_output(payload)


@pytest.mark.parametrize(
    ("format_", "content"),
    [
        (DocumentFormat.PDF, b"not a pdf"),
        (DocumentFormat.XLS, b"not ole"),
        (DocumentFormat.DOC, b"not ole"),
        (DocumentFormat.XLSX, b"not zip"),
    ],
)
def test_signature_and_container_checks_precede_worker_launch(
    format_: DocumentFormat,
    content: bytes,
) -> None:
    """Reject inconsistent native-format bytes before process launch."""
    request = replace(
        _request(content),
        detected_format=format_,
        parser=ParserIdentity("unused", "1", "unused"),
    )
    registry = TrustedRegistry(
        (
            RegistryEntry(
                formats=(format_,),
                module="fixture_backend",
                identity=request.parser,
                fixture_file=_FIXTURE,
            ),
        )
    )
    with pytest.raises(ValueError):
        asyncio.run(_parse_isolated(request, content, registry))


def test_parser_failure_is_opaque_and_does_not_echo_input() -> None:
    """Parser exception text cannot cross the process trust boundary."""
    secret = b"synthetic-secret-that-must-not-echo"
    request = _request(secret, settings=(("mode", "raise"),))
    with pytest.raises(ParserIsolationError) as caught:
        asyncio.run(_parse_isolated(request, secret, _REGISTRY))
    if secret.decode() in str(caught.value):
        pytest.fail("Parser error echoed source content across the boundary")


def test_exact_provenance_is_revalidated_after_strict_decode() -> None:
    """Reject structurally valid output with substituted source provenance."""
    request = _request(settings=(("mode", "bad_provenance"),))
    with pytest.raises(ParserOutputError, match="provenance"):
        asyncio.run(_parse_isolated(request, b"synthetic content", _REGISTRY))


def test_container_member_and_decompression_ceilings_fail_before_parser() -> None:
    """Bound ZIP structure and expansion before native parser import."""
    many = _zip_bytes({"[Content_Types].xml": b"x", "xl/workbook.xml": b"x"})
    request = replace(
        _request(many),
        detected_format=DocumentFormat.XLSX,
        parser=ParserIdentity("unused", "1", "unused"),
        limits=replace(_request(many).limits, container_members=1),
    )
    registry = TrustedRegistry(
        (
            RegistryEntry(
                formats=(DocumentFormat.XLSX,),
                module="fixture_backend",
                identity=request.parser,
                fixture_file=_FIXTURE,
            ),
        )
    )
    with pytest.raises(ValueError, match="member ceiling"):
        asyncio.run(_parse_isolated(request, many, registry))

    expanded = _zip_bytes(
        {
            "[Content_Types].xml": b"x",
            "xl/workbook.xml": b"x" * 4096,
        }
    )
    expanded_request = replace(
        request,
        source=SavedByteReference(
            reference="blob:synthetic-expanded",
            sha256=hashlib.sha256(expanded).hexdigest(),
            byte_count=len(expanded),
        ),
        limits=replace(
            request.limits,
            container_members=8,
            decompressed_bytes=max(len(expanded), 1024),
        ),
    )
    with pytest.raises(ValueError, match="decoded-byte ceiling"):
        asyncio.run(_parse_isolated(expanded_request, expanded, registry))


def _zip_bytes(parts: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def _capture_subprocess_pid(
    monkeypatch: pytest.MonkeyPatch,
    spawned: list[int],
) -> None:
    real_create = asyncio.create_subprocess_exec

    async def capture(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        process = await real_create(*args, **kwargs)
        spawned.append(process.pid)
        return process

    monkeypatch.setattr(isolation_runner.asyncio, "create_subprocess_exec", capture)


async def _wait_for_descendants(
    spawned: list[int],
    *,
    minimum: int,
    seconds: float,
) -> set[int]:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + seconds
    descendants: set[int] = set()
    best: set[int] = set()
    while loop.time() < deadline:
        if spawned:
            descendants = _descendant_pids(spawned[0])
            if len(descendants) > len(best):
                best = descendants
            if len(descendants) >= minimum:
                return descendants
        await asyncio.sleep(0.02)
    return best


def _descendant_pids(root_pid: int) -> set[int]:
    parents: dict[int, int] = {}
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            stat_text = (path / "stat").read_text(encoding="ascii")
            rest = stat_text[stat_text.rindex(")") + 2 :].split()
            parents[int(path.name)] = int(rest[1])
        except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError):
            continue
    descendants: set[int] = set()
    frontier = {root_pid}
    while frontier:
        children = {pid for pid, parent in parents.items() if parent in frontier}
        children -= descendants
        if not children:
            break
        descendants.update(children)
        frontier = children
    return descendants


def _require_processes_gone(processes: set[int]) -> None:
    survivors = [pid for pid in processes if Path(f"/proc/{pid}").exists()]
    if survivors:
        pytest.fail(f"Sandbox descendants survived cleanup: {survivors}")

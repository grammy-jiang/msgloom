"""Sandbox-side parser worker with no persistence or completion authority."""

from __future__ import annotations

import importlib
import math
import os
import resource
import stat
import sys
from pathlib import Path
from types import ModuleType
from typing import Protocol, cast

from msgloom.preparation.contracts import ParserOutput, ParserRequest
from msgloom.preparation.isolation.request_wire import decode_request
from msgloom.preparation.isolation.validation import (
    validate_format_content,
    verify_saved_bytes,
)
from msgloom.preparation.isolation.wire import encode_output

_MAX_REQUEST_BYTES = 64 * 1024
_INPUT_PATH = Path("/input/content")
_OUTPUT_PATH = Path("/output/result.json")


class _Parser(Protocol):
    def __call__(self, request: ParserRequest, content: bytes) -> ParserOutput: ...


def _set_limits(memory_bytes: int, output_bytes: int, wall_time: float) -> None:
    cpu_seconds = max(1, math.ceil(wall_time))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    resource.setrlimit(resource.RLIMIT_FSIZE, (output_bytes, output_bytes))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_NPROC, (16, 16))


def _load_parser(
    module_name: str,
    expected_name: str,
    expected_version: str,
    expected_backend: str,
) -> _Parser:
    module: ModuleType = importlib.import_module(module_name)
    if getattr(module, "PARSER_NAME", None) != expected_name:
        raise RuntimeError("parser name does not match trusted registry")
    if getattr(module, "PARSER_VERSION", None) != expected_version:
        raise RuntimeError("parser version does not match trusted registry")
    if getattr(module, "BACKEND", None) != expected_backend:
        raise RuntimeError("parser backend does not match trusted registry")
    parser = getattr(module, "parse", None)
    if not callable(parser):
        raise TypeError("trusted parser does not export parse")
    return cast(_Parser, parser)


def _read_request() -> bytes:
    payload = sys.stdin.buffer.read(_MAX_REQUEST_BYTES + 1)
    if len(payload) > _MAX_REQUEST_BYTES:
        raise ValueError("parser request exceeds IPC ceiling")
    return payload


def _write_output(payload: bytes, limit: int) -> None:
    if len(payload) > limit:
        raise ValueError("parser output exceeds output-byte ceiling")
    fd = os.open(_OUTPUT_PATH, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError("parser output channel is not a safe regular file")
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(payload)
            stream.flush()
        os.close(fd)
        fd = -1
    finally:
        if fd >= 0:
            os.close(fd)


def main(argv: list[str]) -> int:
    """Run exactly one trusted parser and write one bounded result."""
    if len(argv) != 5:
        return 64
    module_name, expected_name, expected_version, expected_backend = argv[1:]
    try:
        request = decode_request(_read_request())
        _set_limits(
            request.limits.memory_bytes,
            request.limits.output_bytes,
            request.limits.wall_time_seconds,
        )
        content = _INPUT_PATH.read_bytes()
        verify_saved_bytes(request, content)
        validate_format_content(request, content)
        parser = _load_parser(
            module_name,
            expected_name,
            expected_version,
            expected_backend,
        )
        output = parser(request, content)
        if not isinstance(output, ParserOutput):
            raise TypeError("trusted parser returned an unexpected type")
        _write_output(encode_output(output), request.limits.output_bytes)
    # The process boundary converts all ordinary parser/library failures into
    # one opaque status; stderr is discarded so source-derived errors cannot
    # cross the trust boundary. BaseException subclasses retain signal exits.
    except Exception:  # noqa: BLE001
        return 70
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

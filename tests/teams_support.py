"""Serve exact Graph fixtures and run isolated native Scrapy commands.

Routes match the HTTP request target verbatim. This support owns only test
transport and process setup; production code owns paths, parsing, retries,
evidence, and persistence. Teams semantic helpers are deliberately separate.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import deque
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread

import pytest

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class FixtureReply:
    """One immutable response, including duplicate headers and exact bytes."""

    status: int = 200
    body: bytes = b""
    headers: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class SeenRequest:
    """One received target with ordered headers, before reply selection."""

    target: str
    headers: tuple[tuple[str, str], ...]

    def header(self, name: str) -> tuple[str, ...]:
        """Return all values for a case-insensitive header name."""
        return tuple(v for k, v in self.headers if k.lower() == name.lower())


def json_reply(
    payload: object,
    *,
    status: int = 200,
    headers: tuple[tuple[str, str], ...] = (),
) -> FixtureReply:
    """Serialize a supplied payload without editing provider links."""
    return FixtureReply(
        status=status,
        body=json.dumps(payload, ensure_ascii=False).encode(),
        headers=(("Content-Type", "application/json"), *headers),
    )


class GraphFixture:
    """Record requests and consume per-route response sequences under a lock.

    The final response repeats for subsequent requests. Unknown routes fail
    with ``FixtureRouteMissing``; no fallback invents a successful collection.
    ``add`` replaces a route, so repeat crawls can observe a later version.
    The fixture never normalizes paths, percent escapes, or query strings.
    """

    def __init__(self) -> None:
        self.origin = ""
        self._lock = Lock()
        self._routes: dict[str, deque[FixtureReply]] = {}
        self._seen: list[SeenRequest] = []

    @property
    def graph_root(self) -> str:
        """Return the fixture's v1.0 service root."""
        return self.origin + "/v1.0"

    @property
    def seen(self) -> tuple[SeenRequest, ...]:
        """Return a consistent immutable snapshot in arrival order."""
        with self._lock:
            return tuple(self._seen)

    def url(self, target: str) -> str:
        """Prefix an origin-relative target without rebuilding its query."""
        if not target.startswith("/") or target.startswith("//"):
            raise ValueError("Fixture target must be origin-relative")
        return self.origin + target

    def add(self, target: str, *replies: FixtureReply) -> None:
        """Set an exact route and a nonempty response sequence."""
        self.url(target)
        if not replies:
            raise ValueError("Fixture route requires at least one reply")
        with self._lock:
            self._routes[target] = deque(replies)

    def _reply(self, request: SeenRequest) -> FixtureReply:
        """Record and select atomically; do not implement retry behavior."""
        with self._lock:
            self._seen.append(request)
            if replies := self._routes.get(request.target):
                return replies.popleft() if len(replies) > 1 else replies[0]
        return json_reply({"error": {"code": "FixtureRouteMissing"}}, status=404)


@contextmanager
def serve_graph() -> Iterator[GraphFixture]:
    """Start a local server and always drain its threads on exit."""
    fixture = GraphFixture()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            """Keep fixture request URLs out of test runner logs."""

        def do_GET(self) -> None:
            """Write supplied bytes and headers without provider semantics."""
            reply = fixture._reply(
                SeenRequest(self.path, tuple(self.headers.raw_items()))
            )
            self.send_response(reply.status)
            for name, value in reply.headers:
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(reply.body)))
            self.end_headers()
            self.wfile.write(reply.body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    fixture.origin = f"http://127.0.0.1:{server.server_port}"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield fixture
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise RuntimeError("Teams fixture server did not stop")


@pytest.fixture
def graph_fixture() -> Iterator[GraphFixture]:
    """Expose the shared server by importing this fixture in a test module."""
    with serve_graph() as fixture:
        yield fixture


def crawl(
    tmp_path: Path,
    fixture: GraphFixture,
    arguments: Sequence[str],
    *,
    extra_settings: Mapping[str, object] | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    """Run ``scrapy`` arguments with isolated fixture settings and storage.

    Authentication and identity binding are disabled only for this local
    fixture. The real add-on, downloader, retry policy, and fingerprints stay
    enabled. ``CONCURRENT_ITEMS`` remains the project value. Callers inspect
    persisted evidence and logical integrity, not only the CLI return code.
    """
    settings: dict[str, object] = {
        "MS_GRAPH_SERVICE_ROOT": fixture.graph_root,
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        "MSGLOOM_TEAMS_SOURCE_ID": "teams-fixture",
        "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        "MSGLOOM_CATALOG_ENABLED": True,
        "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
        "HTTPCACHE_ENABLED": False,
        "AUTOTHROTTLE_ENABLED": False,
        "LOG_LEVEL": "DEBUG",
    }
    settings.update(extra_settings or {})
    args = [sys.executable, "-m", "scrapy", *arguments]
    for key, value in settings.items():
        encoded = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        args.extend(["-s", f"{key}={encoded}"])
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        (str(ROOT / "tests"), str(ROOT), env.get("PYTHONPATH", ""))
    )
    return subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

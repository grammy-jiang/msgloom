"""Read live, versioned diagnostics through a finite stdio LSP session."""

from __future__ import annotations

import argparse
import json
import os
import selectors
import subprocess
import time
from pathlib import Path
from typing import Any, BinaryIO, cast


class Connection:
    """Frame JSON-RPC messages without a background reader or daemon."""

    def __init__(self, process: subprocess.Popen) -> None:
        """Bind the explicitly piped server streams."""
        self.reader = cast(BinaryIO, process.stdout)
        self.writer = cast(BinaryIO, process.stdin)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.reader, selectors.EVENT_READ)
        self.buffer = b""

    def send(self, value: dict) -> None:
        """Send one complete framed message."""
        raw = json.dumps({"jsonrpc": "2.0", **value}).encode()
        self.writer.write(f"Content-Length: {len(raw)}\r\n\r\n".encode() + raw)
        self.writer.flush()

    def receive(self, deadline: float) -> dict[str, Any] | None:
        """Wait only until the caller's unchanged session deadline."""
        while time.monotonic() < deadline:
            split = self.buffer.find(b"\r\n\r\n")
            if split >= 0:
                headers = dict(
                    line.split(b":", 1) for line in self.buffer[:split].split(b"\r\n")
                )
                size = int(headers[b"Content-Length"])
                if len(self.buffer) >= split + 4 + size:
                    payload = self.buffer[split + 4 : split + 4 + size]
                    self.buffer = self.buffer[split + 4 + size :]
                    return json.loads(payload)
            if not self.selector.select(max(0, deadline - time.monotonic())):
                return None
            chunk = os.read(self.reader.fileno(), 65536)
            if not chunk:
                raise RuntimeError("language server exited before diagnostics")
            self.buffer += chunk
        return None

    def close(self) -> None:
        """Close the selector and both pipes after the server is reaped."""
        self.selector.close()
        self.reader.close()
        self.writer.close()


def _configuration(python: str, section: str) -> dict:
    if section == "python":
        return {"pythonPath": python}
    if section in {"python.analysis", "pyright"}:
        return {"diagnosticMode": "openFilesOnly", "typeCheckingMode": "standard"}
    return {}


def _message(connection: Connection, deadline: float, python: str) -> dict | None:
    while (message := connection.receive(deadline)) is not None:
        if "id" not in message or "method" not in message:
            return message
        result = None
        if message["method"] == "workspace/configuration":
            result = [
                _configuration(python, item.get("section", ""))
                for item in message.get("params", {}).get("items", [])
            ]
        connection.send({"id": message["id"], "result": result})
    return None


def diagnose(
    root: Path,
    python: str,
    paths: list[Path],
    *,
    server_command: tuple[str, ...] = ("pyright-langserver", "--stdio"),
    wait_seconds: float = 180,
    settle_seconds: float = 5,
) -> dict:
    """Require a version-one diagnostic publication for every opened file."""
    if not paths:
        raise ValueError("live LSP requires explicit Python documents")
    uris = {path.resolve().as_uri() for path in paths}
    process = subprocess.Popen(
        server_command,
        cwd=root,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    connection = Connection(process)
    received = {}
    try:
        connection.send(
            {
                "id": 1,
                "method": "initialize",
                "params": {
                    "processId": os.getpid(),
                    "rootUri": root.as_uri(),
                    "workspaceFolders": [{"uri": root.as_uri(), "name": "msgloom"}],
                    "capabilities": {
                        "workspace": {"configuration": True},
                        "textDocument": {
                            "publishDiagnostics": {"versionSupport": True}
                        },
                    },
                },
            }
        )
        initialized = False
        deadline = time.monotonic() + wait_seconds
        while (message := _message(connection, deadline, python)) is not None:
            if message.get("id") == 1:
                initialized = "error" not in message
                break
        if not initialized:
            raise RuntimeError("LSP initialization did not complete")
        connection.send({"method": "initialized", "params": {}})
        for path in paths:
            connection.send(
                {
                    "method": "textDocument/didOpen",
                    "params": {
                        "textDocument": {
                            "uri": path.resolve().as_uri(),
                            "languageId": "python",
                            "version": 1,
                            "text": path.read_text(),
                        },
                    },
                }
            )
        settling = False
        while (message := _message(connection, deadline, python)) is not None:
            if message.get("method") != "textDocument/publishDiagnostics":
                continue
            params = message["params"]
            if params.get("version") == 1 and params["uri"] in uris:
                received[params["uri"]] = params.get("diagnostics", [])
            if uris <= received.keys() and not settling:
                deadline = min(deadline, time.monotonic() + settle_seconds)
                settling = True
        report = {
            "opened_files": len(uris),
            "reported_files": len(received),
            "missing_files": sorted(uris - received.keys()),
            "diagnostics": {uri: rows for uri, rows in received.items() if rows},
        }
        connection.send({"id": 2, "method": "shutdown", "params": None})
        shutdown = time.monotonic() + 10
        while (message := _message(connection, shutdown, python)) is not None:
            if message.get("id") == 2:
                break
        connection.send({"method": "exit", "params": None})
        process.wait(timeout=10)
        return report
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        connection.close()


def main() -> int:
    """Check changed Python files or an explicit development selection."""
    cli = argparse.ArgumentParser()
    cli.add_argument("--root", type=Path, required=True)
    cli.add_argument("--python", required=True)
    cli.add_argument("--base")
    cli.add_argument("--candidate")
    cli.add_argument("files", nargs="*")
    args = cli.parse_args()
    root = args.root.resolve()
    names = args.files
    if not names:
        if not args.base or not args.candidate:
            cli.error("files or exact --base/--candidate are required")
        names = subprocess.check_output(
            [
                "git",
                "-C",
                str(root),
                "diff",
                "--name-only",
                "--diff-filter=ACMR",
                args.base,
                args.candidate,
            ],
            text=True,
            timeout=30,
        ).splitlines()
    paths = [root / name for name in names if name.endswith(".py")]
    try:
        report = diagnose(root, args.python, paths)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return int(bool(report["missing_files"] or report["diagnostics"]))


if __name__ == "__main__":
    raise SystemExit(main())

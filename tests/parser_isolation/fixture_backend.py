"""Synthetic trusted parser used only by parser-isolation tests."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

from msgloom.preparation import (
    BlockRole,
    DocumentLocation,
    ParserOutput,
    ParserProvenance,
    ParserRequest,
    TextBlock,
)

PARSER_NAME = "msgloom.synthetic-fixture"
PARSER_VERSION = "1"
BACKEND = "synthetic-safe-fixture-1"


def _setting(request: ParserRequest, key: str, default: str = "") -> str:
    config = request.config
    return dict(config.settings).get(key, default)


def parse(request: ParserRequest, content: bytes) -> ParserOutput:
    """Exercise process lifecycle and sandbox policy without external data."""
    mode = _setting(request, "mode", "ok")
    if mode == "sleep":
        time.sleep(float(_setting(request, "seconds", "0.25")))
    elif mode == "probe":
        text = _probe()
        return _output(request, text)
    elif mode == "spawn":
        token = _setting(request, "token", "msgloom-synthetic-descendant")
        for suffix in ("one", "two"):
            subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    "import time; time.sleep(30)",
                    f"{token}-{suffix}",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        time.sleep(30)
    elif mode == "fanout":
        created = 0
        for index in range(64):
            try:
                Path(f"/output/fanout-{index}").write_bytes(b"x" * 1024)
            except OSError:
                break
            created += 1
        return _output(request, f"fanout-created={created}")
    elif mode == "large":
        return _output(request, "x" * int(_setting(request, "size", "100000")))
    elif mode == "raise":
        raise ValueError(content.decode("utf-8", errors="replace"))
    elif mode == "bad_provenance":
        output = _output(request, "bad provenance")
        wrong_source = replace(request.source, reference="blob:wrong")
        return replace(
            output,
            provenance=replace(output.provenance, source=wrong_source),
        )
    return _output(request, content.decode("utf-8", errors="strict"))


def _probe() -> str:
    forbidden_path = Path("/home/grammy-jiang/Projects").exists()
    secret = "MSGLOOM_SYNTHETIC_SECRET" in os.environ
    routes = Path("/proc/net/route").read_text(encoding="utf-8").splitlines()
    external_route = len(routes) > 1
    home = os.environ.get("HOME")
    keys = ",".join(sorted(os.environ))
    return (
        f"forbidden_path={int(forbidden_path)};"
        f"secret={int(secret)};"
        f"external_route={int(external_route)};"
        f"home={home};keys={keys}"
    )


def _output(request: ParserRequest, text: str) -> ParserOutput:
    return ParserOutput(
        provenance=ParserProvenance.from_request(request),
        blocks=(
            TextBlock(
                order=0,
                role=BlockRole.TEXT,
                text=text,
                location=DocumentLocation(part="synthetic"),
            ),
        ),
    )

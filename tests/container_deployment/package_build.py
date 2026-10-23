"""Build the qualification fixture offline with an explicit local backend."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import pytest


def build_wheel(source: Path, directory: Path) -> Path:
    """Build an sdist, then its wheel, using isolated PEP 517 environments.

    The locked development toolchain includes virtualenv's seed wheels. Copy
    its exact setuptools artifact to a private wheelhouse instead of relying
    on a warm user cache. An empty uv cache and no index keep this fixture
    reproducible under the formal runner's offline XDG isolation.
    """
    uv = shutil.which("uv")
    if uv is None:
        pytest.fail("uv is required for package qualification tests")
    name = "setuptools-84.2.1-py3-none-any.whl"
    backend = files("virtualenv.seed.wheels.embed").joinpath(name).read_bytes()
    digest = "ca140b45d5325a9478f880e351484f62fef15f336462e449ca0c03c873d589c2"
    if hashlib.sha256(backend).hexdigest() != digest:
        pytest.fail("bundled setuptools wheel differs from the pinned artifact")
    wheelhouse = directory / "build-dependencies"
    wheelhouse.mkdir()
    (wheelhouse / name).write_bytes(backend)
    env = {**os.environ, "UV_CACHE_DIR": str(directory / "uv-cache")}
    for kind in ("sdist", "wheel"):
        output = directory / kind
        run_command(
            [
                uv,
                "build",
                "--offline",
                "--no-progress",
                "--no-config",
                "--no-index",
                "--find-links",
                str(wheelhouse),
                "--python",
                sys.executable,
                f"--{kind}",
                "--out-dir",
                str(output),
                str(source),
            ],
            env=env,
        )
        source = next(output.glob("*.tar.gz" if kind == "sdist" else "*.whl"))
    return source


def run_command(
    command: list[str], *, timeout: int = 30, **kwargs
) -> subprocess.CompletedProcess[str]:
    """Run a finite package command and retain its output on failure."""
    try:
        return subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            **kwargs,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        pytest.fail(f"package command failed: {exc}\n{exc.stdout}")

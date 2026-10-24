"""Build an isolated scratch Kedro interpreter and run the F0 controls in it.

Usage::

    python scripts/research/a2_f0_scratch_kedro_env.py build VENV
    python scripts/research/a2_f0_scratch_kedro_env.py run VENV

``VENV`` is required. The recipe refuses a path inside this repository,
inside the main checkout of the same repository, equal to or inside any
``.venv`` of those trees, inside the running interpreter prefix, or a
non-empty directory that this recipe did not create.

``build`` creates the venv with ``uv venv`` and installs the hash-pinned
file ``a2_f0_scratch_kedro_requirements.txt`` with ``--require-hashes``,
``--only-binary :all:`` and ``--no-deps``. Secure defaults:

* ``--no-config`` ignores user and project uv configuration;
* ``--default-index`` names PyPI only, with no extra index;
* the child environment is an allowlist, so tokens and credentials in the
  caller environment never reach uv;
* the recipe never reads or writes the project environment.

Network use is limited to PyPI by these options. ``--no-python-downloads``
stops uv from fetching an interpreter, so the build fails if no local
Python 3.13 exists. The recipe cannot enforce the limit at the packet
level.

``run`` starts two pytest processes with the current interpreter. The first
runs the pure-Python controls. The second runs the Kedro-dependent controls
with ``A2_F0_KEDRO_OPT_IN=1`` and ``A2_F0_KEDRO_PYTHON`` set to the scratch
interpreter. Both use the gate plugin ``a2_f0_pytest_gate``. ``run`` exits
non-zero for any failure, any skip, or an unexpected test count.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REQUIREMENTS = HERE / "a2_f0_scratch_kedro_requirements.txt"
STATIC_TESTS = ROOT / "tests" / "research" / "a2_f0_static_controls.py"
KEDRO_TESTS = ROOT / "tests" / "research" / "a2_f0_kedro_integration.py"
MARKER_FILE = "a2-f0-scratch-kedro.json"
PYPI_INDEX = "https://pypi.org/simple"
KEDRO_VERSION = "1.7.0"
EXPECTED_STATIC = 69
EXPECTED_KEDRO = 9
ENV_ALLOWLIST = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "UV_CACHE_DIR",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
)


class ScratchEnvError(RuntimeError):
    """Raised when the recipe refuses a path or a precondition fails."""


def scrubbed_environment(
    source: dict[str, str], extra: dict[str, str] | None = None
) -> dict[str, str]:
    """Return an allowlisted copy of ``source`` plus ``extra``."""
    env = {key: source[key] for key in ENV_ALLOWLIST if key in source}
    env.update(extra or {})
    return env


def _main_checkout(repo_root: Path) -> Path | None:
    """Return the main checkout of ``repo_root``, or ``None`` if unknown."""
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except OSError:
        return None
    if done.returncode != 0 or not done.stdout.strip():
        return None
    return Path(done.stdout.strip()).resolve().parent


def _is_inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def check_venv_path(
    venv: str | Path,
    repo_roots: tuple[Path, ...],
    prefixes: tuple[Path, ...] = (),
) -> Path:
    """Return the resolved scratch path or raise :exc:`ScratchEnvError`.

    ``repo_roots`` lists every tree that must not hold the venv. Each tree
    also protects its ``.venv`` directory. ``prefixes`` lists interpreter
    prefixes that must not be reused.
    """
    if not str(venv):
        raise ScratchEnvError("venv path is required")
    path = Path(venv).expanduser().resolve()
    for root in repo_roots:
        if _is_inside(path, root.resolve()):
            raise ScratchEnvError(f"venv path is inside a repository: {path}")
    for prefix in prefixes:
        if _is_inside(path, prefix.resolve()):
            raise ScratchEnvError(f"venv path reuses an interpreter: {path}")
    if ".venv" in path.parts:
        raise ScratchEnvError(f"venv path uses a .venv directory: {path}")
    if not path.exists() or (path / MARKER_FILE).is_file():
        return path
    if not path.is_dir() or any(path.iterdir()):
        raise ScratchEnvError(f"venv path exists and is not ours: {path}")
    return path


def guarded_path(venv: str | Path) -> Path:
    """Apply :func:`check_venv_path` with the real repository roots."""
    roots = [ROOT]
    if (main := _main_checkout(ROOT)) is not None:
        roots.append(main)
    prefixes = (Path(sys.prefix), Path(sys.base_prefix))
    return check_venv_path(venv, tuple(roots), prefixes)


def venv_python(venv: Path) -> Path:
    """Return the interpreter path inside ``venv``."""
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def requirements_sha256() -> str:
    """Return the SHA-256 of the pinned requirements file."""
    return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()


def build_commands(venv: Path, uv: str = "uv") -> list[list[str]]:
    """Return the command lines that create and fill the venv."""
    return [
        [
            uv,
            "venv",
            "--no-config",
            "--no-python-downloads",
            "--python",
            "3.13",
            str(venv),
        ],
        [
            uv,
            "pip",
            "install",
            "--no-config",
            "--python",
            str(venv_python(venv)),
            "--default-index",
            PYPI_INDEX,
            "--require-hashes",
            "--only-binary",
            ":all:",
            "--no-deps",
            "--requirement",
            str(REQUIREMENTS),
        ],
    ]


def build(venv: Path) -> None:
    """Create the scratch venv and verify the Kedro version."""
    env = scrubbed_environment(dict(os.environ))
    venv.parent.mkdir(parents=True, exist_ok=True)
    for command in build_commands(venv):
        done = subprocess.run(command, env=env, check=False, timeout=900)
        if done.returncode != 0:
            raise ScratchEnvError(f"command failed ({done.returncode}): {command[:3]}")
    probe = subprocess.run(
        [str(venv_python(venv)), "-I", "-c", "import kedro; print(kedro.__version__)"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if probe.returncode != 0 or probe.stdout.strip() != KEDRO_VERSION:
        raise ScratchEnvError(f"scratch Kedro version is not {KEDRO_VERSION}")
    marker = {"kedro": KEDRO_VERSION, "requirements_sha256": requirements_sha256()}
    (venv / MARKER_FILE).write_text(json.dumps(marker, indent=1) + "\n")


def _count(junit: Path) -> dict[str, int]:
    suite = ET.parse(junit).getroot()
    if suite.tag == "testsuites":
        suite = suite[0]
    return {
        key: int(suite.get(key, "0"))
        for key in ("tests", "failures", "errors", "skipped")
    }


def _pytest(target: Path, env: dict[str, str], junit: Path) -> int:
    command = [
        sys.executable,
        "-B",
        "-m",
        "pytest",
        "-p",
        "a2_f0_pytest_gate",
        "-p",
        "no:cacheprovider",
        "-q",
        f"--junitxml={junit}",
        str(target),
    ]
    return subprocess.run(command, env=env, cwd=ROOT, check=False).returncode


def run(venv: Path) -> int:
    """Run both control sets and return a process exit code."""
    marker = venv / MARKER_FILE
    if not marker.is_file():
        raise ScratchEnvError(f"not a scratch venv built by this recipe: {venv}")
    recorded = json.loads(marker.read_text()).get("requirements_sha256")
    if recorded != requirements_sha256():
        raise ScratchEnvError("venv was built from different requirements; rebuild")
    python = venv_python(venv)
    if not python.is_file():
        raise ScratchEnvError(f"scratch interpreter is missing: {python}")
    base = scrubbed_environment(
        dict(os.environ), {"PYTHONPATH": f"{HERE}{os.pathsep}{ROOT}"}
    )
    plans = (
        ("static", STATIC_TESTS, EXPECTED_STATIC, {}),
        (
            "kedro",
            KEDRO_TESTS,
            EXPECTED_KEDRO,
            {"A2_F0_KEDRO_OPT_IN": "1", "A2_F0_KEDRO_PYTHON": str(python)},
        ),
    )
    status = 0
    with tempfile.TemporaryDirectory(prefix="a2-f0-junit-") as tmp:
        for label, target, expected, extra in plans:
            junit = Path(tmp) / f"{label}.xml"
            code = _pytest(target, {**base, **extra}, junit)
            counts = _count(junit) if junit.is_file() else {"tests": -1}
            ok = (
                code == 0
                and counts.get("tests") == expected
                and not counts.get("skipped")
                and not counts.get("failures")
                and not counts.get("errors")
            )
            print(f"{label}: exit={code} expected={expected} counts={counts}")
            status = status or (0 if ok else 1)
    return status


def main(argv: list[str]) -> int:
    """Parse arguments and run ``build`` or ``run``."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("action", choices=("build", "run"))
    parser.add_argument("venv", help="scratch venv path outside every repository")
    args = parser.parse_args(argv)
    try:
        venv = guarded_path(args.venv)
        if args.action == "build":
            build(venv)
            print(f"built {venv}")
            return 0
        return run(venv)
    except ScratchEnvError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

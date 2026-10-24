"""Kedro-dependent integration tests for the A2 F0 denial controls.

LABEL: these tests need a scratch interpreter that has Kedro installed. They
are not part of the pure-Python control set in ``a2_f0_static_controls.py``.

Set ``A2_F0_KEDRO_PYTHON`` to the scratch interpreter path. Never point it
at the project ``.venv``. When the variable is missing, every test FAILS with
a clear message. A missing interpreter must not look like a pass.

Each test starts ``a2_f0_kedro_probe.py`` in a fresh ``python -I`` process
with an empty environment, a temporary ``HOME`` and a Python socket event hook that
denies every socket connect, lookup and send. The tests with a default
consent setting are positive controls: they prove the recorder sees an
attempt.

Gate: every test carries the ``kedro_scratch`` marker. The plugin
``scripts/research/a2_f0_pytest_gate.py`` deselects marked tests unless
``A2_F0_KEDRO_OPT_IN=1``. The default test run never collects this file.

Run: ``python scripts/research/a2_f0_scratch_kedro_env.py run VENV``. It
sets the plugin and both variables.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scripts" / "research" / "a2_f0_kedro_probe.py"
CONTROLS = ROOT / "scripts" / "research" / "a2_f0_denial_controls.py"
ENV_NAME = "A2_F0_KEDRO_PYTHON"
EXPECTED_KEDRO = "1.7.0"

pytestmark = pytest.mark.kedro_scratch


def _controls() -> Any:
    spec = importlib.util.spec_from_file_location(CONTROLS.stem, CONTROLS)
    if spec is None or spec.loader is None:
        pytest.fail("denial controls module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ctl = _controls()


@pytest.fixture(scope="module")
def kedro_python() -> str:
    """Return the scratch interpreter path or fail loudly."""
    value = os.environ.get(ENV_NAME)
    if not value:
        pytest.fail(f"{ENV_NAME} is not set; Kedro controls NOT VERIFIED")
    path = Path(value)
    if not path.is_file():
        pytest.fail(f"{ENV_NAME} does not name a file: {value}")
    if ".venv" in path.parts or (ROOT / ".venv") in path.parents:
        pytest.fail(f"{ENV_NAME} must not point at a project .venv: {value}")
    probe = subprocess.run(
        [value, "-I", "-c", "import kedro; print(kedro.__version__)"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if probe.returncode != 0 or probe.stdout.strip() != EXPECTED_KEDRO:
        pytest.fail(f"scratch interpreter lacks Kedro {EXPECTED_KEDRO}: {probe}")
    return value


def _run(
    python: str, mode: str, tmp_path: Path, extra: dict[str, str] | None = None
) -> dict[str, Any]:
    home, work = tmp_path / "home", tmp_path / "work"
    home.mkdir()
    work.mkdir()
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home), **(extra or {})}
    done = subprocess.run(
        [python, "-I", str(PROBE), mode, str(work)],
        env=env,
        cwd=work,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if done.returncode != 0:
        pytest.fail(f"probe {mode} exited {done.returncode}: {done.stderr[-400:]}")
    return json.loads(done.stdout)


def _attempts(result: dict[str, Any]) -> list[dict[str, str]]:
    return result["socket_attempts"]


def test_plain_run_makes_no_network_attempt(kedro_python: str, tmp_path: Path) -> None:
    result = _run(kedro_python, "plain_run", tmp_path, ctl.TELEMETRY_OFF_ENVIRONMENT)
    if result["data"]["result"] != 2:
        pytest.fail("pipeline did not run")
    if _attempts(result) or result["telemetry_module_loaded"]:
        pytest.fail(f"unexpected network or telemetry use: {result}")


def test_default_entry_points_register_the_telemetry_plugin(
    kedro_python: str, tmp_path: Path
) -> None:
    """Positive control: without the disable list the plugin is present."""
    result = _run(kedro_python, "hooks_default", tmp_path)
    if result["data"]["plugins"] != ["kedro-telemetry"]:
        pytest.fail(f"plugin not registered: {result['data']}")


def test_disabled_entry_points_register_no_plugin_and_no_network(
    kedro_python: str, tmp_path: Path
) -> None:
    result = _run(kedro_python, "hooks_disabled", tmp_path)
    if result["data"]["plugins"] or _attempts(result):
        pytest.fail(f"plugin or network use: {result}")


def test_default_consent_telemetry_hook_attempts_a_lookup(
    kedro_python: str, tmp_path: Path
) -> None:
    """Positive control: the recorder sees the plugin's DNS lookup."""
    result = _run(kedro_python, "telemetry_hook", tmp_path)
    events = {item["event"] for item in _attempts(result)}
    if "socket.getaddrinfo" not in events:
        pytest.fail(f"recorder saw no lookup: {result}")


@pytest.mark.parametrize(
    "extra",
    [
        {"DO_NOT_TRACK": "1"},
        {"KEDRO_DISABLE_TELEMETRY": "1"},
        ctl.TELEMETRY_OFF_ENVIRONMENT,
    ],
)
def test_opt_out_environment_stops_the_telemetry_hook(
    kedro_python: str, tmp_path: Path, extra: dict[str, str]
) -> None:
    result = _run(kedro_python, "telemetry_hook", tmp_path, extra)
    if result["data"]["consent_check"] != "False" or _attempts(result):
        pytest.fail(f"opt-out failed: {result}")


def test_dataset_gate_rejects_unsafe_catalogs_with_real_kedro_objects(
    kedro_python: str, tmp_path: Path
) -> None:
    data = _run(kedro_python, "gate_cases", tmp_path)["data"]
    expected = {
        "unknown_name": "rejected",
        "subclass": "rejected",
        "versioned": "rejected",
        "versioned_even_if_type_listed": "rejected: versioned",
        "pipeline_unlisted_output": "rejected",
        "load_version_arg": "rejected",
        "allowed_catalog": "accepted",
        "pipeline_allowed": "accepted",
        "load_without_version": "accepted",
    }
    for key, prefix in expected.items():
        if not str(data[key]).startswith(prefix):
            pytest.fail(f"{key}: expected {prefix!r}, got {data[key]!r}")
    if not data["kedro_runs_unlisted_output_without_gate"]:
        pytest.fail("control failed: Kedro should accept the unlisted output")
    if data["forbidden_modules_loaded"]:
        pytest.fail(f"forbidden modules loaded: {data['forbidden_modules_loaded']}")


def test_logs_contain_no_message_content_after_sanitizing(
    kedro_python: str, tmp_path: Path
) -> None:
    data = _run(kedro_python, "pii_logs", tmp_path, ctl.TELEMETRY_OFF_ENVIRONMENT)[
        "data"
    ]
    raw = data["raw"]
    if not raw["canary_in_text"] or not {"email", "phone"} <= set(raw["pii_hits"]):
        pytest.fail(f"positive control failed: scanner cannot see leaks: {raw}")
    for label in ("sanitized", "success"):
        if data[label]["canary_in_text"] or data[label]["pii_hits"]:
            pytest.fail(f"{label} run leaked message content: {data[label]}")
        if data[label]["log_chars"] == 0:
            pytest.fail(f"{label} run captured no log text; scan is blind")

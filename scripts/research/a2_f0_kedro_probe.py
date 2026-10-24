"""Kedro-dependent probe for the A2 F0 denial controls (research).

Usage: ``python -I a2_f0_kedro_probe.py MODE WORKDIR``

Run it with a scratch interpreter that has Kedro installed. Never run it with
the project ``.venv``. The probe prints one JSON object on stdout. Kedro log
output is captured, so it does not reach the real stdout.

Network denial uses a Python socket event hook. The hook sees the
``socket.connect``, ``socket.getaddrinfo``, ``socket.gethostbyname`` and
``socket.sendto`` events of every socket path, including ``_socket``. It
records the event and raises :exc:`OSError`, so no packet leaves the process.
A mode that must attempt a connection acts as a positive control. It proves
the recorder sees attempts.

Modes:

* ``plain_run``: in-memory pipeline, no session, no hook manager.
* ``hooks_default``: register ``kedro.hooks`` entry points, no disable list.
* ``hooks_disabled``: register entry points with the plugin disabled.
* ``telemetry_hook``: call the real telemetry hook (consent from the env).
* ``gate_cases``: dataset allowlist and path cases with real Kedro objects.
* ``pii_logs``: failing node, raw versus sanitized, captured log text.
"""

from __future__ import annotations

import importlib.util
import io
import json
import logging
import os
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self


def _load_controls() -> Any:
    path = Path(__file__).resolve().with_name("a2_f0_denial_controls.py")
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load a2_f0_denial_controls")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


controls = _load_controls()

CANARY = (
    "jane.doe@example.invalid wants 12 Main Street, call +1 555 010 0199, "
    "body: wire the funds"
)
ATTEMPTS: list[dict[str, str]] = []
SOCKET_EVENTS = {
    "socket.connect",
    "socket.getaddrinfo",
    "socket.gethostbyname",
    "socket.sendto",
}


def _deny_socket_event(event: str, args: tuple[Any, ...]) -> None:
    if event not in SOCKET_EVENTS:
        return
    ATTEMPTS.append({"event": event, "arg": repr(args[1:])[:80]})
    raise OSError(f"network denied by a2_f0 probe: {event}")


def _run_pipeline(hook_manager: Any | None = None) -> object:
    from kedro.io import DataCatalog, MemoryDataset
    from kedro.pipeline import Pipeline, node
    from kedro.runner import SequentialRunner

    catalog = DataCatalog({"a": MemoryDataset(1), "b": MemoryDataset()})
    pipeline = Pipeline([node(lambda x: x + 1, "a", "b", name="n1")])
    SequentialRunner().run(pipeline, catalog, hook_manager=hook_manager)
    return catalog.load("b")


def _reject(func: Any, *args: Any) -> str:
    try:
        func(*args)
    except controls.GateError as exc:
        return f"rejected: {exc}"
    return "accepted"


def _mode_hooks(disabled: bool) -> dict[str, Any]:
    from kedro.framework.hooks.manager import (
        _create_hook_manager,
        _register_hooks_entry_points,
    )

    manager = _create_hook_manager()
    disable = controls.DISABLE_HOOKS_FOR_PLUGINS if disabled else ()
    _register_hooks_entry_points(manager, disable)
    plugins = sorted(name for name, _ in manager.list_name_plugin())
    return {"plugins": plugins, "result": _run_pipeline(manager)}


def _mode_telemetry_hook(workdir: Path) -> dict[str, Any]:
    from kedro.io import DataCatalog, MemoryDataset
    from kedro_telemetry import plugin

    project = workdir / "proj"
    project.mkdir()
    hook = plugin.KedroTelemetryHook()
    consent = plugin._check_for_telemetry_consent(project)
    hook.after_context_created(SimpleNamespace(project_path=project))
    hook.after_catalog_created(DataCatalog({"a": MemoryDataset(1)}))
    return {"consent_check": repr(consent)}


def _mode_gate_cases(workdir: Path) -> dict[str, Any]:
    from pathlib import PurePosixPath

    from kedro.io import DataCatalog, MemoryDataset
    from kedro.io.core import AbstractVersionedDataset, Version
    from kedro.pipeline import Pipeline, node
    from kedro.runner import SequentialRunner

    names = frozenset({"a", "b"})

    class Sub(MemoryDataset):
        pass

    class Versioned(AbstractVersionedDataset):
        def __init__(self) -> None:
            super().__init__(PurePosixPath("/nonexistent/x"), Version(None, None))

        def load(self) -> int:
            return 1

        def save(self, data: Any) -> None:
            return None

        def _load(self) -> int:
            return 1

        def _save(self, data: Any) -> None:
            return None

        def _describe(self) -> dict[str, Any]:
            return {}

        def _exists(self) -> bool:
            return False

    res: dict[str, Any] = {}
    check = controls.check_catalog_datasets
    res["unknown_name"] = _reject(check, {"zzz": MemoryDataset()}, names)
    res["subclass"] = _reject(check, {"a": Sub()}, names)
    res["versioned"] = _reject(check, {"a": Versioned()}, names)
    res["versioned_even_if_type_listed"] = _reject(
        check,
        {"a": Versioned()},
        names,
        frozenset({controls.type_key(Versioned())}),
    )
    res["allowed_catalog"] = _reject(
        check, {"a": MemoryDataset(1), "b": MemoryDataset()}, names
    )
    bad = Pipeline([node(lambda x: x, "a", "zzz", name="bad")])
    good = Pipeline([node(lambda x: x, "a", "b", name="good")])
    res["pipeline_unlisted_output"] = _reject(
        controls.check_pipeline_names, bad.nodes, names
    )
    res["pipeline_allowed"] = _reject(controls.check_pipeline_names, good.nodes, names)
    res["load_version_arg"] = _reject(controls.check_load_version, "2026-01-01")
    res["load_without_version"] = _reject(controls.check_load_version, None)
    # Control: Kedro itself accepts the unlisted output without the gate.
    SequentialRunner().run(bad, DataCatalog({"a": MemoryDataset(1)}))
    res["kedro_runs_unlisted_output_without_gate"] = True
    res["forbidden_modules_loaded"] = sorted(
        m for m in sys.modules if m.startswith(controls.RUNTIME_FORBIDDEN_MODULES)
    )
    return res


class _Failure:
    """Context manager that records an exception and swallows it."""

    def __init__(self) -> None:
        self.text = ""
        self.trace = ""

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> bool:
        if exc is None or not isinstance(exc, Exception):
            return False
        self.text = str(exc)
        self.trace = "".join(traceback.format_exception(exc))
        return True


def _capture_run(func: Any) -> tuple[str, str, str]:
    """Run ``func`` and return log text, exception text and traceback text."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    out, err = io.StringIO(), io.StringIO()
    failure = _Failure()
    try:
        with redirect_stdout(out), redirect_stderr(err), failure:
            func()
    finally:
        root.removeHandler(handler)
    logs = stream.getvalue() + out.getvalue() + err.getvalue()
    return logs, failure.text, failure.trace


def _mode_pii_logs() -> dict[str, Any]:
    from kedro.io import DataCatalog, MemoryDataset
    from kedro.pipeline import Pipeline, node
    from kedro.runner import SequentialRunner

    def parse(value: str) -> str:
        raise ValueError(f"cannot parse {value}")

    def run(func: Any) -> None:
        catalog = DataCatalog({"a": MemoryDataset(CANARY), "b": MemoryDataset()})
        pipeline = Pipeline([node(func, "a", "b", name="parse_node")])
        SequentialRunner().run(pipeline, catalog)

    res: dict[str, Any] = {}
    for label, func in (
        ("raw", parse),
        ("sanitized", controls.sanitized_node("parse_node", parse)),
        ("success", lambda value: value),
    ):
        logs, exc_text, trace_text = _capture_run(lambda f=func: run(f))
        joined = f"{logs}\n{exc_text}\n{trace_text}"
        res[label] = {
            "canary_in_text": CANARY in joined or "jane.doe" in joined,
            "pii_hits": controls.scan_pii(joined),
            "log_chars": len(logs),
            "exception_text": exc_text if label != "raw" else "<raw omitted>",
        }
    return res


def main(argv: list[str]) -> int:
    """Run one mode and print its JSON result."""
    mode, workdir = argv[0], Path(argv[1])
    sys.addaudithook(_deny_socket_event)
    real_stdout = sys.stdout
    out, err = io.StringIO(), io.StringIO()
    result: dict[str, Any] = {"mode": mode}
    handlers = {
        "plain_run": lambda: {"result": _run_pipeline()},
        "hooks_default": lambda: _mode_hooks(disabled=False),
        "hooks_disabled": lambda: _mode_hooks(disabled=True),
        "telemetry_hook": lambda: _mode_telemetry_hook(workdir),
        "gate_cases": lambda: _mode_gate_cases(workdir),
        "pii_logs": _mode_pii_logs,
    }
    if mode not in handlers:
        raise SystemExit(f"unknown mode: {mode}")
    with redirect_stdout(out), redirect_stderr(err):
        result["data"] = handlers[mode]()
    result["env"] = {
        key: os.environ.get(key) for key in controls.TELEMETRY_OFF_ENVIRONMENT
    }
    result["socket_attempts"] = ATTEMPTS
    result["telemetry_module_loaded"] = "kedro_telemetry" in sys.modules
    json.dump(result, real_stdout, indent=1, default=str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

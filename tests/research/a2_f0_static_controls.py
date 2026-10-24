"""Pure-Python tests for the A2 F0 denial controls.

These tests import no Kedro module and need no network. They run in the
project interpreter. Run them by path, because the file name does not match
the default ``test_*.py`` collection pattern:

``python -m pytest tests/research/a2_f0_static_controls.py``
"""

from __future__ import annotations

import ast
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts" / "research" / "a2_f0_denial_controls.py"
PACKAGES = ("message_ingest", "microsoft_graph", "msgloom")
NAMES = frozenset({"a", "b"})


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(MODULE.stem, MODULE)
    if spec is None or spec.loader is None:
        pytest.fail("denial controls module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ctl = _load()


def _fake(name: str, module: str, *bases: type) -> type:
    return type(name, bases or (object,), {"__module__": module})


MemoryDataset = _fake("MemoryDataset", "kedro.io.memory_dataset")
Versioned = _fake("AbstractVersionedDataset", "kedro.io.core")


def _names(source: str) -> list[str]:
    return [finding.name for finding in ctl.scan_source(source)]


# (a) no Kedro CLI entry, no load_versions -----------------------------------


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("from kedro.framework.cli import main\n", "kedro.framework.cli"),
        ("import kedro.framework.cli.utils\n", "kedro.framework.cli.utils"),
        ("from kedro.framework.session import KedroSession\n", "KedroSession"),
        (
            "from kedro.framework.startup import bootstrap_project\n",
            "bootstrap_project",
        ),
        (
            "from kedro.io import DataCatalog\nDataCatalog.from_config({})\n",
            "from_config",
        ),
        ("run(load_versions={'a': '../x'})\n", "load_versions"),
        ("run(save_version='x')\n", "save_version"),
        ("import kedro_datasets.pandas\n", "kedro_datasets.pandas"),
        ("import kedro_telemetry.plugin\n", "kedro_telemetry.plugin"),
        ("from kedro.io import Version\n", "Version"),
        ("from kedro.utils import load_obj\n", "load_obj"),
        ("from kedro.server import http_server\n", "kedro.server"),
        (
            "import importlib\nimportlib.import_module('kedro.framework.cli')\n",
            "kedro.framework.cli",
        ),
        ("import kedro\ncatalog.load('a', version='v1')\n", "load(version=)"),
    ],
)
def test_forbidden_kedro_surface_is_flagged(source: str, expected: str) -> None:
    if expected not in _names(source):
        pytest.fail(f"{expected!r} not flagged in {source!r}")


@pytest.mark.parametrize(
    "source",
    [
        (
            "from kedro.io import DataCatalog, MemoryDataset\n"
            "catalog = DataCatalog({'a': MemoryDataset()})\n"
            "catalog.load('a')\n"
        ),
        "from packaging.version import Version\nVersion('1')\n",
        "loader.load('x', version='1')\n",
    ],
)
def test_allowed_source_is_not_flagged(source: str) -> None:
    if names := _names(source):
        pytest.fail(f"false positive: {names}")


def test_repository_source_uses_no_forbidden_kedro_surface() -> None:
    if findings := ctl.scan_tree(ROOT, PACKAGES):
        pytest.fail(f"forbidden Kedro surface in repository: {findings}")


def test_repository_scan_sees_real_files() -> None:
    count = sum(len(list((ROOT / p).rglob("*.py"))) for p in PACKAGES)
    if count < 100:
        pytest.fail(f"scan covers only {count} files; control is blind")


def test_repository_metadata_has_no_kedro_entry() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if findings := ctl.scan_project_metadata(text):
        pytest.fail(f"Kedro entry in pyproject.toml: {findings}")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('[project.scripts]\nkedro = "kedro.__main__:main"\n', "scripts"),
        ('[project.scripts]\nrun = "kedro.framework.cli:main"\n', "scripts"),
        (
            '[project.entry-points."kedro.hooks"]\nx = "pkg:hook"\n',
            "entry-points group",
        ),
        (
            '[project.entry-points."kedro.project_commands"]\nx = "pkg:c"\n',
            "entry-points group",
        ),
        ('[tool.kedro]\npackage_name = "x"\n', "tool.kedro"),
    ],
)
def test_kedro_metadata_is_flagged(text: str, expected: str) -> None:
    if not any(expected in item for item in ctl.scan_project_metadata(text)):
        pytest.fail(f"{expected!r} not flagged")


def test_unrelated_metadata_is_not_flagged() -> None:
    text = '[project.scripts]\nmsgloom = "msgloom.cli:main"\n'
    if findings := ctl.scan_project_metadata(text):
        pytest.fail(f"false positive: {findings}")


# (b) static dataset allowlist ----------------------------------------------


def _check(datasets: dict[str, object], **kwargs: object) -> None:
    ctl.check_catalog_datasets(datasets, NAMES, **kwargs)


def test_allowed_catalog_is_accepted() -> None:
    _check({"a": MemoryDataset(), "b": MemoryDataset()})


@pytest.mark.parametrize(
    "datasets",
    [
        {"zzz": MemoryDataset()},
        {"a": _fake("Sub", "pkg", MemoryDataset)()},
        {"a": _fake("OtherDataset", "pkg")()},
        {"a": _fake("MemoryDataset", "other.module")()},
        {"a": _fake("Versioned", "pkg", Versioned)()},
    ],
)
def test_unknown_dataset_is_rejected(datasets: dict[str, object]) -> None:
    with pytest.raises(ctl.GateError):
        _check(datasets)


def test_versioned_dataset_is_rejected_even_if_type_is_listed() -> None:
    versioned = _fake("Versioned", "pkg", Versioned)()
    allowed = frozenset({ctl.type_key(versioned)})
    with pytest.raises(ctl.GateError, match="versioned"):
        _check({"a": versioned}, allowed_types=allowed)


def test_dataset_with_version_state_is_rejected() -> None:
    dataset = MemoryDataset()
    dataset._version = "2026-01-01"
    with pytest.raises(ctl.GateError, match="version"):
        _check({"a": dataset})


def _pipeline(*edges: tuple[str, str]) -> list[SimpleNamespace]:
    return [SimpleNamespace(inputs=[i], outputs=[o]) for i, o in edges]


def test_pipeline_with_listed_names_is_accepted() -> None:
    ctl.check_pipeline_names(_pipeline(("a", "b")), NAMES)


def test_pipeline_with_unlisted_output_is_rejected() -> None:
    with pytest.raises(ctl.GateError, match="zzz"):
        ctl.check_pipeline_names(_pipeline(("a", "zzz")), NAMES)


@pytest.mark.parametrize("version", ["2026-01-01", "", "..", 0])
def test_version_argument_is_rejected(version: object) -> None:
    with pytest.raises(ctl.GateError):
        ctl.check_load_version(version)


def test_missing_version_argument_is_accepted() -> None:
    ctl.check_load_version(None)


# (c) path traversal and unsafe paths ---------------------------------------


@pytest.mark.parametrize(
    "relative",
    [
        "../../etc/passwd",
        "sub/../../x",
        "sub/../ok.json",
        "..",
        "/etc/passwd",
        "\\windows\\x",
        "..\\x",
        "C:\\x",
        "C:x",
        "a\x00b",
        "",
        "*",
        "a?b",
        "sub/[x]",
    ],
)
def test_unsafe_relative_path_is_rejected(tmp_path: Path, relative: str) -> None:
    with pytest.raises(ctl.GateError):
        ctl.safe_join(tmp_path, relative)


def test_safe_relative_path_is_accepted(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    result = ctl.safe_join(tmp_path, "sub/ok.json")
    if result != Path(os.path.realpath(tmp_path)) / "sub" / "ok.json":
        pytest.fail(f"unexpected path: {result}")


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    base, outside = tmp_path / "base", tmp_path / "outside"
    base.mkdir()
    outside.mkdir()
    try:
        (base / "link").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.fail(f"symlink creation is not available here: {exc}")
    with pytest.raises(ctl.GateError, match="escapes"):
        ctl.safe_join(base, "link/secret")


# (d) telemetry opt-out environment -----------------------------------------


def test_controlled_environment_sets_both_opt_out_variables() -> None:
    env = ctl.controlled_environment({"HOME": "/h", "DO_NOT_TRACK": "0"})
    expected = {"HOME": "/h", "DO_NOT_TRACK": "1", "KEDRO_DISABLE_TELEMETRY": "1"}
    if env != expected:
        pytest.fail(f"unexpected environment: {env}")


def test_telemetry_plugin_is_in_the_disable_list() -> None:
    if ctl.DISABLE_HOOKS_FOR_PLUGINS != ("kedro-telemetry",):
        pytest.fail(f"unexpected disable list: {ctl.DISABLE_HOOKS_FOR_PLUGINS}")


# (e) no PII in logs ---------------------------------------------------------

CANARY = "jane.doe@example.invalid at 12 Main Street, call +1 555 010 0199"


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("failed for jane.doe@example.invalid", "email"),
        ("call +1 555 010 0199 now", "phone"),
        ("ship to 12 Main Street today", "street_address"),
        ("payload {'body': 'hello'}", "message_body_key"),
        ("Authorization: Bearer abcdefghijklmnop123", "bearer_token"),
    ],
)
def test_pii_scan_detects_patterns(text: str, label: str) -> None:
    if label not in ctl.scan_pii(text):
        pytest.fail(f"{label} not detected in {text!r}")


def test_pii_scan_accepts_ordinary_kedro_log_lines() -> None:
    text = (
        "[10/24/26 13:03:39] INFO Running node: parse_node: "
        "parse([a]) -> [b]\n"
        "INFO Loading data from a (MemoryDataset)...\n"
        "path /tmp/f0-scratch-20261024/venv/lib/python3.13/site-packages/x.py\n"
    )
    if hits := ctl.scan_pii(text):
        pytest.fail(f"false positive: {hits}")


def test_sanitized_node_hides_input_text() -> None:
    def parse(value: str) -> str:
        raise ValueError(f"cannot parse {value}")

    wrapped = ctl.sanitized_node("parse_node", parse)
    with pytest.raises(ctl.NodeFailure) as info:
        wrapped(CANARY)
    error = info.value
    if "jane.doe" in str(error) or ctl.scan_pii(str(error)):
        pytest.fail(f"sanitized text leaks input: {error}")
    if error.__cause__ is not None or not error.__suppress_context__:
        pytest.fail("original exception is still linked")


def test_sanitized_node_returns_the_value_on_success() -> None:
    if ctl.sanitized_node("n", lambda x: x + 1)(1) != 2:
        pytest.fail("success path changed the result")


# Twisted exposure pins (see docs/notes/a2-f0-controls-20261024.md) ---------


def _setting(name: str) -> object:
    tree = ast.parse((ROOT / "message_ingest" / "settings.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return ast.literal_eval(node.value)
    pytest.fail(f"{name} is not set in message_ingest/settings.py")


def test_telnet_console_is_disabled_in_project_settings() -> None:
    if _setting("TELNETCONSOLE_ENABLED") is not False:
        pytest.fail("TELNETCONSOLE_ENABLED must stay False")


def test_project_imports_no_twisted_server_or_protocol_modules() -> None:
    allowed = {"twisted.python.failure"}
    found: set[str] = set()
    for package in PACKAGES:
        for path in (ROOT / package).rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.split(".")[0] == "twisted":
                        found.add(node.module)
                elif isinstance(node, ast.Import):
                    found.update(
                        a.name for a in node.names if a.name.startswith("twisted")
                    )
    if unexpected := found - allowed:
        pytest.fail(f"new Twisted imports need a reachability review: {unexpected}")

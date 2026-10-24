"""V0-02: read-only A1 compatibility check for the A2 Kedro package.

The A1 source (20 Spiders, 13 Task15 scenarios, 28 gates) must stay
untouched. This module opens no database and no provider data. It checks:

* Static discovery of the A1 Spider, scenario and gate sets equals
  hand-written lists that were read from the source, not computed.
* Importing ``msgloom.a2_kedro`` imports no A1 module and changes no
  pinned A1 file.
* A mutated, removed or added A1 file in a ``tmp_path`` copy fails with a
  specific :class:`A1CompatibilityError`.

Measured at base 95a9eeb: 20 / 13 / 28, as the manifest states. Update
``SPIDER_FILES`` and ``PINNED_DIGEST`` only with a deliberate A1 change.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
import pkgutil
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SPIDER_ROOT = "message_ingest/spiders"
PLAN = "scripts/handoff_qualification/plan.py"
AUDIT = "scripts/handoff_qualification/audit.py"
INVENTORY = "tests/handoff_qualification/inventory.py"


def words(text: str) -> tuple[str, ...]:
    """Split a hand-written, space-separated name list."""
    return tuple(text.split())


# Hand-written from ``find message_ingest/spiders -name '*.py'`` plus the
# three files that define the scenario and gate sets.
SPIDER_FILES = words(
    "__init__.py microsoft/__init__.py microsoft/_graph.py "
    "microsoft/contacts/__init__.py microsoft/contacts/delta.py "
    "microsoft/contacts/profile.py microsoft/contacts/snapshot.py "
    "microsoft/onedrive/__init__.py microsoft/onedrive/_base.py "
    "microsoft/onedrive/_handoff.py microsoft/onedrive/content.py "
    "microsoft/onedrive/delta.py microsoft/onedrive/discover.py "
    "microsoft/outlook/__init__.py microsoft/outlook/_mailbox.py "
    "microsoft/outlook/calendar/__init__.py "
    "microsoft/outlook/calendar/_attachments.py "
    "microsoft/outlook/calendar/_base.py "
    "microsoft/outlook/calendar/_delta_state.py "
    "microsoft/outlook/calendar/_handoff.py "
    "microsoft/outlook/calendar/_resume_state.py "
    "microsoft/outlook/calendar/_series.py "
    "microsoft/outlook/calendar/delta.py "
    "microsoft/outlook/calendar/discover.py "
    "microsoft/outlook/calendar/full.py "
    "microsoft/outlook/calendar/window.py "
    "microsoft/outlook/email/__init__.py "
    "microsoft/outlook/email/_attachments.py "
    "microsoft/outlook/email/_base.py "
    "microsoft/outlook/email/_delta_requests.py "
    "microsoft/outlook/email/_delta_state.py "
    "microsoft/outlook/email/_folders.py microsoft/outlook/email/delta.py "
    "microsoft/outlook/email/discover.py "
    "microsoft/outlook/email/folder_delta.py "
    "microsoft/outlook/email/full.py microsoft/profile.py "
    "microsoft/teams/__init__.py microsoft/teams/_base.py "
    "microsoft/teams/_channel_content.py "
    "microsoft/teams/_channel_messages.py "
    "microsoft/teams/_channel_profile.py "
    "microsoft/teams/_channel_topology.py microsoft/teams/_chat_content.py "
    "microsoft/teams/_chat_messages.py microsoft/teams/_chat_profile.py "
    "microsoft/teams/_notification_intake.py "
    "microsoft/teams/_notification_readback.py microsoft/teams/channel.py "
    "microsoft/teams/chat.py microsoft/teams/notifications.py "
    "microsoft/todo/__init__.py microsoft/todo/discover.py "
    "microsoft/todo/sync.py"
)
A1_FILES = (
    *(f"{SPIDER_ROOT}/{rel}" for rel in SPIDER_FILES),
    AUDIT,
    PLAN,
    INVENTORY,
)

# sha256 over sorted ``path NUL file-sha256 LF`` lines, taken from the shell.
PINNED_DIGEST = "d8b53358a509ce17e98d95f28ba0c88dc120134e54c4ecf8a483c0e1795775e3"

# Hand-written from the ``name = "..."`` class attributes in the source.
EXPECTED_SPIDERS = {
    "MicrosoftProfileSpider": "microsoft_profile",
    "MicrosoftContactsDeltaSpider": "microsoft_contacts_delta",
    "MicrosoftContactsDiscoverSpider": "microsoft_contacts_discover",
    "MicrosoftContactsSyncSpider": "microsoft_contacts_sync",
    "MicrosoftOneDriveDiscoverSpider": "microsoft_onedrive_discover",
    "MicrosoftOneDriveDeltaSpider": "microsoft_onedrive_delta",
    "MicrosoftOneDriveContentSpider": "microsoft_onedrive_content",
    "MicrosoftTeamsChatDiscoverSpider": "microsoft_teams_chat_discover",
    "MicrosoftTeamsChannelDiscoverSpider": "microsoft_teams_channel_discover",
    "MicrosoftTeamsNotificationReconcileSpider": (
        "microsoft_teams_notification_reconcile"
    ),
    "OutlookDiscoverSpider": "outlook_discover",
    "OutlookFolderDeltaSpider": "outlook_folder_delta",
    "OutlookDeltaSpider": "outlook_delta",
    "OutlookFullSpider": "outlook_full",
    "OutlookCalendarDiscoverSpider": "outlook_calendar_discover",
    "OutlookCalendarWindowSpider": "outlook_calendar_window",
    "OutlookCalendarDeltaSpider": "outlook_calendar_delta",
    "OutlookCalendarFullSpider": "outlook_calendar_full",
    "MicrosoftTodoDiscoverSpider": "microsoft_todo_discover",
    "MicrosoftTodoSyncSpider": "microsoft_todo_sync",
}

# Task15 scenarios are numbered 1 through 13 in the coverage-map contract.
EXPECTED_SCENARIOS = words("1 2 3 4 5 6 7 8 9 10 11 12 13")

# Hand-written from the ``build_plan`` gate list: 6 runtime, 1 a1, 9
# normal/exclusive/fastmcp, and 12 tool and audit gates.
EXPECTED_GATES = words(
    "runtime312 runtime312fastmcp runtime313 runtime313fastmcp "
    "runtime314 runtime314fastmcp a1 normal313 exclusive313 fastmcp313 "
    "normal312 exclusive312 fastmcp312 normal314 exclusive314 fastmcp314 "
    "scrapy_version ruff_version ruff format pyright_version pyright "
    "contracts diff precommit reverse_imports spider_coverage live_lsp"
)
LITERAL_GATES = set(EXPECTED_GATES[16:])
A1_ROOTS = ("message_ingest", "microsoft_graph", "scripts")
DYNAMIC = ("import_module", "__import__")


class A1CompatibilityError(Exception):
    """Report one specific way the A1 source differs from its baseline."""


def read(root: Path, relative: str) -> bytes:
    """Read one A1 file, or fail with a specific missing-file error."""
    path = root / relative
    if not path.is_file():
        raise A1CompatibilityError(f"A1 file missing: {relative}")
    return path.read_bytes()


def snapshot(root: Path, relatives: tuple[str, ...]) -> dict[str, str]:
    """Map each A1 relative path to the sha256 of its bytes."""
    return {rel: hashlib.sha256(read(root, rel)).hexdigest() for rel in relatives}


def aggregate(files: dict[str, str]) -> str:
    """Combine per-file digests into one order-independent digest."""
    lines = b"".join(f"{rel}\0{files[rel]}\n".encode() for rel in sorted(files))
    return hashlib.sha256(lines).hexdigest()


def spider_files(root: Path) -> list[str]:
    """List the Python files that are present under the A1 Spider tree."""
    base = root / SPIDER_ROOT
    return sorted(p.relative_to(root).as_posix() for p in base.rglob("*.py"))


def verify(root: Path, baseline: dict[str, str]) -> None:
    """Fail on a changed, missing or unexpected A1 file under ``root``."""
    for rel, digest in baseline.items():
        if hashlib.sha256(read(root, rel)).hexdigest() != digest:
            raise A1CompatibilityError(f"A1 file changed: {rel}")
    for rel in spider_files(root):
        if rel not in baseline:
            raise A1CompatibilityError(f"A1 unexpected file: {rel}")


def discover_spiders(root: Path) -> dict[str, str]:
    """Find Spider classes by AST: a class body that assigns ``name``."""
    found: dict[str, str] = {}
    for rel in spider_files(root):
        tree = ast.parse(read(root, rel).decode())
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for stmt in node.body:
                if not isinstance(stmt, ast.Assign):
                    continue
                if [t.id for t in stmt.targets if isinstance(t, ast.Name)] != ["name"]:
                    continue
                if not isinstance(stmt.value, ast.Constant):
                    continue
                if node.name in found:
                    raise A1CompatibilityError(f"duplicate Spider class: {node.name}")
                found[node.name] = str(stmt.value.value)
    return found


def range_bounds(root: Path, relative: str, target: str) -> tuple[int, int]:
    """Read the literal ``range(a, b)`` bounds of module variable ``target``."""
    tree = ast.parse(read(root, relative).decode())
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if [t.id for t in node.targets if isinstance(t, ast.Name)] != [target]:
            continue
        for call in ast.walk(node.value):
            is_range = isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
            if is_range and call.func.id == "range":  # type: ignore[attr-defined]
                low, high = (ast.literal_eval(a) for a in call.args)  # type: ignore[attr-defined]
                return low, high
    raise A1CompatibilityError(f"no range for {target} in {relative}")


def discover_scenarios(root: Path) -> tuple[str, ...]:
    """Read the Task15 scenario ids from the committed inventory source."""
    low, high = range_bounds(root, INVENTORY, "TASK15_SCENARIOS_PENDING")
    return tuple(str(i) for i in range(low, high))


def discover_gates(root: Path) -> tuple[str, ...]:
    """Resolve gate names with ``build_plan``, which only builds commands."""
    plan = importlib.import_module("scripts.handoff_qualification.plan")
    options = {
        f"python{v}{c}": f"<python{v}{c}>"
        for v in ("312", "313", "314")
        for c in ("", "fastmcp")
    }
    args = argparse.Namespace(
        source_root=root,
        output_root=root / "evidence",
        base="base",
        candidate="candidate",
        coverage_map=root / "map.json",
        precommit_python="<precommit-python>",
        precommit_cache=root / "cache",
        **options,
    )
    return tuple(gate.name for gate in plan.build_plan(args))


def literal_gate_names(root: Path) -> set[str]:
    """Collect ``Gate("literal", ...)`` names from ``build_plan`` by AST."""
    tree = ast.parse(read(root, PLAN).decode())
    names: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "Gate" or not node.args:
            continue
        if isinstance(first := node.args[0], ast.Constant):
            names.add(str(first.value))
    return names


def a1_imports(source: str) -> list[str]:
    """List A1 top-level packages imported anywhere in ``source``."""
    names: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.append(node.module)
        elif isinstance(node, ast.Call) and node.args:
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else ""
            called = func.id if isinstance(func, ast.Name) else called
            first = node.args[0]
            if called in DYNAMIC and isinstance(first, ast.Constant):
                names.append(str(first.value))
    return [n for n in names if n.split(".")[0] in A1_ROOTS]


def a2_sources() -> list[Path]:
    """List every Python file of the A2 package."""
    return sorted((REPO / "msgloom" / "a2_kedro").rglob("*.py"))


def a2_module_names() -> list[str]:
    """List every importable ``msgloom.a2_kedro`` module name."""
    package = importlib.import_module("msgloom.a2_kedro")
    walk = pkgutil.walk_packages(package.__path__, "msgloom.a2_kedro.")
    return ["msgloom.a2_kedro", *(info.name for info in walk)]


def copy_a1(tmp_path: Path) -> Path:
    """Copy the pinned A1 files into ``tmp_path``, keeping the layout."""
    for rel in A1_FILES:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, target)
    return tmp_path


# 1. Discovery against independent expected lists.


def test_pinned_file_list_matches_the_spider_tree_on_disk() -> None:
    pinned = [rel for rel in A1_FILES if rel.startswith(SPIDER_ROOT + "/")]
    if spider_files(REPO) != pinned:
        pytest.fail("A1 Spider file list on disk differs from A1_FILES")
    if len(A1_FILES) != len(set(A1_FILES)) or list(A1_FILES) != sorted(A1_FILES):
        pytest.fail("A1_FILES must be unique and sorted")


def test_spider_classes_match_hand_written_list() -> None:
    found = discover_spiders(REPO)
    if len(found) != 20:
        pytest.fail(f"expected 20 Spider classes, found {len(found)}")
    if found != EXPECTED_SPIDERS:
        pytest.fail(f"Spider class or name drift: {found}")
    if len(set(found.values())) != 20:
        pytest.fail("Spider names must be unique")


def test_task15_scenarios_match_hand_written_list() -> None:
    found = discover_scenarios(REPO)
    if len(found) != 13:
        pytest.fail(f"expected 13 Task15 scenarios, found {len(found)}")
    if found != EXPECTED_SCENARIOS:
        pytest.fail(f"Task15 scenario drift: {found}")
    # The audit gate must agree with the inventory on the scenario range.
    if "range(1, 14)" not in read(REPO, AUDIT).decode():
        pytest.fail("audit.py no longer requires scenarios 1..13")


def test_gates_match_hand_written_list() -> None:
    found = discover_gates(REPO)
    if len(found) != 28:
        pytest.fail(f"expected 28 gates, found {len(found)}")
    if found != EXPECTED_GATES:
        pytest.fail(f"gate name or order drift: {found}")
    if len(set(found)) != 28:
        pytest.fail("gate names must be unique")


def test_literal_gate_names_agree_with_source_ast() -> None:
    if literal_gate_names(REPO) != LITERAL_GATES:
        pytest.fail(f"literal Gate names drifted: {literal_gate_names(REPO)}")
    if not LITERAL_GATES <= set(EXPECTED_GATES):
        pytest.fail("literal gates must be a subset of the expected gates")


def test_spider_discovery_ignores_nested_name_assignments(tmp_path: Path) -> None:
    base = tmp_path / SPIDER_ROOT
    base.mkdir(parents=True)
    (base / "one.py").write_text(
        "class A:\n    name = 'a_spider'\n\n"
        "def f():\n    name = 'not_a_spider'\n"
        "class B:\n    other = 'x'\n"
    )
    if discover_spiders(tmp_path) != {"A": "a_spider"}:
        pytest.fail("discovery must use only class-level name assignments")


# 2. A2 does not import or change A1.


def test_a1_source_digest_matches_pin() -> None:
    digest = aggregate(snapshot(REPO, A1_FILES))
    if digest != PINNED_DIGEST:
        pytest.fail(f"A1 source digest {digest} differs from pin {PINNED_DIGEST}")


def test_a2_sources_do_not_import_a1_modules() -> None:
    if len(a2_sources()) < 10:
        pytest.fail("A2 source discovery found too few files")
    for path in a2_sources():
        hits = a1_imports(path.read_text())
        if hits:
            pytest.fail(f"{path.relative_to(REPO)} imports A1 modules: {hits}")


def test_import_scanner_flags_static_and_dynamic_a1_imports() -> None:
    cases = (
        "import message_ingest.spiders.microsoft.profile",
        "from message_ingest.spiders.microsoft import profile",
        "def f():\n    from microsoft_graph import x",
        "import importlib\nimportlib.import_module('message_ingest.settings')",
        "__import__('scripts.handoff_qualification.plan')",
    )
    for source in cases:
        if not a1_imports(source):
            pytest.fail(f"scanner missed: {source!r}")
    if a1_imports("import json\nfrom msgloom.contracts import x"):
        pytest.fail("scanner flagged a non-A1 import")


def test_importing_a2_leaves_a1_digest_unchanged() -> None:
    before = snapshot(REPO, A1_FILES)
    for name in a2_module_names():
        importlib.import_module(name)
    after = snapshot(REPO, A1_FILES)
    if before != after:
        pytest.fail("importing msgloom.a2_kedro changed an A1 file")
    if aggregate(after) != PINNED_DIGEST:
        pytest.fail("A1 digest differs from pin after importing A2")
    verify(REPO, before)
    if spider_files(REPO) != [r for r in A1_FILES if r.startswith(SPIDER_ROOT)]:
        pytest.fail("importing A2 added or removed an A1 Spider file")


def test_fresh_interpreter_imports_a2_without_a1_modules() -> None:
    code = (
        "import importlib, json, pkgutil, sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "package = importlib.import_module('msgloom.a2_kedro')\n"
        "for info in pkgutil.walk_packages(package.__path__, 'msgloom.a2_kedro.'):\n"
        "    importlib.import_module(info.name)\n"
        "roots = ('message_ingest', 'microsoft_graph', 'scripts')\n"
        "print(json.dumps(sorted(\n"
        "    m for m in sys.modules if m.split('.')[0] in roots)))\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code, str(REPO)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=REPO,
        check=False,
    )
    if done.returncode != 0:
        pytest.fail(f"fresh import failed: {done.stderr[-500:]}")
    loaded = json.loads(done.stdout.strip().splitlines()[-1])
    if loaded:
        pytest.fail(f"importing msgloom.a2_kedro loaded A1 modules: {loaded}")


# 3. Negative cases on a tmp_path copy.


def test_clean_copy_passes_the_check(tmp_path: Path) -> None:
    root = copy_a1(tmp_path)
    baseline = snapshot(root, A1_FILES)
    if aggregate(baseline) != PINNED_DIGEST:
        pytest.fail("copy digest must equal the pinned digest")
    verify(root, baseline)


def test_mutated_file_changes_digest_and_fails_check(tmp_path: Path) -> None:
    root = copy_a1(tmp_path)
    baseline = snapshot(root, A1_FILES)
    target = root / SPIDER_ROOT / "microsoft" / "profile.py"
    target.write_bytes(target.read_bytes() + b"\n# mutated\n")
    mutated = snapshot(root, A1_FILES)
    if aggregate(mutated) == PINNED_DIGEST:
        pytest.fail("mutation did not change the aggregate digest")
    changed = [rel for rel in A1_FILES if mutated[rel] != baseline[rel]]
    if changed != [f"{SPIDER_ROOT}/microsoft/profile.py"]:
        pytest.fail(f"unexpected changed files: {changed}")
    with pytest.raises(A1CompatibilityError) as caught:
        verify(root, baseline)
    expected = f"A1 file changed: {SPIDER_ROOT}/microsoft/profile.py"
    if str(caught.value) != expected:
        pytest.fail(f"wrong error: {caught.value}")


def test_removed_file_fails_with_missing_error(tmp_path: Path) -> None:
    root = copy_a1(tmp_path)
    baseline = snapshot(root, A1_FILES)
    (root / INVENTORY).unlink()
    with pytest.raises(A1CompatibilityError) as caught:
        verify(root, baseline)
    if str(caught.value) != f"A1 file missing: {INVENTORY}":
        pytest.fail(f"wrong error: {caught.value}")


def test_added_spider_file_fails_with_unexpected_error(tmp_path: Path) -> None:
    root = copy_a1(tmp_path)
    baseline = snapshot(root, A1_FILES)
    extra = root / SPIDER_ROOT / "microsoft" / "extra.py"
    extra.write_text("name = 'x'\n")
    with pytest.raises(A1CompatibilityError) as caught:
        verify(root, baseline)
    if str(caught.value) != f"A1 unexpected file: {SPIDER_ROOT}/microsoft/extra.py":
        pytest.fail(f"wrong error: {caught.value}")


def test_mutated_copy_no_longer_matches_hand_written_spider_list(
    tmp_path: Path,
) -> None:
    root = copy_a1(tmp_path)
    target = root / SPIDER_ROOT / "microsoft" / "profile.py"
    text = target.read_text().replace(
        'name = "microsoft_profile"', 'name = "microsoft_profile_x"'
    )
    target.write_text(text)
    found = discover_spiders(root)
    if found == EXPECTED_SPIDERS:
        pytest.fail("renamed Spider must differ from the expected list")
    if found["MicrosoftProfileSpider"] != "microsoft_profile_x":
        pytest.fail("discovery must read the mutated Spider name")
    if aggregate(snapshot(root, A1_FILES)) == PINNED_DIGEST:
        pytest.fail("mutation must change the pinned digest")

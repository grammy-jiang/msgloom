"""Qualify integrated non-mail authority paths through real local crawls."""

import json
import subprocess

import pytest
from scrapy.spiderloader import SpiderLoader
from scrapy.utils.project import get_project_settings

from tests import test_contacts_crawl as contacts
from tests import test_onedrive_resync_crawl as drive
from tests import test_todo_crawl as todo
from tests.handoff_qualification.commands import (
    ROOT,
    calendar,
    contacts_args,
    contacts_crawl,
)
from tests.handoff_qualification.feed import (
    authority,
    feed,
    groups,
    initialize,
    no_churn,
    reject_entries,
    restore_entries,
    rows,
    staged,
    successful,
    wait_staged,
)
from tests.handoff_qualification.inventory import MATRIX
from tests.handoff_qualification.server import END, OTHER_END, START, local_graph

graph_server = todo.graph_server
contacts_server = contacts.contacts_server
resync_server = drive.resync_server


def test_installed_spider_matrix_keeps_unqualified_paths_pending():
    """
    Detect inventory drift without declaring unfinished providers complete.
    """
    installed = set(SpiderLoader(get_project_settings()).list())
    if installed != set(MATRIX) or len(installed) != 17:
        pytest.fail("Installed spider inventory differs from the exact mapping")
    for name, coverage in MATRIX.items():
        if bool(coverage.tests) == bool(coverage.pending):
            pytest.fail(f"{name} must have tests or an explicit pending owner")
        for test in coverage.tests:
            if not callable(globals().get(test)):
                pytest.fail(f"{name} cites a nonexistent qualification test")
    if {name for name, c in MATRIX.items() if c.tests} != {
        "microsoft_profile",
        "microsoft_todo_sync",
        "microsoft_contacts_sync",
        "microsoft_contacts_delta",
        "microsoft_onedrive_delta",
        "outlook_calendar_delta",
    }:
        pytest.fail("Qualification status silently expanded beyond this shard")


def test_todo_large_group_pages_and_unchanged_round(tmp_path, graph_server):
    """
    One atomic snapshot must remain pageable with exact hierarchical pins.
    """
    origin, _state, _seen, pages = graph_server
    extra = [f"extra-{number}" for number in range(40)]
    pages[todo.LISTS + todo.CURSOR]["value"].extend(
        {"id": identity} for identity in extra
    )
    for identity in extra:
        pages[f"{todo.LISTS}/{identity}/tasks?%24top=2"] = {"value": []}
    successful(todo._crawl(tmp_path, origin, action="sync"))
    first = feed(tmp_path, "todo-fixture", "todo", limit=7)
    positive = [f for _, facts in first for f in facts if f.role != "transition"]
    expected = {
        ("todo_task_list", (todo.LIST_ID,)),
        ("todo_task_list", ("flagged",)),
        ("todo_task", (todo.LIST_ID, todo.TASK_ID)),
        ("todo_task", (todo.LIST_ID, "second")),
        *(("todo_task_list", (identity,)) for identity in extra),
        *(
            ("todo_checklist_item", (todo.LIST_ID, todo.TASK_ID, identity))
            for identity in ("check-one", "check-two")
        ),
        *(
            ("todo_linked_resource", (todo.LIST_ID, todo.TASK_ID, identity))
            for identity in ("link-one", "link-two")
        ),
    }
    if {
        (f.resource_kind, tuple(json.loads(f.resource_identity))) for f in positive
    } != expected:
        pytest.fail("Snapshot lost exact list/task/component identities")
    for fact in positive:
        identity = json.loads(fact.resource_identity)
        if len(identity) > 1 and (
            json.loads(fact.parent_resource_identity or "null") != identity[:-1]
        ):
            pytest.fail("Component/task lost its exact hierarchical parent")
    if len(first) != 96 or len({e.release_group_id for e, _ in first}) != 1:
        pytest.fail("Large snapshot was split, omitted or duplicated")
    successful(todo._crawl(tmp_path, origin, action="sync"))
    no_churn(first, feed(tmp_path, "todo-fixture", "todo", limit=7))
    if [g["authority_revision"] for g in groups(tmp_path)] != ["1", "2"]:
        pytest.fail("Unchanged snapshot did not record zero-entry authority")


@pytest.mark.parametrize("failure", ["incomplete", "release"])
def test_todo_incomplete_and_release_failure_preserve_authority(
    tmp_path, graph_server, failure
):
    """
    Partial traversal and late entry failure cannot publish scoped absence.
    """
    origin, state, _seen, _pages = graph_server
    successful(todo._crawl(tmp_path, origin, action="sync"))
    before = authority(tmp_path, "todo")
    if failure == "release":
        state["mode"] = "empty"
        reject_entries(tmp_path)
        settings = {}
    else:
        settings = {
            "SPIDER_MIDDLEWARES": json.dumps(
                {
                    "todo_sync_failures.DropChecklistContinuationMiddleware": 700,
                }
            )
        }
    result = todo._crawl(tmp_path, origin, action="sync", extra_settings=settings)
    if result.returncode != 1 or authority(tmp_path, "todo") != before:
        pytest.fail("Failed snapshot changed authority or immutable publication")
    if failure == "release":
        restore_entries(tmp_path)
        successful(todo._crawl(tmp_path, origin, action="sync"))
        absent = [
            f
            for _, facts in feed(tmp_path, "todo-fixture", "todo")
            for f in facts
            if f.transition_reason == "snapshot_absent"
        ]
        if len(absent) != 8 or any(
            (f.scope_kind, f.scope_identity) != ("todo_source", "todo-fixture")
            for f in absent
        ):
            pytest.fail("Retry lost exact source-scoped absence")


def test_contacts_snapshot_identity_churn_and_atomic_failure(tmp_path, contacts_server):
    """Recursive contact and folder authority must bind exact scopes."""
    origin, state, _seen = contacts_server
    successful(contacts_crawl(tmp_path, origin))
    first = feed(tmp_path, "contacts-fixture", "contacts")
    positives = [f for _, facts in first for f in facts if f.role != "transition"]
    if {(f.resource_identity, f.scope_identity) for f in positives} != {
        ("folder-parent", "root"),
        ("folder-other", "root"),
        ("folder-child", "root"),
        ("default-one", "default"),
        ("default-two", "default"),
        ("parent-contact", "folder:folder-parent"),
        ("child-one", "folder:folder-child"),
        ("child-two", "folder:folder-child"),
    }:
        pytest.fail("Recursive snapshot lost contact/folder scope identities")
    successful(contacts_crawl(tmp_path, origin))
    no_churn(first, feed(tmp_path, "contacts-fixture", "contacts"))
    before = authority(tmp_path, "contacts")
    state["mode"] = "empty"
    reject_entries(tmp_path)
    result = contacts_crawl(tmp_path, origin)
    if result.returncode != 1 or authority(tmp_path, "contacts") != before:
        pytest.fail("Contacts release failure partially advanced authority")
    restore_entries(tmp_path)
    successful(contacts_crawl(tmp_path, origin))
    added = feed(tmp_path, "contacts-fixture", "contacts")[len(first) :]
    if len(added) != 8 or any(e.entry_kind != "transition" for e, _ in added):
        pytest.fail("Complete empty snapshot fabricated contact representations")


def test_contacts_sparse_delta_staging_and_release_rollback(tmp_path, contacts_server):
    """
    A failed sparse round stays staged; retry publishes exact provider data.
    """
    origin, _state, _seen = contacts_server
    successful(contacts_crawl(tmp_path, origin, delta=True))
    before = authority(tmp_path, "contacts")
    current = rows(tmp_path, "contacts")
    old_facts = {f["fact_id"] for f in staged(tmp_path)}
    reject_entries(tmp_path)
    failed = contacts_crawl(tmp_path, origin, delta=True)
    if "contacts_delta_promotion_failed" not in failed.stderr:
        pytest.fail("Injected sparse release failure did not reach idle gate")
    if (
        authority(tmp_path, "contacts") != before
        or rows(tmp_path, "contacts") != current
    ):
        pytest.fail("Failed sparse promotion changed checkpoint or merged state")
    residue = [f for f in staged(tmp_path) if f["fact_id"] not in old_facts]
    if len(residue) != 1 or residue[0]["storage_relation"] != "authority_staged":
        pytest.fail("Failed sparse round lost its exact staged observation")
    restore_entries(tmp_path)
    successful(contacts_crawl(tmp_path, origin, delta=True))
    released = feed(tmp_path, "contacts-fixture", "contacts")
    last_run = groups(tmp_path)[-1]["owner_run_id"]
    primary = [
        f
        for e, facts in released
        if e.group.owner_run_id == last_run
        for f in facts
        if f.role == "primary"
    ]
    if len(primary) != 1 or primary[0].resource_identity != "delta-one":
        pytest.fail("Sparse delta released an unrelated or missing contact")
    fact = primary[0]
    locator = fact.source_version_locator
    if locator is None or locator.kind != "observation":
        pytest.fail("Sparse delta lost its immutable observation locator")
    observation = next(
        r
        for r in rows(tmp_path, "contact_delta_observations")
        if [r["source_id"], "folder:" + r["folder_id"], r["run_id"], r["ordinal"]]
        == json.loads(locator.observation_id or "null")
    )
    if json.loads(observation["raw"]) != {"id": "delta-one", "companyName": "second"}:
        pytest.fail("Sparse release substituted a mutable merged contact")
    if any(f.fact_id == residue[0]["fact_id"] for _, fs in released for f in fs):
        pytest.fail("Failed generation residue became a winning publication")


def test_contacts_new_snapshot_fences_inflight_delta(tmp_path):
    """A real newer snapshot must fence a paused older delta generation."""
    with local_graph() as (origin, _state, reached, release, _seen):
        process = subprocess.Popen(
            contacts_args(tmp_path, origin, delta=True, folder="folder-race"),
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            if not reached.wait(15):
                pytest.fail("Older delta never reached the local barrier")
            pending = wait_staged(tmp_path)
            if not pending or groups(tmp_path):
                pytest.fail("In-flight sparse facts leaked or failed to stage")
            successful(contacts_crawl(tmp_path, origin))
            winner = authority(tmp_path, "contacts")
            release.set()
            _stdout, stderr = process.communicate(timeout=30)
            if "contacts_delta_promotion_failed" not in stderr:
                pytest.fail("Older delta was not fenced by the shared generation")
            if authority(tmp_path, "contacts") != winner:
                pytest.fail("Losing delta changed winning authority or feed")
            published = feed(tmp_path, "contacts-fixture", "contacts")
            if any(
                f.fact_id in {p["fact_id"] for p in pending}
                for _, fs in published
                for f in fs
            ):
                pytest.fail("Losing sparse observation became primary work")
            if {r["job_title"] for r in rows(tmp_path, "contacts")} != {"winner"}:
                pytest.fail("Older sparse state replaced the newer snapshot")
        finally:
            release.set()
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)


def test_calendar_410_winning_attempt_is_window_scoped(tmp_path):
    """
    Superseded pages cannot publish; absence affects only the reset window.
    """
    with local_graph() as (origin, state, _reached, _release, seen):
        successful(calendar(tmp_path, origin))
        successful(calendar(tmp_path, origin, end=OTHER_END))
        baseline = feed(tmp_path, "calendar-qualification", "outlook_calendar")
        state["calendar"] = "reset"
        successful(calendar(tmp_path, origin))
        added = feed(tmp_path, "calendar-qualification", "outlook_calendar")[
            len(baseline) :
        ]
        if {e.resource_identity for e, _ in added} != {"kept", "new", "absent"}:
            pytest.fail("Reset released a ghost or omitted a winning impact")
        scope = json.dumps(["default", START, END], separators=(",", ":"))
        for entry, facts in added:
            if entry.scope_identity != scope or entry.group.authority_revision != "2":
                pytest.fail("Calendar release lost fixed-window authority")
            if any(
                f.scope_identity != scope
                or f.resource_identity != entry.resource_identity
                for f in facts
            ):
                pytest.fail("Reset fact escaped its entry's exact event/window")
            prior_membership = {
                f.fact_id for _, fs in baseline for f in fs if f.role == "transition"
            }
            for fact in facts:
                if fact.fact_id in prior_membership:
                    if fact.role != "transition" or entry.resource_identity != "kept":
                        pytest.fail("Reset reused unrelated prior state")
                    continue
                if (
                    fact.run_id != entry.group.owner_run_id
                    or json.loads(fact.transition_reason or "{}").get("attempt") != 1
                ):
                    pytest.fail("A pre-reset attempt leaked into the winning group")
        absence = [
            f
            for _, fs in added
            for f in fs
            if json.loads(f.transition_reason or "{}").get("kind")
            == "rebaseline_absence"
        ]
        if len(absence) != 1 or absence[0].resource_identity != "absent":
            pytest.fail("Reset absence did not name the exact missing event")
        other = [
            r
            for r in rows(tmp_path, "calendar_delta_event_states")
            if r["end_datetime"] == OTHER_END
        ]
        if len(other) != 2 or any(not r["is_present"] for r in other):
            pytest.fail("Fixed-window removal escaped into the other window")
        if any(
            r["is_removed"]
            for r in rows(tmp_path, "calendar_events")
            if r["event_id"] == "absent"
        ):
            pytest.fail("Window absence became global event deletion")
        ghost = [f for f in staged(tmp_path) if f["resource_identity"] == "ghost"]
        if not ghost or not any("/calendar-expired" == p for p in seen):
            pytest.fail("Fixture did not exercise a superseded page followed by 410")
        before = feed(tmp_path, "calendar-qualification", "outlook_calendar")
        state["calendar"] = "unchanged"
        successful(calendar(tmp_path, origin))
        no_churn(before, feed(tmp_path, "calendar-qualification", "outlook_calendar"))


def test_calendar_release_failure_preserves_prior_window(tmp_path):
    """
    Late SQLite publication failure must roll back checkpoint and membership.
    """
    with local_graph() as (origin, state, _reached, _release, _seen):
        successful(calendar(tmp_path, origin))
        before = authority(tmp_path, "outlook_calendar")
        state["calendar"] = "reset"
        reject_entries(tmp_path)
        result = calendar(tmp_path, origin)
        if result.returncode != 1 or authority(tmp_path, "outlook_calendar") != before:
            pytest.fail("Calendar publication failure partially committed authority")
        restore_entries(tmp_path)
        successful(calendar(tmp_path, origin))
        if [g["authority_revision"] for g in groups(tmp_path)] != ["1", "2"]:
            pytest.fail("Calendar retry failed to recover exactly one revision")


def test_onedrive_failed_reset_then_exact_winner(tmp_path, resync_server):
    """
    Failed reset residue cannot become authority during a later clean reset.
    """
    origin, state, _seen = resync_server
    drive._baseline(tmp_path, origin, state)
    before = authority(tmp_path, "onedrive")
    state["mode"] = "malformed"
    failed = drive._crawl(tmp_path, origin)
    if failed.returncode != 1 or authority(tmp_path, "onedrive") != before:
        pytest.fail("Incomplete reset advanced cursor or publication")
    failed_ids = {
        f["fact_id"]
        for f in staged(tmp_path)
        if f["storage_relation"] == "authority_staged"
    }
    if not failed_ids:
        pytest.fail("Failure fixture did not retain partial reset observations")
    state.update(mode="resync", reset_started=False)
    successful(drive._crawl(tmp_path, origin))
    all_entries = feed(tmp_path, "onedrive-resync-fixture", "onedrive")
    winner = groups(tmp_path)[-1]
    released = [(e, fs) for e, fs in all_entries if e.release_group_id == winner["id"]]
    primary = [f for _, fs in released for f in fs if f.role == "primary"]
    if {f.resource_identity for f in primary} != {"kept", "new"}:
        pytest.fail("Winning reset lost its exact materialized item set")
    if any(f.fact_id in failed_ids for _, fs in released for f in fs):
        pytest.fail("Failed reset residue escaped into the winning publication")
    absent = [
        f for _, fs in released for f in fs if f.transition_reason == "resync_absent"
    ]
    if len(absent) != 1 or (absent[0].resource_identity, absent[0].scope_identity) != (
        "absent",
        "onedrive-resync-fixture",
    ):
        pytest.fail("Winning reset absence escaped its source scope")
    if any(
        f.source_version_locator is None
        or f.source_version_locator.kind != "observation"
        for f in primary
    ):
        pytest.fail("Reset release substituted a mutable current item locator")


def test_onedrive_release_failure_preserves_prior_authority(tmp_path, resync_server):
    """
    Late entry failure preserves reset materialization and provider cursor.
    """
    origin, state, _seen = resync_server
    drive._baseline(tmp_path, origin, state)
    before = authority(tmp_path, "onedrive")
    items = rows(tmp_path, "onedrive_items")
    reject_entries(tmp_path)
    failed = drive._crawl(tmp_path, origin)
    if failed.returncode != 1 or authority(tmp_path, "onedrive") != before:
        pytest.fail("Failed reset release partially advanced authority")
    if rows(tmp_path, "onedrive_items") != items:
        pytest.fail("Failed reset release committed materialized item changes")
    restore_entries(tmp_path)
    state["reset_started"] = False
    successful(drive._crawl(tmp_path, origin))
    if [g["authority_revision"] for g in groups(tmp_path)] != ["1", "2"]:
        pytest.fail("Reset retry duplicated or lost authority publication")


def test_onedrive_unchanged_normal_delta_has_no_churn(tmp_path):
    """Repeated provider state advances cursor but does not republish items."""
    with local_graph() as (origin, _state, _reached, _release, _seen):
        successful(drive._crawl(tmp_path, origin))
        first = feed(tmp_path, "onedrive-resync-fixture", "onedrive")
        if {
            f.resource_identity for _, fs in first for f in fs if f.role == "primary"
        } != {"kept", "absent"}:
            pytest.fail("Normal delta lost exact initial item identities")
        successful(drive._crawl(tmp_path, origin))
        no_churn(first, feed(tmp_path, "onedrive-resync-fixture", "onedrive"))
        if [g["authority_revision"] for g in groups(tmp_path)] != ["1", "2"]:
            pytest.fail("Unchanged delta did not advance zero-entry authority")


def test_profile_keeps_evidence_without_handoff(tmp_path):
    """
    The public profile command retains evidence but emits no handoff facts.
    """
    initialize(tmp_path)
    with local_graph() as (origin, _state, _reached, _release, _seen):
        result = contacts._run(tmp_path, origin, "microsoft", "profile")
        successful(result)
    if json.loads(result.stdout).get("id") != "profile-local":
        pytest.fail("Profile command did not return the local fixture")
    if len(rows(tmp_path, "raw_http_evidence")) != 1:
        pytest.fail("Profile no-release result lacks actual persisted evidence")
    if (
        staged(tmp_path)
        or groups(tmp_path)
        or rows(tmp_path, "acquisition_release_entries")
    ):
        pytest.fail("Profile incorrectly entered an acquisition stream")

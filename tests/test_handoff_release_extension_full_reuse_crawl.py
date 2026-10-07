"""Require Full enrich to publish exact prior facts after native no-work idle."""

import json

import pytest
from handoff_full_crawl_helpers import (
    expected_full_members,
    full_graph_server,
    run_full,
    snapshot,
)
from handoff_release_reader_helpers import bind_fixture_source, read_published

__all__ = ["full_graph_server"]


@pytest.mark.parametrize("family", ["mail", "calendar"])
@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize("limited", [False, True])
def test_native_full_no_work_revalidates_prior_profile(
    tmp_path, full_graph_server, family, direct, limited
):
    """A later no-work run must publish old facts without new provenance."""
    bind_fixture_source(tmp_path / "catalog.db", "source")
    root, seen, policy = full_graph_server
    policy["attachments_status"] = 403 if limited else 200
    # Public commands report the expected terminal 403 as a failed run.
    run_full(
        tmp_path,
        root,
        family,
        operation="refresh",
        enabled=False,
        expected_returncode=1 if limited else 0,
    )
    before = snapshot(tmp_path, family)
    if not before["facts"] or before["groups"]:
        pytest.fail("Initial acquisition must persist unpublished Full facts")
    expected_members = expected_full_members(before, family, limited=limited)
    seen.clear()
    log = run_full(
        tmp_path, root, family, operation="enrich", enabled=True, direct=direct
    )
    after = snapshot(tmp_path, family)
    if seen or "already_complete_count': 1" not in log:
        pytest.fail("The native planner did not take the no-work path: " + log)
    if after["facts"] != before["facts"] or after["evidence"] != before["evidence"]:
        pytest.fail("No-work revalidation changed immutable acquisition provenance")
    if len(after["groups"]) != 1 or len(after["entries"]) != 1:
        pytest.fail("Native no-work Full omitted its independently complete target")
    group = after["groups"][0]
    expected = "terminal_with_limitations" if limited else "complete"
    if group["coverage_kind"] != expected or group["authority_revision"]:
        pytest.fail("Reused Full changed terminal coverage or acquired authority")
    if limited and "unauthorized" not in group["limitation_codes"]:
        pytest.fail("A persisted provider limitation was lost during revalidation")
    if after["members"] != expected_members:
        pytest.fail("Release did not bind every exact required Full profile fact")
    old_runs = {json.loads(value)["run_id"] for value in before["facts"].values()}
    if group["owner_run_id"] in old_runs:
        pytest.fail("Release ownership reused the old acquisition run")
    if not direct:
        reads = read_published(
            tmp_path / "catalog.db",
            tmp_path / "raw",
            "source",
            "outlook_mail" if family == "mail" else "outlook_calendar",
        )
        if len(reads) != 1:
            pytest.fail("Full Reader lost its one reused profile")
        entry, result = reads[0]
        if entry.resource_identity != "one" or entry.group.coverage_kind != expected:
            pytest.fail("Full Reader changed target or terminal coverage")
        if {fact.fact_id for fact in result.facts} != set(expected_members):
            pytest.fail("Full Reader changed exact reused fact membership")
        if limited and "unauthorized" not in entry.group.limitation_codes:
            pytest.fail("Full Reader lost persisted terminal limitations")


@pytest.mark.parametrize("family", ["mail", "calendar"])
def test_native_full_cache_replay_can_release_prior_captures(
    tmp_path, full_graph_server, family
):
    """Logical refresh proof may use canonical captures from the first run."""
    root, seen, _ = full_graph_server
    run_full(tmp_path, root, family, operation="refresh", enabled=False, cache=True)
    before = snapshot(tmp_path, family)
    seen.clear()
    log = run_full(
        tmp_path, root, family, operation="refresh", enabled=True, cache=True
    )
    after = snapshot(tmp_path, family)
    if seen or "httpcache/hit" not in log:
        pytest.fail("Second refresh did not exercise native HTTP cache replay")
    if before["evidence"] != after["evidence"]:
        pytest.fail("Cache replay replaced canonical capture provenance")
    if len(after["groups"]) != 1 or len(after["entries"]) != 1:
        pytest.fail("Cache-backed Full proof did not release the complete target")

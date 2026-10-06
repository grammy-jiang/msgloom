"""Qualify mixed-run Full proof and native target-local failure isolation."""

import json

import pytest
from handoff_full_crawl_helpers import full_graph_server, run_full, snapshot

from message_ingest.acquisition.microsoft.outlook.calendar.full_completion import (
    verify_full_v1_target as verify_calendar,
)
from message_ingest.acquisition.microsoft.outlook.email.full_completion import (
    verify_full_v1_target as verify_mail,
)
from message_ingest.catalog import Catalog

__all__ = ["full_graph_server"]


@pytest.mark.parametrize("family", ["mail", "calendar"])
@pytest.mark.parametrize("direct", [False, True])
def test_native_partial_enrich_reuses_detail_and_completes_inventory(
    tmp_path, full_graph_server, family, direct
):
    """Missing inventory must not discard the prior exact primary binding."""
    root, seen, policy = full_graph_server
    policy["attachments_status"] = 503
    run_full(
        tmp_path,
        root,
        family,
        operation="refresh",
        enabled=False,
        expected_returncode=1,
    )
    before = snapshot(tmp_path, family)
    if not before["facts"] or before["entries"]:
        pytest.fail("Partial seed must have unpublished acquisition facts")
    policy["attachments_status"] = 200
    seen.clear()
    run_full(
        tmp_path,
        root,
        family,
        operation="enrich",
        enabled=True,
        direct=direct,
    )
    after = snapshot(tmp_path, family)
    kind = "messages" if family == "mail" else "events"
    if seen != [f"/v1.0/me/{kind}/one/attachments"]:
        pytest.fail(f"Partial enrich reacquired an already complete surface: {seen}")
    if len(after["groups"]) != 1 or len(after["entries"]) != 1:
        pytest.fail("Mixed-run Full proof did not release its complete target")
    for fact_id, payload in before["facts"].items():
        if after["facts"].get(fact_id) != payload:
            pytest.fail("Partial enrich rewrote an immutable prior fact")
    if not before["evidence"] < after["evidence"]:
        pytest.fail("Missing inventory did not add evidence to prior captures")
    bound = [json.loads(after["facts"][key]) for key in after["members"]]
    components = {fact["component_kind"] for fact in bound}
    expected = {None, "detail", "attachments"}
    if family == "mail":
        expected.add("mime")
    if components != expected or len(bound) != len(expected):
        pytest.fail("Mixed-run release did not bind each exact required surface")
    old_ids = {
        fact_id
        for fact_id in after["members"]
        if json.loads(after["facts"][fact_id])["component_kind"] != "attachments"
    }
    if not old_ids <= before["facts"].keys():
        pytest.fail("Full enrich failed to reuse its exact stored primary facts")
    group = after["groups"][0]
    inventory = next(fact for fact in bound if fact["component_kind"] == "attachments")
    if inventory["run_id"] != group["owner_run_id"]:
        pytest.fail("New inventory was not acquired by the releasing logical run")
    if group["coverage_kind"] != "complete" or group["authority_revision"]:
        pytest.fail("Partial enrich changed coverage or acquired authority")


@pytest.mark.parametrize("family", ["mail", "calendar"])
@pytest.mark.parametrize("failure", ["callback", "item"])
@pytest.mark.parametrize("direct", [False, True])
def test_native_full_failure_blocks_only_affected_complete_target(
    tmp_path, full_graph_server, family, failure, direct
):
    """A real failure after output must block one target at drained idle.

    Both targets retain complete persisted facts. This makes the test fail if
    failure attribution is ignored, or if the run-wide failure blocks the
    unrelated target. No synthetic signal or close reason authorizes release.
    """
    root, _, _ = full_graph_server
    log = run_full(
        tmp_path,
        root,
        family,
        operation="refresh",
        enabled=True,
        direct=direct,
        targets="one,two",
        failure=failure,
        expected_returncode=0 if direct else 1,
    )
    # Production privacy filters remove exception text. Native signal stats
    # still prove that the injected callback or persisted-item failure ran.
    counter = (
        "spider_exceptions/RuntimeError"
        if failure == "callback"
        else "msgloom/crawl/integrity_failure_reason_count/item_error"
    )
    if f"'{counter}': 1" not in log:
        pytest.fail("Native failure injection did not reach Scrapy: " + log)
    state = snapshot(tmp_path, family)
    if len(state["groups"]) != 1 or len(state["entries"]) != 1:
        pytest.fail("Native failure lost target-local release isolation")
    entry = json.loads(state["entries"][0]["payload"])
    if entry["resource_identity"] != "two":
        pytest.fail("The failed target escaped native failure attribution")
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.db'}")
    try:
        for target in ("one", "two"):
            if family == "mail":
                proof = verify_mail(
                    catalog,
                    source_id="source",
                    run_id=state["groups"][0]["owner_run_id"],
                    message_id=target,
                )
            else:
                proof = verify_calendar(
                    catalog,
                    source_id="source",
                    run_id=state["groups"][0]["owner_run_id"],
                    event_id=target,
                )
            if not proof.complete:
                pytest.fail("Injected failure must leave complete persisted proof")
    finally:
        catalog.close()
    facts = [json.loads(payload) for payload in state["facts"].values()]
    required = {None, "detail", "attachments"}
    if family == "mail":
        required.add("mime")
    for target in ("one", "two"):
        components = {
            fact["component_kind"]
            for fact in facts
            if fact["resource_identity"] == target
        }
        if not required <= components:
            pytest.fail("Failure fixture did not retain a complete target profile")
    primary = "message" if family == "mail" else "calendar_event"
    surface = "message_surface" if family == "mail" else "calendar_event_surface"
    expected_members = {
        fact_id
        for fact_id, payload in state["facts"].items()
        if (fact := json.loads(payload))["resource_identity"] == "two"
        and fact["resource_kind"] in {primary, surface}
        and fact["component_kind"] in required
    }
    if len(expected_members) != len(required):
        pytest.fail("Unrelated target fixture has ambiguous required facts")
    if state["members"] != expected_members:
        pytest.fail("Release did not bind exactly the unaffected target facts")
    group = state["groups"][0]
    if group["subject_identity"] != "two" or group["coverage_kind"] != "complete":
        pytest.fail("Target failure changed the independent release subject")
    if group["authority_revision"]:
        pytest.fail("Non-authoritative target acquired absence authority")

"""C0-17f: the A3 replay plan binds prepared family @1 or @2 exactly.

Synthetic data only. The expected values are written by hand from the
blueprint rule: ``triage_input@1`` reads the ``@1`` family, ``triage_input@2``
reads the ``@2`` family, and the plan never mixes or converts them.
"""

from __future__ import annotations

import dataclasses
from dataclasses import FrozenInstanceError, replace

import pytest

from msgloom.contracts import ResultRef, VersionRef
from msgloom.triage import TopicAllocation
from msgloom.triage_input import SourceRole, SourceRoleBinding
from msgloom.triage_pipeline import TriageMode, TriageReplayPlan
from tests.a2_kedro.helpers import check

SOURCE = VersionRef("source", "source-1", "v1")
FAMILY = (
    ("prepared", "prepared_results"),
    ("filter_result", "filter_results"),
    ("group_result", "group_results"),
)


def family(version: str, tag: str = "a") -> dict[str, tuple[ResultRef, ...]]:
    """Return one ref per family kind, all at ``version``."""
    return {
        field: (ResultRef(f"{tag}-{kind}", kind, version),) for kind, field in FAMILY
    }


def make_plan(version: str = "1", **changes: object) -> TriageReplayPlan:
    """Build one replay plan with the whole family at ``version``."""
    plan = TriageReplayPlan(
        expected_targets=(SOURCE,),
        prior_triage_results=(),
        roles=(SourceRoleBinding(source_ref=SOURCE, role=SourceRole.NEW_SOURCE),),
        topic_allocations=(
            TopicAllocation(
                allocation_key="allocation-0",
                topic_ref=VersionRef("topic", "topic-0", "v1"),
                assessment_ref=VersionRef("topic-assessment", "topic-0", "v1-0"),
            ),
        ),
        mode=TriageMode.REPLAY,
        replay_context_result=ResultRef("context-1", "working_context_snapshot", "1"),
        **family(version),
    )
    return replace(plan, **changes) if changes else plan


def refuses(plan: TriageReplayPlan, text: str) -> None:
    """Require the exact fixed ``ValueError`` message from ``source_version``."""
    with pytest.raises(ValueError) as caught:
        plan.source_version()
    check(str(caught.value) == text, f"unexpected message: {caught.value}")
    check(caught.value.__cause__ is None, "no chained cause")
    check("a-prepared" not in str(caught.value), "no ref value in message")


def test_v1_plan_reads_as_version_1() -> None:
    plan = make_plan("1")
    check(plan.source_version() == "1", "family @1 selects version 1")
    check(plan.validated() == plan, "validated @1 plan is equal")


def test_v2_plan_reads_as_version_2() -> None:
    plan = make_plan("2")
    check(plan.source_version() == "2", "family @2 selects version 2")
    checked = plan.validated()
    check(checked == plan, "validated @2 plan is equal")
    check(checked.source_version() == "2", "version survives validation")
    for kind, field in FAMILY:
        refs = getattr(checked, field)
        check(
            tuple((r.kind, r.schema_version) for r in refs) == ((kind, "2"),),
            f"{field} keeps exact @2 identity",
        )


def test_v1_golden_is_unchanged() -> None:
    plan = make_plan("1").validated()
    names = [item.name for item in dataclasses.fields(TriageReplayPlan)]
    check(
        names
        == [
            "expected_targets",
            "prepared_results",
            "filter_results",
            "group_results",
            "prior_triage_results",
            "roles",
            "topic_allocations",
            "mode",
            "replay_context_result",
        ],
        "plan fields are unchanged",
    )
    check(plan.prepared_results == (ResultRef("a-prepared", "prepared", "1"),), "p")
    check(
        plan.filter_results == (ResultRef("a-filter_result", "filter_result", "1"),),
        "f",
    )
    check(
        plan.group_results == (ResultRef("a-group_result", "group_result", "1"),), "g"
    )
    check(plan.expected_targets == (VersionRef("source", "source-1", "v1"),), "target")
    check(plan.prior_triage_results == (), "no prior results")
    check(plan.mode.value == "replay", "mode value")
    check(
        plan.replay_context_result
        == ResultRef("context-1", "working_context_snapshot", "1"),
        "context ref",
    )
    check(plan.roles[0].role.value == "new-source", "role value")
    check(plan.topic_allocations[0].allocation_key == "allocation-0", "allocation")


def test_v1_plan_keeps_old_ref_shape_without_check() -> None:
    # The composition fixture uses kind "prepared_record". Construction and
    # validated() must still accept it, as before C0-17f.
    plan = make_plan(
        "1", prepared_results=(ResultRef("prepared-1", "prepared_record", "1"),)
    )
    check(plan.validated() == plan, "legacy-shaped plan is still valid")


def test_mixed_versions_are_refused() -> None:
    text = "triage plan source versions must not be mixed"
    for position, (_kind, field) in enumerate(FAMILY):
        versions = ["1", "1", "1"]
        versions[position] = "2"
        changes = {}
        for index, (kind, name) in enumerate(FAMILY):
            changes[name] = (ResultRef(f"a-{kind}", kind, versions[index]),)
        plan = make_plan("1", **changes)
        check(field in changes, "field is part of the mix")
        refuses(plan, text)
        check(plan.validated() == plan, "construction path stays as before")
    two_in_one = make_plan(
        "1",
        prepared_results=(
            ResultRef("p-1", "prepared", "1"),
            ResultRef("p-2", "prepared", "2"),
        ),
    )
    refuses(two_in_one, text)


def test_unknown_and_malformed_versions_are_refused() -> None:
    text = "triage plan source version is unsupported"
    for bad in ("3", "9", "02", "2.0", " 2", "2 ", "v2", "@2", "1,2", "٢"):
        refuses(make_plan(bad), text)
    refuses(
        make_plan("2", group_results=(ResultRef("a-g", "group_result", "3"),)), text
    )
    refuses(
        make_plan(
            "1",
            prepared_results=(
                ResultRef("p-1", "prepared", "1"),
                ResultRef("p-3", "prepared", "3"),
            ),
        ),
        text,
    )


def test_downgrade_and_upgrade_confusion_is_refused() -> None:
    # A triage_input@2 name is not a family version.
    refuses(
        make_plan("1", prepared_results=(ResultRef("a-p", "triage_input", "2"),)),
        "triage plan source result kind is invalid",
    )
    # A filter ref cannot stand in for a prepared ref at the same version.
    for version in ("1", "2"):
        refuses(
            make_plan(
                version,
                prepared_results=(ResultRef("a-p", "filter_result", version),),
            ),
            "triage plan source result kind is invalid",
        )
    # One result identity cannot appear as @1 and as @2 in the same plan.
    with pytest.raises(ValueError, match="result identities must be unique"):
        make_plan(
            "1",
            filter_results=(
                ResultRef("same", "filter_result", "1"),
                ResultRef("same", "filter_result", "2"),
            ),
        )
    with pytest.raises(ValueError, match="result identities must be unique"):
        make_plan(
            "1",
            prepared_results=(ResultRef("same", "prepared", "1"),),
            group_results=(ResultRef("same", "group_result", "2"),),
        )
    # The version is exact: a @2 plan is never reported as @1 or reverse.
    check(make_plan("2").source_version() != "1", "@2 is not @1")
    check(make_plan("1").source_version() != "2", "@1 is not @2")


def test_duplicate_refs_are_refused() -> None:
    for version in ("1", "2"):
        for _kind, field in FAMILY:
            ref = getattr(make_plan(version), field)[0]
            with pytest.raises(ValueError, match="bindings must be unique"):
                make_plan(version, **{field: (ref, ref)})
    with pytest.raises(ValueError, match="result identities must be unique"):
        make_plan(
            "2",
            filter_results=(ResultRef("a-prepared", "filter_result", "2"),),
        )


def test_plan_is_frozen_and_validated_copy_is_detached() -> None:
    plan = make_plan("2")
    probe = make_plan("2")
    with pytest.raises(FrozenInstanceError):
        probe.prepared_results = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        probe.mode = TriageMode.LIVE  # type: ignore[misc]
    check(probe == plan, "failed writes leave the plan unchanged")
    check(isinstance(plan.prepared_results, tuple), "refs are an immutable tuple")
    with pytest.raises(FrozenInstanceError):
        plan.prepared_results[0].schema_version = "1"  # type: ignore[misc]
    before = (plan.prepared_results, plan.filter_results, plan.group_results)
    plan.source_version()
    checked = plan.validated()
    after = (plan.prepared_results, plan.filter_results, plan.group_results)
    check(before == after, "checks do not change the plan")
    check(checked is not plan, "validated returns a new plan")
    check(
        checked.prepared_results[0] is not plan.prepared_results[0],
        "validated rebuilds each ref",
    )

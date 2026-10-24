"""Provisional C0-00 header, limits and transition identity (golden)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import canonical_json_bytes
from msgloom.a2_kedro.contracts.header import (
    LIMITS,
    WIRE_PROFILE,
    StageHeader,
    approved_pairs,
)
from msgloom.a2_kedro.contracts.schema_ids import (
    HISTORICAL_READ_ONLY,
    STAGE_SCHEMAS,
)
from tests.a2_kedro.helpers import accepted_ref, check, stage_identity, transition_for

GOLDEN = Path(__file__).parent / "golden" / "c0_00_provisional.json"


def golden() -> dict[str, Any]:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_golden_is_labeled_provisional() -> None:
    data = golden()
    check(data["status"] == "PROVISIONAL_RESEARCH_NOT_PRODUCTION", "label")
    check(data["profile"] == WIRE_PROFILE, "profile")
    check(data["limits"] == LIMITS, "limits")


def test_every_approved_pair_matches_its_golden_header() -> None:
    expected = golden()["headers"]
    check(
        set(expected) == {f"{k}@{v}" for k, v in approved_pairs().items()},
        "golden covers exactly the approved pairs",
    )
    for kind, version in approved_pairs().items():
        header = StageHeader(kind=kind, version=version)
        row = expected[f"{kind}@{version}"]
        data = canonical_json_bytes(header.model_dump(mode="json"))
        check(data.decode() == row["canonical"], "canonical bytes")
        check(header.digest() == row["digest"], "header digest")


def test_unapproved_pairs_are_rejected() -> None:
    for kind, version in (
        ("prepared", "1"),
        ("prepared", "3"),
        ("unknown_kind", "1"),
        ("triage_input", "1"),
    ):
        with pytest.raises(ValueError, match="not approved"):
            StageHeader(kind=kind, version=version)
    check(("prepared", "1") in HISTORICAL_READ_ONLY, "v1 stays read-only")
    check(STAGE_SCHEMAS["prepared"] == "2", "prepared@2 is the new version")
    check(approved_pairs()["triage_input"] == "2", "triage_input@2 header")


def test_wrong_profile_or_extra_field_is_rejected() -> None:
    with pytest.raises(ValueError):
        StageHeader.model_validate(
            {"kind": "prepared", "version": "2", "profile": "other"}
        )
    with pytest.raises(ValueError):
        StageHeader.model_validate({"kind": "prepared", "version": "2", "extra": "x"})


def test_transition_batch_identity_matches_golden() -> None:
    batch = (transition_for(1, "c"), transition_for(1, "d"))
    kw: dict[str, Any] = {
        "stage_kind": "prepared_transitions",
        "schema_version": "2",
        "selected": (),
        "upstream": (accepted_ref("1"),),
    }
    row = golden()["transition_batch"]
    ordered = stage_identity(transitions=batch, **kw).logical_key()
    flipped = stage_identity(transitions=batch[::-1], **kw).logical_key()
    check(ordered == row["ordered_keys"], "ordered batch key")
    check(flipped == row["reversed_keys"], "reversed batch key")
    check(ordered != flipped, "order is part of the identity")

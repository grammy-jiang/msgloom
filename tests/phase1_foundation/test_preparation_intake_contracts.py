"""Bounded immutable intake data must account for each exact admitted entry."""

import json

import pytest
from pydantic import ValidationError


def test_codec_roundtrip_preserves_transition_scope_and_held_reason():
    from msgloom.preparation_pipeline.intake_codec import PreparationIntakeWorksetCodec
    from msgloom.preparation_pipeline.intake_models import IntakeTransition
    from tests.phase1_foundation import intake_helpers as h

    value = h.workset()
    transition = IntakeTransition(
        entry=h.entry(),
        fact_id="f" * 64,
        transition_kind="membership_removal",
        resource_kind="mail_message",
        resource_identity="mail",
        scope_kind="folder",
        scope_identity="folder-one",
    )
    value = value.model_copy(update={"held": (), "transitions": (transition,)})
    codec = PreparationIntakeWorksetCodec()
    payload = codec.encode(value)
    if codec.decode(payload) != value:
        pytest.fail("Typed transition or exact scope was changed")
    with pytest.raises(ValueError):
        codec.decode(json.dumps(json.loads(payload), indent=2).encode())
    with pytest.raises(ValueError):
        codec.decode(payload + b" ")


@pytest.mark.parametrize(
    "mutation",
    [
        "unordered",
        "unaccounted",
        "conflicting",
        "outside_cut",
        "cutoff_digest",
        "foreign_catalog",
        "empty",
        "oversized",
        "bad_result_kind",
        "unknown_field",
        "bad_reason",
        "boolean_sequence",
        "genesis_digest",
    ],
)
def test_workset_rejects_unsafe_or_unbounded_contract(mutation):
    from msgloom.preparation_pipeline.intake_models import PreparationIntakeWorkset
    from tests.phase1_foundation import intake_helpers as h

    value = h.workset()
    data = value.model_dump(mode="json")
    ref = h.entry(8).model_dump(mode="json")
    if mutation == "unordered":
        data["entries"] = [ref, data["entries"][0]]
    elif mutation == "unaccounted":
        data["held"] = []
    elif mutation == "conflicting":
        data["held"] *= 2
    elif mutation == "outside_cut":
        data["previous"] = {
            "last_release_entry_seq": 7,
            "last_release_entry_digest": "0" * 64,
        }
    elif mutation == "cutoff_digest":
        data["cutoff"]["last_release_entry_digest"] = "e" * 64
    elif mutation == "foreign_catalog":
        data["entries"][0]["catalog"]["catalog_identity"] = "foreign"
    elif mutation == "empty":
        data["entries"] = []
        data["held"] = []
    elif mutation == "oversized":
        data["entries"] *= 1025
    elif mutation == "bad_result_kind":
        data["selections"] = [
            {
                "entry": data["entries"][0],
                "result": {
                    "result_id": "secret",
                    "kind": "prepared",
                    "schema_version": "1",
                },
            }
        ]
        data["held"] = []
    elif mutation == "unknown_field":
        data["provider_body"] = "must not enter neutral ledger"
    elif mutation == "bad_reason":
        data["held"][0]["reason"] = "https://download.invalid/token"
    elif mutation == "boolean_sequence":
        data["previous"]["last_release_entry_seq"] = True
    else:
        data["previous"]["last_release_entry_digest"] = "0" * 64
    with pytest.raises(ValidationError):
        PreparationIntakeWorkset.model_validate_json(json.dumps(data), strict=True)


def test_forged_model_copy_is_revalidated_at_codec_boundary():
    from msgloom.preparation_pipeline.intake_codec import PreparationIntakeWorksetCodec
    from tests.phase1_foundation import intake_helpers as h

    forged = h.workset().model_copy(update={"held": ()})
    with pytest.raises((TypeError, ValueError)):
        PreparationIntakeWorksetCodec().encode(forged)

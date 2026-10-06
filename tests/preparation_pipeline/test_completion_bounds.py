"""Keep complete replay manifests within the frozen producer output bound."""

from dataclasses import replace
from functools import partial

import pytest

from msgloom.contracts import ResultRef, TerminalStatus
from msgloom.persistence import DependencyNotReadyError, intake_store
from msgloom.preparation import DocumentFormat, DocumentLocation
from msgloom.sources import CollectedBody, ContentKind
from msgloom.sources._snapshot import capture_selection
from tests.phase1_foundation import intake_completion_helpers as c
from tests.phase1_foundation import intake_helpers as h
from tests.preparation_pipeline.helpers import profiles


@pytest.mark.parametrize("count", [513, 1024])
def test_full_large_workset_keeps_every_accepted_output(tmp_path, count, monkeypatch):
    """Disjoint real replay plans must finalize the complete admitted cut."""
    store = h.store(tmp_path / "neutral.db")
    try:
        monkeypatch.setattr(
            h, "processing_claim", partial(h.processing_claim, lease=180)
        )
        value, saved, owner, selections = c.admit(store, count=count)
        refs = []
        for start in range(0, count, 100):
            outcome = c.replay(store, owner, selections[start : start + 100])
            if outcome.status is not TerminalStatus.INCOMPLETE:
                pytest.fail("Fixture did not accept the exact replay plan")
            refs.extend(outcome.result_refs)
        outputs = tuple(refs)
        if len(outputs) != 3 * count:
            pytest.fail("Fixture requires prepared, filter, and group per selection")
        if count == 513:
            with pytest.raises(DependencyNotReadyError):
                store.finalize_preparation_intake_workset(
                    saved.result_id,
                    TerminalStatus.INCOMPLETE,
                    outputs[:-1],
                    claim=owner,
                )
            if not store.list_preparation_intake_worksets(value.scope):
                pytest.fail("An incomplete accepted manifest consumed pending work")
        store.finalize_preparation_intake_workset(
            saved.result_id, TerminalStatus.INCOMPLETE, outputs, claim=owner
        )
        states = store.list_preparation_intake_worksets(value.scope, pending_only=False)
        if len(states) != 1 or states[0].result_refs != outputs:
            pytest.fail("Completion lost or substituted accepted output references")
        if states[0].state != "terminal":
            pytest.fail("Accepted large workset remained pending")
        if store.get_preparation_intake_cursor(value.scope) != value.cutoff:
            pytest.fail("Completion changed the exact admission cursor")
    finally:
        store.close()


def test_output_bound_uses_frozen_selections_before_output_reads(tmp_path):
    """A tiny admitted workset cannot request arbitrarily many output proofs."""
    store = h.store(tmp_path / "neutral.db")
    try:
        value, saved, owner, _ = c.admit(store)
        refs = tuple(ResultRef(f"missing-{i}", "prepared", "1") for i in range(5))
        with pytest.raises(DependencyNotReadyError, match="bounded"):
            store.finalize_preparation_intake_workset(
                saved.result_id, TerminalStatus.COMPLETE, refs, claim=owner
            )
        if not store.list_preparation_intake_worksets(value.scope):
            pytest.fail("Oversized proof erased pending work")
    finally:
        store.close()


@pytest.mark.parametrize("stage", ["scan", "duplicates", "serialization"])
def test_oversized_manifest_rejects_before_reference_work(tmp_path, monkeypatch, stage):
    """Reject five outputs for one body-free selection before caller work."""

    class CallerIdentity(str):
        def encode(self, *args, **kwargs):
            if stage == "scan":
                pytest.fail("Oversized caller references reached shape scanning")
            return super().encode(*args, **kwargs)

        def __hash__(self):
            if stage == "duplicates":
                pytest.fail("Oversized caller references reached duplicate hashing")
            return super().__hash__()

    def reject_serialization(refs):
        pytest.fail("Oversized caller references reached encode_result_refs")

    store = h.store(tmp_path / "neutral.db")
    try:
        value, saved, owner, _ = c.admit(store)
        refs = tuple(
            ResultRef(CallerIdentity(f"missing-{index}"), "prepared", "1")
            for index in range(5)
        )
        if stage == "serialization":
            monkeypatch.setattr(
                intake_store, "encode_result_refs", reject_serialization
            )
        with pytest.raises(DependencyNotReadyError, match="bounded"):
            store.finalize_preparation_intake_workset(
                saved.result_id, TerminalStatus.COMPLETE, refs, claim=owner
            )
        if not store.list_preparation_intake_worksets(value.scope):
            pytest.fail("Oversized caller references consumed pending work")
    finally:
        store.close()


def test_within_count_bound_retains_reference_shape_rejection(tmp_path):
    """A single malformed reference still raises the established shape error."""
    store = h.store(tmp_path / "neutral.db")
    try:
        value, saved, owner, _ = c.admit(store)
        with pytest.raises(ValueError, match="bounded"):
            store.finalize_preparation_intake_workset(
                saved.result_id,
                TerminalStatus.COMPLETE,
                (ResultRef("x" * 2049, "prepared", "1"),),
                claim=owner,
            )
        if not store.list_preparation_intake_worksets(value.scope):
            pytest.fail("Malformed caller reference consumed pending work")
    finally:
        store.close()


def test_body_and_alternate_derived_outputs_fit_exact_bound(tmp_path, monkeypatch):
    """Metadata, primary body, and each alternate body can emit derived bytes."""
    store = h.store(tmp_path / "neutral.db")
    original = h.selection

    def with_bodies(store, token, **kwargs):
        saved = original(store, token, **kwargs)
        payload = store.load_semantic_data(saved.semantic_data_ref)
        body = CollectedBody(
            kind=ContentKind.PLAIN,
            content="Exact body",
            saved_bytes=None,
            location=DocumentLocation(part="body"),
            limitations=(),
        )
        value = capture_selection(
            payload.record.model_copy(
                update={"body": body, "alternate_bodies": (body, body)}
            )
        )
        result = replace(
            saved,
            result_id=saved.result_id + "-bodies",
            source_versions=(value.source, value.selection),
            semantic_data_ref=store.semantic_reference(
                saved.result_id + "-bodies-data", "collected_selection", "1", value
            ),
        )
        store.append_result_with_data(result, value, claim=token)
        return result

    try:
        with monkeypatch.context() as patch:
            patch.setattr(h, "selection", with_bodies)
            value, saved, owner, selections = c.admit(store)
        outcome = c.replay(
            store,
            owner,
            selections,
            parser_profiles=profiles(DocumentFormat.JSON, DocumentFormat.TEXT),
        )
        if (
            len(outcome.result_refs) != 7
            or outcome.status is not TerminalStatus.COMPLETE
        ):
            pytest.fail("Fixture must produce all seven exact output references")
        store.finalize_preparation_intake_workset(
            saved.result_id, outcome.status, outcome.result_refs, claim=owner
        )
        if store.list_preparation_intake_worksets(value.scope):
            pytest.fail("Complete derived output manifest remained pending")
    finally:
        store.close()

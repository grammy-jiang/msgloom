"""Full captures cannot publish through an uncommitted equivalent pin."""

import pytest

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook._email_handoff import (
    primary_projection,
    semantic_digest,
)
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from tests._mail_provisional import LATER, capture, prepare, promote
from tests.source_reader.release_mail_helpers import (
    mail_catalog as mail_catalog,  # noqa: PLC0414 - fixture registration
)
from tests.source_reader.release_nonmail_helpers import SOURCE, save_evidence


@pytest.mark.parametrize("component_first", [False, True])
def test_exact_full_capture_waits_for_winning_primary(mail_catalog, component_first):
    saved = mail_catalog
    primary = {"id": "m", "changeKey": "v2"}
    save_evidence(saved, "parent", primary)
    save_evidence(saved, "mime", b"Subject: winner\r\n\r\nbody")
    catalog = Catalog(f"sqlite:///{saved['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        validated = prepare(store, "winner")

        def component():
            return store.set_surface(
                run_id="winner",
                message_id="m",
                surface="mime",
                status="acquired",
                observed_at=LATER,
                evidence_id="mime",
                selection_id="selected",
                resource_version=semantic_digest(primary_projection(primary)),
                parent_evidence_id="parent",
                profile_version="outlook-mail-full-v1",
            )

        if component_first:
            component()
        capture(store, "winner", primary, evidence="parent", selection="selected")
        if not component_first:
            component()
        if store.get_surfaces(message_id="m"):
            pytest.fail("Full component escaped provisional primary authority")
        promote(store, validated)
        if (
            store.get_surfaces(message_id="m").get("mime", {}).get("evidence_id")
            != "mime"
        ):
            pytest.fail("Winning exact primary did not apply its retained Full capture")
    finally:
        catalog.close()


def test_late_losing_equivalent_selection_cannot_publish_components(mail_catalog):
    saved = mail_catalog
    primary = {"id": "m", "changeKey": "same"}
    save_evidence(saved, "parent", primary)
    save_evidence(saved, "late-mime", b"losing bytes")
    catalog = Catalog(f"sqlite:///{saved['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        winner = prepare(store, "winner")
        loser = prepare(store, "loser")
        capture(store, "winner", primary, evidence="parent")
        promote(store, winner)
        capture(
            store, "loser", primary, evidence="parent", selection="loser", when=LATER
        )
        outcome = store.set_surface(
            run_id="loser",
            message_id="m",
            surface="mime",
            status="acquired",
            observed_at=LATER,
            evidence_id="late-mime",
            selection_id="loser",
            resource_version=semantic_digest(primary_projection(primary)),
            parent_evidence_id="parent",
            profile_version="outlook-mail-full-v1",
        )
        if outcome.fact is not None or store.get_surfaces(message_id="m"):
            pytest.fail("Losing equivalent primary used the winner's component rights")
        with pytest.raises(RuntimeError, match="displaced"):
            promote(store, loser)
    finally:
        catalog.close()


def test_late_independent_component_does_not_get_overwritten_by_delta() -> None:
    """A winning cursor does not grant a stale component replacement right."""
    catalog = Catalog("sqlite:///:memory:")
    store = OutlookMailStore(catalog, source_id="source")
    primary = {"id": "m", "subject": "same"}
    try:
        store.record_message(
            run_id="seed",
            kind="discovery",
            message=primary,
            evidence_id=None,
            observed_at="2026-10-01T00:00:00+00:00",
        )
        validated = prepare(store, "delta")
        pending = capture(store, "delta", primary)
        store.set_surface(
            run_id="delta",
            message_id="m",
            surface="discovery",
            status="acquired",
            evidence_id=None,
            observed_at="2026-10-01T00:00:00+00:00",
            resource_version=pending.fact.source_state_key,
        )
        store.set_surface(
            run_id="independent",
            message_id="m",
            surface="discovery",
            status="acquired",
            evidence_id=None,
            observed_at="2026-10-02T00:00:00+00:00",
            profile_version="newer",
            resource_version=pending.fact.source_state_key,
        )
        before = store.get_surfaces(message_id="m")
        if before["discovery"]["profile_version"] != "newer":
            pytest.fail("Independent component did not establish newer state")
        promote(store, validated)
        if store.get_surfaces(message_id="m") != before:
            pytest.fail("Earlier delta component replaced newer independent state")
    finally:
        catalog.close()


def test_later_causal_delta_owns_surface_even_with_earlier_observation_time() -> None:
    """A newer accepted cursor can apply an older-clock observation it owns."""
    from tests._mail_provisional import WHEN

    catalog = Catalog("sqlite:///:memory:")
    store = OutlookMailStore(catalog, source_id="source")
    try:
        old = prepare(store, "first", when=LATER)
        old_primary = capture(
            store, "first", {"id": "m", "changeKey": "v1"}, when=LATER
        )
        store.set_surface(
            run_id="first",
            message_id="m",
            surface="discovery",
            status="acquired",
            evidence_id=None,
            observed_at=LATER,
            resource_version=old_primary.fact.source_state_key,
        )
        promote(store, old)
        new = prepare(store, "second", when=WHEN)
        new_primary = capture(
            store, "second", {"id": "m", "changeKey": "v2"}, when=WHEN
        )
        store.set_surface(
            run_id="second",
            message_id="m",
            surface="discovery",
            status="acquired",
            evidence_id=None,
            observed_at=WHEN,
            resource_version=new_primary.fact.source_state_key,
        )
        promote(store, new)
        current = store.get_surfaces(message_id="m").get("discovery")
        if current is None or current["observed_at"] != WHEN:
            pytest.fail("Winning new cursor could not replace prior owned surface")
    finally:
        catalog.close()


def test_independent_component_clears_prior_delta_ownership() -> None:
    """A new cursor cannot use an old ownership pin to rewind later Full state."""
    from tests._mail_provisional import WHEN

    catalog = Catalog("sqlite:///:memory:")
    store = OutlookMailStore(catalog, source_id="source")
    try:
        original = prepare(store, "first", when=WHEN)
        first = capture(store, "first", {"id": "m", "changeKey": "v1"}, when=WHEN)
        store.set_surface(
            run_id="first",
            message_id="m",
            surface="discovery",
            status="acquired",
            observed_at=WHEN,
            evidence_id=None,
            resource_version=first.fact.source_state_key,
        )
        promote(store, original)
        store.set_surface(
            run_id="full",
            message_id="m",
            surface="discovery",
            status="acquired",
            observed_at=LATER,
            evidence_id=None,
            profile_version="independent-newer",
            resource_version=first.fact.source_state_key,
        )
        expected = store.get_surfaces(message_id="m")
        if expected["discovery"]["profile_version"] != "independent-newer":
            pytest.fail("Independent capture did not become effective")
        second = prepare(store, "second", when=WHEN)
        second_fact = capture(
            store, "second", {"id": "m", "changeKey": "v2"}, when=WHEN
        )
        store.set_surface(
            run_id="second",
            message_id="m",
            surface="discovery",
            status="acquired",
            observed_at=WHEN,
            evidence_id=None,
            resource_version=second_fact.fact.source_state_key,
        )
        promote(store, second)
        if store.get_surfaces(message_id="m") != expected:
            pytest.fail("Stale delta reused old owner to rewind newer independent Full")
    finally:
        catalog.close()


def test_same_version_full_before_delta_commit_keeps_discovery_component() -> None:
    """Deferred Delta may publish its own discovery even after matching Full."""
    from message_ingest.acquisition.handoff import AcquisitionStream
    from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
    from tests._mail_provisional import WHEN

    catalog = Catalog("sqlite:///:memory:")
    store = OutlookMailStore(catalog, source_id="source")
    resource = {"id": "m", "parentFolderId": "inbox", "changeKey": "v1"}
    try:
        pending = prepare(store, "delta", when=WHEN)
        original = capture(store, "delta", resource, when=WHEN)
        store.set_surface(
            run_id="delta",
            message_id="m",
            surface="discovery",
            status="acquired",
            evidence_id=None,
            observed_at=WHEN,
            resource_version=original.fact.source_state_key,
        )
        store.record_message(
            run_id="full",
            message=resource,
            kind="detail",
            evidence_id=None,
            observed_at=LATER,
        )
        if store.get_surfaces(message_id="m").get("discovery") is not None:
            pytest.fail("Fixture unexpectedly provided independent discovery")
        promote(store, pending)
        ledger = AcquisitionHandoffStore(catalog)
        entries = ledger.list_release_entries(
            "source",
            AcquisitionStream.OUTLOOK_MAIL,
            after_seq=0,
            limit=100,
        )
        selected = [
            fact
            for entry in entries
            for fact in ledger.load_release_facts(entry["release_entry_seq"])
            if fact.resource_kind == "message_surface"
            and fact.resource_identity == "m"
            and fact.component_kind == "discovery"
            and fact.run_id == "delta"
        ]
        if len(selected) != 1:
            pytest.fail("Deferred Delta dropped its exact same-version discovery")
        if store.get_surfaces(message_id="m").get("discovery") is None:
            pytest.fail("Deferred Delta failed to materialize its discovery surface")
    finally:
        catalog.close()

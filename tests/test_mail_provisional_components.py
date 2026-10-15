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

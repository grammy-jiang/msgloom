"""Guard Mail authority publication after A/B/A exact-capture reapplication."""

import pytest

from message_ingest.acquisition.handoff import AcquisitionStream, StorageRelation
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from tests._mail_provisional import prepare, promote
from tests.source_reader.authority_release_helpers import CURRENT, MESSAGE
from tests.source_reader.release_mail_helpers import mail_catalog as _mail_catalog
from tests.source_reader.release_nonmail_helpers import SOURCE, save_evidence

mail_catalog = _mail_catalog


def test_mail_authority_preserves_advanced_a_b_a_exact_capture(mail_catalog) -> None:
    """A new advanced fact cannot be suppressed by its displaced-state pin."""
    saved = mail_catalog
    a = {**MESSAGE, "changeKey": "A"}
    b = {**MESSAGE, "changeKey": "B"}
    save_evidence(saved, "exact-a", {"value": [a]})
    save_evidence(saved, "exact-b", {"value": [b]})
    catalog = Catalog(f"sqlite:///{saved['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        validated = prepare(store, "same-authority-run", when=CURRENT)
        first = store.record_message(
            run_id="same-authority-run",
            message=a,
            kind="delta",
            evidence_id="exact-a",
            observed_at=CURRENT,
        )
        second = store.record_message(
            run_id="same-authority-run",
            message=b,
            kind="delta",
            evidence_id="exact-b",
            observed_at=CURRENT,
        )
        latest = store.record_message(
            run_id="same-authority-run",
            message=a,
            kind="delta",
            evidence_id="exact-a",
            observed_at=CURRENT,
        )
        if (
            first.fact.fact_id == latest.fact.fact_id
            or second.fact.fact_id == latest.fact.fact_id
            or latest.storage_relation is not StorageRelation.ADVANCED
            or latest.fact.revalidated_fact_id != second.fact.fact_id
        ):
            pytest.fail("Fixture did not enter advanced exact-capture reapplication")
        ledger = AcquisitionHandoffStore(catalog)
        with catalog.writer_session() as writer:
            current = ledger.current_effective_state(writer, latest.fact.effective_key)
            if current is not None:
                pytest.fail(
                    "Provisional A/B/A became effective before cursor ownership"
                )
        promote(store, validated)
        rows = ledger.list_release_entries(
            SOURCE, AcquisitionStream.OUTLOOK_MAIL, after_seq=0, limit=100
        )
        facts = [
            fact
            for row in rows
            for fact in ledger.load_release_facts(row["release_entry_seq"])
            if fact.resource_kind == "message"
        ]
        if len(facts) != 1 or facts[0].fact_id != latest.fact.fact_id:
            pytest.fail("Mail authority failed to release current advanced A fact")
    finally:
        catalog.close()

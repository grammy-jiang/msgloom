"""Small real-writer fixtures for Mail provisional authority tests."""

from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
)
from message_ingest.sync.microsoft.outlook.email.promotion import (
    ValidatedMailDeltaRun,
    promote_validated_mail_delta,
)

WHEN = "2026-10-01T00:00:00+00:00"
LATER = "2026-10-02T00:00:00+00:00"


def prepare(store, run, *, folder="inbox", when=WHEN):
    """Capture the original generation and stage an exact native handoff."""
    checkpoints = OutlookDeltaCheckpointStore(store.catalog, store.source_id)
    baseline = checkpoints.get_delta_start(folder)[1]
    store.upsert_folder(
        folder={"id": folder}, run_id=run, evidence_id=None, observed_at=when
    )
    store.write_folder_snapshot_candidate(
        run_id=run, observed_at=when, evidence_id=None
    )
    checkpoints.write_candidate(
        run_id=run,
        folder_id=folder,
        delta_link=f"cursor-{run}",
        observed_at=when,
        baseline_identity=baseline,
    )
    return ValidatedMailDeltaRun(run, frozenset({folder}), False, frozenset({folder}))


def promote(store, validated):
    """Exercise the public atomic promotion boundary."""
    return promote_validated_mail_delta(
        store.catalog, source_id=store.source_id, validated=validated
    )


def capture(
    store, run, message, *, evidence=None, when=WHEN, scope="inbox", selection=None
):
    """Use explicit original scope, independently of current parent metadata."""
    return store.record_message(
        run_id=run,
        message=message,
        kind="delta",
        evidence_id=evidence,
        observed_at=when,
        authority_scope=scope,
        selection_id=selection,
    )

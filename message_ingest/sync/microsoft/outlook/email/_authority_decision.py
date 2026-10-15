"""Seal Mail promotion inputs and make exact transaction retries read-only."""

import json
from typing import Any, cast

from sqlalchemy import Table, select

from message_ingest.catalog.models.microsoft.outlook._email_authority import (
    MailAuthorityDecision as Decision,
)
from message_ingest.catalog.models.microsoft.outlook._email_authority import (
    MailAuthorityObservation as Observation,
)
from message_ingest.catalog.models.microsoft.outlook.email import (
    DeltaCheckpointCandidate,
    FolderDeltaCheckpointCandidate,
    MailDeltaCandidateBase,
    MailFolderDeltaCandidateBase,
    MailFolderSighting,
    MailFolderSnapshotCandidate,
    MessagePresenceCandidate,
    MessagePresenceSighting,
)
from message_ingest.catalog.stores.microsoft.outlook._email_handoff import (
    semantic_digest,
)


def input_digest(session, source, run, authority, validated=None):
    """Hash original retained inputs, excluding commit timestamps and row IDs."""
    models: list[Any] = [Observation]
    if authority == "message_delta":
        models.extend(
            (
                DeltaCheckpointCandidate,
                MailDeltaCandidateBase,
                MailFolderSnapshotCandidate,
                MailFolderSighting,
                MessagePresenceCandidate,
                MessagePresenceSighting,
            )
        )
    else:
        models.extend((FolderDeltaCheckpointCandidate, MailFolderDeltaCandidateBase))
    material = []
    for model in models:
        table = cast(Table, model.__table__)
        columns = [
            col for col in table.columns if col.name not in {"id", "committed_at"}
        ]
        query = select(*columns).where(
            table.c.source_id == source, table.c.run_id == run
        )
        if model is Observation:
            query = query.where(table.c.authority_kind == authority)
        values = [list(row) for row in session.execute(query)]
        material.append((table.name, sorted(values, key=str)))
    if validated is not None:
        material.append(
            (sorted(validated.expected_folder_ids), validated.reconcile_messages)
        )
    return semantic_digest(material)


def replay(session, source, run, authority, digest):
    """Return a sealed result only after caller validates cursor ownership."""
    row = session.get(Decision, (source, run, authority))
    if row is None:
        return None
    if row.input_digest != digest:
        raise RuntimeError("Mail authority input set changed after sealing")
    return json.loads(row.payload)["result"]


def seal(session, source, run, authority, digest, result, applied):
    """Persist the exact application set with the original transaction."""
    session.add(
        Decision(
            source_id=source,
            run_id=run,
            authority_kind=authority,
            input_digest=digest,
            payload=json.dumps(
                {
                    "result": result,
                    "applied": sorted(
                        {fact.fact_id for fact in applied.values()}
                        | session.info.get("mail_authority_applied", set())
                    ),
                },
                sort_keys=True,
            ),
        )
    )

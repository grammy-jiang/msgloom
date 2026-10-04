"""Immutable Contacts facts, distinct from mutable merged contact state."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind,
    AcquisitionStream,
    FactSpec,
    SourceVersionLocator,
    StorageRelation,
    canonical_json,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.items.microsoft.contacts import ContactFolderItem, ContactItem

_TRANSPORT_FIELDS = frozenset(
    {
        "@odata.context",
        "@odata.nextLink",
        "@odata.deltaLink",
        "@microsoft.graph.downloadUrl",
    }
)


def stage_contacts_fact(
    writer: Session,
    handoff: AcquisitionHandoffStore,
    *,
    source_id: str,
    spider_name: str,
    item: ContactFolderItem | ContactItem,
    outcome: Literal["created", "changed", "unchanged", "stale"] = "created",
    ordinal: int | None = None,
) -> None:
    """
    Stage the exact provider projection in the caller's writer transaction.

    Snapshot facts reference immutable canonical evidence. Sparse delta facts
    reference the ordered observation by ``[source, folder, run, ordinal]``;
    they never read or serialize a merged :class:`ContactRecord`. The ordinal
    disambiguates repeated contact IDs even within one response. Only Task 9's
    winning promotion may apply their authority-staged state to the ledger.
    """
    if isinstance(item, ContactFolderItem):
        kind, identity = "contact_folder", item.folder_id
        scope_kind, scope_identity = "contacts_inventory", "root"
        fact_kind = AcquisitionFactKind.CONTROL_CONTEXT
        # The folder primary key excludes its mutable parent. Keep parent
        # metadata in the hashed projection and exact evidence; including it
        # in the effective identity would leave moved-folder facts eligible.
        parent_kind = None
        parent_identity = None
    else:
        kind, identity = "contact", item.contact_id
        scope_kind = "contacts_collection"
        scope_identity = (
            "default" if item.is_default_scope else f"folder:{item.folder_id}"
        )
        fact_kind = AcquisitionFactKind.RESOURCE_OBSERVATION
        parent_kind = "contact_folder" if item.folder_id else None
        parent_identity = item.folder_id
    projection = {
        "resource_kind": kind,
        "resource_identity": identity,
        "scope": scope_identity,
        "raw": {
            key: value
            for key, value in item.raw.items()
            if key not in _TRANSPORT_FIELDS
        },
    }
    key = hashlib.sha256(
        json.dumps(
            projection,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()
    locator = None
    if item.evidence_id:
        locator = SourceVersionLocator(
            kind="observation" if ordinal is not None else "evidence",
            evidence_id=item.evidence_id,
            resource_identity=identity,
            observation_id=(
                canonical_json([source_id, scope_identity, item.run_id, ordinal])
                if ordinal is not None
                else None
            ),
        )
    relation = (
        StorageRelation.STALE
        if outcome == "stale"
        else StorageRelation.CURRENT_EQUIVALENT
        if outcome == "unchanged"
        else StorageRelation.ADVANCED
    )
    spec = FactSpec(
        source_id=source_id,
        stream=AcquisitionStream.CONTACTS,
        run_id=item.run_id,
        spider_name=spider_name,
        fact_kind=fact_kind,
        resource_kind=kind,
        resource_identity=identity,
        parent_resource_kind=parent_kind,
        parent_resource_identity=parent_identity,
        scope_kind=scope_kind,
        scope_identity=scope_identity,
        provider_observed_at=item.observed_at,
        evidence_id=item.evidence_id,
        source_state_key=key,
        source_version_locator=locator,
        storage_relation=relation,
        provider_order=ordinal,
    )
    if ordinal is not None:
        handoff.stage_authority_fact_in_session(writer, spec)
    else:
        handoff.stage_state_fact_in_session(writer, spec)

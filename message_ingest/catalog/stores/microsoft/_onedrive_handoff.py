"""Derive bounded OneDrive facts inside provider-owned writer transactions."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Literal

from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind,
    AcquisitionStream,
    FactSpec,
    SourceVersionLocator,
    StorageRelation,
    source_state_key,
)
from message_ingest.catalog.models.microsoft.onedrive import OneDriveContentCapture
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.items.microsoft.onedrive import (
    OneDriveContentItem,
    OneDriveDeltaResyncObservationItem,
    OneDriveDriveItem,
    OneDriveItem,
)

if TYPE_CHECKING:
    from message_ingest.catalog import Catalog

type Outcome = Literal["created", "changed", "unchanged", "stale"]


def _relation(outcome: Outcome) -> StorageRelation:
    """Keep unchanged pre-ledger rows outside future-only bootstrap."""
    if outcome == "stale":
        return StorageRelation.STALE
    if outcome == "unchanged":
        return StorageRelation.CURRENT_EQUIVALENT
    return StorageRelation.ADVANCED


def metadata_fact(
    source_id: str,
    spider_name: str,
    item: OneDriveDriveItem | OneDriveItem,
    outcome: Outcome,
) -> FactSpec:
    """
    Pin the sanitized provider observation, never a merged current row.

    The state digest also disambiguates repeated IDs within one evidence page.
    An exact reader matches that digest after the same URL sanitization.
    """
    if not item.run_id:
        raise ValueError("OneDrive handoff requires a logical run_id")
    drive = isinstance(item, OneDriveDriveItem)
    key = source_state_key(item.raw)
    return FactSpec(
        source_id=source_id,
        stream=AcquisitionStream.ONEDRIVE,
        run_id=item.run_id,
        spider_name=spider_name,
        fact_kind=(
            AcquisitionFactKind.CONTROL_CONTEXT
            if drive
            else AcquisitionFactKind.RESOURCE_OBSERVATION
        ),
        resource_kind="onedrive_drive" if drive else "onedrive_item",
        resource_identity=item.id,
        provider_observed_at=item.observed_at,
        evidence_id=item.evidence_id,
        source_state_key=key,
        source_version_locator=(
            SourceVersionLocator(
                kind="evidence",
                evidence_id=item.evidence_id,
                resource_identity=item.id,
                resource_version=key,
            )
            if item.evidence_id
            else None
        ),
        storage_relation=_relation(outcome),
    )


def content_state_key(item: OneDriveContentItem | OneDriveContentCapture) -> str:
    """Hash bytes and version proof independently of capture/run provenance."""
    return source_state_key(
        {
            "content_sha256": item.content_sha256,
            "content_bytes": item.content_bytes,
            "planned_e_tag": item.planned_e_tag,
            "planned_c_tag": item.planned_c_tag,
            "response_e_tag": item.response_e_tag,
        }
    )


def stage_content(
    catalog: Catalog,
    session: Session,
    *,
    source_id: str,
    spider_name: str,
    item: OneDriveContentItem,
    outcome: Outcome,
    previous_key: str | None,
) -> None:
    """
    Stage the exact immutable capture with the latest-content transaction.

    The provider's timestamp decision gates freshness. A change only to the
    metadata-version binding still advances the content component. An
    unchanged pre-ledger capture remains equivalent without inventing history.
    """
    if not item.run_id or not item.evidence_id:
        raise ValueError("OneDrive content handoff requires run and evidence")
    key = content_state_key(item)
    relation = _relation(outcome)
    if outcome != "stale":
        relation = (
            StorageRelation.CURRENT_EQUIVALENT
            if previous_key == key
            else StorageRelation.ADVANCED
        )
    spec = FactSpec(
        source_id=source_id,
        stream=AcquisitionStream.ONEDRIVE,
        run_id=item.run_id,
        spider_name=spider_name,
        fact_kind=AcquisitionFactKind.COMPONENT_OBSERVATION,
        resource_kind="onedrive_content",
        resource_identity=item.item_id,
        parent_resource_kind="onedrive_item",
        parent_resource_identity=item.item_id,
        component_kind="item_content",
        provider_observed_at=item.observed_at,
        evidence_id=item.evidence_id,
        source_state_key=key,
        source_version_locator=SourceVersionLocator(
            kind="content_capture",
            evidence_id=item.evidence_id,
            resource_identity=item.item_id,
            capture_id=item.evidence_id,
            component_kind="item_content",
            resource_version=item.planned_e_tag,
        ),
        storage_relation=relation,
    )
    AcquisitionHandoffStore(catalog).stage_state_fact_in_session(session, spec)


def stage_resync(
    catalog: Catalog,
    session: Session,
    *,
    source_id: str,
    spider_name: str,
    item: OneDriveDeltaResyncObservationItem,
    observation_id: int,
) -> None:
    """Retain exact reset ordering without making partial state effective."""
    spec = metadata_fact(source_id, spider_name, item, "created")
    if not item.evidence_id:
        raise ValueError("OneDrive resync handoff requires evidence")
    spec = replace(
        spec,
        source_version_locator=SourceVersionLocator(
            kind="observation",
            evidence_id=item.evidence_id,
            resource_identity=item.id,
            observation_id=str(observation_id),
        ),
        authority_revision=str(item.base_revision),
        # The immutable observation resolves reset/page/entry ordering exactly.
        provider_order=item.entry_index,
    )
    AcquisitionHandoffStore(catalog).stage_authority_fact_in_session(session, spec)

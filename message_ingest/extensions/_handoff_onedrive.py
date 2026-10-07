"""Validate OneDrive traversal and version-linked content at native idle."""

from datetime import UTC, datetime

from sqlalchemy import select

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    FactRole,
    FactSpec,
    ReleaseEntryKind,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
)
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.onedrive import OneDriveContentCapture
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.spiders.microsoft.onedrive._handoff import discovery_scope


def _evidence(writer, source, evidence_id, purpose=None):
    if not isinstance(evidence_id, str) or not evidence_id:
        return None
    evidence = writer.get(RawHttpEvidence, evidence_id)
    if (
        evidence is None
        or evidence.source_id != source
        or evidence.response_status != 200
        or evidence.error_type is not None
        or (purpose is not None and evidence.purpose != purpose)
    ):
        return None
    return evidence


def _completion(writer, source, spider, proof, scope, purpose):
    if (
        not isinstance(proof, dict)
        or proof.get("source_id") != source
        or proof.get("run_id") != spider.run_id
        or proof.get("scope") != scope
    ):
        return None
    return _evidence(writer, source, proof.get("evidence_id"), purpose)


def onedrive_discovery_group(writer, source, spider):
    """Require both drive and terminal root-page proof for this exact scope."""
    scope = discovery_scope(spider)
    if not spider.handoff_drive_id:
        return None
    for proof, purpose in (
        (spider.handoff_drive, "onedrive-drive"),
        (spider.handoff_completion, "onedrive-root-children-page"),
    ):
        if _completion(writer, source, spider, proof, scope, purpose) is None:
            return None
    return ReleaseGroupSpec(
        source_id=source,
        stream=AcquisitionStream.ONEDRIVE,
        release_kind=ReleaseKind.RESOURCE_SET,
        subject_kind="onedrive_discovery",
        subject_identity=spider.handoff_drive_id,
        owner_run_id=spider.run_id,
        released_at=datetime.now(UTC).isoformat(),
        coverage_kind="complete",
        scope_kind="onedrive_root_inventory",
        scope_identity=scope,
    )


def release_onedrive_content(catalog, writer, source, spider, target):
    """
    Publish one exact persisted capture with matching metadata version proof.

    A successful HTTP response alone is insufficient. The immutable capture
    must name successful metadata evidence and matching nonempty eTags. Facts
    and effective-state freshness are selected in the release transaction.
    Other failed explicit targets do not invalidate this independently proven
    target. No download URL or file body enters the release payload.
    """
    evidence = _completion(
        writer,
        source,
        spider,
        spider.handoff_completions.get(target),
        target,
        "onedrive-content",
    )
    if evidence is None:
        return
    capture = writer.get(OneDriveContentCapture, (source, evidence.evidence_id))
    if (
        capture is None
        or capture.item_id != target
        or not capture.planned_e_tag
        or capture.response_e_tag != capture.planned_e_tag
        or capture.content_sha256 != evidence.response_body_sha256
        or capture.content_bytes != evidence.response_body_bytes
    ):
        return
    metadata = _evidence(writer, source, capture.planned_metadata_evidence_id)
    if metadata is None or metadata.observed_at != capture.planned_metadata_observed_at:
        return
    facts = [
        FactSpec.from_json(payload)
        for payload in writer.scalars(
            select(AcquisitionFact.payload).where(
                AcquisitionFact.source_id == source,
                AcquisitionFact.stream == AcquisitionStream.ONEDRIVE,
                AcquisitionFact.run_id == spider.run_id,
            )
        )
    ]
    members: list[tuple[str, FactRole]] = [
        (fact.fact_id, "component")
        for fact in facts
        if fact.resource_kind == "onedrive_content"
        and fact.resource_identity == target
        and fact.evidence_id == evidence.evidence_id
        and fact.source_version_locator is not None
        and fact.source_version_locator.capture_id == evidence.evidence_id
        and fact.storage_relation in {"advanced", "current_equivalent"}
    ]
    if not members:
        return
    group = ReleaseGroupSpec(
        source_id=source,
        stream=AcquisitionStream.ONEDRIVE,
        release_kind=ReleaseKind.CONTENT_CAPTURE,
        subject_kind="onedrive_item",
        subject_identity=target,
        owner_run_id=spider.run_id,
        released_at=datetime.now(UTC).isoformat(),
        coverage_kind="complete",
    )
    entry = ReleaseEntrySpec(
        resource_kind="onedrive_item",
        resource_identity=target,
        entry_kind=ReleaseEntryKind.COMPONENT,
        facts=tuple(members),
    )
    AcquisitionHandoffStore(catalog).release_effective_group_in_session(
        writer, group, [entry]
    )

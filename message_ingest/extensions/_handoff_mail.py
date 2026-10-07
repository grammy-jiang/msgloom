"""Validate Mail discovery completion before additive scope publication."""

from datetime import UTC, datetime

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    ReleaseGroupSpec,
    ReleaseKind,
)
from message_ingest.acquisition.microsoft.outlook.email.profile import DISCOVERY_V1
from message_ingest.catalog.models.acquisition import RawHttpEvidence


def mail_discovery_group(writer, source, spider):
    """
    Bind current-attempt completion to committed canonical terminal evidence.

    The callback retains the raw item, whose evidence ID the awaited raw
    pipeline canonicalizes in place. A cached capture may belong to an older
    run. Mail discovery rejects JOBDIR, so this reference never crosses a
    scheduler serialization boundary. Native idle supplies the write drain;
    stats and the eventual close reason are not completion proof.
    """
    completion = spider.discovery_completion
    if completion is None:
        return None
    run, scope, coverage, item = completion
    if run != spider.run_id or scope != spider.discovery_scope():
        return None
    evidence = writer.get(RawHttpEvidence, item.evidence_id)
    if (
        evidence is None
        or evidence.source_id != source
        or evidence.response_status != 200
        or evidence.error_type is not None
        or evidence.purpose != "message-list"
    ):
        return None
    return ReleaseGroupSpec(
        source_id=source,
        stream=AcquisitionStream.OUTLOOK_MAIL,
        release_kind=ReleaseKind.RESOURCE_SET,
        subject_kind="mail_discovery",
        subject_identity=spider.target_mailbox or "me",
        owner_run_id=run,
        released_at=datetime.now(UTC).isoformat(),
        coverage_kind=coverage,
        scope_kind="mail_discovery_policy",
        scope_identity=scope,
        profile=DISCOVERY_V1,
        limitation_codes=("max_pages",) if coverage == "truncated" else (),
    )

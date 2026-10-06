"""Validate exact Calendar terminal scope inside the release transaction."""

from datetime import UTC, datetime

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    ReleaseGroupSpec,
    ReleaseKind,
)
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.handoff import AcquisitionReleaseGroup
from message_ingest.spiders.microsoft.outlook.calendar._handoff import traversal_scope


def calendar_traversal_group(writer, source, spider):
    """
    Require canonical terminal evidence bound to the current logical run.

    Window SpiderState retains only primitive completion fields across clean
    JOBDIR shutdown. Inventory remains attempt-local and rejects JOBDIR.
    A cached terminal capture can belong to an older run, but source, purpose,
    and successful persistence must still agree. No absence authority follows.
    """
    completion = spider.handoff_completion
    scope = traversal_scope(spider)
    if (
        not isinstance(completion, dict)
        or completion.get("run_id") != spider.run_id
        or completion.get("scope") != scope
    ):
        return None
    evidence_id = completion.get("evidence_id")
    if not isinstance(evidence_id, str) or not evidence_id:
        return None
    window = spider.name == "outlook_calendar_window"
    purpose = "calendar-window-page" if window else "calendar-inventory-page"
    evidence = writer.get(RawHttpEvidence, evidence_id)
    if (
        evidence is None
        or evidence.source_id != source
        or evidence.response_status != 200
        or evidence.error_type is not None
        or evidence.purpose != purpose
    ):
        return None
    subject = "calendar_window" if window else "calendar_inventory"
    group = ReleaseGroupSpec(
        source_id=source,
        stream=AcquisitionStream.OUTLOOK_CALENDAR,
        release_kind=ReleaseKind.RESOURCE_SET,
        subject_kind=subject,
        subject_identity=spider.calendar_id or "default"
        if window
        else spider.target_mailbox or "me",
        owner_run_id=spider.run_id,
        released_at=datetime.now(UTC).isoformat(),
        coverage_kind="complete",
        scope_kind=subject,
        scope_identity=scope,
    )
    # Completed JOBDIR replay must not rebuild old membership from newer
    # effective state. The original immutable group already owns this scope.
    if writer.get(AcquisitionReleaseGroup, group.release_group_id) is not None:
        return None
    return group

"""Reconstruct a content-only impact through its immutable metadata binding."""

import json

from msgloom.contracts import VersionRef
from msgloom.sources._catalog import encode_parts
from msgloom.sources._mapping import source_time
from msgloom.sources._release_evidence import clean, digest
from msgloom.sources._release_observations import content_capture
from msgloom.sources._release_records import record
from msgloom.sources.handoff_models import SourceVersionLocator
from msgloom.sources.models import SourceEvidenceError, SourceMetadata


def content_parent(fact, evidence, scope):
    """Pin metadata from the named capture without reading any current row."""
    capture = content_capture(evidence.catalog, fact)
    data, saved = evidence.load(capture["planned_metadata_evidence_id"], fact.source_id)
    payload = json.loads(data)
    candidates = payload.get("value", [payload])
    matches = [
        raw
        for raw in candidates
        if isinstance(raw, dict)
        and raw.get("id") == fact.resource_identity
        and raw.get("eTag") == capture["planned_e_tag"]
    ]
    if len(matches) != 1:
        raise SourceEvidenceError("Content metadata association is ambiguous")
    locator = SourceVersionLocator(
        kind="evidence",
        evidence_id=capture["planned_metadata_evidence_id"],
        resource_identity=fact.resource_identity,
        resource_version=digest(clean(matches[0])),
    )
    source = VersionRef(
        "a1_released_source",
        encode_parts(
            fact.source_id,
            fact.stream,
            "onedrive_item",
            fact.resource_identity,
            "-",
            "-",
            "-",
            "-",
        ),
        digest(locator.model_dump(mode="json")),
    )
    value = record(fact, matches[0], saved, scope)
    observed = capture["planned_metadata_observed_at"]
    return value.model_copy(
        update={
            "source": source,
            "semantic_identity": source.identity,
            "observed_at": source_time(observed, observed),
            "metadata": (SourceMetadata(name="resource_kind", value="onedrive_item"),),
        }
    )

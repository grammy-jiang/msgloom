"""Resolve exact fact-owned representations through bounded evidence I/O."""

import hashlib
import json
from typing import Any

from msgloom.contracts import VersionRef
from msgloom.sources._catalog import ReadOnlyCatalog, encode_parts
from msgloom.sources._io import EvidenceFiles
from msgloom.sources._mapping import graph_object
from msgloom.sources._release_observations import observation
from msgloom.sources.handoff_models import ReleasedFact
from msgloom.sources.models import (
    SourceEvidenceError,
    SourceEvidenceLimitError,
    SourceReferenceError,
)


def digest(value: object) -> str:
    """Hash canonical exact locator material independently of release order."""
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def fact_reference(fact: ReleasedFact) -> VersionRef:
    """Pin one representation independently of run and release sequence."""
    locator = fact.source_version_locator
    if locator is None:
        if (
            fact.resource_kind
            not in {"calendar_event_surface", "calendar_series", "message_surface"}
            or fact.evidence_id is not None
            or fact.source_state_key is None
        ):
            raise SourceReferenceError("Released source lacks an immutable locator")
        if fact.stream == "outlook_mail":
            from msgloom.sources._release_mail import outcome

            if outcome(fact)[0] == "acquired":
                raise SourceReferenceError("Acquired Mail component lacks evidence")
        return VersionRef(
            "a1_released_terminal",
            encode_parts(
                fact.source_id,
                fact.stream,
                fact.resource_kind,
                fact.resource_identity,
                fact.component_kind or "-",
            ),
            digest({"state": fact.source_state_key, "reason": fact.transition_reason}),
        )
    material = locator.model_dump(mode="json")
    if fact.fact_kind == "component_observation" and fact.transition_reason is not None:
        material = {"locator": material, "terminal_reason": fact.transition_reason}
    return VersionRef(
        "a1_released_source",
        encode_parts(
            fact.source_id,
            fact.stream,
            fact.resource_kind,
            fact.resource_identity,
            fact.parent_resource_kind or "-",
            fact.parent_resource_identity or "-",
            fact.scope_kind or "-",
            fact.scope_identity or "-",
        ),
        digest(material),
    )


class ReleaseEvidence:
    """Apply an aggregate byte budget and exact ownership to one entry."""

    def __init__(self, catalog: ReadOnlyCatalog, files: EvidenceFiles):
        """Share pinned read resources within one bounded reconstruction."""
        self.catalog = catalog
        self.files = files
        self.remaining = catalog.limits.max_snapshot_bytes
        self.cache: dict[str, tuple[bytes, Any]] = {}

    def load(self, evidence_id: str, source_id: str):
        """Load canonical capture bytes regardless of logical-run ownership."""
        row = self.catalog.evidence(evidence_id)
        if row.source_id != source_id:
            raise SourceEvidenceError("Released evidence belongs to another source")
        if evidence_id not in self.cache:
            self.remaining -= row.response_body_bytes
            if self.remaining < 0:
                raise SourceEvidenceLimitError("Released input exceeds byte budget")
            self.cache[evidence_id] = (self.files.read(row), self.files.reference(row))
        return self.cache[evidence_id]

    @staticmethod
    def validate_locator(fact: ReleasedFact):
        """Reject evidence references that do not belong to this exact fact."""
        locator = fact.source_version_locator
        if locator is None or (
            locator.resource_identity != fact.resource_identity
            or locator.evidence_id != fact.evidence_id
            or locator.component_kind != fact.component_kind
        ):
            raise SourceReferenceError("Released locator ownership mismatch")
        return locator

    def object(self, fact: ReleasedFact) -> tuple[dict[str, Any], Any]:
        """Require fact ownership before selecting a provider object."""
        locator = fact.source_version_locator
        if locator is None or (
            locator.resource_identity != fact.resource_identity
            or locator.evidence_id != fact.evidence_id
            or locator.component_kind != fact.component_kind
        ):
            raise SourceReferenceError("Released locator ownership mismatch")
        if locator.kind not in {"evidence", "observation"}:
            raise SourceReferenceError("Unsupported exact observation locator")
        provider_id = fact.resource_identity
        if fact.stream == "todo":
            try:
                parts = json.loads(provider_id)
            except ValueError:
                raise SourceReferenceError("Invalid To Do resource identity") from None
            if (
                not isinstance(parts, list)
                or not parts
                or any(not isinstance(part, str) or not part for part in parts)
            ):
                raise SourceReferenceError("Invalid To Do resource identity")
            provider_id = parts[-1]
        data, saved = self.load(locator.evidence_id, fact.source_id)
        try:
            payload = json.loads(data)
            if not isinstance(payload, dict):
                raise SourceEvidenceError("Released evidence is not a JSON object")
            if locator.kind == "observation":
                found = observation(self.catalog, fact)
                if fact.stream == "outlook_mail":
                    raw = clean(graph_object(payload, provider_id))
                    if (
                        locator.resource_version
                        and raw.get("changeKey") != locator.resource_version
                    ):
                        raise SourceReferenceError("Mail observation version mismatch")
                    return raw, saved
                raw = json.loads(found["raw"])
                candidates = payload.get("value", [payload])
                if not isinstance(candidates, list) or not isinstance(raw, dict):
                    raise SourceEvidenceError("Invalid observation payload")
                matches = [item for item in candidates if clean(item) == clean(raw)]
                if "entry_index" in found:
                    index = found["entry_index"]
                    if (
                        type(index) is not int
                        or not 0 <= index < len(candidates)
                        or clean(candidates[index]) != clean(raw)
                    ):
                        raise SourceEvidenceError("Observation page position mismatch")
                if not matches or raw.get("id") != provider_id:
                    raise SourceEvidenceError(
                        "Observation does not match saved evidence"
                    )
                return clean(raw), saved
            if fact.stream == "onedrive" and locator.resource_version:
                candidates = payload.get("value", [payload])
                matches = [
                    clean(item)
                    for item in candidates
                    if isinstance(item, dict)
                    and item.get("id") == provider_id
                    and digest(clean(item)) == locator.resource_version
                ]
                if not matches or any(item != matches[0] for item in matches):
                    raise SourceEvidenceError("OneDrive exact state mismatch")
                return matches[0], saved
            return clean(graph_object(payload, provider_id)), saved
        except (ValueError, UnicodeDecodeError, RecursionError):
            raise SourceEvidenceError("Invalid released JSON evidence") from None


def clean(value: Any) -> Any:
    """Exclude preauthenticated URLs from saved selections at every depth."""
    if isinstance(value, dict):
        return {
            key: clean(item)
            for key, item in value.items()
            if key != "@microsoft.graph.downloadUrl"
        }
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value

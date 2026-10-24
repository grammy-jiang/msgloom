"""
Builders that produce real A1 typed evidence for the C0 v2 tests.

Every value here is a real ``ReleasedInput``, ``ReleasedFact``,
``ReleaseEntryRef``, ``CollectedSelection`` or ``PreparationIntakeWorkset``.
No look-alike stub is used. The only reader double is :class:`TypedReader`,
which returns a prepared ``ReleasedInput`` and records every call.
"""

from __future__ import annotations

from datetime import UTC, datetime

from msgloom.contracts import ResultRef, VersionRef
from msgloom.preparation.records import NativeRelationship, PreparedSourceType
from msgloom.preparation_pipeline.intake import _identity
from msgloom.preparation_pipeline.intake_models import (
    IntakeAnchor,
    IntakeSelection,
    PreparationIntakeWorkset,
)
from msgloom.sources import CollectedRecord, ContentKind
from msgloom.sources._snapshot import capture_selection
from msgloom.sources.handoff_models import FactRole, ReleasedFact, ReleaseEntryRef
from msgloom.sources.models import CollectedSelection
from msgloom.sources.release_models import ReleasedInput
from tests.a2_kedro.helpers import CODE, CONFIG, SCOPE, entry, hexd


def collected(name: str) -> CollectedSelection:
    """Return a real exact selection for the synthetic mail ``name``."""
    source = VersionRef("outlook_email", name, "observation-1")
    scope = VersionRef("source_scope", "source", "1")
    when = datetime(2026, 1, 1, tzinfo=UTC)
    record = CollectedRecord(
        source=source,
        source_scope=scope,
        source_type=PreparedSourceType.OUTLOOK_EMAIL,
        semantic_identity=name,
        observed_at=when,
        source_time=when,
        subject=None,
        sender=None,
        author=None,
        recipients=(),
        source_content_kind=ContentKind.JSON,
        source_bytes=None,
        body=None,
        alternate_bodies=(),
        attachments=(),
        relationships=(NativeRelationship(kind="source_scope", target=scope),),
        metadata=(),
        source_locations=(),
        limitations=(),
    )
    return capture_selection(record)


def fact(index: int, role: FactRole) -> ReleasedFact:
    """Return a real released fact with a stable id and ``role``."""
    return ReleasedFact(
        source_id="src-1",
        stream="outlook_mail",
        run_id="run-1",
        spider_name="spider-1",
        fact_kind="resource_observation",
        resource_kind="mail",
        resource_identity=f"r-{index}",
        provider_observed_at="2026-01-01T00:00:00Z",
        storage_relation="advanced",
        fact_id=hexd("abcdef"[index % 6]),
        role=role,
        ordinal=index,
    )


def released(
    seq: int,
    *,
    components: int = 0,
    primary: bool = True,
    reference: ReleaseEntryRef | None = None,
) -> ReleasedInput:
    """Return a real released input with the requested occurrences."""
    roles: list[FactRole] = ["primary"] if primary else []
    roles.extend("component" for _ in range(components))
    return ReleasedInput(
        reference=reference or entry(seq),
        selection=collected(f"p{seq}") if primary else None,
        components=tuple(collected(f"c{seq}-{i}") for i in range(components)),
        facts=tuple(fact(i, role) for i, role in enumerate(roles)),
    )


def selection_of(
    value: ReleasedInput, ordinal: int, *, config: str = CONFIG
) -> IntakeSelection:
    """Return the Intake selection that Intake derives for ``ordinal``."""
    members = tuple((item.fact_id, item.role) for item in value.facts)
    identity = _identity(
        "selection",
        [
            SCOPE.claim_key(),
            value.reference.model_dump(mode="json"),
            members,
            config,
            CODE,
            ordinal,
        ],
    )
    return IntakeSelection(
        entry=value.reference,
        result=ResultRef(identity, "collected_selection", "1"),
    )


def workset_of(
    value: ReleasedInput, selections: tuple[IntakeSelection, ...]
) -> PreparationIntakeWorkset:
    """Return a valid one-entry workset that selects ``selections``."""
    ref = value.reference
    return PreparationIntakeWorkset(
        scope=SCOPE,
        previous=IntakeAnchor(),
        cutoff=IntakeAnchor(
            last_release_entry_seq=ref.release_entry_seq,
            last_release_entry_digest=ref.entry_digest,
        ),
        entries=(ref,),
        selections=selections,
        configuration_version=CONFIG,
        code_version=CODE,
    )


class TypedReader:
    """Reader double that returns one prepared real ``ReleasedInput``."""

    def __init__(self, value: object) -> None:
        self.value = value
        self.calls: list[ReleaseEntryRef] = []

    async def read_entry(self, entry: ReleaseEntryRef) -> object:
        """Record the call and return the prepared answer."""
        self.calls.append(entry)
        return self.value

"""Real persistence and immutable selection fixtures for intake tests."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ResultRef,
    ResultSchemaRegistry,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence.store import Phase1Store
from msgloom.preparation.records import NativeRelationship, PreparedSourceType
from msgloom.preparation_pipeline.intake_models import (
    HeldIntakeEntry,
    IntakeAnchor,
    IntakeScope,
    IntakeSelection,
    PreparationIntakeWorkset,
)
from msgloom.sources import CollectedRecord, ContentKind
from msgloom.sources._snapshot import capture_selection
from msgloom.sources.handoff_models import A1CatalogIdentity, ReleaseEntryRef, Stream

CATALOG = A1CatalogIdentity(catalog_identity="catalog-one", schema_version=1)


def scope(stream: Stream = "outlook_mail", consumer="daily"):
    """Return a stable source/consumer scope."""
    return IntakeScope(
        catalog=CATALOG,
        source_id="source",
        stream=stream,
        consumer_id=consumer,
    )


def entry(seq=7, catalog=CATALOG):
    """Return a hand-specified immutable admission anchor."""
    return ReleaseEntryRef(
        catalog=catalog,
        release_entry_seq=seq,
        entry_digest=f"{seq:064x}",
    )


def workset(*, previous=None, seq=7, selected=False, target=None):
    """Account for every admitted entry with one explicit disposition."""
    ref = entry(seq)
    return PreparationIntakeWorkset(
        scope=target or scope(),
        previous=previous or IntakeAnchor(),
        cutoff=IntakeAnchor(
            last_release_entry_seq=seq,
            last_release_entry_digest=ref.entry_digest,
        ),
        entries=(ref,),
        selections=(
            IntakeSelection(
                entry=ref,
                result=ResultRef("selection", "collected_selection", "1"),
            ),
        )
        if selected
        else (),
        held=()
        if selected
        else (HeldIntakeEntry(entry=ref, reason="missing_evidence"),),
        configuration_version="config-1",
        code_version="code-1",
    )


def store(path: Path):
    """Open the real synchronous store with a bounded test output schema."""
    return Phase1Store(
        f"sqlite:///{path}",
        ResultSchemaRegistry.phase1().with_schema("test_output", "1"),
    )


def claim(store, value=None, *, lease=60, identity="run", kind=None, key=None):
    """Acquire actual durable intake ownership."""
    value = value or workset()
    return store.acquire_claim(
        key or value.scope.claim_key(),
        kind or ClaimKind.PREPARE_INTAKE,
        ExecutionIdentity(identity),
        AttemptIdentity(identity),
        (),
        lease,
    )


def result(store, value, token, result_id="workset"):
    """Build a truthful stage result bound to its workset payload."""
    return StageResult(
        result_id=result_id,
        kind="preparation_intake_workset",
        schema_version="1",
        execution=token.execution,
        attempt=token.attempt,
        input_refs=tuple(dict.fromkeys(item.result for item in value.selections)),
        source_versions=(),
        prepared_versions=(),
        topic_versions=(),
        configuration_version=value.configuration_version,
        code_version=value.code_version,
        status=TerminalStatus.COMPLETE,
        acceptable=True,
        semantic_data_ref=store.semantic_reference(
            "data-" + result_id,
            "preparation_intake_workset",
            "1",
            value,
        ),
    )


def selection(store, token, *, result_id="selection", source=None):
    """Persist a real exact selection without evidence file reads."""
    source = source or VersionRef("outlook_email", "mail-one", "observation-one")
    source_scope = VersionRef("source_scope", "source", "1")
    record = CollectedRecord(
        source=source,
        source_scope=source_scope,
        source_type=PreparedSourceType.OUTLOOK_EMAIL,
        semantic_identity="mail-one",
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        source_time=datetime(2026, 1, 1, tzinfo=UTC),
        subject=None,
        sender=None,
        author=None,
        recipients=(),
        source_content_kind=ContentKind.JSON,
        source_bytes=None,
        body=None,
        alternate_bodies=(),
        attachments=(),
        relationships=(NativeRelationship(kind="source_scope", target=source_scope),),
        metadata=(),
        source_locations=(),
        limitations=(),
    )
    value = capture_selection(record)
    saved = StageResult(
        result_id=result_id,
        kind="collected_selection",
        schema_version="1",
        execution=token.execution,
        attempt=token.attempt,
        input_refs=(),
        source_versions=(source, value.selection),
        prepared_versions=(),
        topic_versions=(),
        configuration_version="config-1",
        code_version="code-1",
        status=TerminalStatus.COMPLETE,
        acceptable=True,
        semantic_data_ref=store.semantic_reference(
            "data-" + result_id,
            "collected_selection",
            "1",
            value,
        ),
    )
    store.append_result_with_data(saved, value, claim=token)
    return saved


def processing_claim(store, result, *, lease=60, identity="processing", key=None):
    """Fence pending processing with its distinct PREPARE scope and input."""
    from msgloom.preparation_pipeline.intake_models import workset_claim_key

    return store.acquire_claim(
        key or workset_claim_key(result.result_id),
        ClaimKind.PREPARE,
        ExecutionIdentity(identity),
        AttemptIdentity(identity),
        (ResultRef(result.result_id, result.kind, result.schema_version),),
        lease,
    )


def output(store, saved, token):
    """Save one acceptable output from the actual processing owner."""
    value = replace(
        saved,
        result_id="output",
        kind="test_output",
        semantic_data_ref=None,
        execution=token.execution,
        attempt=token.attempt,
        input_refs=(ResultRef(saved.result_id, saved.kind, saved.schema_version),),
    )
    store.append_result(value, claim=token)
    return ResultRef("output", "test_output", "1")

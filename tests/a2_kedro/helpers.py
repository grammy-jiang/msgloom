"""
Portable fixtures for the A2 C0 v2 contract tests.

All data is synthetic. No test here touches a provider, a network or a
real database. Intake identities come from the real Intake helper so the
mirrored ordinal formula is tested against the code that produces them.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

import pytest
from pydantic import BaseModel

from msgloom.a2_kedro.contracts.identity import AttemptProof, StageIdentity
from msgloom.a2_kedro.contracts.source import (
    FrozenRoot,
    OccurrenceEvidence,
    verify_exact_occurrence,
)
from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ClaimToken,
    ExecutionIdentity,
    Limitation,
    ResultRef,
    SemanticDataRef,
    StageResult,
    TerminalStatus,
)
from msgloom.preparation_pipeline.intake import _identity
from msgloom.preparation_pipeline.intake_models import (
    HeldIntakeEntry,
    IntakeAnchor,
    IntakeScope,
    IntakeSelection,
    IntakeTransition,
    PreparationIntakeWorkset,
)
from msgloom.sources.handoff_models import A1CatalogIdentity, ReleaseEntryRef

CONFIG = "config-1"
CODE = "code-1"


def check(condition: bool, message: str) -> None:
    """Fail the test with ``message`` unless ``condition`` holds."""
    if not condition:
        pytest.fail(message)


def hexd(char: str) -> str:
    """Return a 64-character digest made of ``char``."""
    return char * 64


def accepted_ref(char: str, kind: str = "frozen_source_selection", ver: str = "1"):
    """Return an upstream ref that looks like an accepted logical key."""
    return ResultRef("a2-accepted:" + hexd(char), kind, ver)


SCOPE = IntakeScope(
    catalog=A1CatalogIdentity(catalog_identity="cat-1", schema_version=1),
    source_id="src-1",
    stream="outlook_mail",
    consumer_id="consumer-1",
)
MEMBERS = (("f" * 64, "primary"),)


def entry(seq: int) -> ReleaseEntryRef:
    """Return a synthetic release entry at sequence ``seq``."""
    return ReleaseEntryRef(
        catalog=SCOPE.catalog,
        release_entry_seq=seq,
        entry_digest=hexd("abcdef"[seq % 6]),
    )


def selection_for(seq: int, ordinal: int = 0) -> IntakeSelection:
    """Return the Intake selection with the real ordinal identity."""
    ref = entry(seq)
    identity = _identity(
        "selection",
        [
            SCOPE.claim_key(),
            ref.model_dump(mode="json"),
            MEMBERS,
            CONFIG,
            CODE,
            ordinal,
        ],
    )
    return IntakeSelection(
        entry=ref, result=ResultRef(identity, "collected_selection", "1")
    )


def transition_for(seq: int, fact: str = "c") -> IntakeTransition:
    """Return a context refresh transition on entry ``seq``."""
    return IntakeTransition(
        entry=entry(seq),
        fact_id=hexd(fact),
        transition_kind="context_refresh",
        resource_kind="mail",
        resource_identity="r-" + fact,
        scope_kind="folder",
        scope_identity="inbox",
    )


def workset(
    selected: int = 2,
    transitions: int = 0,
    held: int = 0,
    *,
    selections: tuple[IntakeSelection, ...] | None = None,
) -> PreparationIntakeWorkset:
    """
    Build a valid incremental workset: selected, transition, held order.

    ``selections`` replaces the generated selections. The workset is still
    fully validated, so a test never relies on an unchecked copy.
    """
    seqs = list(range(1, selected + transitions + held + 1))
    items = [entry(seq) for seq in seqs]
    last = items[-1]
    return PreparationIntakeWorkset(
        scope=SCOPE,
        previous=IntakeAnchor(),
        cutoff=IntakeAnchor(
            last_release_entry_seq=last.release_entry_seq,
            last_release_entry_digest=last.entry_digest,
        ),
        entries=tuple(items),
        selections=selections or tuple(selection_for(s) for s in seqs[:selected]),
        transitions=tuple(
            transition_for(s, "cd"[i % 2])
            for i, s in enumerate(seqs[selected : selected + transitions])
        ),
        held=tuple(
            HeldIntakeEntry(entry=entry(s), reason="missing_evidence")
            for s in seqs[selected + transitions :]
        ),
        configuration_version=CONFIG,
        code_version=CODE,
    )


def mutate(model: BaseModel, **changes: Any) -> Any:
    """
    Rebuild ``model`` through full validation with ``changes`` applied.

    Values may be models, dataclasses or enums; they are converted to JSON
    data first. This avoids ``model_copy(update=...)``, which skips checks.
    """
    data = model.model_dump(mode="json")
    for name, value in changes.items():
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json")
        elif is_dataclass(value) and not isinstance(value, type):
            value = asdict(value)
        data[name] = value
    return type(model).model_validate_json(json.dumps(data))


def evidence_for(seq: int, sha: str = "1" * 64) -> OccurrenceEvidence:
    """Return evidence whose ordinal 0 is a primary selection with ``sha``."""
    return OccurrenceEvidence(
        reference=entry(seq),
        members=MEMBERS,
        occurrence_sha256=(sha,),
        has_primary=True,
    )


def root_for(ws: PreparationIntakeWorkset, index: int = 0) -> FrozenRoot:
    """Return a verified root for the selection at ``index``."""
    return verify_exact_occurrence(
        ws,
        ws.selections[index],
        evidence_for(ws.selections[index].entry.release_entry_seq),
        saved_selection_sha256="1" * 64,
    )


WORKSET_REF = ResultRef(
    "intake-workset:" + hexd("9"), "preparation_intake_workset", "1"
)


def stage_identity(**changes: Any) -> StageIdentity:
    """Return a valid root-stage identity with ``changes`` applied."""
    ws = workset(1)
    values: dict[str, Any] = {
        "scope_key": hexd("5"),
        "workset": WORKSET_REF,
        "partition_ordinal": 0,
        "stage_kind": "frozen_source_selection",
        "schema_version": "1",
        "selected": (root_for(ws),),
        "configuration_version": CONFIG,
        "code_version": CODE,
        "parser_version": "parser-1",
        "rule_version": "rule-1",
        "partition_policy_version": "part-1",
    }
    values.update(changes)
    return StageIdentity.model_validate(values)


def claim(attempt: str = "attempt-1", token: str = "secret-1") -> ClaimToken:
    """Return a synthetic PREPARE claim for ``attempt``."""
    return ClaimToken(
        claim_key="prepare:ws",
        token=token,
        kind=ClaimKind.PREPARE,
        execution=ExecutionIdentity("exec-" + attempt),
        attempt=AttemptIdentity(attempt),
    )


def proof(attempt: str = "attempt-1") -> AttemptProof:
    """Return the attempt proof for ``attempt``."""
    return AttemptProof.from_claim(claim(attempt))


def result_for(
    identity: StageIdentity,
    *,
    attempt: str = "attempt-1",
    status: TerminalStatus = TerminalStatus.COMPLETE,
    limitations: tuple[Limitation, ...] = (),
    sha: str = "a" * 64,
    size: int = 100,
    **changes: Any,
) -> StageResult:
    """Return an acceptable saved result for ``identity``."""
    values: dict[str, Any] = {
        "result_id": identity.logical_key(),
        "kind": identity.stage_kind,
        "schema_version": identity.schema_version,
        "execution": ExecutionIdentity("exec-" + attempt),
        "attempt": AttemptIdentity(attempt),
        "input_refs": identity.upstream,
        "source_versions": (),
        "prepared_versions": (),
        "topic_versions": (),
        "configuration_version": identity.configuration_version,
        "code_version": identity.code_version,
        "status": status,
        "acceptable": True,
        "limitations": limitations,
        "semantic_data_ref": SemanticDataRef(
            "data-" + identity.logical_key()[-8:],
            identity.stage_kind,
            identity.schema_version,
            sha,
            size,
        ),
    }
    values.update(changes)
    return StageResult(**values)

"""C0 contract prototype only; not installed or wired into production A2.

This module prototypes deterministic acceptance keys, explicit A2-held and
the A2 completion receipt; the real transaction authority remains an open
implementation gate. It intentionally imports only accepted frozen A1/Intake
model types and the stdlib/Pydantic installed in msgloom.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from msgloom.contracts import ResultRef, TerminalStatus, VersionRef
from msgloom.preparation_pipeline.intake_models import (
    IntakeSelection,
    IntakeTransition,
    PreparationIntakeWorkset,
)
from msgloom.sources import CollectedSelection, CollectedSelectionCodec
from msgloom.sources.handoff_models import Digest, ReleaseEntryRef
from msgloom.sources.release_models import ReleasedInput


class C0ContractError(ValueError):
    """A producer proof is unsafe or incomplete, never a source payload."""


class _C0Model(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class FrozenRoot(_C0Model):
    """One selected occurrence, including explicitly approved baseline input."""

    selected: ResultRef
    occurrence: Annotated[int, Field(ge=0, le=1023)]
    role: Literal["primary", "component", "baseline"]
    selection_sha256: Digest
    a1_ordinal_proof: Digest | None = None
    entry: ReleaseEntryRef | None = None
    baseline_source: VersionRef | None = None
    baseline_approval: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> FrozenRoot:
        if (self.selected.kind, self.selected.schema_version) != (
            "collected_selection",
            "1",
        ):
            raise C0ContractError("frozen root is not collected_selection@1")
        if self.role == "baseline":
            if (
                self.entry is not None
                or self.a1_ordinal_proof is not None
                or self.baseline_source is None
                or not self.baseline_approval
            ):
                raise C0ContractError("baseline needs explicit approval and source")
        elif (
            self.entry is None
            or self.a1_ordinal_proof is None
            or self.baseline_source is not None
            or self.baseline_approval is not None
        ):
            raise C0ContractError("incremental root needs exact release and ordinal")
        return self


class StageIdentity(_C0Model):
    """All *input* parts of one accepted A2 stage; no attempt or output."""

    scope_key: Digest
    workset: ResultRef
    partition_ordinal: Annotated[int, Field(ge=0, le=1023)]
    selected: tuple[FrozenRoot, ...] = ()
    transitions: tuple[IntakeTransition, ...] = ()
    stage_kind: Literal[
        "frozen_source_selection",
        "extracted_components",
        "parsed_parts",
        "normalized_content",
        "zones",
        "native_relations",
        "prepared",
        "filter_result",
        "group_result",
        "prepared_transitions",
        "a2_input_disposition",
    ]
    schema_version: Literal["1", "2"]
    upstream: tuple[ResultRef, ...] = ()
    configuration_version: str
    code_version: str
    parser_version: str
    rule_version: str
    partition_policy_version: str

    @model_validator(mode="after")
    def validate_stages(self) -> StageIdentity:
        if (self.workset.kind, self.workset.schema_version) != (
            "preparation_intake_workset",
            "1",
        ):
            raise C0ContractError("stage workset schema mismatch")
        if bool(self.selected) == bool(self.transitions):
            raise C0ContractError("stage needs selected roots XOR transition batch")
        if len(set(self.transitions)) != len(self.transitions):
            raise C0ContractError("duplicate exact transition in batch")
        if len(self.selected) != len(
            {(root.entry, root.selected, root.occurrence) for root in self.selected}
        ):
            raise C0ContractError("duplicate selected occurrence")
        entries = [root.entry for root in self.selected if root.entry is not None]
        if entries and any(entry.catalog != entries[0].catalog for entry in entries):
            raise C0ContractError("cross-catalog selected roots")
        if bool(entries) and len(entries) != len(self.selected):
            raise C0ContractError("incremental and baseline roots cannot mix")
        if len(self.upstream) != len(set(self.upstream)):
            raise C0ContractError("duplicate upstream result")
        if self.stage_kind == "prepared_transitions" and not self.transitions:
            raise C0ContractError("transition stage requires exact transition batch")
        if self.stage_kind != "prepared_transitions" and self.transitions:
            raise C0ContractError("transition cannot become a message")
        expected_versions = {
            "frozen_source_selection": "1",
            "extracted_components": "1",
            "parsed_parts": "1",
            "normalized_content": "1",
            "zones": "1",
            "native_relations": "1",
            "prepared": "2",
            "filter_result": "2",
            "group_result": "2",
            "prepared_transitions": "2",
            "a2_input_disposition": "1",
        }
        if self.schema_version != expected_versions[self.stage_kind]:
            raise C0ContractError("stage kind/version pairing is not approved")
        for version in (
            self.configuration_version,
            self.code_version,
            self.parser_version,
            self.rule_version,
            self.partition_policy_version,
        ):
            if not version.strip() or len(version.encode()) > 2048:
                raise C0ContractError("unbounded/empty frozen stage version")
        return self

    def logical_acceptance_key(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return (
            "a2-accepted:"
            + hashlib.sha256(b"a2-stage-accepted-input@1\x00" + payload).hexdigest()
        )


class AcceptedPayload(_C0Model):
    """Separately verified output; execution/attempt remain external audit."""

    logical_key: Annotated[str, Field(pattern=r"^a2-accepted:[0-9a-f]{64}$")]
    output: ResultRef
    canonical_sha256: Digest
    canonical_byte_count: Annotated[int, Field(ge=1, le=64 * 1024 * 1024)]

    @model_validator(mode="after")
    def valid_identity(self) -> AcceptedPayload:
        if (
            not self.logical_key.startswith("a2-accepted:")
            or len(self.logical_key) != 76
        ):
            raise C0ContractError("invalid logical key")
        return self


def append_or_verify(
    known: AcceptedPayload | None, proposed: AcceptedPayload
) -> AcceptedPayload:
    """Pure acceptance decision; DB MUST make compare+insert atomic."""
    if known is None:
        return proposed
    if known != proposed:
        raise C0ContractError("a2-accepted-result-integrity-conflict")
    return known


class HeldReason(StrEnum):
    ROLE_UNVERIFIABLE = "role_unverifiable"
    SOURCE_EVIDENCE_UNAVAILABLE = "source_evidence_unavailable"
    PARSER_UNSUPPORTED = "parser_unsupported"
    INPUT_LIMIT = "input_limit"
    PROOF_MISSING = "proof_missing"


class InputDisposition(_C0Model):
    """A2-owned held record for exact incremental OR approved baseline input."""

    selected: ResultRef
    entry: ReleaseEntryRef | None = None
    baseline_source: VersionRef | None = None
    baseline_approval: str | None = None
    occurrence: Annotated[int, Field(ge=0, le=1023)]
    reason: HeldReason
    selection_sha256: Digest
    configuration_version: str
    code_version: str
    repair_class: Literal["operator_repair"] = "operator_repair"

    @model_validator(mode="after")
    def selection_schema(self) -> InputDisposition:
        if (self.selected.kind, self.selected.schema_version) != (
            "collected_selection",
            "1",
        ):
            raise C0ContractError("A2 held must reference collected_selection@1")
        if self.entry is not None:
            if self.baseline_source is not None or self.baseline_approval is not None:
                raise C0ContractError("incremental held cannot use baseline approval")
        elif self.baseline_source is None or not self.baseline_approval:
            raise C0ContractError("baseline held must carry approved source")
        return self


class TerminalRoot(_C0Model):
    """One exact v2 prepared outcome OR A2-held, for one selected occurrence."""

    selection: IntakeSelection | None = None
    baseline_selection: ResultRef | None = None
    baseline_source: VersionRef | None = None
    workset_selection_index: Annotated[int, Field(ge=0, le=1023)]
    result: ResultRef
    disposition: Literal["prepared", "held"]
    status: TerminalStatus

    @model_validator(mode="after")
    def validate_output(self) -> TerminalRoot:
        if self.selection is not None:
            if self.baseline_selection is not None or self.baseline_source is not None:
                raise C0ContractError("incremental root cannot impersonate baseline")
        elif self.baseline_source is None or self.baseline_selection is None:
            raise C0ContractError("baseline root must bind source and selection")
        if self.baseline_selection is not None and (
            self.baseline_selection.kind,
            self.baseline_selection.schema_version,
        ) != ("collected_selection", "1"):
            raise C0ContractError("baseline selected result schema differs")
        expected = (
            ("prepared", "2")
            if self.disposition == "prepared"
            else ("a2_input_disposition", "1")
        )
        if (self.result.kind, self.result.schema_version) != expected:
            raise C0ContractError("terminal root result has wrong kind/version")
        if self.disposition == "held" and self.status is not TerminalStatus.INCOMPLETE:
            raise C0ContractError("A2 held cannot be COMPLETE")
        if self.status not in {TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE}:
            raise C0ContractError("failed stages cannot appear accepted")
        return self


class TransitionBatch(_C0Model):
    """One workset-scoped batch result covering exact frozen transitions."""

    transitions: tuple[IntakeTransition, ...]
    result: ResultRef
    status: TerminalStatus

    @model_validator(mode="after")
    def validate_output(self) -> TransitionBatch:
        if not self.transitions or len(set(self.transitions)) != len(self.transitions):
            raise C0ContractError("transition batch needs distinct exact transitions")
        if (self.result.kind, self.result.schema_version) != (
            "prepared_transitions",
            "2",
        ):
            raise C0ContractError("transition output is not prepared_transitions@2")
        if self.status not in {TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE}:
            raise C0ContractError("transition output is not terminal accepted")
        return self


class CompletionReceipt(_C0Model):
    """A2-only receipt: proof must cover every selected occurrence and transition."""

    workset: ResultRef
    roots: tuple[TerminalRoot, ...] = ()
    transition_batch: TransitionBatch | None = None
    status: TerminalStatus
    policy_version: str

    @model_validator(mode="after")
    def validate_policy(self) -> CompletionReceipt:
        if not self.policy_version.strip() or len(self.policy_version.encode()) > 2048:
            raise C0ContractError("invalid frozen receipt policy")
        if self.status not in {TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE}:
            raise C0ContractError("receipt must be a terminal accepted outcome")
        return self

    def validate_against(
        self, workset: PreparationIntakeWorkset, expected_workset_ref: ResultRef
    ) -> None:
        if self.workset != expected_workset_ref:
            raise C0ContractError("receipt references a different immutable workset")
        if (self.workset.kind, self.workset.schema_version) != (
            "preparation_intake_workset",
            "1",
        ):
            raise C0ContractError("foreign workset kind/version")
        expected_count = (
            len(workset.baseline_selections)
            if workset.baseline_approval is not None
            else len(workset.selections)
        )
        if len(self.roots) != expected_count:
            raise C0ContractError("missing/overlapping selected occurrences")
        if workset.baseline_approval is not None:
            expected_roots = tuple(
                (None, selection, source, index)
                for index, (selection, source) in enumerate(
                    zip(
                        workset.baseline_selections,
                        workset.baseline_sources,
                        strict=True,
                    )
                )
            )
        else:
            expected_roots = tuple(
                (selection, None, None, index)
                for index, selection in enumerate(workset.selections)
            )
        actual_roots = tuple(
            (
                outcome.selection,
                outcome.baseline_selection,
                outcome.baseline_source,
                outcome.workset_selection_index,
            )
            for outcome in self.roots
        )
        if actual_roots != expected_roots:
            raise C0ContractError("terminal root coverage differs from frozen intake")
        if len({outcome.result for outcome in self.roots}) != len(self.roots):
            raise C0ContractError("one A2 result covers multiple selected occurrences")
        if bool(workset.transitions) != (self.transition_batch is not None):
            raise C0ContractError("missing/unexpected transition batch")
        if self.transition_batch is not None:
            if self.transition_batch.transitions != workset.transitions:
                raise C0ContractError("foreign or altered scoped transition batch")
            if self.transition_batch.result in {x.result for x in self.roots}:
                raise C0ContractError("transition result reused as selected result")

        incomplete = (
            bool(workset.held)
            or any(row.status is TerminalStatus.INCOMPLETE for row in self.roots)
            or (
                self.transition_batch is not None
                and self.transition_batch.status is TerminalStatus.INCOMPLETE
            )
        )
        if not self.roots and self.transition_batch is None and not workset.held:
            raise C0ContractError("empty receipt without eligible source work")
        expected_status = (
            TerminalStatus.INCOMPLETE if incomplete else TerminalStatus.COMPLETE
        )
        if self.status is not expected_status:
            raise C0ContractError("receipt status conflicts with frozen coverage")
        if not self.policy_version.strip() or len(self.policy_version.encode()) > 2048:
            raise C0ContractError("invalid frozen receipt policy")


def receipt_digest(receipt: CompletionReceipt) -> str:
    """Canonical receipt digest for the future separately accepted semantic data."""
    return hashlib.sha256(
        json.dumps(
            receipt.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()


def verify_exact_release_root(
    workset: PreparationIntakeWorkset,
    selection: IntakeSelection,
    released: ReleasedInput,
    saved_selection: CollectedSelection,
) -> FrozenRoot:
    """Prototype only: verify full A1 intake ordinal hash against exact Reader.

    This research helper mirrors A1's documented input-only identity; production
    C0 must qualify a public read-only ordinal verifier before cutover. Neither
    role nor content can be inferred from a provider-current projection.
    """
    if workset.baseline_approval is not None:
        raise C0ContractError("baseline cannot impersonate a release entry")
    if (
        selection not in workset.selections
        or selection.entry not in workset.entries
        or selection.entry != released.reference
        or selection.entry.catalog != workset.scope.catalog
    ):
        raise C0ContractError("frozen intake does not match exact release")
    members = tuple((fact.fact_id, fact.role) for fact in released.facts)
    values = tuple(
        candidate
        for candidate in (released.selection, *released.components)
        if candidate is not None
    )
    matching = []
    for ordinal, value in enumerate(values):
        parts = [
            workset.scope.claim_key(),
            selection.entry.model_dump(mode="json"),
            members,
            workset.configuration_version,
            workset.code_version,
            ordinal,
        ]
        encoded = json.dumps(
            parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        if selection.result.result_id == "intake-selection:" + digest:
            matching.append((ordinal, value, digest))
    if len(matching) != 1:
        raise C0ContractError("ordinal identity cannot uniquely establish role")
    ordinal, exact_value, proof = matching[0]
    if saved_selection != exact_value:
        raise C0ContractError("frozen selection differs from verified release")
    selected_digest = hashlib.sha256(
        CollectedSelectionCodec().encode(saved_selection)
    ).hexdigest()
    return FrozenRoot(
        entry=released.reference,
        selected=selection.result,
        occurrence=ordinal,
        role="primary"
        if released.selection is not None and ordinal == 0
        else "component",
        selection_sha256=selected_digest,
        a1_ordinal_proof=proof,
    )

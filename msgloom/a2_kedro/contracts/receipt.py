"""
``a2_completion_receipt@2``: structural completeness of one workset.

A receipt names exactly one terminal outcome for every frozen selected
occurrence, in frozen order, and exactly one transition batch when the
workset has transitions. This module proves structure and status only. It
does not prove that any result was saved. A candidate finalizer must
check each ``ResultRef`` against durable accepted-stage proofs.

Status rule: COMPLETE needs every root and the batch COMPLETE, no A2-held
root and no intake-held entry. Anything held or partial is INCOMPLETE. A
held-only workset (no roots, no batch) is a legal terminal INCOMPLETE.
This intentionally differs from the legacy v1 completion proof, which
could mark a held-only workset COMPLETE.

CANDIDATE/RESEARCH: no writer or finalizer uses this model yet.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, Field, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    Text,
    domain_sha256,
)
from msgloom.a2_kedro.contracts.held import KIND as HELD_KIND
from msgloom.a2_kedro.contracts.held import VERSION as HELD_VERSION
from msgloom.a2_kedro.contracts.identity import ACCEPTED_STATUSES
from msgloom.a2_kedro.contracts.schema_ids import STAGE_SCHEMAS, is_accepted_key
from msgloom.a2_kedro.contracts.source import Index
from msgloom.contracts import ResultRef, TerminalStatus, VersionRef
from msgloom.preparation_pipeline.intake_models import (
    IntakeSelection,
    IntakeTransition,
    PreparationIntakeWorkset,
)

RECEIPT_DOMAIN = "a2-completion-receipt@2"


def _accepted_only(status: TerminalStatus) -> TerminalStatus:
    if status not in ACCEPTED_STATUSES:
        raise A2ContractError("only complete or incomplete can be accepted")
    return status


Accepted = Annotated[TerminalStatus, AfterValidator(_accepted_only)]


def _require_accepted_result(ref: ResultRef, kind: str, version: str) -> None:
    if (ref.kind, ref.schema_version) != (kind, version):
        raise A2ContractError("terminal result has wrong kind/version")
    if not is_accepted_key(ref.result_id):
        raise A2ContractError("terminal result is not an accepted key")


class TerminalRoot(A2Model):
    """The one terminal outcome of one selected occurrence."""

    workset_selection_index: Index
    result: ResultRef
    disposition: Literal["prepared", "held"]
    status: Accepted
    selection: IntakeSelection | None = None
    baseline_selection: ResultRef | None = None
    baseline_source: VersionRef | None = None

    @model_validator(mode="after")
    def _shape(self) -> TerminalRoot:
        if self.selection is not None:
            if self.baseline_selection or self.baseline_source:
                raise A2ContractError("incremental root cannot be baseline")
        elif self.baseline_selection is None or self.baseline_source is None:
            raise A2ContractError("baseline root needs source and selection")
        if self.disposition == "prepared":
            _require_accepted_result(self.result, "prepared", STAGE_SCHEMAS["prepared"])
            return self
        _require_accepted_result(self.result, HELD_KIND, HELD_VERSION)
        if self.status is not TerminalStatus.INCOMPLETE:
            raise A2ContractError("A2 held cannot be COMPLETE")
        return self


class TransitionBatch(A2Model):
    """One workset-scoped batch result for every exact frozen transition."""

    transitions: tuple[IntakeTransition, ...]
    result: ResultRef
    status: Accepted

    @model_validator(mode="after")
    def _shape(self) -> TransitionBatch:
        if not self.transitions or len(set(self.transitions)) != len(self.transitions):
            raise A2ContractError("batch needs distinct exact transitions")
        _require_accepted_result(
            self.result, "prepared_transitions", STAGE_SCHEMAS["prepared_transitions"]
        )
        return self


def expected_status(
    roots: tuple[TerminalRoot, ...],
    batch: TransitionBatch | None,
    intake_held_count: int,
) -> TerminalStatus:
    """Return the only status a receipt with this coverage may carry."""
    statuses = [root.status for root in roots]
    if batch is not None:
        statuses.append(batch.status)
    if intake_held_count or TerminalStatus.INCOMPLETE in statuses:
        return TerminalStatus.INCOMPLETE
    return TerminalStatus.COMPLETE


class CompletionReceipt(A2Model):
    """Structural receipt for one frozen workset."""

    workset: ResultRef
    status: Accepted
    policy_version: Text
    roots: tuple[TerminalRoot, ...] = ()
    transition_batch: TransitionBatch | None = None
    intake_held_count: Annotated[int, Field(ge=0, le=1024)] = 0

    @model_validator(mode="after")
    def _structure(self) -> CompletionReceipt:
        if (self.workset.kind, self.workset.schema_version) != (
            "preparation_intake_workset",
            "1",
        ):
            raise A2ContractError("foreign workset kind/version")
        if not (self.roots or self.transition_batch or self.intake_held_count):
            raise A2ContractError("empty receipt without any frozen work")
        if [r.workset_selection_index for r in self.roots] != list(
            range(len(self.roots))
        ):
            raise A2ContractError("roots must cover frozen indexes in order")
        results = [r.result for r in self.roots]
        if self.transition_batch is not None:
            results.append(self.transition_batch.result)
        if len(set(results)) != len(results):
            raise A2ContractError("one result covers several occurrences")
        want = expected_status(
            self.roots, self.transition_batch, self.intake_held_count
        )
        if self.status is not want:
            raise A2ContractError("receipt status conflicts with coverage")
        return self

    def digest(self) -> str:
        """Return the domain-separated canonical receipt digest."""
        return domain_sha256(RECEIPT_DOMAIN, self.model_dump(mode="json"))

    def validate_against(
        self, workset: PreparationIntakeWorkset, workset_ref: ResultRef
    ) -> None:
        """
        Check coverage against the exact frozen workset.

        CANDIDATE/RESEARCH: structural only, not production-ready.

        Raises :exc:`A2ContractError` for a different workset, missing or
        extra occurrences, altered transitions or a wrong intake-held count.
        """
        if self.workset != workset_ref:
            raise A2ContractError("receipt references a different workset")
        baseline = workset.baseline_approval is not None
        expected = (
            tuple(
                (None, ref, source, index)
                for index, (ref, source) in enumerate(
                    zip(
                        workset.baseline_selections,
                        workset.baseline_sources,
                        strict=True,
                    )
                )
            )
            if baseline
            else tuple(
                (sel, None, None, index) for index, sel in enumerate(workset.selections)
            )
        )
        actual = tuple(
            (
                r.selection,
                r.baseline_selection,
                r.baseline_source,
                r.workset_selection_index,
            )
            for r in self.roots
        )
        if actual != expected:
            raise A2ContractError("terminal roots differ from frozen intake")
        if self.intake_held_count != len(workset.held):
            raise A2ContractError("intake-held count differs from frozen intake")
        if bool(workset.transitions) != (self.transition_batch is not None):
            raise A2ContractError("missing or unexpected transition batch")
        batch = self.transition_batch
        if batch is not None and batch.transitions != workset.transitions:
            raise A2ContractError("transition batch differs from frozen intake")

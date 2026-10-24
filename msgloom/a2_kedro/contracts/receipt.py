"""
``a2_completion_receipt@2``: structural completeness of one workset.

A receipt names exactly one terminal outcome for every frozen selected
occurrence, in frozen order, and exactly one transition batch when the
workset has transitions. This module proves structure and status only. It
does not prove that any result was saved. A candidate finalizer must
check each ``ResultRef`` against durable accepted-stage proofs.

Occurrence rule: ``roots`` holds one terminal for each frozen
``workset.selections`` occurrence, in frozen order. A repeated selection
ref at two occurrences needs two terminals. The de-duplicated
``workset.selection_refs`` is never the unit of coverage. A terminal is
an accepted ``prepared@2`` (COMPLETE, or INCOMPLETE with explicit
limitations) or an accepted ``a2_input_disposition@1`` (INCOMPLETE, with
explicit limitations). One occurrence never has two terminals, and no
terminal names an occurrence outside the frozen workset.

Status rule: COMPLETE needs every root and the batch COMPLETE, no A2-held
root and no intake-held entry. Anything held or partial is INCOMPLETE. A
held-only workset (no roots, no batch) is a legal terminal INCOMPLETE.
This intentionally differs from the legacy v1 completion proof, which
could mark a held-only workset COMPLETE.

Index and proof fields: ``acceptance_index_sha256`` is a digest over the
ordered terminal coverage (index, disposition, status, result ref and
limitations) and the batch. The wire value is required. Parsing wire data
without it fails. Code that builds a receipt in memory calls
:meth:`CompletionReceipt.build`, which computes it. A supplied value must
match. ``claim_proofs`` holds one structural
:class:`~msgloom.a2_kedro.contracts.identity.AttemptProof` per terminal
result. They are digests of claims, never tokens. They are all or
nothing; :meth:`CompletionReceipt.require_claim_proofs` lets a finalizer
refuse a receipt that has none. No code here reads a database or checks
that a claim is live.

CANDIDATE/RESEARCH: no writer or finalizer uses this model yet.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    Digest,
    Text,
    domain_sha256,
)
from msgloom.a2_kedro.contracts.held import KIND as HELD_KIND
from msgloom.a2_kedro.contracts.held import VERSION as HELD_VERSION
from msgloom.a2_kedro.contracts.identity import AttemptProof
from msgloom.a2_kedro.contracts.result_base import (
    Accepted,
    check_limitations,
)
from msgloom.a2_kedro.contracts.schema_ids import STAGE_SCHEMAS, is_accepted_key
from msgloom.a2_kedro.contracts.source import Index
from msgloom.contracts import Limitation, ResultRef, TerminalStatus, VersionRef
from msgloom.preparation_pipeline.intake_models import (
    IntakeSelection,
    IntakeTransition,
    PreparationIntakeWorkset,
)

RECEIPT_DOMAIN = "a2-completion-receipt@2"
INDEX_DOMAIN = "a2-acceptance-index@1"
MAX_ROOTS = 1024


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
    limitations: tuple[Limitation, ...] = ()
    selection: IntakeSelection | None = None
    baseline_selection: ResultRef | None = None
    baseline_source: VersionRef | None = None

    @model_validator(mode="after")
    def _shape(self) -> TerminalRoot:
        check_limitations(self.status, self.limitations)
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


class ResultClaimProof(A2Model):
    """Structural claim proof: one terminal result and its attempt digest."""

    result: ResultRef
    proof: AttemptProof


def _limitation_pairs(limitations: tuple[Limitation, ...]) -> list[list[str]]:
    return [[item.code, item.detail] for item in limitations]


def acceptance_index(
    roots: tuple[TerminalRoot, ...], batch: TransitionBatch | None
) -> str:
    """
    Return the digest of the ordered terminal coverage.

    The digest covers, for each root in order: index, disposition, status,
    result ref and limitations; then the batch result and status. Order
    matters, so a reordered or swapped terminal gives another digest.
    """
    covered: list[Any] = [
        [
            root.workset_selection_index,
            root.disposition,
            root.status.value,
            [root.result.result_id, root.result.kind, root.result.schema_version],
            _limitation_pairs(root.limitations),
        ]
        for root in roots
    ]
    if batch is not None:
        ref = batch.result
        covered.append(
            [batch.status.value, [ref.result_id, ref.kind, ref.schema_version]]
        )
    return domain_sha256(INDEX_DOMAIN, covered)


class CompletionReceipt(A2Model):
    """Structural receipt for one frozen workset."""

    workset: ResultRef
    status: Accepted
    policy_version: Text
    roots: tuple[TerminalRoot, ...] = ()
    transition_batch: TransitionBatch | None = None
    intake_held_count: Annotated[int, Field(ge=0, le=1024)] = 0
    acceptance_index_sha256: Digest
    claim_proofs: tuple[ResultClaimProof, ...] = ()

    @classmethod
    def build(cls, **fields: Any) -> CompletionReceipt:
        """
        Build a receipt in memory and compute the acceptance index.

        ``roots`` and ``transition_batch`` must be model instances. An
        explicit ``acceptance_index_sha256`` is kept and then checked, so
        a wrong value still fails. Wire parsing never calls this method.
        """
        fields.setdefault(
            "acceptance_index_sha256",
            acceptance_index(fields.get("roots", ()), fields.get("transition_batch")),
        )
        return cls(**fields)

    @model_validator(mode="after")
    def _structure(self) -> CompletionReceipt:
        if (self.workset.kind, self.workset.schema_version) != (
            "preparation_intake_workset",
            "1",
        ):
            raise A2ContractError("foreign workset kind/version")
        if not (self.roots or self.transition_batch or self.intake_held_count):
            raise A2ContractError("empty receipt without any frozen work")
        if len(self.roots) > MAX_ROOTS:
            raise A2ContractError("root count is out of bounds")
        indexes = [r.workset_selection_index for r in self.roots]
        if len(set(indexes)) != len(indexes):
            raise A2ContractError("one occurrence has several terminals")
        if indexes != list(range(len(self.roots))):
            raise A2ContractError("roots must cover frozen indexes in order")
        results = [r.result for r in self.roots]
        if self.transition_batch is not None:
            results.append(self.transition_batch.result)
        if len(set(results)) != len(results):
            raise A2ContractError("one result covers several occurrences")
        if self.acceptance_index_sha256 != acceptance_index(
            self.roots, self.transition_batch
        ):
            raise A2ContractError("acceptance index differs from coverage")
        self._check_claim_proofs(results)
        want = expected_status(
            self.roots, self.transition_batch, self.intake_held_count
        )
        if self.status is not want:
            raise A2ContractError("receipt status conflicts with coverage")
        return self

    def _check_claim_proofs(self, results: list[ResultRef]) -> None:
        proofs = [item.result for item in self.claim_proofs]
        if not proofs:
            return
        if len(set(proofs)) != len(proofs):
            raise A2ContractError("duplicate claim proof for one result")
        if set(proofs) != set(results):
            raise A2ContractError("claim proofs differ from terminal results")

    def require_claim_proofs(self) -> None:
        """
        Raise :exc:`A2ContractError` unless every terminal has a claim proof.

        A finalizer calls this before it accepts the receipt. The proofs are
        structural. This method does not check that a claim was live.
        """
        if not self.claim_proofs:
            raise A2ContractError("receipt has no claim proofs")

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

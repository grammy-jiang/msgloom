"""
Scoped transition batch for ``prepared_transitions@2`` (C0-08).

A :class:`TransitionBatch` holds the complete ordered list of scoped
transition facts of one workset. Each :class:`TransitionItem` carries its
exact fact ID, scope, kind and authority. The batch binds the Workset Ref,
the code version, the policy version and every item in order.

Two proofs exist and neither can be dropped:

* The item digest binds the item fields and its ordinal. It proves one
  fact at one position.
* The batch digest binds the Workset Ref, the code and policy identity,
  the item count and every item digest in order. It is stored in the
  record, and the validator recomputes it. A removed, reordered,
  duplicated or substituted item, or a changed workset ref, code or
  policy, makes the stored digest wrong, so construction fails.

An :class:`ItemProof` ties one item to its batch. ``verify_item_proof``
checks it against a batch.

Failure handling: any violation raises :exc:`A2ContractError`. Messages
carry no fact content.

CANDIDATE/RESEARCH, PROVISIONAL: field names, domains and limits are not
frozen. See ``docs/notes/a2-v2-contract-c0-08.md``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    Digest,
    Text,
    canonical_model_bytes,
    decode_model_bytes,
    domain_sha256,
)
from msgloom.a2_kedro.contracts.header import LIMITS, StageHeader
from msgloom.contracts import ResultRef
from msgloom.preparation_pipeline.intake_models import IntakeTransition
from msgloom.sources.handoff_models import ReleaseEntryRef

KIND = "prepared_transitions"
VERSION = "2"
ITEM_DOMAIN = "a2-transition-item@1"
BATCH_DOMAIN = "a2-transition-batch@1"

TransitionKind = Literal[
    "presence", "absence", "membership_removal", "deletion", "context_refresh"
]


class TransitionItem(A2Model):
    """One exact scoped fact at one position of the batch."""

    ordinal: int = Field(ge=0, lt=LIMITS["max_transitions"])
    entry: ReleaseEntryRef
    fact_id: Digest
    scope_kind: Text
    scope_id: Text
    kind: TransitionKind
    authority: Text

    def digest(self) -> str:
        """Return the domain-separated digest of this item and ordinal."""
        return domain_sha256(ITEM_DOMAIN, self.model_dump(mode="json"))

    @classmethod
    def from_intake(
        cls, ordinal: int, transition: IntakeTransition, authority: str
    ) -> TransitionItem:
        """Build an item from a frozen Intake transition plus authority."""
        return cls(
            ordinal=ordinal,
            entry=transition.entry,
            fact_id=transition.fact_id,
            scope_kind=transition.scope_kind,
            scope_id=transition.scope_identity,
            kind=transition.transition_kind,
            authority=authority,
        )


def batch_digest(
    workset: ResultRef,
    code_version: str,
    policy_version: str,
    items: tuple[TransitionItem, ...],
) -> str:
    """Return the batch identity over workset, code, policy and items."""
    return domain_sha256(
        BATCH_DOMAIN,
        {
            "workset": [workset.result_id, workset.kind, workset.schema_version],
            "code_version": code_version,
            "policy_version": policy_version,
            "count": len(items),
            "items": [item.digest() for item in items],
        },
    )


class TransitionBatch(A2Model):
    """The complete ordered transition list of one workset."""

    header: StageHeader = Field(
        default_factory=lambda: StageHeader(kind=KIND, version=VERSION)
    )
    workset: ResultRef
    code_version: Text
    policy_version: Text
    items: tuple[TransitionItem, ...]
    batch_sha256: Digest

    @model_validator(mode="after")
    def _closed(self) -> TransitionBatch:
        if (self.header.kind, self.header.version) != (KIND, VERSION):
            raise A2ContractError("header is not prepared_transitions@2")
        if (self.workset.kind, self.workset.schema_version) != (
            "preparation_intake_workset",
            "1",
        ):
            raise A2ContractError("batch workset schema mismatch")
        if not 1 <= len(self.items) <= LIMITS["max_transitions"]:
            raise A2ContractError("transition count is out of bounds")
        if [item.ordinal for item in self.items] != list(range(len(self.items))):
            raise A2ContractError("item ordinals are not contiguous")
        facts = [(i.fact_id, i.scope_kind, i.scope_id) for i in self.items]
        if len(set(facts)) != len(facts):
            raise A2ContractError("duplicate fact in scope")
        expected = batch_digest(
            self.workset, self.code_version, self.policy_version, self.items
        )
        if self.batch_sha256 != expected:
            raise A2ContractError("batch identity does not match its items")
        return self

    @classmethod
    def build(
        cls,
        workset: ResultRef,
        code_version: str,
        policy_version: str,
        items: tuple[TransitionItem, ...],
    ) -> TransitionBatch:
        """Build a batch and compute its identity from the ordered items."""
        return cls(
            workset=workset,
            code_version=code_version,
            policy_version=policy_version,
            items=items,
            batch_sha256=batch_digest(workset, code_version, policy_version, items),
        )

    def proof(self, ordinal: int) -> ItemProof:
        """Return the proof that binds one item to this batch."""
        if not 0 <= ordinal < len(self.items):
            raise A2ContractError("item ordinal is out of range")
        return ItemProof(
            batch_sha256=self.batch_sha256,
            ordinal=ordinal,
            count=len(self.items),
            item_sha256=self.items[ordinal].digest(),
        )

    def encode(self) -> bytes:
        """Return the bounded canonical bytes of this record."""
        return canonical_model_bytes(self)

    @classmethod
    def decode(cls, data: bytes) -> TransitionBatch:
        """Strictly decode canonical bytes; reject anything else."""
        return decode_model_bytes(cls, data)


class ItemProof(A2Model):
    """Proof that one item sits at one ordinal of one batch."""

    batch_sha256: Digest
    ordinal: int = Field(ge=0, lt=LIMITS["max_transitions"])
    count: int = Field(ge=1, le=LIMITS["max_transitions"])
    item_sha256: Digest


def verify_item_proof(
    batch: TransitionBatch, item: TransitionItem, proof: ItemProof
) -> None:
    """Raise :exc:`A2ContractError` unless ``proof`` binds ``item``."""
    if proof.batch_sha256 != batch.batch_sha256 or proof.count != len(batch.items):
        raise A2ContractError("proof is for another batch")
    if proof.ordinal != item.ordinal or proof.item_sha256 != item.digest():
        raise A2ContractError("proof does not match the item")
    if proof.ordinal >= len(batch.items) or batch.items[proof.ordinal] != item:
        raise A2ContractError("item is not in the batch at that ordinal")

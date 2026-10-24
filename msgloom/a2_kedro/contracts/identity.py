"""
Deterministic stage identity, lineage, attempt proof and metadata digests.

Three identities stay separate on purpose:

* ``StageIdentity.logical_key`` depends on frozen inputs only. It never
  contains an output digest, a timestamp, an execution, an attempt or a
  Kedro node name, so a retry by any worker computes the same key.
* ``AttemptProof`` records who tried (execution, attempt, claim). It is
  stored beside the accepted stage and is never part of the key.
* ``stage_metadata_digest`` covers status, limitations, input refs,
  versions and lineage of a saved ``StageResult``. Equal payload bytes with
  a different status or limitation set are therefore not equivalent.

CANDIDATE/RESEARCH: key and digest domains are provisional until C0-00.
"""

from __future__ import annotations

from itertools import pairwise
from typing import Annotated

from pydantic import Field, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    Digest,
    Text,
    domain_sha256,
)
from msgloom.a2_kedro.contracts.schema_ids import (
    ACCEPTED_KEY_PREFIX,
    ROOT_STAGES,
    STAGE_SCHEMAS,
    is_accepted_key,
    require_stage_schema,
)
from msgloom.a2_kedro.contracts.source import FrozenRoot
from msgloom.contracts import (
    ClaimToken,
    Limitation,
    ResultRef,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.preparation_pipeline.intake_models import IntakeTransition

KEY_DOMAIN = "a2-stage-accepted-input@1"
LINEAGE_DOMAIN = "a2-stage-lineage@1"
LIMITATIONS_DOMAIN = "a2-stage-status-limitations@1"
METADATA_DOMAIN = "a2-stage-metadata@1"
ACCEPTED_STATUSES = frozenset({TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE})

Ordinal = Annotated[int, Field(ge=0, le=1023)]


def _ref(ref: ResultRef) -> list[str]:
    return [ref.result_id, ref.kind, ref.schema_version]


def lineage_digest(upstream: tuple[ResultRef, ...]) -> str:
    """
    Digest the ordered full upstream chain of accepted result refs.

    Every upstream ref must carry an accepted logical key and an approved
    ``(kind, version)`` pair. Order matters. Duplicates are rejected.
    """
    if len(set(upstream)) != len(upstream):
        raise A2ContractError("duplicate upstream result")
    for ref in upstream:
        require_stage_schema(ref.kind, ref.schema_version)
        if not is_accepted_key(ref.result_id):
            raise A2ContractError("upstream is not an accepted result")
    return domain_sha256(LINEAGE_DOMAIN, [_ref(ref) for ref in upstream])


def status_limitations_digest(
    status: TerminalStatus, limitations: tuple[Limitation, ...]
) -> str:
    """
    Digest an accepted status and its limitation set.

    Limitations are a set: order does not change the digest, duplicates are
    rejected. Only COMPLETE and INCOMPLETE are accepted statuses, and
    COMPLETE cannot carry a limitation.
    """
    if status not in ACCEPTED_STATUSES:
        raise A2ContractError("only complete or incomplete can be accepted")
    pairs = sorted([item.code, item.detail] for item in limitations)
    if any(a == b for a, b in pairwise(pairs)):
        raise A2ContractError("duplicate limitation")
    if status is TerminalStatus.COMPLETE and pairs:
        raise A2ContractError("complete result cannot carry limitations")
    return domain_sha256(LIMITATIONS_DOMAIN, [status.value, pairs])


class StageIdentity(A2Model):
    """Input-only identity of one accepted A2 stage."""

    scope_key: Digest
    workset: ResultRef
    partition_ordinal: Ordinal
    stage_kind: Text
    schema_version: Text
    selected: tuple[FrozenRoot, ...] = ()
    transitions: tuple[IntakeTransition, ...] = ()
    upstream: tuple[ResultRef, ...] = ()
    configuration_version: Text
    code_version: Text
    parser_version: Text
    rule_version: Text
    partition_policy_version: Text

    @model_validator(mode="after")
    def _closed_and_complete(self) -> StageIdentity:
        require_stage_schema(self.stage_kind, self.schema_version)
        if (self.workset.kind, self.workset.schema_version) != (
            "preparation_intake_workset",
            "1",
        ):
            raise A2ContractError("stage workset schema mismatch")
        if self.stage_kind == "prepared_transitions":
            if self.selected or not self.transitions:
                raise A2ContractError("transition stage needs only a batch")
        elif self.transitions or not self.selected:
            raise A2ContractError("message stage needs roots, not transitions")
        if len(set(self.transitions)) != len(self.transitions):
            raise A2ContractError("duplicate exact transition in batch")
        indexes = [root.workset_index for root in self.selected]
        if len(set(indexes)) != len(indexes):
            raise A2ContractError("duplicate selected occurrence")
        if len({root.role == "baseline" for root in self.selected}) > 1:
            raise A2ContractError("baseline and incremental roots cannot mix")
        catalogs = {
            root.entry.catalog.catalog_identity for root in self.selected if root.entry
        }
        if len(catalogs) > 1:
            raise A2ContractError("cross-catalog selected roots")
        lineage_digest(self.upstream)
        if not self.upstream and self.stage_kind not in ROOT_STAGES:
            raise A2ContractError("stage needs accepted upstream results")
        if self.upstream and self.stage_kind in ROOT_STAGES:
            raise A2ContractError("root stage cannot have upstream results")
        return self

    def lineage(self) -> str:
        """Return the digest of the ordered upstream chain."""
        return lineage_digest(self.upstream)

    def logical_key(self) -> str:
        """Return ``a2-accepted:`` plus the domain-separated input digest."""
        return ACCEPTED_KEY_PREFIX + domain_sha256(
            KEY_DOMAIN, self.model_dump(mode="json")
        )

    def result_ref(self) -> ResultRef:
        """Return the deterministic ``ResultRef`` this stage will publish."""
        return ResultRef(self.logical_key(), self.stage_kind, self.schema_version)


class AttemptProof(A2Model):
    """
    Who tried to publish a stage; separate from the logical key.

    Only a SHA-256 of the claim token is kept. The raw token is a secret
    ownership proof and never enters a stored record.
    """

    execution_id: Text
    attempt_id: Text
    claim_key: Text
    claim_token_sha256: Digest

    @classmethod
    def from_claim(cls, claim: ClaimToken) -> AttemptProof:
        """Derive the proof from a live claim token."""
        return cls(
            execution_id=claim.execution.value,
            attempt_id=claim.attempt.value,
            claim_key=claim.claim_key,
            claim_token_sha256=domain_sha256("a2-claim-token@1", claim.token),
        )


class StageMetadata(A2Model):
    """
    Attempt-free, deterministic view of a saved ``StageResult``.

    Excluded on purpose: execution, attempt and exposed diagnostics. They
    differ between legitimate retries of the same logical stage.
    """

    result_id: Text
    kind: Text
    schema_version: Text
    status: TerminalStatus
    limitations_digest: Digest
    lineage_digest: Digest
    input_refs: tuple[tuple[str, str, str], ...]
    configuration_version: Text
    code_version: Text
    versions: tuple[tuple[str, str, str, str], ...]
    optional_versions: tuple[str | None, ...]
    semantic_data_id: Text
    semantic_kind: Text
    semantic_schema_version: Text
    semantic_sha256: Digest
    semantic_byte_count: Annotated[int, Field(ge=1)]

    def digest(self) -> str:
        """Return the canonical stage metadata SHA-256."""
        return domain_sha256(METADATA_DOMAIN, self.model_dump(mode="json"))


def _version_text(ref: VersionRef | None) -> str | None:
    return None if ref is None else f"{ref.kind}/{ref.identity}/{ref.version}"


def stage_metadata(result: StageResult) -> StageMetadata:
    """
    Project a ``StageResult`` without execution, attempt or diagnostics.

    Raises :exc:`A2ContractError` when the result is not an acceptable
    COMPLETE or INCOMPLETE stage with saved semantic data and no failure.
    """
    require_stage_schema(result.kind, result.schema_version)
    if not result.acceptable or result.failures:
        raise A2ContractError("result is not an acceptable stage")
    data = result.semantic_data_ref
    if data is None:
        raise A2ContractError("accepted stage needs saved semantic data")
    versions = tuple(
        (group, ref.kind, ref.identity, ref.version)
        for group, refs in (
            ("source", result.source_versions),
            ("prepared", result.prepared_versions),
            ("topic", result.topic_versions),
        )
        for ref in refs
    )
    return StageMetadata(
        result_id=result.result_id,
        kind=result.kind,
        schema_version=result.schema_version,
        status=result.status,
        limitations_digest=status_limitations_digest(result.status, result.limitations),
        lineage_digest=lineage_digest(result.input_refs),
        input_refs=tuple(
            (ref.result_id, ref.kind, ref.schema_version) for ref in result.input_refs
        ),
        configuration_version=result.configuration_version,
        code_version=result.code_version,
        versions=versions,
        optional_versions=(
            result.rule_version,
            result.prompt_version,
            result.model_identifier,
            _version_text(result.working_context_version),
            _version_text(result.exposed_output_ref),
        ),
        semantic_data_id=data.data_id,
        semantic_kind=data.kind,
        semantic_schema_version=data.schema_version,
        semantic_sha256=data.sha256,
        semantic_byte_count=data.byte_count,
    )


def check_stage_matches_identity(identity: StageIdentity, result: StageResult) -> None:
    """Raise unless a saved result is the one ``identity`` should publish."""
    if STAGE_SCHEMAS.get(result.kind) != result.schema_version:
        raise A2ContractError("stage kind/version pairing is not approved")
    if (
        result.result_id != identity.logical_key()
        or result.kind != identity.stage_kind
        or result.schema_version != identity.schema_version
        or result.input_refs != identity.upstream
        or result.configuration_version != identity.configuration_version
        or result.code_version != identity.code_version
    ):
        raise A2ContractError("saved result does not match frozen identity")

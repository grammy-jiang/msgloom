"""Prove terminal preparation lineage before the intake writer transaction."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.engine import Connection

from msgloom.contracts import (
    ClaimToken,
    ResultRef,
    ResultSchemaRegistry,
    StageResult,
    TerminalStatus,
)
from msgloom.persistence.codecs import decode_result_refs
from msgloom.persistence.errors import (
    DependencyNotReadyError,
    ImmutableRecordError,
    StaleClaimError,
)
from msgloom.persistence.intake_records import saved_result
from msgloom.persistence.preparation_proof import (
    AcceptedPreparationProof,
    load_accepted_preparation,
)
from msgloom.persistence.records import PREPARATION_RESULT_BINDINGS as BINDINGS
from msgloom.persistence.semantic import SemanticDataRegistry
from msgloom.persistence.semantic_store import load_semantic_data
from msgloom.preparation import PreparedRecord
from msgloom.preparation.filtering import FilterResult
from msgloom.preparation.grouping import GroupResult
from msgloom.preparation_pipeline.codec import DerivedByteArtifact
from msgloom.preparation_pipeline.intake_models import PreparationIntakeWorkset
from msgloom.preparation_pipeline.transitions import PreparedTransitions
from msgloom.sources import CollectedSelection

_OUTPUT_KINDS = {
    "derived_bytes",
    "prepared",
    "filter_result",
    "group_result",
    "prepared_transitions",
}


@dataclass(frozen=True)
class CompletionProof:
    """Carry payload metadata and exact accepted-plan snapshots."""

    results: tuple[StageResult, ...]
    receipts: tuple[AcceptedPreparationProof, ...]


@dataclass(frozen=True)
class CompletionInputs:
    """Carry frozen selection payloads and metadata into completion proof."""

    results: dict[ResultRef, StageResult]
    selections: dict[ResultRef, CollectedSelection]


def load_completion_inputs(
    connection: Connection,
    workset: PreparationIntakeWorkset,
    output_count: int,
    registry: ResultSchemaRegistry,
    semantic_registry: SemanticDataRegistry,
) -> CompletionInputs:
    """Bound caller output count using only saved, frozen producer inputs."""
    results: dict[ResultRef, StageResult] = {}
    selections: dict[ResultRef, CollectedSelection] = {}
    for ref in workset.selection_refs:
        result = saved_result(connection, ref, registry)
        if result.semantic_data_ref is None:
            raise DependencyNotReadyError("preparation proof lacks semantic data")
        value = load_semantic_data(
            connection, result.semantic_data_ref, semantic_registry
        )
        if not isinstance(value, CollectedSelection):
            raise DependencyNotReadyError("frozen input is not a collected selection")
        results[ref], selections[ref] = result, value

    # RecordSteps emits prepared + filter, at most one derived metadata result,
    # one primary body result, and one result per alternate body. Attachments
    # use saved-byte references inside prepared data, not separate outputs.
    # StageSteps groups partition records, so there is at most one group per
    # selection, even when the workset uses several disjoint replay plans.
    # Reject before scanning, hashing, or serializing any caller references.
    # Reuse these inputs in the exact proof and final metadata rechecks.
    output_bound = sum(
        4 + int(value.record.body is not None) + len(value.record.alternate_bodies)
        for value in selections.values()
    )
    # A transition producer emits one tuple for the exact workset, not one
    # result per fact. Selection-only and held-only bounds stay unchanged.
    output_bound += int(bool(workset.transitions))
    if output_count > output_bound:
        raise DependencyNotReadyError(
            "terminal result references must be bounded by frozen inputs"
        )
    return CompletionInputs(results, selections)


def completion_receipts(
    connection: Connection,
    workset: PreparationIntakeWorkset,
    workset_ref: ResultRef,
    refs: tuple[ResultRef, ...],
    status: TerminalStatus,
    registry: ResultSchemaRegistry,
) -> tuple[AcceptedPreparationProof, ...]:
    """Require whole manifests and disjoint, complete frozen-input coverage."""
    tokens = []
    for ref in refs:
        binding = (
            connection.execute(
                select(BINDINGS).where(
                    BINDINGS.c.result_id == ref.result_id,
                )
            )
            .mappings()
            .first()
        )
        if binding is None or (binding["kind"], binding["schema_version"]) != (
            ref.kind,
            ref.schema_version,
        ):
            raise DependencyNotReadyError("output lacks exact publishing plan binding")
        if binding["claim_token"] not in tokens:
            tokens.append(binding["claim_token"])
    proofs = tuple(
        load_accepted_preparation(connection, token, registry) for token in tokens
    )
    covered: set[ResultRef] = set()
    expected_roots = set(workset.selection_refs)
    if workset.transitions:
        expected_roots.add(workset_ref)
    for proof in proofs:
        raw = proof.plan["required_inputs"]
        if len(raw.encode()) > 4 * 1024 * 1024:
            raise DependencyNotReadyError(
                "frozen preparation inputs exceed proof bound"
            )
        roots = decode_result_refs(raw)
        if (
            not roots
            or len(roots) > 1024
            or len(set(roots)) != len(roots)
            or covered.intersection(roots)
            or not set(roots).issubset(expected_roots)
        ):
            raise DependencyNotReadyError("plan frozen inputs are foreign or overlap")
        manifest = tuple(
            ResultRef(result.result_id, result.kind, result.schema_version)
            for result in proof.results
        )
        if tuple(ref for ref in refs if ref in manifest) != manifest:
            raise DependencyNotReadyError(
                "terminal outputs omit or substitute plan results"
            )
        allowed = set(roots) | set(manifest)
        prepared_roots = set()
        for result in proof.results:
            if not set(result.input_refs).issubset(allowed):
                raise DependencyNotReadyError(
                    "output substitutes another plan's inputs"
                )
            if result.kind == "prepared_transitions":
                if roots != (workset_ref,) or result.input_refs != roots:
                    raise DependencyNotReadyError(
                        "transition receipt has a foreign root"
                    )
                prepared_roots.add(workset_ref)
            if result.kind == "prepared" and result.input_refs:
                prepared_roots.add(result.input_refs[0])
        if prepared_roots != set(roots):
            raise DependencyNotReadyError(
                "plan does not prepare its complete frozen inputs"
            )
        covered.update(roots)
    if covered != expected_roots:
        raise DependencyNotReadyError("accepted plans do not cover frozen inputs")
    if proofs:
        aggregate = (
            TerminalStatus.INCOMPLETE
            if any(
                p.plan["accepted_status"] == TerminalStatus.INCOMPLETE.value
                for p in proofs
            )
            else TerminalStatus.COMPLETE
        )
        if status is not aggregate:
            raise DependencyNotReadyError(
                "terminal status differs from exact accepted plans"
            )
    return proofs


def recheck_completion(
    connection: Connection,
    saved: StageResult,
    proof: CompletionProof,
    workset: PreparationIntakeWorkset,
    refs: tuple[ResultRef, ...],
    status: TerminalStatus,
    registry: ResultSchemaRegistry,
) -> None:
    """Recheck metadata snapshots without evidence or payload reads."""
    for expected in (saved, *proof.results):
        ref = ResultRef(expected.result_id, expected.kind, expected.schema_version)
        if saved_result(connection, ref, registry) != expected:
            raise ImmutableRecordError("preparation proof changed before commit")
    if (
        completion_receipts(
            connection,
            workset,
            ResultRef(saved.result_id, saved.kind, saved.schema_version),
            refs,
            status,
            registry,
        )
        != proof.receipts
    ):
        raise ImmutableRecordError("accepted preparation proof changed")


def validate_completion(
    connection: Connection,
    workset: PreparationIntakeWorkset,
    workset_ref: ResultRef,
    frozen_inputs: CompletionInputs,
    refs: tuple[ResultRef, ...],
    claim: ClaimToken,
    status: TerminalStatus,
    registry: ResultSchemaRegistry,
    semantic_registry: SemanticDataRegistry,
) -> CompletionProof:
    """
    Validate bounded saved replay outputs against every exact frozen selection.

    The existing handler returns derived/prepared/filter/group results, whose
    dependencies are included in that same outcome. Selections are roots, never
    outputs. A prepared record proves coverage; ancillary outputs must trace
    through those exact records. Accepted INCOMPLETE records remain legitimate.
    Held entries already have durable dispositions. Transition tuples require
    their exact workset root and a separate accepted producer receipt.

    Reuse the bounded frozen-input snapshots. Read output semantic data here,
    before writer ownership. Return immutable metadata for the final transaction
    to recheck without reading payloads.
    """
    if workset.selections and not refs:
        raise ValueError("readable intake workset requires processing output")
    results = frozen_inputs.results
    selections = frozen_inputs.selections
    values: dict[ResultRef, object] = dict(selections)

    for ref in refs:
        result = saved_result(connection, ref, registry)
        if result.execution != claim.execution:
            raise StaleClaimError("terminal output belongs to another execution")
        if ref.kind not in _OUTPUT_KINDS or ref.schema_version != "1":
            raise DependencyNotReadyError("result is not a preparation output")
        if result.semantic_data_ref is None:
            raise DependencyNotReadyError("preparation proof lacks semantic data")
        results[ref] = result
        values[ref] = load_semantic_data(
            connection,
            result.semantic_data_ref,
            semantic_registry,
        )

    covered: set[ResultRef] = set()
    for ref in refs:
        result, value = results[ref], values[ref]
        inputs = result.input_refs
        if ref.kind == "prepared_transitions":
            if (
                not isinstance(value, PreparedTransitions)
                or value.transitions != workset.transitions
                or inputs != (workset_ref,)
                or result.source_versions
                or result.prepared_versions
                or result.topic_versions
                or result.status is not TerminalStatus.COMPLETE
            ):
                raise DependencyNotReadyError(
                    "transition output differs from frozen facts"
                )
            continue
        if len(inputs) > len(results) or len(inputs) != len(set(inputs)):
            raise DependencyNotReadyError("preparation output dependencies are invalid")
        if any(item not in results for item in inputs):
            raise DependencyNotReadyError(
                "preparation output has unrelated dependencies"
            )
        if isinstance(value, (DerivedByteArtifact, PreparedRecord)):
            if not inputs or inputs[0] not in selections:
                raise DependencyNotReadyError("output lacks its exact frozen selection")
            selected = selections[inputs[0]]
            if value.source != selected.source:
                raise DependencyNotReadyError("output source differs from frozen input")
            if isinstance(value, DerivedByteArtifact):
                if (
                    inputs != (inputs[0],)
                    or value.selection != selected.selection
                    or result.source_versions != (value.source,)
                    or result.prepared_versions
                ):
                    raise DependencyNotReadyError("derived output lineage is invalid")
            else:
                _require_prepared(result, value, results, values)
                covered.add(inputs[0])
        elif isinstance(value, FilterResult):
            _require_filter(result, value, results, values)
        elif isinstance(value, GroupResult):
            _require_group(result, value, results, values)
        else:
            raise DependencyNotReadyError("unsupported preparation output payload")
        for dependency in inputs:
            parent = results[dependency]
            if dependency in selections:
                continue
            if (
                parent.execution != result.execution
                or parent.attempt != result.attempt
                or parent.configuration_version != result.configuration_version
                or parent.code_version != result.code_version
            ):
                raise DependencyNotReadyError("preparation output mixes plan lineage")
    if covered != set(selections):
        raise DependencyNotReadyError("preparation outputs do not cover frozen inputs")
    snapshots = tuple(results.values())
    receipts = completion_receipts(
        connection, workset, workset_ref, refs, status, registry
    )
    return CompletionProof(snapshots, receipts)


def _require_prepared(result, value: PreparedRecord, results, values) -> None:
    """Bind prepared semantic data and derived artifacts to one selection."""
    if (
        result.source_versions
        != (
            value.source,
            *(item.reference for item in value.attachments),
        )
        or len(result.prepared_versions) != 1
        or result.prepared_versions[0].kind != "prepared"
    ):
        raise DependencyNotReadyError("prepared output versions are invalid")
    selected = values[result.input_refs[0]]
    for ref in result.input_refs[1:]:
        derived = values[ref]
        if (
            not isinstance(derived, DerivedByteArtifact)
            or results[ref].input_refs != (result.input_refs[0],)
            or derived.source != selected.source
            or derived.selection != selected.selection
        ):
            raise DependencyNotReadyError("prepared output has unrelated derived bytes")


def _require_filter(result, value: FilterResult, results, values) -> None:
    """Bind each filter to its exact prepared version and source."""
    if len(result.input_refs) != 1:
        raise DependencyNotReadyError("filter output requires one prepared input")
    ref = result.input_refs[0]
    prepared = values[ref]
    if (
        not isinstance(prepared, PreparedRecord)
        or value.input != prepared.source
        or result.source_versions != (value.input,)
        or result.prepared_versions != results[ref].prepared_versions
    ):
        raise DependencyNotReadyError("filter output lineage is invalid")


def _require_group(result, value: GroupResult, results, values) -> None:
    """Bind group members and filters to the exact prepared dependency set."""
    count = len(value.members)
    prepared_refs = result.input_refs[:count]
    filter_refs = result.input_refs[count:]
    if len(prepared_refs) != count or len(filter_refs) != count:
        raise DependencyNotReadyError("group output dependencies are incomplete")
    for source, prepared_ref, filter_ref, filtered in zip(
        value.members,
        prepared_refs,
        filter_refs,
        value.filters,
        strict=True,
    ):
        prepared = values[prepared_ref]
        if (
            not isinstance(prepared, PreparedRecord)
            or prepared.source != source
            or values[filter_ref] != filtered
            or results[filter_ref].input_refs != (prepared_ref,)
        ):
            raise DependencyNotReadyError("group output lineage is invalid")
    if result.source_versions != value.members or result.prepared_versions != tuple(
        version for ref in prepared_refs for version in results[ref].prepared_versions
    ):
        raise DependencyNotReadyError("group output versions are invalid")

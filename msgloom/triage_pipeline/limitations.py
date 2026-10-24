"""
Trusted limitation propagation for the A3 producer.

Two independent paths live here.

The v1 path (:func:`working_context_limitations` and
:func:`merge_trusted_source_limitations`) is unchanged.

The v2 path (:func:`verify_v2_provenance` and
:func:`v2_input_limitations`, C0-17g) turns the state of a saved
``triage_input@2`` snapshot into explicit A3 limitations. The input is the
verified snapshot of one upstream v2 run. The output is a sorted tuple of
:class:`~msgloom.contracts.Limitation` with these stable codes:

* ``triage-v2-input-incomplete``: the snapshot is not complete. The detail
  names the ``snapshot_sha256`` and ``binding_sha256`` it came from.
* ``triage-v2-coverage-failure``: one per saved coverage failure (unit
  id, reason, remaining count and digest, snapshot digest).
* ``triage-v2-held-source``: one per held source (prepared and filter
  result ids, held reasons, snapshot digest). A held source blocks a
  terminal complete proof even when the snapshot is complete.
* ``triage-v2-upstream-<code>``: each upstream limitation, with its
  original detail text.

Failure handling: :func:`verify_v2_provenance` raises
:exc:`V2ProvenanceError` before any limitation is derived. A missing,
forged or invalid digest never yields a partial result. More than
:data:`MAX_PROPAGATED_LIMITATIONS` v2 limitations raise
:exc:`KnownLimitationError` (never a truncated list).

CANDIDATE/RESEARCH, PROVISIONAL: the v2 codes and detail layout are not
frozen. No v2 snapshot is loaded by a real run yet (see ``adapter_v2``).
"""

from __future__ import annotations

from msgloom.contracts import Limitation, VersionRef
from msgloom.preparation import PreparedRecord
from msgloom.triage import (
    Priority,
    SourceDisposition,
    SourceDispositionKind,
    TopicCandidate,
    TriageCandidate,
)
from msgloom.triage_input.codec_v2 import (
    DigestMismatchError,
    TriageInputV2Codec,
    TriageInputV2Error,
)
from msgloom.triage_input.models_v2 import TriageInputSnapshot as V2Snapshot
from msgloom.working_context import FileCaptureState, WorkingContextSnapshot

MAX_PROPAGATED_LIMITATIONS = 64

V2_INCOMPLETE_CODE = "triage-v2-input-incomplete"
V2_COVERAGE_CODE = "triage-v2-coverage-failure"
V2_HELD_CODE = "triage-v2-held-source"
V2_UPSTREAM_PREFIX = "triage-v2-upstream-"

_CONTEXT_COMPLETE_STATES = {
    FileCaptureState.CAPTURED,
    FileCaptureState.EMPTY,
}


class KnownLimitationError(ValueError):
    """Expose one stable classification for trusted limitation rejection."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class V2ProvenanceError(KnownLimitationError):
    """Reject v2 input whose provenance is missing, forged or invalid.

    ``code`` is one of ``v2-provenance-missing``, ``v2-provenance-forged``
    or ``v2-provenance-invalid``. The message carries no input value.
    """


def verify_v2_provenance(
    snapshot: object, expected_snapshot_sha256: str | None = None
) -> V2Snapshot:
    """Return the verified v2 snapshot or raise :exc:`V2ProvenanceError`.

    The snapshot is encoded and decoded again by the v2 codec. That check
    validates the whole model and recomputes the binding, configuration and
    snapshot digests, so a value built without validation cannot pass. If
    ``expected_snapshot_sha256`` is set, it must equal the saved digest.
    """
    if not isinstance(snapshot, V2Snapshot):
        raise V2ProvenanceError("v2-provenance-missing")
    for name in ("binding_sha256", "configuration_sha256", "snapshot_sha256"):
        value = getattr(snapshot, name, None)
        if not isinstance(value, str) or not value:
            raise V2ProvenanceError("v2-provenance-missing")
    codec = TriageInputV2Codec()
    code = "v2-provenance-invalid"
    try:
        return _expected_digest(
            codec.decode(codec.encode(snapshot)), expected_snapshot_sha256
        )
    except DigestMismatchError:
        code = "v2-provenance-forged"
    except (TriageInputV2Error, ValueError, TypeError, AttributeError):
        pass
    # Raised outside the handlers so no input-bearing context is chained.
    raise V2ProvenanceError(code)


def _expected_digest(snapshot: V2Snapshot, expected: str | None) -> V2Snapshot:
    if expected is not None and snapshot.snapshot_sha256 != expected:
        raise DigestMismatchError
    return snapshot


def v2_input_limitations(
    snapshot: object, expected_snapshot_sha256: str | None = None
) -> tuple[Limitation, ...]:
    """Derive stable A3 limitations from one upstream v2 snapshot.

    The snapshot is verified first (see :func:`verify_v2_provenance`). An
    empty result means the snapshot is complete and holds no source.
    """
    verified = verify_v2_provenance(snapshot, expected_snapshot_sha256)
    origin = f"snapshot_sha256={verified.snapshot_sha256}"
    values: list[Limitation] = []
    if not verified.complete:
        values.append(
            Limitation(
                V2_INCOMPLETE_CODE,
                f"{origin} binding_sha256={verified.binding_sha256}",
            )
        )
    values.extend(
        Limitation(f"{V2_UPSTREAM_PREFIX}{item.code}", item.detail)
        for item in verified.limitations
    )
    values.extend(
        Limitation(
            V2_COVERAGE_CODE,
            f"unit_id={item.unit_id} reason={item.reason} "
            f"remaining={item.remaining_occurrences} "
            f"remaining_sha256={item.remaining_sha256} {origin}",
        )
        for item in verified.failures
    )
    values.extend(
        Limitation(
            V2_HELD_CODE,
            f"source={item.prepared.result_id} filter={item.filter.result_id} "
            f"reasons={','.join(reason.value for reason in item.reasons)} {origin}",
        )
        for item in verified.held
    )
    ordered = sorted(set(values), key=lambda item: (item.code, item.detail))
    if len(ordered) > MAX_PROPAGATED_LIMITATIONS:
        raise KnownLimitationError("v2-limitation-overflow")
    return tuple(ordered)


def working_context_limitations(
    snapshot: WorkingContextSnapshot,
) -> tuple[Limitation, ...]:
    """Derive privacy-safe gaps from the exact saved working-context snapshot."""
    values: list[Limitation] = []
    for item in snapshot.files:
        if item.limitations:
            values.extend(
                Limitation(
                    code=f"working-context-{limitation.code}",
                    detail=limitation.detail,
                )
                for limitation in item.limitations
            )
            continue
        if item.state not in _CONTEXT_COMPLETE_STATES:
            values.append(
                Limitation(
                    code=f"working-context-{item.state.value}",
                    detail=(
                        "Selected working context has state "
                        f"{item.state.value.replace('_', '-')}"
                    ),
                )
            )
    return _bounded(values, "working-context-limitation-overflow")


def merge_trusted_source_limitations(
    candidate: TriageCandidate,
    records: tuple[PreparedRecord, ...],
) -> tuple[TriageCandidate, tuple[Limitation, ...]]:
    """Merge saved source gaps without trusting the model to repeat them."""
    by_source = {record.source: record.limitations for record in records}
    if len(by_source) != len(records):
        raise KnownLimitationError("duplicate-prepared-source")

    topics = tuple(_merge_topic(topic, by_source) for topic in candidate.topics)
    operation: list[Limitation] = []
    dispositions = []
    for disposition in candidate.dispositions:
        known = by_source.get(disposition.source_ref, ())
        if known and disposition.kind is not SourceDispositionKind.EXCLUDED:
            operation.extend(known)
        dispositions.append(_review_incomplete_disposition(disposition, known))
    return (
        candidate.model_copy(
            update={"topics": topics, "dispositions": tuple(dispositions)}
        ),
        _bounded(operation, "operation-limitation-overflow"),
    )


def _merge_topic(
    topic: TopicCandidate,
    by_source: dict[VersionRef, tuple[Limitation, ...]],
) -> TopicCandidate:
    known = [
        limitation
        for source in topic.source_refs
        for limitation in by_source.get(source, ())
    ]
    if known and topic.priority is Priority.LOW_VALUE:
        raise KnownLimitationError("incomplete-source-low-value")
    limitations = _unique((*topic.limitations, *known))
    if len(limitations) > MAX_PROPAGATED_LIMITATIONS:
        raise KnownLimitationError("topic-limitation-overflow")
    return topic.model_copy(update={"limitations": limitations})


def _review_incomplete_disposition(
    disposition: SourceDisposition,
    known: tuple[Limitation, ...],
) -> SourceDisposition:
    if not known or disposition.kind is not SourceDispositionKind.NO_REPORTABLE_CONTENT:
        return disposition
    return disposition.model_copy(
        update={
            "kind": SourceDispositionKind.REVIEW_REQUIRED,
            "reason": "Known incomplete source evidence requires review",
        }
    )


def _bounded(values: list[Limitation], code: str) -> tuple[Limitation, ...]:
    if len(values) > MAX_PROPAGATED_LIMITATIONS:
        raise KnownLimitationError(code)
    return tuple(values)


def _unique(values: tuple[Limitation, ...]) -> tuple[Limitation, ...]:
    result: list[Limitation] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)

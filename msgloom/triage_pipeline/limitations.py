"""Trusted limitation propagation for the A3 producer."""

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
from msgloom.working_context import FileCaptureState, WorkingContextSnapshot

MAX_PROPAGATED_LIMITATIONS = 64

_CONTEXT_COMPLETE_STATES = {
    FileCaptureState.CAPTURED,
    FileCaptureState.EMPTY,
}


class KnownLimitationError(ValueError):
    """Expose one stable classification for trusted limitation rejection."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


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

"""
Strict loader for saved upstream results, v1 and v2 (A3 owner).

:class:`~msgloom.triage_pipeline.io_mixin._TriageIOMixin` calls
:func:`load_values` for each upstream family (``prepared``,
``filter_result`` and ``group_result``). This module lives beside the
adapter because ``io_mixin.py`` is near the 500-line module cap.

Dispatch (explicit, never inferred from the payload alone):

* Refs that are all version ``1``, or have no family ref, go to the
  unchanged v1 path. It is the former ``_load_values`` body: load by the
  exact semantic reference and check the Python type.
* Refs that are all version ``2`` go to the strict v2 path. The caller
  names a v2 model type (:class:`Prepared`, :class:`FilterResult` or
  :class:`GroupResult`) as ``expected``.
* A mix of ``1`` and ``2`` raises :exc:`MixedVersionsError`. Any other
  version (for example ``3``) raises :exc:`UnsupportedVersionError`.
* v2 refs with a v1 ``expected`` type raise :exc:`LossyProjectionError`.
  v1 refs with a v2 ``expected`` type raise :exc:`HistoricalVersionError`.
  No v2 value is ever converted to a v1 record, so no status, limitation
  or incomplete state is dropped.

The v2 path checks, in this order: the declared byte count against the
source bound, the semantic reference against the result, then the loaded
payload: size bound, SHA-256 and byte count of the saved reference, UTF-8
JSON without duplicate key, float or ``NaN``, canonical form, mixed
version markers, the header pair, strict model validation (an unknown
field is an :exc:`ExtraFieldError`), and last that the saved result status
and limitations equal the decoded ones.

The persistence layer may return canonical ``bytes`` or an instance of the
v2 model. An instance is re-encoded and decoded again, so a value built
without validation cannot pass. Any other type raises
:exc:`InvalidValueError`.

Failure handling: errors are the typed, fixed-message classes of
:mod:`~msgloom.triage_input.adapter_v2` and
:mod:`~msgloom.triage_input.codec_v2`. None carries a value, a key or a
chained cause. Errors raised by persistence itself pass through unchanged.

Exception delta for v1 input: :func:`load_values` first classifies the refs.
A v1 mix or an unknown version raises the typed adapter errors instead of
loading. The handler cannot reach that case, because ``admit_upstream`` has
already checked a superset of these refs.

CANDIDATE/RESEARCH, PROVISIONAL: the handler still stops an upstream-v2 run
as INCOMPLETE before this loader runs (see ``adapter_v2``), so the v2 branch
has no caller in a real run and only the unit tests reach it. No v2 claim
path, builder or provider call exists yet. The ``phase1`` semantic registry
has no persistence codec for ``prepared@2``, ``filter_result@2`` or
``group_result@2`` yet, so a real SQLite load of a v2 ref is not supported.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from typing import Any, Protocol

from pydantic import ValidationError

from msgloom.a2_kedro.contracts.codec import (
    MAX_CANONICAL_BYTES,
    A2ContractError,
    canonical_json_bytes,
)
from msgloom.a2_kedro.contracts.result_base import ResultModel
from msgloom.a2_kedro.contracts.results import FilterResult, GroupResult, Prepared
from msgloom.a2_kedro.contracts.schema_ids import HISTORICAL_READ_ONLY, STAGE_SCHEMAS
from msgloom.contracts import ResultRef, SemanticDataRef, StageResult
from msgloom.triage_input.adapter_v2 import (
    LossyProjectionError,
    MixedVersionsError,
    UpstreamStateError,
    _check_v2_result,
    classify_upstream,
)
from msgloom.triage_input.codec_v2 import (
    DigestMismatchError,
    ExtraFieldError,
    HistoricalVersionError,
    InvalidValueError,
    MalformedInputError,
    NonCanonicalError,
    OversizedInputError,
    SchemaViolationError,
    TriageInputV2Error,
    UnknownKindError,
    UnknownVersionError,
    _no_duplicates,
    _no_number_constant,
)

#: v2 model type for each family kind. These are the v2 ``expected`` types.
V2_MODELS: Mapping[str, type[ResultModel]] = {
    "prepared": Prepared,
    "filter_result": FilterResult,
    "group_result": GroupResult,
}
_V2_KINDS: Mapping[type, str] = {model: kind for kind, model in V2_MODELS.items()}

#: Source size bound of one upstream v2 payload.
MAX_SOURCE_BYTES = MAX_CANONICAL_BYTES


class _SemanticLoader(Protocol):
    async def load_semantic_data(self, reference: SemanticDataRef) -> object: ...


def _parse(payload: bytes) -> dict[str, Any]:
    failure: TriageInputV2Error | None = None
    value: Any = None
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_no_duplicates,
            parse_constant=_no_number_constant,
            parse_float=_no_number_constant,
        )
    except TriageInputV2Error as error:
        failure = error
    except (UnicodeDecodeError, ValueError, RecursionError):
        failure = MalformedInputError()
    if failure is not None:
        # Raised outside the handler so no input-bearing context is chained.
        raise failure
    if not isinstance(value, dict):
        raise MalformedInputError
    try:
        canonical = canonical_json_bytes(value, max_bytes=MAX_SOURCE_BYTES)
    except A2ContractError:
        canonical = b""
    if canonical != payload:
        raise NonCanonicalError
    return value


def _check_header(value: dict[str, Any], kind: str) -> None:
    header = value.get("header")
    if "schema_version" in value:
        raise MixedVersionsError if header is not None else HistoricalVersionError
    if not isinstance(header, dict):
        raise SchemaViolationError
    found_kind, found_version = header.get("kind"), header.get("version")
    if not isinstance(found_kind, str) or not isinstance(found_version, str):
        raise SchemaViolationError
    pair = (found_kind, found_version)
    if pair == (kind, STAGE_SCHEMAS[kind]):
        return
    if pair in HISTORICAL_READ_ONLY:
        raise HistoricalVersionError
    raise UnknownVersionError if found_kind == kind else UnknownKindError


def decode_v2[M: ResultModel](
    payload: bytes, expected: type[M], semantic: SemanticDataRef
) -> M:
    """Return the verified v2 record in ``payload`` or raise a typed error."""
    kind = _V2_KINDS.get(expected)
    if kind is None:
        raise InvalidValueError
    if len(payload) > MAX_SOURCE_BYTES:
        raise OversizedInputError
    if (
        len(payload) != semantic.byte_count
        or sha256(payload).hexdigest() != semantic.sha256
    ):
        raise DigestMismatchError
    _check_header(_parse(payload), kind)
    failure: TriageInputV2Error | None = None
    record: M | None = None
    try:
        record = expected.model_validate_json(payload, strict=True)
    except ValidationError as error:
        types = {item["type"] for item in error.errors(include_input=False)}
        failure = (
            ExtraFieldError() if "extra_forbidden" in types else SchemaViolationError()
        )
    except ValueError:
        failure = SchemaViolationError()
    if failure is not None or record is None:
        raise failure or SchemaViolationError()
    return record


def _payload_of(value: object, expected: type[ResultModel]) -> bytes:
    if isinstance(value, bytes | bytearray):
        return bytes(value)
    if not isinstance(value, expected):
        raise InvalidValueError
    encoded = b""
    try:
        encoded = value.encode()
    except (A2ContractError, ValueError, TypeError, RecursionError):
        encoded = b""
    if not encoded:
        raise InvalidValueError
    return encoded


def _check_saved(reference: ResultRef, saved: StageResult) -> SemanticDataRef:
    semantic = saved.semantic_data_ref
    if semantic is None:
        raise ValueError("upstream semantic reference is missing")
    if (semantic.kind, semantic.schema_version) != (
        reference.kind,
        reference.schema_version,
    ):
        raise UpstreamStateError
    if semantic.byte_count > MAX_SOURCE_BYTES:
        raise OversizedInputError
    return semantic


async def _load_v2[T](
    persistence: _SemanticLoader,
    refs: tuple[ResultRef, ...],
    by_id: dict[str, StageResult],
    expected: type[T],
) -> tuple[T, ...]:
    kind = _V2_KINDS.get(expected)
    if kind is None:
        raise LossyProjectionError(("v2-references",))
    values: list[T] = []
    for ref in refs:
        if ref.kind != kind:
            raise InvalidValueError
        saved = by_id[ref.result_id]
        semantic = _check_saved(ref, saved)
        _check_v2_result(ref, saved)  # failures, status vs limitations
        loaded = await persistence.load_semantic_data(semantic)
        model = V2_MODELS[kind]
        record: Any = decode_v2(_payload_of(loaded, model), model, semantic)
        if saved.status is not record.status or set(saved.limitations) != set(
            record.limitations
        ):
            raise UpstreamStateError
        values.append(record)
    return tuple(values)


async def _load_v1[T](
    persistence: _SemanticLoader,
    refs: tuple[ResultRef, ...],
    by_id: dict[str, StageResult],
    expected: type[T],
) -> tuple[T, ...]:
    values: list[T] = []
    for ref in refs:
        semantic = by_id[ref.result_id].semantic_data_ref
        if semantic is None:
            raise ValueError("upstream semantic reference is missing")
        value = await persistence.load_semantic_data(semantic)
        if not isinstance(value, expected):
            raise TypeError("upstream semantic value has unexpected type")
        values.append(value)
    return tuple(values)


async def load_values[T](
    persistence: _SemanticLoader,
    refs: tuple[ResultRef, ...],
    by_id: dict[str, StageResult],
    expected: type[T],
) -> tuple[T, ...]:
    """Load one upstream family through the reader that owns its version."""
    version = classify_upstream(refs)
    if version == "2":
        return await _load_v2(persistence, refs, by_id, expected)
    if expected in _V2_KINDS and refs:
        raise HistoricalVersionError
    return await _load_v1(persistence, refs, by_id, expected)

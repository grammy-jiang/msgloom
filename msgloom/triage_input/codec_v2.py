"""
Canonical bounded codec for ``triage_input@2`` (A3 owner).

This codec is separate from the v1 codec in
:mod:`~msgloom.triage_input.codec`. It reads and writes only
``triage_input@2``. It refuses ``triage_input@1`` data and any other
``(kind, version)`` pair with a typed error.

Rules, in the order the decoder applies them:

1. Input above the byte bound is refused before any parse.
2. The bytes must parse as UTF-8 JSON with no duplicate key, no float and
   no ``NaN``.
3. The bytes must equal the canonical encoding of what they parse to
   (sorted keys, no whitespace, no escaped-but-equal text).
4. The header pair must be exactly ``triage_input@2``.
5. Every nested reference ``(kind, schema_version)`` pair must sit in the
   closed allowlists :data:`ALLOWED_REF_PAIRS`. ``prepared``,
   ``filter_result`` and ``group_result`` are approved only at ``2``.
6. Strict model validation. An unknown field is an :exc:`ExtraFieldError`.
7. The three digests are recomputed under v2 domains and must match.
8. Every saved part is ``pending`` and the payload fits the configured
   snapshot bound.

Failure handling: every error is a subclass of :exc:`TriageInputV2Error`
with a fixed message. No error carries a value, a key, a field path or a
chained input-bearing exception.

CANDIDATE/RESEARCH, PROVISIONAL: digest domain names and bounds are not
frozen. See ``docs/notes/a2-v2-a3-triage-input-v2.md``.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from pydantic import ValidationError

from msgloom.a2_kedro.contracts.codec import (
    MAX_CANONICAL_BYTES,
    A2ContractError,
    canonical_json_bytes,
    domain_sha256,
)
from msgloom.a2_kedro.contracts.schema_ids import STAGE_SCHEMAS
from msgloom.triage_input.models_v2 import (
    PART_KIND,
    PART_VERSION,
    RULE_KIND,
    RULE_VERSION,
    TRIAGE_INPUT_V2_KIND,
    TRIAGE_INPUT_V2_VERSION,
    PartState,
    SelectionBinding,
    SnapshotConfig,
    TriageInputSnapshot,
)

MAX_TRIAGE_INPUT_V2_BYTES = MAX_CANONICAL_BYTES

#: Closed allowlist of accepted header pairs.
ALLOWED_HEADER_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {(TRIAGE_INPUT_V2_KIND, TRIAGE_INPUT_V2_VERSION)}
)
#: Closed allowlist of nested reference pairs. A3 binds only these.
ALLOWED_REF_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("prepared", STAGE_SCHEMAS["prepared"]),
        ("filter_result", STAGE_SCHEMAS["filter_result"]),
        ("group_result", STAGE_SCHEMAS["group_result"]),
        (RULE_KIND, RULE_VERSION),
        (PART_KIND, PART_VERSION),
    }
)
_REF_KINDS = frozenset(kind for kind, _ in ALLOWED_REF_PAIRS)

BINDING_DOMAIN = "triage-input-binding@2"
CONFIGURATION_DOMAIN = "triage-input-configuration@2"
SNAPSHOT_DOMAIN = "triage-input-snapshot@2"


class TriageInputV2Error(ValueError):
    """Base of all typed errors. The message is fixed and carries no value."""

    MESSAGE: ClassVar[str] = "triage_input@2 data was rejected"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class OversizedInputError(TriageInputV2Error):
    MESSAGE = "triage_input@2 data exceeds a size bound"


class MalformedInputError(TriageInputV2Error):
    MESSAGE = "triage_input@2 data is not valid UTF-8 JSON"


class DuplicateKeyError(TriageInputV2Error):
    MESSAGE = "triage_input@2 data repeats an object key"


class NonCanonicalError(TriageInputV2Error):
    MESSAGE = "triage_input@2 data is not in canonical form"


class UnknownKindError(TriageInputV2Error):
    MESSAGE = "triage_input@2 data names a kind that is not allowed"


class UnknownVersionError(TriageInputV2Error):
    MESSAGE = "triage_input@2 data names a version that is not allowed"


class HistoricalVersionError(UnknownVersionError):
    MESSAGE = "triage_input@1 data needs the v1 reader"


class ExtraFieldError(TriageInputV2Error):
    MESSAGE = "triage_input@2 data has a field that is not in the contract"


class SchemaViolationError(TriageInputV2Error):
    MESSAGE = "triage_input@2 data does not match the contract"


class DigestMismatchError(TriageInputV2Error):
    MESSAGE = "triage_input@2 digest does not match its content"


class InvalidValueError(TriageInputV2Error):
    MESSAGE = "triage_input@2 encode needs a valid TriageInputSnapshot"


def binding_digest(binding: SelectionBinding) -> str:
    """Return the v2 selection-binding digest (own domain, not the v1 hash)."""
    return domain_sha256(BINDING_DOMAIN, binding.model_dump(mode="json"))


def configuration_digest(configuration: SnapshotConfig) -> str:
    """Return the v2 configuration digest."""
    return domain_sha256(CONFIGURATION_DOMAIN, configuration.model_dump(mode="json"))


def snapshot_digest(snapshot: TriageInputSnapshot) -> str:
    """Return the v2 snapshot digest over everything but itself."""
    data = snapshot.model_dump(mode="json")
    data["snapshot_sha256"] = ""
    return domain_sha256(SNAPSHOT_DOMAIN, data)


def seal_snapshot(snapshot: TriageInputSnapshot) -> TriageInputSnapshot:
    """Return ``snapshot`` with all three digests recomputed."""
    inner = snapshot.model_copy(
        update={
            "binding_sha256": binding_digest(snapshot.binding),
            "configuration_sha256": configuration_digest(snapshot.configuration),
        }
    )
    return inner.model_copy(update={"snapshot_sha256": snapshot_digest(inner)})


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise DuplicateKeyError
    return dict(pairs)


def _no_number_constant(_name: str) -> Any:
    raise NonCanonicalError


def _parse(payload: bytes, max_bytes: int) -> Any:
    if len(payload) > max_bytes:
        raise OversizedInputError
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
    try:
        canonical = canonical_json_bytes(value, max_bytes=max_bytes)
    except A2ContractError:
        canonical = b""
    if canonical != payload:
        raise NonCanonicalError
    return value


def _check_header(value: Any) -> None:
    header = value.get("header") if isinstance(value, dict) else None
    if not isinstance(header, dict):
        if isinstance(value, dict) and "schema_version" in value:
            raise HistoricalVersionError
        raise SchemaViolationError
    kind, version = header.get("kind"), header.get("version")
    if not isinstance(kind, str) or not isinstance(version, str):
        raise SchemaViolationError
    if (kind, version) in ALLOWED_HEADER_PAIRS:
        return
    if kind in {pair[0] for pair in ALLOWED_HEADER_PAIRS}:
        raise UnknownVersionError
    raise UnknownKindError


def _check_ref_pairs(value: Any) -> None:
    if isinstance(value, list):
        for item in value:
            _check_ref_pairs(item)
        return
    if not isinstance(value, dict):
        return
    kind, version = value.get("kind"), value.get("schema_version")
    is_ref = isinstance(kind, str) and isinstance(version, str)
    if is_ref and (kind, version) not in ALLOWED_REF_PAIRS:
        raise UnknownVersionError if kind in _REF_KINDS else UnknownKindError
    for key, item in value.items():
        if key != "header":
            _check_ref_pairs(item)


def _classify(error: ValidationError) -> TriageInputV2Error:
    kinds = {item["type"] for item in error.errors(include_input=False)}
    return ExtraFieldError() if "extra_forbidden" in kinds else SchemaViolationError()


def _verify(snapshot: TriageInputSnapshot, size: int) -> None:
    if (
        snapshot.binding_sha256 != binding_digest(snapshot.binding)
        or snapshot.configuration_sha256 != configuration_digest(snapshot.configuration)
        or snapshot.snapshot_sha256 != snapshot_digest(snapshot)
    ):
        raise DigestMismatchError
    if any(part.state is not PartState.PENDING for part in snapshot.parts):
        raise SchemaViolationError
    if size > snapshot.configuration.max_snapshot_bytes:
        raise OversizedInputError


class TriageInputV2Codec:
    """Canonical validating codec for ``triage_input@2`` semantic data."""

    kind = TRIAGE_INPUT_V2_KIND
    schema_version = TRIAGE_INPUT_V2_VERSION
    python_type = TriageInputSnapshot
    max_bytes = MAX_TRIAGE_INPUT_V2_BYTES

    def encode(self, value: object) -> bytes:
        """Fully revalidate ``value`` and return canonical UTF-8 JSON."""
        if not isinstance(value, TriageInputSnapshot):
            raise InvalidValueError
        payload = b""
        try:
            data = value.model_dump(mode="json", warnings="error")
            payload = canonical_json_bytes(data, max_bytes=2**31)
        except (A2ContractError, ValueError, TypeError, RecursionError):
            payload = b""
        if not payload:
            raise InvalidValueError
        self.decode(payload)
        return payload

    def decode(self, payload: bytes) -> TriageInputSnapshot:
        """Decode exact canonical bytes. Refuse everything else."""
        value = _parse(payload, self.max_bytes)
        _check_header(value)
        _check_ref_pairs(value)
        failure: TriageInputV2Error | None = None
        snapshot: TriageInputSnapshot | None = None
        try:
            snapshot = TriageInputSnapshot.model_validate_json(payload, strict=True)
        except ValidationError as error:
            failure = _classify(error)
        if failure is not None or snapshot is None:
            raise failure or SchemaViolationError()
        _verify(snapshot, len(payload))
        return snapshot

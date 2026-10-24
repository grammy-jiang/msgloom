"""C0-17b: canonical ``triage_input@2`` codec. Synthetic data only."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import canonical_json_bytes
from msgloom.triage_input import TriageInputCodec, build_triage_input
from msgloom.triage_input.codec_v2 import (
    ALLOWED_HEADER_PAIRS,
    ALLOWED_REF_PAIRS,
    DigestMismatchError,
    DuplicateKeyError,
    ExtraFieldError,
    HistoricalVersionError,
    InvalidValueError,
    MalformedInputError,
    NonCanonicalError,
    OversizedInputError,
    SchemaViolationError,
    TriageInputV2Codec,
    TriageInputV2Error,
    UnknownKindError,
    UnknownVersionError,
    binding_digest,
    seal_snapshot,
    snapshot_digest,
)
from msgloom.triage_input.models_v2 import TriageInputSnapshot
from tests.a2_kedro.helpers import check
from tests.a2_kedro.test_c0_17a import (
    SECRET,
    edit,
    incomplete_data,
    load,
    snapshot_data,
)
from tests.triage_input.helpers import config, record, selection

CODEC = TriageInputV2Codec()
#: Pinned digests of the synthetic fixture (PROVISIONAL wire decision).
GOLDEN_BINDING = "21407dce84e36e04ed8aae37f8edb9855a3e1b8e8ea64974bb33987375d56c34"
GOLDEN_SNAPSHOT = "f2d1417e4b7825821260644f06ef553e29c5ac165d9f0b34c40bf48a7c6a99e4"


def sealed(data: dict[str, Any] | None = None) -> TriageInputSnapshot:
    return seal_snapshot(load(data or snapshot_data()))


def payload_of(data: dict[str, Any]) -> bytes:
    """Return canonical bytes of ``data`` without any codec validation."""
    return canonical_json_bytes(data, max_bytes=2**31)


def resealed_bytes(data: dict[str, Any]) -> bytes:
    return CODEC.encode(sealed(data))


def rejects(payload: bytes, error: type[TriageInputV2Error]) -> TriageInputV2Error:
    """Assert ``decode`` raises exactly ``error`` and leaks nothing."""
    with pytest.raises(error) as caught:
        CODEC.decode(payload)
    found = caught.value
    check(type(found) is error, f"expected {error.__name__}")
    check(found.__cause__ is None, "no chained cause")
    check(found.__context__ is None, "no chained context")
    check(not found.args[0].count(SECRET), "message is fixed")
    return found


@pytest.mark.parametrize("make", [snapshot_data, incomplete_data])
def test_strict_canonical_round_trip(make: Any, tmp_path: Path) -> None:
    value = sealed(make())
    data = CODEC.encode(value)
    check(CODEC.decode(data) == value, "decode(encode(x)) == x")
    check(CODEC.encode(CODEC.decode(data)) == data, "re-encode is byte-identical")
    check(canonical_json_bytes(json.loads(data), max_bytes=2**31) == data, "canonical")
    path = tmp_path / "snapshot.json"
    path.write_bytes(data)
    check(CODEC.decode(path.read_bytes()) == value, "file round trip")
    check(sha256(data).hexdigest() == sha256(CODEC.encode(value)).hexdigest(), "stable")


def test_codec_registry_shape_and_allowlists_are_closed() -> None:
    check(CODEC.kind == "triage_input", "kind")
    check(CODEC.schema_version == "2", "version")
    check(CODEC.python_type is TriageInputSnapshot, "python type")
    check(ALLOWED_HEADER_PAIRS == {("triage_input", "2")}, "header allowlist")
    check(
        ALLOWED_REF_PAIRS
        == {
            ("prepared", "2"),
            ("filter_result", "2"),
            ("group_result", "2"),
            ("triage_rules", "2"),
            ("triage_input_part", "2"),
        },
        "ref allowlist",
    )
    for pair in (("prepared", "1"), ("filter_result", "1"), ("group_result", "1")):
        check(pair not in ALLOWED_REF_PAIRS, "historical pair is not allowed")


def test_digests_are_domain_separated_and_pinned() -> None:
    value = sealed()
    plain = sha256(
        canonical_json_bytes(value.binding.model_dump(mode="json"), max_bytes=2**31)
    ).hexdigest()
    check(binding_digest(value.binding) != plain, "domain separated from raw hash")
    check(value.binding_sha256 == binding_digest(value.binding), "binding sealed")
    check(value.snapshot_sha256 == snapshot_digest(value), "snapshot sealed")
    check(binding_digest(value.binding) == GOLDEN_BINDING, "binding golden")
    check(value.snapshot_sha256 == GOLDEN_SNAPSHOT, "snapshot golden")


def test_binding_digest_covers_every_binding_field() -> None:
    base = binding_digest(sealed().binding)
    for path, value in (
        ("binding.roles.0.role", "earlier-context"),
        ("binding.working_context.version", "v2"),
        ("binding.versions.model.identity", "other"),
        ("binding.rule.sha256", "1" * 64),
        ("binding.prepared.0.data.byte_count", 101),
        ("binding.filters.1.data.sha256", "1" * 64),
        ("binding.groups.0.result.result_id", "a2-accepted:" + "1" * 64),
    ):
        data = edit(snapshot_data(), path, value)
        if path == "binding.rule.sha256":
            data = edit(data, "held.0.rule.sha256", value)
        if path == "binding.groups.0.result.result_id":
            data = edit(data, "units.0.group.result_id", value)
        changed = binding_digest(sealed(data).binding)
        check(changed != base, f"binding digest ignores {path}")


def test_unsealed_or_tampered_digests_are_rejected() -> None:
    value = sealed()
    payload = CODEC.encode(value)
    for field in ("binding_sha256", "configuration_sha256", "snapshot_sha256"):
        data = json.loads(payload)
        data[field] = "1" * 64
        rejects(payload_of(data), DigestMismatchError)
    data = json.loads(payload)
    data["complete"] = True
    data["units"][0]["occurrence_count"] = 13
    rejects(payload_of(data), DigestMismatchError)
    with pytest.raises(DigestMismatchError):
        CODEC.encode(load(snapshot_data()))


def test_unknown_version_and_kind_are_typed() -> None:
    good = json.loads(CODEC.encode(sealed()))
    for version in ("1", "3", "20"):
        data = edit(good, "header.version", version)
        rejects(payload_of(data), UnknownVersionError)
    for kind in ("prepared", "triage_inputs", "Triage_Input"):
        rejects(payload_of(edit(good, "header.kind", kind)), UnknownKindError)
    for path, value, error in (
        ("binding.prepared.0.result.schema_version", "1", UnknownVersionError),
        ("binding.prepared.0.data.schema_version", "3", UnknownVersionError),
        ("binding.filters.0.result.kind", "filter_results", UnknownKindError),
        ("binding.groups.0.data.kind", "other", UnknownKindError),
        ("binding.rule.schema_version", "1", UnknownVersionError),
        ("parts.0.data.schema_version", "1", UnknownVersionError),
        ("units.0.prepared.0.schema_version", "1", UnknownVersionError),
    ):
        rejects(payload_of(edit(good, path, value)), error)


def test_v1_payload_is_historical_and_v1_codec_rejects_v2() -> None:
    v1 = build_triage_input(selection((record("one"),)), config())
    v1_bytes = TriageInputCodec().encode(v1)
    rejects(v1_bytes, HistoricalVersionError)
    check(issubclass(HistoricalVersionError, UnknownVersionError), "subclass")
    with pytest.raises(ValueError, match="failed validation"):
        TriageInputCodec().decode(CODEC.encode(sealed()))
    check(TriageInputCodec().decode(v1_bytes) == v1, "v1 reader still reads v1")


def test_non_canonical_bytes_are_rejected() -> None:
    data = CODEC.encode(sealed())
    value = json.loads(data)
    cases = [
        json.dumps(value).encode(),
        json.dumps(value, indent=2, sort_keys=True).encode(),
        b" " + data,
        data + b"\n",
        data.replace(b'"complete":true', b'"complete" : true'),
        data.replace(b"synthetic", b"\\u0073ynthetic", 1),
        data.replace(b'"max_parts_per_unit":8', b'"max_parts_per_unit":8.0'),
        data.replace(b'"occurrence_count":12', b'"occurrence_count":1.2e1'),
        data.replace(b'"occurrence_count":12', b'"occurrence_count":NaN'),
    ]
    for case in cases:
        check(case != data, "mutation changed bytes")
        rejects(case, NonCanonicalError)


def test_duplicate_keys_are_rejected() -> None:
    data = CODEC.encode(sealed())
    dup = data.replace(b'"complete":true', b'"complete":true,"complete":false')
    rejects(dup, DuplicateKeyError)
    nested = data.replace(b'"kind":"triage_input"', b'"kind":"triage_input","kind":"x"')
    rejects(nested, DuplicateKeyError)


def test_extra_fields_are_rejected_without_echo() -> None:
    good = json.loads(CODEC.encode(sealed()))
    for path in ("extra", "binding.extra", "units.0.extra", "header.extra"):
        data = edit(good, path, SECRET)
        error = rejects(payload_of(data), ExtraFieldError)
        check(SECRET not in str(error) + repr(error), "no echo")
    key_leak = json.loads(json.dumps(good))
    key_leak["binding"]["roles"][0]["extra_" + SECRET] = 1
    error = rejects(payload_of(key_leak), ExtraFieldError)
    check(SECRET not in str(error) + repr(error), "key name not echoed")


def test_schema_violations_are_typed_and_do_not_echo() -> None:
    good = json.loads(CODEC.encode(sealed()))
    value_leak = edit(good, "binding.versions.prompt.identity", SECRET + "\n")
    error = rejects(payload_of(value_leak), SchemaViolationError)
    check(SECRET not in str(error) + repr(error), "value not echoed")
    for path, value in (
        ("binding.roles.0.role", SECRET),
        ("parts.0.state", SECRET),
        ("complete", SECRET),
        ("configuration.max_part_bytes", True),
    ):
        error = rejects(payload_of(edit(good, path, value)), SchemaViolationError)
        check(SECRET not in str(error) + repr(error), "value not echoed")
    for raw in (b"[]", b"{}", b'{"header":1}', b'{"header":{"kind":1,"version":2}}'):
        rejects(raw, SchemaViolationError)


def test_malformed_and_oversized_input_is_rejected() -> None:
    for raw in (
        b"",
        b"\xff\xfe",
        b"\xef\xbb\xbf" + CODEC.encode(sealed()),
        b"{",
        b"nul",
        b"[" * 100_000,
        b'{"a":' * 5000,
    ):
        rejects(raw, MalformedInputError)
    rejects(b"x" * (CODEC.max_bytes + 1), OversizedInputError)
    small = TriageInputV2Codec()
    small.max_bytes = 100
    with pytest.raises(OversizedInputError):
        small.decode(CODEC.encode(sealed()))
    data = snapshot_data()
    data["configuration"]["max_snapshot_bytes"] = 4096
    over = sealed(data)
    check(len(CODEC.encode(sealed())) > 4096, "fixture exceeds the tight bound")
    with pytest.raises(OversizedInputError):
        CODEC.encode(over)


def test_encode_refuses_wrong_types_and_bypassed_models() -> None:
    for bad in (None, {}, "x", b"x", object()):
        with pytest.raises(InvalidValueError):
            CODEC.encode(bad)
    v1 = build_triage_input(selection((record("one"),)), config())
    with pytest.raises(InvalidValueError):
        CODEC.encode(v1)
    broken = sealed().model_copy(update={"complete": False})
    with pytest.raises(SchemaViolationError):
        CODEC.encode(broken)
    stale = sealed().model_copy(update={"binding_sha256": "1" * 64})
    with pytest.raises(DigestMismatchError):
        CODEC.encode(stale)
    badpart = sealed(edit(snapshot_data(), "parts.0.state", "complete"))
    with pytest.raises(SchemaViolationError):
        CODEC.encode(badpart)


def test_every_sampled_byte_mutation_and_truncation_is_rejected() -> None:
    data = CODEC.encode(sealed(incomplete_data()))
    for index in range(0, len(data), 5):
        mutated = bytearray(data)
        mutated[index] ^= 0x01
        try:
            CODEC.decode(bytes(mutated))
        except TriageInputV2Error:
            continue
        pytest.fail("a mutated payload was accepted")
    for cut in range(0, len(data), 97):
        with pytest.raises(TriageInputV2Error):
            CODEC.decode(data[:cut])

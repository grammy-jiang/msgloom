"""Validated codecs for provider-neutral persistence records."""

from __future__ import annotations

import json
from collections.abc import Iterable

from msgloom.contracts import Diagnostic, Failure, Limitation, ResultRef, VersionRef


def _dump(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def encode_result_refs(refs: Iterable[ResultRef]) -> str:
    """Encode exact result references."""
    return _dump(
        [
            {
                "result_id": ref.result_id,
                "kind": ref.kind,
                "schema_version": ref.schema_version,
            }
            for ref in refs
        ]
    )


def decode_result_refs(value: str) -> tuple[ResultRef, ...]:
    """Decode exact result references."""
    data = _list(value)
    return tuple(
        ResultRef(
            result_id=_text(item, "result_id"),
            kind=_text(item, "kind"),
            schema_version=_text(item, "schema_version"),
        )
        for item in _objects(data)
    )


def encode_version_refs(refs: Iterable[VersionRef]) -> str:
    """Encode exact version references."""
    return _dump(
        [
            {"kind": ref.kind, "identity": ref.identity, "version": ref.version}
            for ref in refs
        ]
    )


def decode_version_refs(value: str) -> tuple[VersionRef, ...]:
    """Decode exact version references."""
    return tuple(
        VersionRef(
            kind=_text(item, "kind"),
            identity=_text(item, "identity"),
            version=_text(item, "version"),
        )
        for item in _objects(_list(value))
    )


def encode_version_ref(ref: VersionRef | None) -> str | None:
    """Encode one optional version reference."""
    return None if ref is None else encode_version_refs((ref,))


def decode_version_ref(value: str | None) -> VersionRef | None:
    """Decode one optional version reference."""
    if value is None:
        return None
    refs = decode_version_refs(value)
    if len(refs) != 1:
        raise ValueError("expected exactly one version reference")
    return refs[0]


def encode_diagnostics(values: Iterable[Diagnostic]) -> str:
    """Encode safe diagnostics."""
    return _dump([{"code": item.code, "detail": item.detail} for item in values])


def decode_diagnostics(value: str) -> tuple[Diagnostic, ...]:
    """Decode safe diagnostics."""
    return tuple(
        Diagnostic(code=_text(item, "code"), detail=_text(item, "detail"))
        for item in _objects(_list(value))
    )


def encode_limitations(values: Iterable[Limitation]) -> str:
    """Encode explicit limitations."""
    return _dump([{"code": item.code, "detail": item.detail} for item in values])


def decode_limitations(value: str) -> tuple[Limitation, ...]:
    """Decode explicit limitations."""
    return tuple(
        Limitation(code=_text(item, "code"), detail=_text(item, "detail"))
        for item in _objects(_list(value))
    )


def encode_failures(values: Iterable[Failure]) -> str:
    """Encode safe failure classifications."""
    return _dump(
        [
            {"code": item.code, "detail": item.detail, "retryable": item.retryable}
            for item in values
        ]
    )


def decode_failures(value: str) -> tuple[Failure, ...]:
    """Decode safe failure classifications."""
    failures: list[Failure] = []
    for item in _objects(_list(value)):
        retryable = item.get("retryable")
        if not isinstance(retryable, bool):
            raise TypeError("failure retryable must be boolean")
        failures.append(
            Failure(
                code=_text(item, "code"),
                detail=_text(item, "detail"),
                retryable=retryable,
            )
        )
    return tuple(failures)


def _list(value: str) -> list[object]:
    data = json.loads(value)
    if not isinstance(data, list):
        raise TypeError("encoded contract must be a list")
    return data


def _objects(values: list[object]) -> tuple[dict[str, object], ...]:
    objects: list[dict[str, object]] = []
    for value in values:
        if not isinstance(value, dict):
            raise TypeError("encoded contract entry must be an object")
        objects.append(value)
    return tuple(objects)


def _text(value: dict[str, object], key: str) -> str:
    field = value.get(key)
    if not isinstance(field, str):
        raise TypeError(f"{key} must be text")
    return field

"""Read-only saved-status inspection that never initializes persistence."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from urllib.parse import quote

from msgloom.contracts import ResultRef
from msgloom.persistence import sqlite_file_path


class StatusError(ValueError):
    """Expose a fixed privacy-safe status inspection failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def read_saved_status(database_url: str, execution: str) -> dict[str, object]:
    """Read a saved terminal outcome without database creation or migration."""
    path = _database_path(database_url)
    if not path.is_file():
        raise StatusError("status_store_unavailable")
    uri = f"file:{quote(str(path), safe='/')}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=1.0)
        connection.row_factory = sqlite3.Row
        try:
            _require_schema(connection)
            row = connection.execute(
                "SELECT execution_id, capability, status, result_refs, "
                "limitations, failures, external_effect "
                "FROM phase1_operation_outcomes WHERE execution_id = ?",
                (execution,),
            ).fetchone()
        finally:
            connection.close()
    except StatusError:
        raise
    except sqlite3.Error:
        raise StatusError("status_store_incompatible") from None
    if row is None:
        raise StatusError("status_not_found")
    refs = _result_refs(row["result_refs"])
    return {
        "execution": row["execution_id"],
        "capability": row["capability"],
        "status": row["status"],
        "result_refs": [
            {
                "result_id": item.result_id,
                "kind": item.kind,
                "schema_version": item.schema_version,
            }
            for item in refs
        ],
        "limitation_codes": _codes(row["limitations"]),
        "failure_codes": _codes(row["failures"]),
        "external_effect": row["external_effect"],
    }


def _database_path(database_url: str) -> Path:
    try:
        return sqlite_file_path(database_url)
    except (TypeError, ValueError):
        raise StatusError("status_store_incompatible") from None


def _require_schema(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        "SELECT value FROM phase1_schema_metadata WHERE key = 'schema_version'"
    ).fetchone()
    # Schema v4 adds intake tables; the saved outcome layout is unchanged.
    if row is None or row[0] not in {"3", "4"}:
        raise StatusError("status_store_incompatible")


def _result_refs(payload: str) -> tuple[ResultRef, ...]:
    try:
        values = json.loads(payload)
        if not isinstance(values, list) or len(values) > 1024:
            raise TypeError
        return tuple(
            ResultRef(
                result_id=_text(item, "result_id"),
                kind=_text(item, "kind"),
                schema_version=_text(item, "schema_version"),
            )
            for item in values
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        raise StatusError("status_store_incompatible") from None


def _codes(payload: str) -> list[str]:
    try:
        values = json.loads(payload)
        if not isinstance(values, list) or len(values) > 1024:
            raise TypeError
        return [_text(item, "code") for item in values]
    except (json.JSONDecodeError, TypeError, ValueError):
        raise StatusError("status_store_incompatible") from None


def _text(value: object, key: str) -> str:
    if not isinstance(value, dict):
        raise TypeError
    item = value.get(key)
    if not isinstance(item, str) or not item.strip() or len(item) > 2048:
        raise TypeError
    return item

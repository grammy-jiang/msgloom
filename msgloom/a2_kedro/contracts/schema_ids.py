"""
Closed ``(kind, version)`` allowlist for A2 v2 stage results.

A stage kind has exactly one approved version. A caller cannot choose
version 1 or 2 freely. ``prepared@1`` is a historical read format and is
never accepted as a new A2 v2 stage.

CANDIDATE/RESEARCH: names are provisional until C0-00 freezes them.
"""

from __future__ import annotations

from msgloom.a2_kedro.contracts.codec import A2ContractError

#: Approved stage kinds and their only accepted schema version.
STAGE_SCHEMAS: dict[str, str] = {
    "frozen_source_selection": "1",
    "extracted_components": "1",
    "parsed_parts": "1",
    "normalized_content": "1",
    "zones": "1",
    "native_relations": "1",
    "prepared": "2",
    "filter_result": "2",
    "group_result": "2",
    "prepared_transitions": "2",
    "a2_input_disposition": "1",
    "a2_result_manifest": "1",
}

#: Read-only historical formats that A2 v2 must refuse to write.
HISTORICAL_READ_ONLY: frozenset[tuple[str, str]] = frozenset(
    {("prepared", "1"), ("filter_result", "1"), ("group_result", "1")}
)

#: The completion receipt is not a stage; it has its own approved version.
RECEIPT_SCHEMA = ("a2_completion_receipt", "2")

#: Stages that may be accepted without any upstream accepted result.
ROOT_STAGES = frozenset({"frozen_source_selection", "a2_input_disposition"})

ACCEPTED_KEY_PREFIX = "a2-accepted:"
ACCEPTED_KEY_LENGTH = len(ACCEPTED_KEY_PREFIX) + 64


def require_stage_schema(kind: str, version: str) -> None:
    """Raise :exc:`A2ContractError` unless the pair is approved for writing."""
    if (kind, version) in HISTORICAL_READ_ONLY:
        raise A2ContractError("historical schema is read-only")
    if STAGE_SCHEMAS.get(kind) != version:
        raise A2ContractError("stage kind/version pairing is not approved")


def is_accepted_key(value: str) -> bool:
    """Return whether ``value`` has the shape of an accepted logical key."""
    if len(value) != ACCEPTED_KEY_LENGTH:
        return False
    if not value.startswith(ACCEPTED_KEY_PREFIX):
        return False
    digest = value[len(ACCEPTED_KEY_PREFIX) :]
    return all(char in "0123456789abcdef" for char in digest)

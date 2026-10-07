"""Exercise Graph removal-marker shape without resource removal policy."""

from copy import deepcopy
from typing import Any

import pytest

from microsoft_graph.protocol import GraphProtocolError
from microsoft_graph.protocol.delta import graph_tombstone


@pytest.mark.parametrize("payload", [{}, {"@removed": None}])
def test_absent_or_null_marker_is_not_a_tombstone(payload: dict[str, Any]) -> None:
    if graph_tombstone(payload) is not None:
        pytest.fail("Absent or null markers must not indicate removal")


@pytest.mark.parametrize(
    "marker",
    [
        {},
        {"reason": "deleted"},
        {"reason": "changed"},
        {"reason": "future-provider-reason", "extension": {"value": 1}},
        {"reason": None},
        {"reason": 42},
    ],
)
def test_tombstone_preserves_provider_object_and_reason(marker: dict[str, Any]) -> None:
    payload = {"id": "resource-1", "@removed": marker}
    original = deepcopy(payload)
    result = graph_tombstone(payload)
    if result is not marker:
        pytest.fail("The exact removal object must reach the resource consumer")
    if payload != original:
        pytest.fail("Reading a tombstone must not modify the resource")


@pytest.mark.parametrize("marker", [False, True, 0, 1, "", "deleted", [], ["deleted"]])
def test_invalid_marker_is_rejected_without_payload_disclosure(marker: Any) -> None:
    with pytest.raises(GraphProtocolError, match="Calendar delta @removed") as error:
        graph_tombstone({"@removed": marker}, context="Calendar delta")
    if "deleted" in str(error.value):
        pytest.fail("Shape failures must not expose provider payload values")


@pytest.mark.parametrize("marker", [False, True, 0, 1, "", "deleted", [], ["deleted"]])
def test_legacy_nonobject_marker_can_be_ignored_explicitly(marker: Any) -> None:
    if graph_tombstone({"@removed": marker}, strict=False) is not None:
        pytest.fail("Compatibility parsing must ignore malformed markers")


def test_compatibility_mode_keeps_empty_tombstones() -> None:
    marker: dict[str, Any] = {}
    if graph_tombstone({"@removed": marker}, strict=False) is not marker:
        pytest.fail("Empty removal objects still represent a provider tombstone")

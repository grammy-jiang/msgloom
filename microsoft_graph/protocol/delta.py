"""Pure Graph delta resource markers, without removal semantics."""

from typing import Any

from . import GraphProtocolError


def graph_tombstone(
    payload: dict[str, Any],
    *,
    strict: bool = True,
    context: str = "Graph delta",
) -> dict[str, Any] | None:
    """
    Read an optional ``@removed`` object without interpreting its reason.

    Missing and null markers return ``None``. A removal object is returned
    unchanged, including unknown fields and reason values. Consumers must
    compare the result with ``None`` because an empty object is a tombstone.

    Raise :class:`~microsoft_graph.protocol.GraphProtocolError` for other
    marker shapes. ``strict=False`` explicitly preserves consumers that
    treated malformed markers as absent. Resource identity validation and
    the meaning of removal remain with the resource consumer.
    """
    removed = payload.get("@removed")
    if removed is None or isinstance(removed, dict):
        return removed
    if strict:
        raise GraphProtocolError(f"{context} @removed value must be an object")
    return None

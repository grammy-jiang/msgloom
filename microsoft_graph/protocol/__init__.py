"""Pure Graph JSON envelopes; no transport, persistence, or cursor ownership."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self


class GraphProtocolError(ValueError):
    """Report a malformed Graph envelope or invalid delta state."""


class GraphObjectTypeError(GraphProtocolError, TypeError):
    """Report an incorrect JSON type, also compatible with ``TypeError``."""


def graph_object(payload: Any, *, context: str = "Graph response") -> dict[str, Any]:
    """Require a JSON object without changing provider fields."""
    if not isinstance(payload, dict):
        raise GraphObjectTypeError(f"{context} must be a JSON object")
    return payload


@dataclass(frozen=True)
class GraphCollectionPage:
    """
    Retain collection values and opaque continuation links.

    Entries remain provider values; resource callbacks validate their schema.
    The default requires a list and validates links immediately. Consumers
    that must emit evidence or observations first can defer link validation.
    ``missing_value_empty`` and ``empty_links_absent`` are explicit legacy
    compatibility options, never defaults. JSON null links mean absent.
    """

    payload: dict[str, Any]
    values: list[Any]
    context: str = "Graph collection"
    empty_links_absent: bool = False

    @classmethod
    def from_payload(
        cls,
        payload: Any,
        *,
        context: str = "Graph collection",
        missing_value_empty: bool = False,
        empty_links_absent: bool = False,
        validate_links: bool = True,
    ) -> Self:
        """Parse an already decoded JSON page with explicit validation policy."""
        obj = graph_object(payload, context=context)
        values = obj.get("value", [] if missing_value_empty else None)
        if not isinstance(values, list):
            raise GraphObjectTypeError(f"{context} must contain a value list")
        page = cls(obj, values, context, empty_links_absent)
        if validate_links:
            page._validate_links()
        return page

    def _link(self, key: str) -> str | None:
        value = self.payload.get(key)
        if value is None or (self.empty_links_absent and not value):
            return None
        if not isinstance(value, str) or not value:
            raise GraphProtocolError(f"{self.context} {key} must be a non-empty string")
        return value

    @property
    def next_link(self) -> str | None:
        """Return the unmodified next link, validating its type on access."""
        return self._link("@odata.nextLink")

    def _validate_links(self) -> None:
        self._link("@odata.nextLink")


@dataclass(frozen=True)
class GraphDeltaPage(GraphCollectionPage):
    """
    Parse delta pages without storing or promoting provider cursors.

    Strict parsing requires exactly one next/delta link. ``strict=False``
    leaves missing/conflicting-state decisions to the consumer. Reading only
    ``next_link`` with deferred validation preserves next-link precedence.
    """

    @classmethod
    def from_payload(
        cls,
        payload: Any,
        *,
        context: str = "Graph delta",
        strict: bool = True,
        missing_value_empty: bool = False,
        empty_links_absent: bool = False,
        validate_links: bool = True,
    ) -> Self:
        page = super().from_payload(
            payload,
            context=context,
            missing_value_empty=missing_value_empty,
            empty_links_absent=empty_links_absent,
            validate_links=validate_links,
        )
        if strict:
            page.validate_state()
        return page

    @property
    def delta_link(self) -> str | None:
        """Return an opaque terminal cursor without interpreting its contents."""
        return self._link("@odata.deltaLink")

    @property
    def has_conflicting_state(self) -> bool:
        """Detect two supplied links before validating either link's type."""
        return all(
            self.payload.get(key) is not None
            for key in ("@odata.nextLink", "@odata.deltaLink")
        )

    def _validate_links(self) -> None:
        super()._validate_links()
        self._link("@odata.deltaLink")

    def validate_state(self) -> None:
        """Require exactly one validated next/delta link."""
        if (self.next_link is None) == (self.delta_link is None):
            raise GraphProtocolError(
                f"{self.context} requires exactly one nextLink or deltaLink"
            )


@dataclass(frozen=True)
class GraphError:
    """Retain an error envelope and outer-to-inner provider error codes."""

    codes: tuple[str, ...]
    message: str | None
    raw: dict[str, Any]

    @classmethod
    def from_payload(cls, payload: Any) -> Self:
        """Walk both Graph inner-error spellings without interpreting codes."""
        obj = graph_object(payload)
        error = graph_object(obj.get("error"), context="Graph error")
        codes: list[str] = []
        current = error
        seen: set[int] = set()
        while isinstance(current, dict) and id(current) not in seen:
            seen.add(id(current))
            if isinstance(code := current.get("code"), str) and code:
                codes.append(code)
            nested = current.get("innerError")
            if nested is None:
                nested = current.get("innererror")
            current = nested
        message = error.get("message")
        return cls(tuple(codes), message if isinstance(message, str) else None, error)


__all__ = [
    "GraphCollectionPage",
    "GraphDeltaPage",
    "GraphError",
    "GraphProtocolError",
    "graph_object",
]

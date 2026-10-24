"""
Error types of the receipt store (C0-14a), PROVISIONAL.

Every error carries a fixed ``reason`` code. A code never holds a path, an
id, a digest, a claim value or pydantic text.
"""

from __future__ import annotations

from msgloom.a2_kedro.contracts.codec import A2ContractError


class A2ReceiptError(A2ContractError):
    """A request was refused. ``reason`` is a fixed code, never data."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class A2ReceiptBoundError(A2ReceiptError):
    """An explicit item or byte bound was exceeded."""


class A2ReceiptConflict(A2ReceiptError):
    """A stored record would change. ``fields`` names fields, not values."""

    def __init__(self, reason: str, fields: tuple[str, ...]) -> None:
        super().__init__(reason)
        self.fields = fields

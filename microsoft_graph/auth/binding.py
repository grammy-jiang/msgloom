"""Provider-neutral account-binding contract for Microsoft Graph auth."""

from __future__ import annotations

import asyncio
from typing import Protocol


class MicrosoftGraphAccountBinding(Protocol):
    """Bind one opaque Microsoft account key to an external application source."""

    @property
    def write_lock(self) -> asyncio.Lock:
        """Return the application lock serializing first-binding decisions."""
        ...

    def has_binding(self) -> bool:
        """Return whether an application source is already account-bound."""
        ...

    def matches_account_key(self, account_key: str) -> bool:
        """Return whether an opaque MSAL account key matches the binding."""
        ...

    def bind_or_verify_account_key(self, account_key: str) -> str:
        """Bind a first account key or verify it against the stored binding."""
        ...


__all__ = ["MicrosoftGraphAccountBinding"]

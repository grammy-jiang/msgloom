"""Test helper for P3-06: bind a selection to the scope of its grant.

``publish_context`` now takes a ``FrozenSelection``. Most P3-06 tests check
other rules, so this wrapper freezes the selection under the scope and
workset of the grant. Any other argument passes through unchanged, so the
wrong-type cases still reach the real function. Binding tests build
``FrozenSelection`` directly and call the real function.
"""

from __future__ import annotations

from typing import Any

from msgloom.a2_kedro.semantics import context_types as ct
from msgloom.a2_kedro.semantics.context_types import (
    ContextGrant,
    ContextPublication,
    FrozenSelection,
    PublicationTarget,
)
from msgloom.sources.models import CollectedSelection


def publish_context(
    selection: Any, grant: Any, target: PublicationTarget
) -> ContextPublication:
    """Freeze ``selection`` under the grant binding, then publish."""
    frozen: Any = selection
    if isinstance(selection, CollectedSelection) and isinstance(grant, ContextGrant):
        frozen = FrozenSelection(selection, grant.scope, grant.workset)
    return ct.publish_context(frozen, grant, target)

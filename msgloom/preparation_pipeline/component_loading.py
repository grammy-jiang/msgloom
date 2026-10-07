"""Classify selected saved-component byte loading without recollection."""

from __future__ import annotations

from msgloom.contracts import Limitation
from msgloom.preparation import SavedByteReference
from msgloom.sources import (
    CollectedSourceReader,
    SourceEvidenceError,
    SourceEvidenceLimitError,
    SourceReferenceError,
)


async def load_selected_component(
    reader: CollectedSourceReader,
    reference: SavedByteReference,
    limitations: list[Limitation],
) -> bytes | None:
    """Load exact selected bytes or retain a post-selection evidence gap."""
    try:
        return await reader.load_saved_bytes(reference)
    except SourceEvidenceLimitError:
        raise
    except (SourceEvidenceError, SourceReferenceError):
        limitations.append(
            Limitation(
                "saved-content-unavailable",
                "Selected saved content became unavailable or failed "
                "integrity verification.",
            )
        )
        return None

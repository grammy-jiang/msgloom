"""Public exact release reconstruction for scheduled intake and context."""

import asyncio
import sqlite3

from msgloom.sources._release_assemble import reconstruct
from msgloom.sources._release_evidence import ReleaseEvidence
from msgloom.sources.handoff_catalog import HandoffCatalog
from msgloom.sources.handoff_models import ReleaseEntry, ReleaseEntryRef
from msgloom.sources.models import SavedSourceReaderConfig, SourceReferenceError
from msgloom.sources.reader import SavedSourceReader
from msgloom.sources.release_models import ReleasedInput, SupportingContext


class ReleaseSourceReader(SavedSourceReader):
    """Add exact release reads while preserving manual LIVE/REPLAY."""

    def __init__(self, config: SavedSourceReaderConfig) -> None:
        """Pin catalog and evidence roots without opening A1 write services."""
        super().__init__(config)
        self.catalog = HandoffCatalog(config.catalog_path, config.limits)

    async def read_entry(
        self,
        reference: ReleaseEntryRef | ReleaseEntry,
    ) -> ReleasedInput:
        """Resolve an exact admission anchor and fail closed if unavailable."""
        self._revalidate_config()
        ref = reference.reference if isinstance(reference, ReleaseEntry) else reference
        ref = ReleaseEntryRef.model_validate(ref.model_dump())
        entry = await self.catalog.get_release_entry(ref.release_entry_seq)
        if entry is None or entry.reference != ref:
            raise SourceReferenceError("Release entry anchor mismatch")
        facts = await self.catalog.get_release_facts(ref)
        try:
            return await self._gate.run(
                lambda: reconstruct(
                    entry, facts, ReleaseEvidence(self._catalog, self._files)
                )
            )
        except (sqlite3.Error, ValueError, TypeError, KeyError, RecursionError):
            raise SourceReferenceError("Invalid exact released input") from None

    async def read_supporting_context(
        self,
        reference: ReleaseEntryRef | ReleaseEntry,
    ) -> SupportingContext:
        """Pin named history without enumerating or admitting work."""
        result = await self.read_entry(reference)
        selection = result.selection
        if selection is None and len(result.contexts) == 1:
            selection = result.contexts[0]
        if selection is None:
            raise SourceReferenceError("Historical entry has no readable selection")
        return SupportingContext(
            reference=result.reference,
            selection=selection,
        )

    async def close(self) -> None:
        """Drain both read boundaries, including when the caller cancels."""
        cancelled = False
        try:
            await self.catalog.close()
        except asyncio.CancelledError:
            cancelled = True
        finally:
            await super().close()
        if cancelled:
            raise asyncio.CancelledError

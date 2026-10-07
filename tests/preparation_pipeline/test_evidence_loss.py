"""Evidence-loss regressions for the real synthetic A1 catalog."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest

from msgloom.contracts import AttemptIdentity, ResultRef, TerminalStatus
from msgloom.preparation import DocumentFormat, PreparedRecord, PreparedSourceType
from msgloom.preparation_pipeline import (
    PreparationHandler,
    PreparationMode,
)
from msgloom.sources import (
    CollectedSelection,
    CollectedSourceReader,
    SavedSourceReader,
    SavedSourceReaderConfig,
    SourceEvidenceLimitError,
)

from .helpers import open_store, plan, profiles
from .test_integration import _request

_FORMATS = (
    DocumentFormat.HTML,
    DocumentFormat.TEXT,
    DocumentFormat.JSON,
    DocumentFormat.MIME,
)


def _reader(saved_catalog: dict[str, object]) -> SavedSourceReader:
    return SavedSourceReader(
        SavedSourceReaderConfig(
            catalog_path=cast(Path, saved_catalog["database"]),
            evidence_roots=(cast(Path, saved_catalog["evidence_root"]),),
        )
    )


async def _source(reader: SavedSourceReader, saved_catalog: dict[str, object]):
    versions = await reader.list_versions(
        PreparedSourceType.OUTLOOK_EMAIL,
        source_id=cast(str, saved_catalog["source_id"]),
        limit=10,
    )
    return next(item for item in versions if item.version == "obs-current")


async def _prepared(store, outcome) -> PreparedRecord:
    ref = next(item for item in outcome.result_refs if item.kind == "prepared")
    result = await store.get_result(ref.result_id)
    if result is None or result.semantic_data_ref is None:
        pytest.fail("prepared result omitted durable semantic data")
    value = await store.load_semantic_data(result.semantic_data_ref)
    if not isinstance(value, PreparedRecord):
        pytest.fail("prepared semantic data has the wrong type")
    return value


class _RaceReader:
    """Mutate selected evidence once, after exact selection capture."""

    def __init__(self, real: SavedSourceReader, mutate) -> None:
        self.real = real
        self.mutate = mutate
        self.selection: CollectedSelection | None = None

    async def read_selection(self, requested):
        value = await self.real.read_selection(requested)
        self.selection = value
        self.mutate(value)
        return value

    async def load_saved_bytes(self, reference):
        return await self.real.load_saved_bytes(reference)


def test_attachment_loss_retains_partial_record_and_exact_reference(
    saved_catalog: dict[str, object], tmp_path: Path
) -> None:
    """Post-selection attachment loss is explicit, partial, and replay-safe."""

    async def exercise() -> None:
        real = _reader(saved_catalog)
        store = await open_store(tmp_path / "attachment-loss.sqlite3")
        source = await _source(real, saved_catalog)
        root = cast(Path, saved_catalog["evidence_root"])

        def remove_attachment(selection: CollectedSelection) -> None:
            saved = selection.record.attachments[0].saved_bytes
            if saved is None:
                pytest.fail("fixture attachment has no saved bytes")
            (root / f"{saved.sha256}.bin").unlink()

        race = _RaceReader(real, remove_attachment)
        outcome = await PreparationHandler(
            store,
            cast(CollectedSourceReader, race),
            plan(
                source,
                attempt=AttemptIdentity("attachment-loss"),
                parser_profiles=profiles(*_FORMATS),
            ),
        ).run(_request("attachment-loss-execution", source))
        if outcome.status is not TerminalStatus.INCOMPLETE:
            pytest.fail(f"attachment loss was not partial: {outcome}")
        if not any(
            item.code == "saved-content-unavailable" for item in outcome.limitations
        ):
            pytest.fail("attachment loss omitted its explicit limitation")
        value = await _prepared(store, outcome)
        if value.subject != "Current subject" or value.body != "Current body":
            pytest.fail("valid message metadata/body was lost")
        selected = race.selection
        if selected is None:
            pytest.fail("race reader did not retain captured selection")
        selected_attachment = selected.record.attachments[0]
        if (
            value.source != source
            or value.attachments[0].reference != selected_attachment.reference
            or value.attachments[0].saved_bytes != selected_attachment.saved_bytes
        ):
            pytest.fail("partial record lost selected source/attachment lineage")
        if not any(
            '"semantic_identity"' in getattr(block, "text", "")
            for item in value.parsed_contents
            for block in item.output.blocks
        ):
            pytest.fail("partial record lost valid parsed collected metadata")
        if value.attachments[0].parsed_content_ref is not None:
            pytest.fail("unverified attachment bytes reached parsing")
        await store.close()
        await real.close()

    asyncio.run(exercise())


def test_saved_alternate_body_loss_preserves_other_valid_components(
    saved_catalog: dict[str, object], tmp_path: Path
) -> None:
    """Saved alternate-body loss preserves unrelated valid components."""

    async def exercise() -> None:
        real = _reader(saved_catalog)
        store = await open_store(tmp_path / "body-loss.sqlite3")
        source = await _source(real, saved_catalog)
        root = cast(Path, saved_catalog["evidence_root"])

        def remove_mime(selection: CollectedSelection) -> None:
            saved = selection.record.alternate_bodies[0].saved_bytes
            if saved is None:
                pytest.fail("fixture alternate body has no saved bytes")
            (root / f"{saved.sha256}.bin").unlink()

        outcome = await PreparationHandler(
            store,
            cast(CollectedSourceReader, _RaceReader(real, remove_mime)),
            plan(
                source,
                attempt=AttemptIdentity("body-loss"),
                parser_profiles=profiles(*_FORMATS),
            ),
        ).run(_request("body-loss-execution", source))
        if outcome.status is not TerminalStatus.INCOMPLETE:
            pytest.fail(f"saved body loss was not partial: {outcome}")
        value = await _prepared(store, outcome)
        if value.body != "Current body" or not value.attachments:
            pytest.fail("saved body loss erased unrelated valid components")
        if value.attachments[0].parsed_content_ref is None:
            pytest.fail("valid attachment was not parsed after body loss")
        await store.close()
        await real.close()

    asyncio.run(exercise())


def test_integrity_change_never_reaches_parser(
    saved_catalog: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changed post-selection bytes are rejected before parser admission."""

    async def exercise() -> None:
        real = _reader(saved_catalog)
        store = await open_store(tmp_path / "integrity-change.sqlite3")
        source = await _source(real, saved_catalog)
        root = cast(Path, saved_catalog["evidence_root"])
        changed = b"changed attachment!!"
        seen: list[bytes] = []

        from msgloom.preparation_pipeline import record_steps

        original = record_steps.parse_isolated

        async def tracked(request, content):
            seen.append(content)
            return await original(request, content)

        monkeypatch.setattr(record_steps, "parse_isolated", tracked)

        def change_attachment(selection: CollectedSelection) -> None:
            saved = selection.record.attachments[0].saved_bytes
            if saved is None:
                pytest.fail("fixture attachment has no saved bytes")
            if len(changed) != saved.byte_count:
                pytest.fail("integrity mutation changed selected byte count")
            (root / f"{saved.sha256}.bin").write_bytes(changed)

        outcome = await PreparationHandler(
            store,
            cast(CollectedSourceReader, _RaceReader(real, change_attachment)),
            plan(
                source,
                attempt=AttemptIdentity("integrity-change"),
                parser_profiles=profiles(*_FORMATS),
            ),
        ).run(_request("integrity-change-execution", source))
        if outcome.status is not TerminalStatus.INCOMPLETE:
            pytest.fail(f"integrity change was not partial: {outcome}")
        if changed in seen:
            pytest.fail("changed unverified content reached the parser")
        value = await _prepared(store, outcome)
        if value.attachments[0].parsed_content_ref is not None:
            pytest.fail("changed attachment acquired parsed provenance")
        await store.close()
        await real.close()

    asyncio.run(exercise())


def test_restart_replay_reproduces_honest_partial_record(
    saved_catalog: dict[str, object], tmp_path: Path
) -> None:
    """Restart replay uses captured lineage and reproduces the evidence gap."""

    async def exercise() -> None:
        real = _reader(saved_catalog)
        path = tmp_path / "partial-replay.sqlite3"
        store = await open_store(path)
        source = await _source(real, saved_catalog)
        root = cast(Path, saved_catalog["evidence_root"])

        def remove_attachment(selection: CollectedSelection) -> None:
            saved = selection.record.attachments[0].saved_bytes
            if saved is None:
                pytest.fail("fixture attachment has no saved bytes")
            (root / f"{saved.sha256}.bin").unlink()

        live = await PreparationHandler(
            store,
            cast(CollectedSourceReader, _RaceReader(real, remove_attachment)),
            plan(
                source,
                attempt=AttemptIdentity("partial-live"),
                parser_profiles=profiles(*_FORMATS),
            ),
        ).run(_request("partial-live-execution", source))
        live_value = await _prepared(store, live)
        selection_ref = next(
            item for item in live.result_refs if item.kind == "collected_selection"
        )
        selection_result = await store.get_result(selection_ref.result_id)
        if selection_result is None or selection_result.semantic_data_ref is None:
            pytest.fail("live partial omitted captured selection")
        selection = await store.load_semantic_data(selection_result.semantic_data_ref)
        if not isinstance(selection, CollectedSelection):
            pytest.fail("captured selection decoded to wrong type")
        replay_ref = ResultRef(
            selection_result.result_id,
            selection_result.kind,
            selection_result.schema_version,
        )
        await store.close()

        reopened = await open_store(path)

        class ReplayReader:
            async def read_selection(self, _requested):
                pytest.fail("replay recollected mutable source state")

            async def load_saved_bytes(self, reference):
                return await real.load_saved_bytes(reference)

        replay = await PreparationHandler(
            reopened,
            cast(CollectedSourceReader, ReplayReader()),
            plan(
                source,
                attempt=AttemptIdentity("partial-replay"),
                mode=PreparationMode.REPLAY,
                replay_result=replay_ref,
                replay_selection=selection.selection,
                parser_profiles=profiles(*_FORMATS),
            ),
        ).run(_request("partial-replay-execution", source))
        if replay.status is not TerminalStatus.INCOMPLETE:
            pytest.fail(f"replay changed honest partial status: {replay}")
        replay_value = await _prepared(reopened, replay)
        if (
            replay_value.source != live_value.source
            or replay_value.subject != live_value.subject
            or replay_value.body != live_value.body
            or replay_value.relationships != live_value.relationships
            or replay_value.attachments != live_value.attachments
            or replay_value.limitations != live_value.limitations
        ):
            pytest.fail("restart changed stable honest partial semantics")
        if replay_value.attachments[0].parsed_content_ref is not None:
            pytest.fail("restart parsed the unavailable attachment")
        await reopened.close()
        await real.close()

    asyncio.run(exercise())


def test_source_byte_limit_and_aggregate_parser_budget_remain_fatal(
    saved_catalog: dict[str, object], tmp_path: Path
) -> None:
    """Resource ceilings remain fatal instead of becoming partial success."""

    async def exercise() -> None:
        real = _reader(saved_catalog)
        source = await _source(real, saved_catalog)
        store = await open_store(tmp_path / "fatal-limits.sqlite3")

        class LimitedReader:
            async def read_selection(self, requested):
                return await real.read_selection(requested)

            async def load_saved_bytes(self, _reference):
                raise SourceEvidenceLimitError("synthetic finite byte ceiling")

        limited = await PreparationHandler(
            store,
            cast(CollectedSourceReader, LimitedReader()),
            plan(
                source,
                attempt=AttemptIdentity("source-limit"),
                parser_profiles=profiles(*_FORMATS),
            ),
        ).run(_request("source-limit-execution", source))
        if limited.status is not TerminalStatus.FAILED:
            pytest.fail("source byte ceiling was converted to partial success")
        if any(item.kind == "prepared" for item in limited.result_refs):
            pytest.fail("source byte ceiling published prepared semantics")

        aggregate_plan = plan(
            source,
            attempt=AttemptIdentity("aggregate-limit"),
            parser_profiles=profiles(*_FORMATS),
        ).model_copy(update={"max_total_parser_output_bytes": 1})
        aggregate = await PreparationHandler(
            store, cast(CollectedSourceReader, real), aggregate_plan
        ).run(_request("aggregate-limit-execution", source))
        if aggregate.status is not TerminalStatus.FAILED:
            pytest.fail("aggregate parser budget became partial success")
        if any(item.kind == "prepared" for item in aggregate.result_refs):
            pytest.fail("aggregate parser budget published prepared semantics")
        await store.close()
        await real.close()

    asyncio.run(exercise())

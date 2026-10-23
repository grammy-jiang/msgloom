"""C0 exact A1 release/intake research gate on a local native Mail fixture.

Scrapy acquisition is invoked through the existing real Task15 fixture.
No A1 implementation is modified and no production provider is contacted.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from msgloom.contracts import AttemptIdentity, ExecutionIdentity, ResultRef
from msgloom.persistence import Phase1Persistence
from msgloom.preparation_pipeline.intake import PreparationIntakeService
from msgloom.preparation_pipeline.intake_models import (
    IntakeScope,
    IntakeSelection,
    PreparationIntakeWorkset,
)
from msgloom.sources import CollectedSelection
from msgloom.sources.release_reader import ReleaseSourceReader
from scripts.research.c0_contract_prototype import (
    C0ContractError,
    verify_exact_release_root,
)
from tests.handoff_qualification.mail_scheduled import (
    CONSUMER,
    SOURCE,
    acquire_one,
    configuration,
)


def test_c0_exact_accepted_a1_release_selection_role_and_ordinal(
    tmp_path: Path,
) -> None:
    """Native released Mail is the only admissible C0 incremental input."""
    acquire_one(tmp_path)
    config = configuration(tmp_path)

    async def scenario() -> None:
        reader = ReleaseSourceReader(config.source_reader_config())
        storage = await Phase1Persistence.open(config.database_url)
        try:
            catalog = await reader.catalog.catalog_identity()
            page = await reader.catalog.list_release_entries(
                SOURCE, "outlook_mail", after_seq=0, through_seq=1, limit=2
            )
            if len(page.entries) != 1 or page.has_more:
                pytest.fail("native A1 release did not yield an exact single entry")
            entry = page.entries[0]
            released = await reader.read_entry(entry.reference)
            if released.selection is None:
                pytest.fail("native A1 primary selection was not reconstructed")
            scope = IntakeScope(
                catalog=catalog,
                source_id=SOURCE,
                stream="outlook_mail",
                consumer_id=CONSUMER,
            )
            intake_result = await PreparationIntakeService(storage, reader).run(
                scope,
                execution=ExecutionIdentity("c0-a1-e2e"),
                attempt=AttemptIdentity("c0-a1-e2e"),
                configuration_version="c0-config",
                code_version="c0-code",
                limit=1,
                lease_seconds=120,
            )
            if intake_result is None or intake_result.semantic_data_ref is None:
                pytest.fail("accepted A1 did not create durable intake workset")
            workset = await storage.load_semantic_data(intake_result.semantic_data_ref)
            if not isinstance(workset, PreparationIntakeWorkset):
                pytest.fail("saved workset is not frozen intake type")
            if len(workset.selections) != 1 or len(workset.entries) != 1:
                pytest.fail("native frozen selection count is wrong")
            if workset.entries[0] != released.reference:
                pytest.fail("intake entry differs from immutable release reference")
            selected = workset.selections[0]
            selected_result = await storage.get_result(selected.result.result_id)
            if selected_result is None or selected_result.semantic_data_ref is None:
                pytest.fail("native A1 selection was not saved with semantic data")
            saved_selection = await storage.load_semantic_data(
                selected_result.semantic_data_ref
            )
            if not isinstance(saved_selection, CollectedSelection):
                pytest.fail("stored selection is not accepted CollectedSelection")
            root = verify_exact_release_root(
                workset, selected, released, saved_selection
            )
            if root.entry != entry.reference or root.role != "primary":
                pytest.fail("role verifier lost exact released primary")
            if root.occurrence != 0:
                pytest.fail("primary ordinal proof changed")
            if selected_result.semantic_data_ref.sha256 != root.selection_sha256:
                pytest.fail("role verifier digest differs from saved semantic bytes")
            if selected.result.result_id != f"intake-selection:{root.a1_ordinal_proof}":
                pytest.fail("role verifier did not bind exact A1 ordinal identity")

            wrong = IntakeSelection(
                entry=selected.entry,
                result=ResultRef(
                    "intake-selection:000000000000",
                    selected.result.kind,
                    selected.result.schema_version,
                ),
            )
            # Negative 1: the candidate is absent from the frozen workset, so
            # only the membership guard fires; ordinal hashing is not reached.
            with pytest.raises(C0ContractError, match="frozen intake"):
                verify_exact_release_root(workset, wrong, released, saved_selection)

            # Negative 2: the candidate IS a frozen workset selection of the
            # exact released entry, but its result ID is not the A1 ordinal
            # identity of any released value. The workset below is a local
            # in-memory copy; the saved A1 workset and release stay untouched.
            # Two matching ordinals cannot be built honestly, because the
            # ordinal is hashed into the ID, so that branch stays unexercised.
            forged = IntakeSelection(
                entry=selected.entry,
                result=ResultRef(
                    "intake-selection:" + "0" * 64,
                    selected.result.kind,
                    selected.result.schema_version,
                ),
            )
            forged_workset = PreparationIntakeWorkset.model_validate(
                {
                    name: getattr(workset, name)
                    for name in PreparationIntakeWorkset.model_fields
                }
                | {"selections": (forged,)}
            )
            if forged not in forged_workset.selections:
                pytest.fail("forged candidate must be a frozen workset selection")
            with pytest.raises(C0ContractError, match="ordinal identity"):
                verify_exact_release_root(
                    forged_workset, forged, released, saved_selection
                )

            # Negative 3: the ordinal identity is correct, but the stored
            # CollectedSelection content differs from the release re-read.
            differing = saved_selection.model_copy(
                update={
                    "record": saved_selection.record.model_copy(
                        update={"subject": "c0-differing-stored-subject"}
                    )
                }
            )
            if differing == saved_selection:
                pytest.fail("differing stored selection must change its content")
            with pytest.raises(C0ContractError, match="differs from verified"):
                verify_exact_release_root(workset, selected, released, differing)
            # The accepted intake was a one-cut immutable projection; role
            # recovery did not re-admit work or mutate A1's release sequence.
            if (
                await reader.catalog.max_release_entry_seq(SOURCE, "outlook_mail")
                != entry.release_entry_seq
            ):
                pytest.fail("role verifier unexpectedly advanced the A1 ledger")
        finally:
            await reader.close()
            await storage.close()

    asyncio.run(scenario())

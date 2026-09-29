"""Verify enclosing claim ownership on every AI evidence transition."""

import asyncio
import sqlite3
from pathlib import Path

import pytest

from msgloom.ai import AnalysisResponse, AttemptStatus, TraceEvent, TraceKind
from msgloom.ai_evidence import EvidenceSession
from msgloom.contracts import AttemptIdentity, ClaimKind, ExecutionIdentity
from msgloom.persistence import StaleClaimError

from .helpers import analysis_attempt, open_store, save_seed, trusted_policy


@pytest.mark.parametrize("transition", ["request", "trace", "terminal"])
def test_reclaimed_operation_cannot_publish_child_evidence(
    tmp_path: Path, transition: str
) -> None:
    async def exercise() -> None:
        path = tmp_path / "evidence.sqlite3"
        persistence = await open_store(path)
        try:
            seed = await save_seed(persistence)
            execution = ExecutionIdentity("enclosing-operation")
            token = await persistence.acquire_claim(
                "triage:child-evidence",
                ClaimKind.TRIAGE,
                execution,
                AttemptIdentity("enclosing-attempt"),
            )
            request = analysis_attempt("child-ai-attempt")

            async def begin():
                return await EvidenceSession.begin(
                    persistence,
                    execution,
                    request,
                    trusted_policy=trusted_policy(request),
                    required_inputs=(seed,),
                    configuration_version="config",
                    code_version="code",
                    claim=token,
                )

            session = await begin() if transition != "request" else None
            connection = sqlite3.connect(path)
            try:
                connection.execute(
                    "UPDATE phase1_work_claims SET expires_at = ?",
                    ("2000-01-01T00:00:00+00:00",),
                )
                connection.commit()
            finally:
                connection.close()
            await persistence.acquire_claim(
                "triage:child-evidence",
                ClaimKind.TRIAGE,
                ExecutionIdentity("replacement-operation"),
                AttemptIdentity("replacement-attempt"),
            )
            with pytest.raises(StaleClaimError):
                if transition == "request":
                    await begin()
                elif session is None:
                    pytest.fail("Synthetic session was not created")
                elif transition == "trace":
                    await session.write(
                        TraceEvent(
                            attempt=request.attempt,
                            sequence=0,
                            kind=TraceKind.DIAGNOSTIC,
                            name="synthetic",
                            text="synthetic",
                            data={},
                        )
                    )
                else:
                    await session.finish(
                        AnalysisResponse(
                            attempt=request.attempt,
                            status=AttemptStatus.COMPLETE,
                            structured_output={"result": "synthetic"},
                            trace_count=0,
                        )
                    )
            if session is not None and (session.trace_refs or session.terminal_ref):
                pytest.fail("Rejected evidence advanced session state")
        finally:
            await persistence.close()

    asyncio.run(exercise())

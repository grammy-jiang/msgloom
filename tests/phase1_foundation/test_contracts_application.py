"""Contract and non-CLI application tests for the Phase 1 foundation."""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError

import pytest

from msgloom.application import Application
from msgloom.contracts import (
    AttemptIdentity,
    EvidenceReader,
    ExecutionIdentity,
    ExternalEffectState,
    Failure,
    Limitation,
    OperationOutcome,
    OperationRequest,
    PhaseCapability,
    ResultProducer,
    ResultRef,
    StageResult,
    TerminalStatus,
    TrustedAdmission,
    VersionRef,
)


class RecordingOutcomeStore:
    """Collect saved outcomes through the same async boundary as persistence."""

    def __init__(self) -> None:
        self.outcomes: list[OperationOutcome] = []

    async def save_outcome(self, outcome: OperationOutcome) -> None:
        self.outcomes.append(outcome)


class LoopRecordingHandler:
    """Return one result while proving the caller's event loop is reused."""

    def __init__(self, expected_loop: asyncio.AbstractEventLoop) -> None:
        self.expected_loop = expected_loop
        self.called = False

    async def run(self, request: OperationRequest) -> OperationOutcome:
        self.called = True
        if asyncio.get_running_loop() is not self.expected_loop:
            pytest.fail("Application created or switched to a nested event loop")
        return OperationOutcome(
            execution=request.execution,
            capability=request.capability,
            status=TerminalStatus.COMPLETE,
            result_refs=(ResultRef("result-1", "prepared", "1"),),
            external_effect=ExternalEffectState.NONE,
        )


def _trusted(capability: PhaseCapability) -> tuple[TrustedAdmission, ...]:
    return (
        TrustedAdmission(
            caller="synthetic-caller",
            authority_ref="authority-1",
            capabilities=frozenset({capability}),
        ),
    )


def _request(capability: PhaseCapability) -> OperationRequest:
    return OperationRequest(
        execution=ExecutionIdentity("execution-1"),
        caller="synthetic-caller",
        capability=capability,
        target_inputs=(VersionRef("source", "source-1", "v1"),),
        authority_ref="authority-1",
    )


def test_contracts_are_transport_neutral_and_immutable() -> None:
    request = _request(PhaseCapability.PREPARE)
    if request.capability is not PhaseCapability.PREPARE:
        pytest.fail("Expected typed Phase 1 capability")
    with pytest.raises(FrozenInstanceError):
        request.caller = "changed"  # type: ignore[misc]


def test_non_cli_caller_awaits_application_in_existing_loop() -> None:
    async def exercise() -> None:
        store = RecordingOutcomeStore()
        loop = asyncio.get_running_loop()
        handler = LoopRecordingHandler(loop)
        application = Application(
            store,
            trusted_admissions=_trusted(PhaseCapability.PREPARE),
            prepare_factory=lambda: handler,
        )

        outcome = await application.run(_request(PhaseCapability.PREPARE))

        if not handler.called:
            pytest.fail("Expected enabled capability handler to run")
        if outcome.status is not TerminalStatus.COMPLETE:
            pytest.fail("Expected completed non-CLI operation")
        if store.outcomes != [outcome]:
            pytest.fail("Expected terminal outcome to be durably handed to persistence")

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "capability",
    [
        PhaseCapability.INVESTIGATE,
        PhaseCapability.PROPOSE_ACTION,
        PhaseCapability.EXECUTE_ACTION,
    ],
)
def test_later_capabilities_block_before_factory_invocation(
    capability: PhaseCapability,
) -> None:
    async def exercise() -> None:
        store = RecordingOutcomeStore()
        constructed = False

        def forbidden_factory() -> LoopRecordingHandler:
            nonlocal constructed
            constructed = True
            return LoopRecordingHandler(asyncio.get_running_loop())

        application = Application(
            store,
            prepare_factory=forbidden_factory,
            triage_factory=forbidden_factory,
            report_build_factory=forbidden_factory,
            report_submit_factory=forbidden_factory,
        )
        outcome = await application.run(_request(capability))

        if constructed:
            pytest.fail("Blocked capability constructed an adapter or client")
        if outcome.status is not TerminalStatus.BLOCKED:
            pytest.fail("Later capability must be saved as blocked")
        if outcome.external_effect is not ExternalEffectState.NONE:
            pytest.fail("Admission rejection must have no external effect")
        if not outcome.limitations:
            pytest.fail("Blocked outcome must explain its limitation")
        if store.outcomes != [outcome]:
            pytest.fail("Blocked outcome was not saved")

    asyncio.run(exercise())


def test_outcome_carries_failures_limitations_and_result_refs() -> None:
    outcome = OperationOutcome(
        execution=ExecutionIdentity("execution-2"),
        capability=PhaseCapability.TRIAGE,
        status=TerminalStatus.INCOMPLETE,
        result_refs=(ResultRef("result-2", "triage", "1"),),
        limitations=(Limitation("missing_context", "Synthetic context unavailable"),),
        failures=(Failure("part_failed", "Synthetic part failed", retryable=True),),
        external_effect=ExternalEffectState.NONE,
    )
    if outcome.result_refs[0].kind != "triage":
        pytest.fail("Result reference kind was not retained")
    if outcome.limitations[0].code != "missing_context":
        pytest.fail("Limitation was not retained")
    if not outcome.failures[0].retryable:
        pytest.fail("Failure retryability was not retained")


class FakeEvidenceReader:
    """Synthetic evidence implementation with no provider dependency."""

    async def read(self, reference: VersionRef) -> bytes:
        return f"{reference.kind}:{reference.version}".encode()


class FakeResultProducer:
    """Synthetic result producer accepted through the narrow protocol."""

    async def produce(self, request: OperationRequest) -> StageResult:
        return StageResult(
            result_id="fake-produced",
            kind="prepared",
            schema_version="1",
            execution=request.execution,
            attempt=AttemptIdentity("fake-attempt"),
            input_refs=(),
            source_versions=request.target_inputs,
            prepared_versions=(),
            topic_versions=(),
            configuration_version="config-v1",
            code_version="build-v1",
            status=TerminalStatus.COMPLETE,
            acceptable=True,
        )


def test_fake_evidence_and_result_producer_fit_extension_protocols() -> None:
    async def consume(
        reader: EvidenceReader, producer: ResultProducer
    ) -> tuple[bytes, StageResult]:
        request = _request(PhaseCapability.PREPARE)
        evidence = await reader.read(request.target_inputs[0])
        produced = await producer.produce(request)
        return evidence, produced

    evidence, produced = asyncio.run(
        consume(FakeEvidenceReader(), FakeResultProducer())
    )
    if evidence != b"source:v1":
        pytest.fail("Fake evidence reader did not satisfy the extension boundary")
    if produced.result_id != "fake-produced":
        pytest.fail("Fake result producer did not satisfy the extension boundary")


def test_report_submit_failure_is_saved_with_unknown_effect() -> None:
    class FailingSubmitHandler:
        async def run(self, request: OperationRequest) -> OperationOutcome:
            raise RuntimeError("synthetic submit failure")

    async def exercise() -> None:
        store = RecordingOutcomeStore()
        application = Application(
            store,
            trusted_admissions=_trusted(PhaseCapability.REPORT_SUBMIT),
            report_submit_factory=lambda: FailingSubmitHandler(),
        )
        outcome = await application.run(_request(PhaseCapability.REPORT_SUBMIT))
        if outcome.status is not TerminalStatus.FAILED:
            pytest.fail("Expected failed report submission outcome")
        if outcome.external_effect is not ExternalEffectState.UNKNOWN:
            pytest.fail("Unexpected submit failure must not be treated as safe retry")
        if store.outcomes != [outcome]:
            pytest.fail("Unknown-effect submit failure was not saved")

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("capability", "expected_effect"),
    [
        (PhaseCapability.PREPARE, ExternalEffectState.NONE),
        (PhaseCapability.REPORT_SUBMIT, ExternalEffectState.UNKNOWN),
    ],
)
def test_factory_failure_is_saved_as_safe_failed_outcome(
    capability: PhaseCapability,
    expected_effect: ExternalEffectState,
) -> None:
    async def exercise() -> None:
        store = RecordingOutcomeStore()

        def failing_factory() -> LoopRecordingHandler:
            raise RuntimeError("synthetic constructor failure")

        factories = {
            PhaseCapability.PREPARE: {"prepare_factory": failing_factory},
            PhaseCapability.REPORT_SUBMIT: {"report_submit_factory": failing_factory},
        }
        application = Application(
            store,
            trusted_admissions=_trusted(capability),
            **factories[capability],
        )
        outcome = await application.run(_request(capability))
        if outcome.status is not TerminalStatus.FAILED:
            pytest.fail("Factory failure did not become a failed outcome")
        if outcome.external_effect is not expected_effect:
            pytest.fail("Factory failure external effect was not conservative")
        if store.outcomes != [outcome]:
            pytest.fail("Factory failure outcome was not saved before return")

    asyncio.run(exercise())


def test_handler_contract_mismatch_is_saved_as_failed_outcome() -> None:
    class MismatchingHandler:
        async def run(self, request: OperationRequest) -> OperationOutcome:
            return OperationOutcome(
                execution=ExecutionIdentity("forged-execution"),
                capability=PhaseCapability.TRIAGE,
                status=TerminalStatus.COMPLETE,
            )

    async def exercise() -> None:
        store = RecordingOutcomeStore()
        application = Application(
            store,
            trusted_admissions=_trusted(PhaseCapability.PREPARE),
            prepare_factory=lambda: MismatchingHandler(),
        )
        outcome = await application.run(_request(PhaseCapability.PREPARE))
        if outcome.status is not TerminalStatus.FAILED:
            pytest.fail("Handler contract mismatch did not become a failed outcome")
        if store.outcomes != [outcome]:
            pytest.fail("Handler contract mismatch outcome was not saved")

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "capability",
    [
        PhaseCapability.PREPARE,
        PhaseCapability.TRIAGE,
        PhaseCapability.REPORT_BUILD,
        PhaseCapability.REPORT_SUBMIT,
    ],
)
def test_untrusted_request_cannot_construct_enabled_factory(
    capability: PhaseCapability,
) -> None:
    async def exercise() -> None:
        store = RecordingOutcomeStore()
        constructed = False

        def forbidden_factory() -> LoopRecordingHandler:
            nonlocal constructed
            constructed = True
            return LoopRecordingHandler(asyncio.get_running_loop())

        if capability is PhaseCapability.PREPARE:
            application = Application(store, prepare_factory=forbidden_factory)
        elif capability is PhaseCapability.TRIAGE:
            application = Application(store, triage_factory=forbidden_factory)
        elif capability is PhaseCapability.REPORT_BUILD:
            application = Application(store, report_build_factory=forbidden_factory)
        else:
            application = Application(store, report_submit_factory=forbidden_factory)
        outcome = await application.run(_request(capability))
        if constructed:
            pytest.fail("Default-denied request reached an enabled factory")
        if outcome.status is not TerminalStatus.BLOCKED:
            pytest.fail("Untrusted request must be blocked")
        if store.outcomes != [outcome]:
            pytest.fail("Admission denial was not saved")

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("caller", "authority_ref"),
    [
        ("forged-caller", "authority-1"),
        ("synthetic-caller", "forged-authority"),
        ("synthetic-caller", None),
    ],
)
def test_forged_caller_or_authority_cannot_reach_factory(
    caller: str,
    authority_ref: str | None,
) -> None:
    async def exercise() -> None:
        store = RecordingOutcomeStore()
        constructed = False

        def forbidden_factory() -> LoopRecordingHandler:
            nonlocal constructed
            constructed = True
            return LoopRecordingHandler(asyncio.get_running_loop())

        request = OperationRequest(
            execution=ExecutionIdentity("forged-admission"),
            caller=caller,
            capability=PhaseCapability.REPORT_BUILD,
            authority_ref=authority_ref,
        )
        application = Application(
            store,
            trusted_admissions=_trusted(PhaseCapability.REPORT_BUILD),
            report_build_factory=forbidden_factory,
        )
        outcome = await application.run(request)
        if constructed:
            pytest.fail("Forged caller or authority reached the report factory")
        if outcome.status is not TerminalStatus.BLOCKED:
            pytest.fail("Forged caller or authority must be blocked")

    asyncio.run(exercise())


def test_repeated_cancellation_drains_cancelled_outcome_save() -> None:
    class WaitingHandler:
        async def run(self, request: OperationRequest) -> OperationOutcome:
            await asyncio.Event().wait()
            raise RuntimeError("unreachable")

    class SlowOutcomeStore(RecordingOutcomeStore):
        def __init__(self) -> None:
            super().__init__()
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def save_outcome(self, outcome: OperationOutcome) -> None:
            self.started.set()
            await self.release.wait()
            await super().save_outcome(outcome)

    async def exercise() -> None:
        store = SlowOutcomeStore()
        application = Application(
            store,
            trusted_admissions=_trusted(PhaseCapability.PREPARE),
            prepare_factory=lambda: WaitingHandler(),
        )
        task = asyncio.create_task(application.run(_request(PhaseCapability.PREPARE)))
        await asyncio.sleep(0)
        task.cancel()
        await store.started.wait()
        task.cancel()
        await asyncio.sleep(0)
        if task.done():
            pytest.fail("Repeated cancellation returned before outcome persistence")
        store.release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        if len(store.outcomes) != 1:
            pytest.fail("Cancelled invocation did not save exactly one outcome")
        if store.outcomes[0].status is not TerminalStatus.CANCELLED:
            pytest.fail("Cancelled invocation saved the wrong terminal status")

    asyncio.run(exercise())


def test_cancellation_during_normal_terminal_save_is_drained() -> None:
    class CompleteHandler:
        async def run(self, request: OperationRequest) -> OperationOutcome:
            return OperationOutcome(
                execution=request.execution,
                capability=request.capability,
                status=TerminalStatus.COMPLETE,
            )

    class SlowOutcomeStore(RecordingOutcomeStore):
        def __init__(self) -> None:
            super().__init__()
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def save_outcome(self, outcome: OperationOutcome) -> None:
            self.started.set()
            await self.release.wait()
            await super().save_outcome(outcome)

    async def exercise() -> None:
        store = SlowOutcomeStore()
        application = Application(
            store,
            trusted_admissions=_trusted(PhaseCapability.PREPARE),
            prepare_factory=lambda: CompleteHandler(),
        )
        task = asyncio.create_task(application.run(_request(PhaseCapability.PREPARE)))
        await store.started.wait()
        task.cancel()
        task.cancel()
        await asyncio.sleep(0)
        if task.done():
            pytest.fail("Terminal save was abandoned on cancellation")
        store.release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        if len(store.outcomes) != 1:
            pytest.fail("Normal terminal outcome did not finish saving")
        if store.outcomes[0].status is not TerminalStatus.COMPLETE:
            pytest.fail("Cancellation rewrote an already terminal handler outcome")

    asyncio.run(exercise())

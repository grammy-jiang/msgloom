"""Durable filtering, grouping, and result-writing steps."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Callable
from typing import TypeVar

from msgloom.contracts import (
    ExternalEffectState,
    Failure,
    Limitation,
    OperationOutcome,
    OperationRequest,
    ResultRef,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence, StaleClaimError
from msgloom.preparation import PreparedRecord
from msgloom.preparation.codec import PreparedDataCodec
from msgloom.preparation.filtering import FilterResult, apply_filters
from msgloom.preparation.grouping import group_records

from ._state import RunState as _RunState
from .models import PreparationPlan

_T = TypeVar("_T")


class StageSteps:
    """Persist deterministic A2 stages after their dependencies are durable."""

    _persistence: Phase1Persistence
    _plan: PreparationPlan

    async def _filter_all(
        self,
        request: OperationRequest,
        records: tuple[PreparedRecord, ...],
        prepared_refs: tuple[ResultRef, ...],
        prepared_versions: tuple[VersionRef, ...],
        state: _RunState,
    ) -> tuple[tuple[FilterResult, ...], tuple[ResultRef, ...]]:
        values: list[FilterResult] = []
        refs: list[ResultRef] = []
        for ordinal, (record, prepared_ref, prepared_version) in enumerate(
            zip(records, prepared_refs, prepared_versions, strict=True)
        ):
            value = await self._run_sync_owned(
                apply_filters, record, self._plan.filter_config
            )
            ref = await self._save_value(
                request,
                state,
                "filter_result",
                "1",
                value,
                source_versions=(record.source,),
                prepared_versions=(prepared_version,),
                input_refs=(prepared_ref,),
                tag=f"filter:{ordinal}:{prepared_version.version}",
                rule_version=self._plan.filter_config.reference.version,
            )
            values.append(value)
            refs.append(ref)
        return tuple(values), tuple(refs)

    async def _group_all(
        self,
        request: OperationRequest,
        records: tuple[PreparedRecord, ...],
        prepared_refs: tuple[ResultRef, ...],
        prepared_versions: tuple[VersionRef, ...],
        filters: tuple[FilterResult, ...],
        filter_refs: tuple[ResultRef, ...],
        state: _RunState,
    ) -> tuple[ResultRef, ...]:
        groups = await self._run_sync_owned(group_records, records, filters)
        prepared_by_source = {
            record.source: (ref, version)
            for record, ref, version in zip(
                records, prepared_refs, prepared_versions, strict=True
            )
        }
        filter_by_source = {
            value.input: ref for value, ref in zip(filters, filter_refs, strict=True)
        }
        refs: list[ResultRef] = []
        for ordinal, value in enumerate(groups):
            inputs = tuple(
                prepared_by_source[member][0] for member in value.members
            ) + tuple(filter_by_source[member] for member in value.members)
            versions = tuple(prepared_by_source[member][1] for member in value.members)
            tag_members = "|".join(
                f"{item.kind}:{item.identity}:{item.version}" for item in versions
            )
            ref = await self._save_value(
                request,
                state,
                "group_result",
                "1",
                value,
                source_versions=value.members,
                prepared_versions=versions,
                input_refs=inputs,
                tag=f"group:{ordinal}:{tag_members}",
                rule_version=self._plan.filter_config.reference.version,
            )
            refs.append(ref)
        return tuple(refs)

    async def _save_value(
        self,
        request: OperationRequest,
        state: _RunState,
        kind: str,
        schema_version: str,
        value: object,
        *,
        source_versions: tuple[VersionRef, ...],
        input_refs: tuple[ResultRef, ...],
        tag: str,
        prepared_versions: tuple[VersionRef, ...] = (),
        status: TerminalStatus = TerminalStatus.COMPLETE,
        rule_version: str | None = None,
    ) -> ResultRef:
        result_id = self._result_id(request, kind, tag)
        data_ref = await self._run_sync_owned(
            self._persistence.semantic_reference,
            f"{result_id}:data",
            kind,
            schema_version,
            value,
        )
        result = StageResult(
            result_id=result_id,
            kind=kind,
            schema_version=schema_version,
            execution=request.execution,
            attempt=self._plan.attempt,
            input_refs=input_refs,
            source_versions=source_versions,
            prepared_versions=prepared_versions,
            topic_versions=(),
            configuration_version=self._plan.configuration_version,
            code_version=self._plan.code_version,
            rule_version=rule_version,
            status=status,
            acceptable=True,
            semantic_data_ref=data_ref,
        )
        ref = ResultRef(result_id, kind, schema_version)
        try:
            await self._persistence.append_result_with_data(
                result, value, claim=state.claim
            )
        except asyncio.CancelledError:
            saved = await self._persistence.get_result(result_id)
            if saved is not None and ref not in state.refs:
                state.refs.append(ref)
            raise
        state.refs.append(ref)
        return ref

    async def _prepared_version(self, record: PreparedRecord) -> VersionRef:
        payload = await self._run_sync_owned(PreparedDataCodec().encode, record)
        identity = hashlib.sha256(
            (
                f"{record.source.kind}\0{record.source.identity}\0"
                f"{record.source.version}\0prepared@1"
            ).encode()
        ).hexdigest()
        material = (
            self._plan.configuration_version.encode()
            + b"\0"
            + self._plan.code_version.encode()
            + b"\0"
            + payload
        )
        return VersionRef("prepared", identity, hashlib.sha256(material).hexdigest())

    def _result_id(
        self,
        request: OperationRequest,
        kind: str,
        tag: str,
    ) -> str:
        material = (
            f"{request.execution.value}\0{self._plan.attempt.value}\0"
            f"{kind}\0{tag}\0{self._plan.configuration_version}\0"
            f"{self._plan.code_version}\0{self._plan_fingerprint()}"
        ).encode()
        return "a2-" + hashlib.sha256(material).hexdigest()

    def _plan_fingerprint(self) -> str:
        work = self._plan.model_dump(mode="json", round_trip=True, warnings="error")
        work.pop("attempt")
        payload = json.dumps(
            work,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(payload).hexdigest()

    async def _run_sync_owned(
        self, function: Callable[..., _T], /, *args: object
    ) -> _T:
        """Run finite CPU/codec work off-loop and drain it on cancellation."""
        task = asyncio.create_task(asyncio.to_thread(function, *args))
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
        if cancelled:
            raise asyncio.CancelledError
        return task.result()

    @staticmethod
    def _outcome(
        request: OperationRequest,
        status: TerminalStatus,
        *,
        refs: tuple[ResultRef, ...] = (),
        limitations: tuple[Limitation, ...] = (),
        failures: tuple[Failure, ...] = (),
    ) -> OperationOutcome:
        return OperationOutcome(
            execution=request.execution,
            capability=request.capability,
            status=status,
            result_refs=refs,
            limitations=limitations,
            failures=failures,
            external_effect=ExternalEffectState.NONE,
        )


async def _finish_uninterrupted(
    persistence: Phase1Persistence,
    token,
    status: TerminalStatus,
    *,
    suppress_stale: bool = False,
    preserve_cancellation: bool = False,
) -> bool:
    """Drain claim completion without allowing stale cleanup to mask ownership."""
    task = asyncio.create_task(
        persistence.finish_claim(token, status, ExternalEffectState.NONE)
    )
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
        except StaleClaimError:
            break
    if task.cancelled():
        if cancelled or preserve_cancellation:
            raise asyncio.CancelledError
        raise RuntimeError("claim completion was cancelled")
    error = task.exception()
    if isinstance(error, StaleClaimError) and (suppress_stale or cancelled):
        if cancelled or preserve_cancellation:
            raise asyncio.CancelledError
        return False
    if error is not None:
        if cancelled or preserve_cancellation:
            raise asyncio.CancelledError
        raise error
    if cancelled or preserve_cancellation:
        raise asyncio.CancelledError
    return True

"""R2 effect fencing, cancellation, budget, and MIME regressions."""

from __future__ import annotations

import asyncio
import sqlite3
from email import policy
from email.parser import BytesParser
from pathlib import Path
from time import monotonic

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ExternalEffectState,
    TerminalStatus,
    VersionRef,
)
from msgloom.delivery import (
    ReportSubmissionPlanCodec,
    SubmissionAttempt,
    SubmissionAttemptCodec,
    TransportReceipt,
    build_mime,
    submission_claim_key,
)
from tests.delivery.helpers import (
    RecordingTransport,
    build_report,
    open_store,
    submission_handler,
    submission_plan,
    submission_request,
)


class CleanupTransport:
    """Hold cancellation cleanup behind an explicit synthetic barrier."""

    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.cleanup_started = asyncio.Event()
        self.cleanup_release = asyncio.Event()

    async def submit(
        self, send_bytes: bytes, *, timeout_seconds: float
    ) -> TransportReceipt:
        """Remain in owned cleanup until the test releases it."""
        del send_bytes, timeout_seconds
        self.entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cleanup_started.set()
            await self.cleanup_release.wait()
            raise
        raise RuntimeError("unreachable synthetic cleanup transport")


class SlowTransport:
    """Block until the handler's total operation deadline cancels the call."""

    def __init__(self) -> None:
        self.entered = asyncio.Event()

    async def submit(
        self, send_bytes: bytes, *, timeout_seconds: float
    ) -> TransportReceipt:
        """Wait forever unless the handler cancels the owned call."""
        del send_bytes, timeout_seconds
        self.entered.set()
        await asyncio.Event().wait()
        raise RuntimeError("unreachable synthetic transport")


def test_invalid_post_call_response_stays_unknown_across_restart(
    tmp_path: Path,
) -> None:
    """Oversized response metadata after PENDING cannot release the send gate."""

    async def exercise() -> None:
        path = tmp_path / "oversized.sqlite3"
        first = await open_store(path)
        report_ref, report = await build_report(first)
        plan_value = submission_plan(report_ref, report, suffix="oversized")
        transport = RecordingTransport(
            TransportReceipt(ExternalEffectState.ACCEPTED, "x" * 513)
        )
        outcome = await submission_handler(first, plan_value, transport).run(
            submission_request(plan_value)
        )
        if outcome.external_effect is not ExternalEffectState.UNKNOWN:
            pytest.fail("invalid post-call response released the effect gate")
        if len(transport.calls) != 1:
            pytest.fail("synthetic external call count changed")
        if not any(
            ref.result_id == plan_value.parts[0].attempt_result_id
            for ref in outcome.result_refs
        ):
            pytest.fail("unknown outcome lost its durable attempt prefix")
        await first.close()

        reopened = await open_store(path)
        try:
            retry = submission_plan(report_ref, report, suffix="oversized-retry")
            retry_transport = RecordingTransport()
            blocked = await submission_handler(
                reopened,
                retry,
                retry_transport,
                attempt="oversized-retry-attempt",
            ).run(submission_request(retry, identity="oversized-retry"))
            if blocked.external_effect is not ExternalEffectState.UNKNOWN:
                pytest.fail("restart lost the uncertain external effect")
            if retry_transport.calls:
                pytest.fail("uncertain response allowed a duplicate external call")
        finally:
            await reopened.close()

    asyncio.run(exercise())


def test_rejected_retry_requires_exact_saved_attempt(tmp_path: Path) -> None:
    """A proven rejection alone does not authorize regenerated MIME bytes."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "rejected-exact.sqlite3")
        try:
            report_ref, report = await build_report(store)
            initial = submission_plan(report_ref, report, suffix="reject")
            first = RecordingTransport(
                TransportReceipt(ExternalEffectState.REJECTED, "400")
            )
            await submission_handler(store, initial, first).run(
                submission_request(initial)
            )
            unsafe = submission_plan(report_ref, report, suffix="unsafe")
            second = RecordingTransport()
            outcome = await submission_handler(
                store, unsafe, second, attempt="unsafe-retry"
            ).run(submission_request(unsafe, identity="unsafe-retry"))
            if outcome.status is TerminalStatus.COMPLETE or second.calls:
                pytest.fail("rejected retry regenerated or resent MIME")
        finally:
            await store.close()

    asyncio.run(exercise())


def test_repeated_cancellation_waits_for_transport_cleanup(tmp_path: Path) -> None:
    """Repeated caller cancellation cannot hand back transport ownership early."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "cancel-cleanup.sqlite3")
        try:
            report_ref, report = await build_report(store)
            plan_value = submission_plan(report_ref, report, suffix="cleanup")
            transport = CleanupTransport()
            task = asyncio.create_task(
                submission_handler(store, plan_value, transport, timeout=30.0).run(
                    submission_request(plan_value)
                )
            )
            await transport.entered.wait()
            task.cancel()
            await transport.cleanup_started.wait()
            task.cancel()
            await asyncio.sleep(0.05)
            if task.done():
                pytest.fail("caller returned before owned transport cleanup")
            transport.cleanup_release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            key = submission_claim_key(
                report.report_ref.identity,
                report.report_ref.version,
                report.policy_ref.identity,
                report.policy_ref.version,
                1,
            )
            snapshot = await store.inspect_claim(key)
            if snapshot.current_effect is not ExternalEffectState.UNKNOWN:
                pytest.fail("cancelled external call did not retain UNKNOWN")
        finally:
            await store.close()

    asyncio.run(exercise())


def test_total_deadline_cannot_report_success_and_keeps_attempt_prefix(
    tmp_path: Path,
) -> None:
    """The total budget includes transport and returns only after cleanup."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "deadline.sqlite3")
        try:
            report_ref, report = await build_report(store)
            plan_value = submission_plan(report_ref, report, suffix="deadline")
            transport = SlowTransport()
            started = monotonic()
            outcome = await submission_handler(
                store, plan_value, transport, timeout=5.0
            ).run(submission_request(plan_value))
            elapsed = monotonic() - started
            if outcome.status is TerminalStatus.COMPLETE:
                pytest.fail("operation completed after its total deadline")
            if outcome.external_effect is not ExternalEffectState.UNKNOWN:
                pytest.fail("deadline after call start did not remain UNKNOWN")
            if not any(
                ref.result_id == plan_value.parts[0].attempt_result_id
                for ref in outcome.result_refs
            ):
                pytest.fail("deadline discarded the durable attempt prefix")
            if elapsed < 4.0:
                pytest.fail("synthetic deadline returned before the configured budget")
        finally:
            await store.close()

    asyncio.run(exercise())


def test_stale_owner_cannot_publish_attempt_after_reclaim(tmp_path: Path) -> None:
    """A reclaimed NOT_STARTED claim fences the old attempt publication."""

    async def exercise() -> None:
        path = tmp_path / "stale-publication.sqlite3"
        first = await open_store(path)
        report_ref, report = await build_report(first)
        plan_value = submission_plan(report_ref, report, suffix="stale")
        entered = asyncio.Event()
        release = asyncio.Event()
        original = first.append_result_with_data

        async def pause_attempt(result, value, **kwargs):
            if isinstance(value, SubmissionAttempt):
                entered.set()
                await release.wait()
            return await original(result, value, **kwargs)

        first.append_result_with_data = pause_attempt  # type: ignore[method-assign]
        task = asyncio.create_task(
            submission_handler(
                first,
                plan_value,
                RecordingTransport(),
                timeout=30.0,
            ).run(submission_request(plan_value))
        )
        await entered.wait()
        key = submission_claim_key(
            report.report_ref.identity,
            report.report_ref.version,
            report.policy_ref.identity,
            report.policy_ref.version,
            1,
        )
        old = (await first.inspect_claim(key)).current_token
        if old is None:
            pytest.fail("synthetic old claim is missing")
        connection = sqlite3.connect(path)
        try:
            connection.execute(
                "UPDATE phase1_work_claims SET expires_at = ? WHERE claim_token = ?",
                ("2000-01-01T00:00:00+00:00", old.token),
            )
            connection.commit()
        finally:
            connection.close()

        second = await open_store(path)
        try:
            winner = await second.acquire_claim(
                key,
                ClaimKind.REPORT_SUBMIT,
                ExecutionIdentity("winner-execution"),
                AttemptIdentity("winner-attempt"),
                required_inputs=(report_ref,),
                lease_seconds=10.0,
            )
            release.set()
            outcome = await task
            if outcome.status is TerminalStatus.COMPLETE:
                pytest.fail("stale owner reported successful publication")
            if (
                await second.get_result(plan_value.parts[0].attempt_result_id)
                is not None
            ):
                pytest.fail("stale owner published attempt evidence after reclaim")
            await second.finish_claim(
                winner,
                TerminalStatus.FAILED,
                ExternalEffectState.NOT_STARTED,
            )
        finally:
            await second.close()
            await first.close()

    asyncio.run(exercise())


def test_claim_key_is_unambiguous_for_colon_bearing_references() -> None:
    """Canonical tuple hashing prevents delimiter-collision claim scopes."""
    first = submission_claim_key("a:b", "c", "d", "e", 1)
    second = submission_claim_key("a", "b:c", "d", "e", 1)
    if first == second:
        pytest.fail("colon-bearing report references collided")


def test_mime_headers_wrapping_and_attempt_codec_are_exact(tmp_path: Path) -> None:
    """Generated MIME is injection-safe, wrapped, and byte-exact on replay."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "mime.sqlite3")
        try:
            report_ref, report = await build_report(store)
            unicode_report = report.model_copy(
                update={"report_ref": VersionRef("report", "报告", "v1")}
            )
            raw = build_mime(
                unicode_report,
                unicode_report.parts[0],
                unicode_report.destination.destination_identity,
            )
            message = BytesParser(policy=policy.default).parsebytes(raw)
            if "报告" not in str(message["Subject"]):
                pytest.fail("non-ASCII report identity was not safely encoded")
            payloads = list(message.iter_parts())
            if len(payloads) != 2:
                pytest.fail("multipart alternative structure is invalid")
            if (
                payloads[0].get_payload(decode=True)
                != report.parts[0].plain_text.encode()
            ):
                pytest.fail("plain MIME payload changed")
            if payloads[1].get_payload(decode=True) != report.parts[0].html.encode():
                pytest.fail("HTML MIME payload changed")
            for block in raw.split(b"Content-Transfer-Encoding: base64\r\n\r\n")[1:]:
                encoded = block.split(b"\r\n--", 1)[0]
                if any(len(line) > 76 for line in encoded.split(b"\r\n")):
                    pytest.fail("base64 MIME line exceeded 76 characters")

            bad = report.model_copy(
                update={"report_ref": VersionRef("report", "bad\nidentity", "v1")}
            )
            with pytest.raises(ValueError, match="header newlines"):
                build_mime(bad, bad.parts[0], bad.destination.destination_identity)

            plan_value = submission_plan(report_ref, report, suffix="codec")
            outcome = await submission_handler(
                store,
                plan_value,
                RecordingTransport(
                    TransportReceipt(ExternalEffectState.REJECTED, "400")
                ),
            ).run(submission_request(plan_value))
            attempt_ref = next(
                ref
                for ref in outcome.result_refs
                if ref.result_id == plan_value.parts[0].attempt_result_id
            )
            result = await store.get_result(attempt_ref.result_id)
            if result is None or result.semantic_data_ref is None:
                pytest.fail("submission attempt evidence is missing")
            attempt = await store.load_semantic_data(result.semantic_data_ref)
            if not isinstance(attempt, SubmissionAttempt):
                pytest.fail("submission attempt semantic type changed")
            codec = SubmissionAttemptCodec()
            encoded = codec.encode(attempt)
            decoded = codec.decode(encoded)
            if decoded.send_bytes != attempt.send_bytes:
                pytest.fail("attempt codec changed exact saved send bytes")
            if decoded.send_sha256 != attempt.send_sha256:
                pytest.fail("attempt codec changed the send digest")

            forged = plan_value.model_copy(update={"parts": ()})
            with pytest.raises(TypeError, match="delivery data failed validation"):
                ReportSubmissionPlanCodec().encode(forged)
        finally:
            await store.close()

    asyncio.run(exercise())

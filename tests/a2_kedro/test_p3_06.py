"""P3-06: typed, scoped context for non-communication sources.

All data is synthetic. No test touches a provider, a network or a file.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.semantics import context_types as ct
from msgloom.a2_kedro.semantics.context_types import (
    ContextGrant,
    ContextPublication,
    ContextRefusal,
    ContextType,
    ConversationScope,
    PublicationTarget,
    context_type_of,
)
from msgloom.contracts import Limitation, ResultRef, VersionRef
from msgloom.preparation.contracts import PageLocation
from msgloom.preparation.records import NativeRelationship, PreparedSourceType
from msgloom.preparation_pipeline.intake_models import IntakeScope
from msgloom.sources import CollectedRecord, ContentKind
from msgloom.sources._snapshot import capture_selection
from msgloom.sources.handoff_models import A1CatalogIdentity
from msgloom.sources.models import (
    CollectedBody,
    CollectedSelection,
    SourceMetadata,
)
from tests.a2_kedro.helpers import check
from tests.a2_kedro.p3_06_bound import publish_context

PII = "alice.secret@example.test"
WHEN = datetime(2026, 1, 1, 12, 30, 45, 999999, tzinfo=UTC)
WORKSET = ResultRef("workset-1", "preparation_intake_workset", "1")
CONVERSATION = ConversationScope("thread", "conv-1")

CASES: tuple[tuple[PreparedSourceType, ContextType, str], ...] = (
    (
        PreparedSourceType.OUTLOOK_CALENDAR,
        ContextType.CALENDAR_EVENT,
        "outlook_calendar",
    ),
    (PreparedSourceType.TODO, ContextType.TODO_ITEM, "todo"),
    (PreparedSourceType.ONEDRIVE, ContextType.ONEDRIVE_FILE, "onedrive"),
    (PreparedSourceType.CONTACT, ContextType.CONTACT, "contacts"),
)


def scope_for(stream: str, source_id: str = "src-1") -> IntakeScope:
    return IntakeScope(
        catalog=A1CatalogIdentity(catalog_identity="cat-1", schema_version=1),
        source_id=source_id,
        stream=stream,  # type: ignore[arg-type]
        consumer_id="consumer-1",
    )


def record_of(
    source_type: PreparedSourceType,
    *,
    identity: str = "item-1",
    subject: str | None = PII,
    **changes: Any,
) -> CollectedRecord:
    source = VersionRef(source_type.value, identity, "observation-1")
    scope = VersionRef("source_scope", "src-1", "1")
    values: dict[str, Any] = {
        "source": source,
        "source_scope": scope,
        "source_type": source_type,
        "semantic_identity": identity,
        "observed_at": WHEN,
        "source_time": WHEN,
        "subject": subject,
        "sender": None,
        "author": None,
        "recipients": (),
        "source_content_kind": ContentKind.JSON,
        "source_bytes": None,
        "body": None,
        "alternate_bodies": (),
        "attachments": (),
        "relationships": (NativeRelationship(kind="source_scope", target=scope),),
        "metadata": (),
        "source_locations": (),
        "limitations": (),
    }
    values.update(changes)
    return CollectedRecord(**values)


def selection_of(source_type: PreparedSourceType, **kw: Any) -> CollectedSelection:
    return capture_selection(record_of(source_type, **kw))


def raw_selection(base: PreparedSourceType, **changes: Any) -> CollectedSelection:
    """Build a selection that skips validation, as a hostile caller could."""
    record = record_of(base).model_copy(update=changes)
    return CollectedSelection.model_construct(
        source=record.source,
        selection=VersionRef("collected_selection", "s", "1"),
        record=record,
    )


def grant_for(stream: str, *conversations: ConversationScope) -> ContextGrant:
    return ContextGrant(scope_for(stream), WORKSET, tuple(conversations))


def target_for(
    stream: str, conversation: ConversationScope | None = None
) -> PublicationTarget:
    return PublicationTarget(scope_for(stream), WORKSET, conversation)


def refusal_code(call: Callable[[], object]) -> str:
    try:
        call()
    except ContextRefusal as error:
        check(PII not in str(error) and PII not in repr(error), "error echoes input")
        return error.code
    return "published"


def publish_default(
    source_type: PreparedSourceType, stream: str, **kw: Any
) -> ContextPublication:
    return publish_context(
        selection_of(source_type, **kw), grant_for(stream), target_for(stream)
    )


# --- positive, one per type -------------------------------------------------


@pytest.mark.parametrize(("source_type", "expected", "stream"), CASES)
def test_each_context_type_is_published_with_metadata_only(
    source_type: PreparedSourceType, expected: ContextType, stream: str
) -> None:
    out = publish_default(source_type, stream)
    check(out.context_type is expected, "closed context type")
    check(out.stream == stream and out.workset == WORKSET, "scope fields")
    check(out.conversation is None, "no conversation requested")
    check(out.source.kind == source_type.value, "exact source ref")
    check(out.source_time == int(WHEN.timestamp()), "whole seconds, floored")
    check(len(out.identity_sha256) == 64 and out.title_sha256 is not None, "digests")
    check(PII not in repr(out), "the subject text is never published")
    check(
        out.limitations == ("time_whole_seconds", "type_fields_unavailable"),
        "sorted fixed limitations",
    )


def test_conversation_target_is_published_when_granted() -> None:
    stream = "outlook_calendar"
    out = publish_context(
        selection_of(PreparedSourceType.OUTLOOK_CALENDAR),
        grant_for(stream, CONVERSATION, ConversationScope("mailbox", "m-1")),
        target_for(stream, CONVERSATION),
    )
    check(out.conversation == CONVERSATION, "conversation kept")


def test_content_and_limits_are_counted_not_published() -> None:
    body = CollectedBody(
        kind=ContentKind.PLAIN,
        content=PII,
        saved_bytes=None,
        location=PageLocation(page_number=1),
    )
    meta = (SourceMetadata(name="n", value=PII),)
    out = publish_default(
        PreparedSourceType.ONEDRIVE,
        "onedrive",
        body=body,
        metadata=meta,
        limitations=(Limitation("code", "detail"),),
        subject=None,
    )
    check(out.metadata_count == 1 and out.title_sha256 is None, "counts only")
    check(
        out.limitations
        == (
            "content_not_published",
            "source_limited",
            "time_whole_seconds",
            "type_fields_unavailable",
        ),
        "content and source limits",
    )
    check(PII not in repr(out), "no body or metadata value")


def test_non_utc_time_is_floored_in_utc() -> None:
    zone = timezone(timedelta(hours=5))
    local = datetime(2026, 1, 1, 17, 30, 45, 5, tzinfo=zone)
    out = publish_default(PreparedSourceType.TODO, "todo", source_time=local)
    check(out.source_time == int(local.timestamp()), "same instant as UTC")


# --- determinism -------------------------------------------------------------


def test_publication_is_deterministic_and_type_scoped() -> None:
    first = publish_default(PreparedSourceType.TODO, "todo")
    second = publish_default(PreparedSourceType.TODO, "todo")
    check(first == second, "same input, same output")
    other = publish_default(PreparedSourceType.TODO, "todo", identity="item-2")
    check(first.identity_sha256 != other.identity_sha256, "identity digest differs")
    same_id = publish_default(PreparedSourceType.CONTACT, "contacts")
    check(same_id.identity_sha256 != first.identity_sha256, "type is in the digest")


# --- negative: type ----------------------------------------------------------


@pytest.mark.parametrize(
    "source_type",
    (
        PreparedSourceType.OUTLOOK_EMAIL,
        PreparedSourceType.TEAMS_CHAT_MESSAGE,
        PreparedSourceType.TEAMS_CHANNEL_MESSAGE,
    ),
)
def test_communication_sources_are_not_context(source_type: PreparedSourceType) -> None:
    code = refusal_code(
        lambda: publish_context(
            selection_of(source_type), grant_for("todo"), target_for("todo")
        )
    )
    check(code == "not_context_source", "communication refused")


def test_unknown_source_type_is_refused() -> None:
    for bad in ("calendar_v2", "todo", None, 7):
        selection = raw_selection(PreparedSourceType.TODO, source_type=bad)
        code = refusal_code(
            lambda s=selection: publish_context(
                s, grant_for("todo"), target_for("todo")
            )
        )
        check(code == "unknown_source_type", f"refuse a non-enum source type {bad!r}")
    check(refusal_code(lambda: context_type_of("todo")) == "unknown_source_type", "str")


# --- negative: scope ---------------------------------------------------------


def _scope_cases() -> dict[str, tuple[ContextGrant, PublicationTarget]]:
    stream = "todo"
    return {
        "other_source": (
            grant_for(stream),
            PublicationTarget(scope_for(stream, "src-2"), WORKSET, None),
        ),
        "other_workset": (
            grant_for(stream),
            PublicationTarget(
                scope_for(stream),
                ResultRef("workset-2", "preparation_intake_workset", "1"),
                None,
            ),
        ),
        "ungranted_conversation": (grant_for(stream), target_for(stream, CONVERSATION)),
        "other_conversation": (
            grant_for(stream, CONVERSATION),
            target_for(stream, ConversationScope("thread", "conv-2")),
        ),
        "same_id_other_kind": (
            grant_for(stream, CONVERSATION),
            target_for(stream, ConversationScope("channel", "conv-1")),
        ),
    }


@pytest.mark.parametrize("name", sorted(_scope_cases()))
def test_out_of_scope_publication_is_refused(name: str) -> None:
    grant, target = _scope_cases()[name]
    code = refusal_code(
        lambda: publish_context(selection_of(PreparedSourceType.TODO), grant, target)
    )
    check(code == "out_of_scope", f"{name} must be refused")


def test_grant_stream_must_carry_the_type() -> None:
    code = refusal_code(
        lambda: publish_context(
            selection_of(PreparedSourceType.TODO),
            grant_for("outlook_calendar"),
            target_for("outlook_calendar"),
        )
    )
    check(code == "stream_mismatch", "a todo cannot enter a calendar scope")
    mail = refusal_code(
        lambda: publish_context(
            selection_of(PreparedSourceType.CONTACT),
            grant_for("outlook_mail"),
            target_for("outlook_mail"),
        )
    )
    check(mail == "stream_mismatch", "a contact cannot enter a mail scope")


def test_unknown_conversation_kind_and_wrong_workset_kind_are_refused() -> None:
    bad_kind = ConversationScope("calendar", "x")  # type: ignore[arg-type]
    code = refusal_code(
        lambda: publish_context(
            selection_of(PreparedSourceType.TODO),
            grant_for("todo", bad_kind),
            target_for("todo", bad_kind),
        )
    )
    check(code == "out_of_scope", "conversation kind is closed")
    wrong = ResultRef("w", "prepared", "2")
    code = refusal_code(
        lambda: publish_context(
            selection_of(PreparedSourceType.TODO),
            ContextGrant(scope_for("todo"), wrong),
            PublicationTarget(scope_for("todo"), wrong),
        )
    )
    check(code == "wrong_type", "workset must be preparation_intake_workset@1")


def test_disabling_the_scope_guard_is_detected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutation check: with the guard off, every scope negative would fail."""
    escaped: list[str] = []
    for name, (grant, target) in _scope_cases().items():
        run = lambda g=grant, t=target: publish_context(
            selection_of(PreparedSourceType.TODO), g, t
        )
        check(refusal_code(run) == "out_of_scope", f"{name} refused with guard")
        with monkeypatch.context() as patch:
            patch.setattr(ct, "_check_scope", lambda *_a, **_k: None)
            if refusal_code(run) == "published":
                escaped.append(name)
    check(
        sorted(escaped) == sorted(_scope_cases()),
        "each scope negative must publish when the guard is disabled",
    )


# --- negative: hostile, oversized, wrong types ------------------------------


HOSTILE = (
    "id\x00x",
    "id\nx",
    "id x",
    "id\u0085x",
    "id\x7fx",
    "\ud800id",
    "",
)


@pytest.mark.parametrize("text", HOSTILE)
def test_hostile_identity_text_is_refused_without_echo(text: str) -> None:
    selection = raw_selection(PreparedSourceType.TODO, semantic_identity=PII + text)
    unsafe = refusal_code(
        lambda: publish_context(selection, grant_for("todo"), target_for("todo"))
    )
    check(unsafe == ("unsafe_text" if text else "published"), "hostile identity")
    empty = raw_selection(PreparedSourceType.TODO, semantic_identity=text)
    code = refusal_code(
        lambda: publish_context(empty, grant_for("todo"), target_for("todo"))
    )
    check(code == "unsafe_text", "identity with no clean text is refused")


@pytest.mark.parametrize("text", HOSTILE[:5])
def test_hostile_scope_text_is_refused(text: str) -> None:
    scope = scope_for("todo", PII + text)
    code = refusal_code(
        lambda: publish_context(
            selection_of(PreparedSourceType.TODO),
            ContextGrant(scope, WORKSET),
            PublicationTarget(scope, WORKSET),
        )
    )
    check(code == "unsafe_text", "scope text is checked")


def test_hostile_subject_is_hashed_never_echoed() -> None:
    out = publish_default(PreparedSourceType.TODO, "todo", subject=PII + "\n\x00")
    check(PII not in repr(out), "subject text stays out")
    surrogate = raw_selection(PreparedSourceType.TODO, subject=PII + "\ud800")
    code = refusal_code(
        lambda: publish_context(surrogate, grant_for("todo"), target_for("todo"))
    )
    check(code == "unsafe_text", "unencodable subject refused")


def test_oversized_inputs_are_refused() -> None:
    big_subject = PII + "a" * ct.MAX_SUBJECT_BYTES
    check(
        refusal_code(
            lambda: publish_default(
                PreparedSourceType.TODO, "todo", subject=big_subject
            )
        )
        == "oversized",
        "subject bound",
    )
    many = tuple(SourceMetadata(name="n", value="v") for _ in range(ct.MAX_ITEMS + 1))
    check(
        refusal_code(
            lambda: publish_default(PreparedSourceType.TODO, "todo", metadata=many)
        )
        == "oversized",
        "item bound",
    )
    long_id = PII + "b" * ct.MAX_TEXT_BYTES
    scope = scope_for("todo")
    grant = ContextGrant(scope, WORKSET, (ConversationScope("thread", long_id),))
    code = refusal_code(
        lambda: publish_context(
            selection_of(PreparedSourceType.TODO),
            grant,
            PublicationTarget(scope, WORKSET, ConversationScope("thread", long_id)),
        )
    )
    check(code == "oversized", "text bound")
    crowd = tuple(ConversationScope("thread", f"c{i}") for i in range(65))
    code = refusal_code(
        lambda: publish_context(
            selection_of(PreparedSourceType.TODO),
            ContextGrant(scope, WORKSET, crowd),
            PublicationTarget(scope, WORKSET, crowd[0]),
        )
    )
    check(code == "oversized", "grant list bound")


def test_time_range_is_enforced() -> None:
    early = datetime(1960, 1, 1, tzinfo=UTC)
    code = refusal_code(
        lambda: publish_default(PreparedSourceType.TODO, "todo", source_time=early)
    )
    check(code == "invalid_time", "before the epoch refused")


def test_wrong_types_are_refused() -> None:
    sel = selection_of(PreparedSourceType.TODO)
    grant, target = grant_for("todo"), target_for("todo")
    naive = record_of(PreparedSourceType.TODO).model_copy(
        update={"source_time": datetime(2026, 1, 1)}
    )
    bad_time = CollectedSelection.model_construct(
        source=naive.source, selection=sel.selection, record=naive
    )
    other = replace(sel.record.source, identity="other")
    mismatch = CollectedSelection.model_construct(
        source=other, selection=sel.selection, record=sel.record
    )
    calls: dict[str, Callable[[], object]] = {
        "record": lambda: publish_context(sel.record, grant, target),  # type: ignore[arg-type]
        "none": lambda: publish_context(None, grant, target),  # type: ignore[arg-type]
        "dict": lambda: publish_context({"x": PII}, grant, target),  # type: ignore[arg-type]
        "grant": lambda: publish_context(sel, None, target),  # type: ignore[arg-type]
        "target": lambda: publish_context(sel, grant, grant),  # type: ignore[arg-type]
        "conversations": lambda: publish_context(
            sel,
            ContextGrant(grant.scope, WORKSET, [CONVERSATION]),  # type: ignore[arg-type]
            target_for("todo", CONVERSATION),
        ),
        "scope": lambda: publish_context(
            sel,
            ContextGrant(PII, WORKSET),  # type: ignore[arg-type]
            target,
        ),
        "naive_time": lambda: publish_context(bad_time, grant, target),
    }
    for name, call in calls.items():
        check(refusal_code(call) == "wrong_type", f"{name} must be wrong_type")
    check(
        refusal_code(lambda: publish_context(mismatch, grant, target))
        == "inconsistent_record",
        "selection source must equal the record source",
    )


def test_errors_are_fixed_text_for_every_code() -> None:
    for code, text in ct._MESSAGES.items():
        error = ContextRefusal(code)
        check(str(error) == text and error.code == code, "fixed message")
        check(isinstance(error, A2ContractError), "is an A2 contract error")

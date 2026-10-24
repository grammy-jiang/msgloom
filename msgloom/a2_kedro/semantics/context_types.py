"""
Typed, scoped context for non-communication sources (P3-06).

Calendar, To Do, OneDrive and Contacts records are not messages. They do
not join a communication group. This module is a pure, deterministic
function layer. It reads one typed
:class:`~msgloom.sources.models.CollectedSelection` and returns one
:class:`ContextPublication`: metadata-level context of a closed type and an
explicit scope. It reads no file, clock, database, provider or network.

Closed context types
====================

=====================  ===========================  ====================
Context type           Source type                  Stream
=====================  ===========================  ====================
``calendar_event``     ``outlook_calendar``         ``outlook_calendar``
``todo_item``          ``todo``                     ``todo``
``onedrive_file``      ``onedrive``                 ``onedrive``
``contact``            ``contact``                  ``contacts``
=====================  ===========================  ====================

Mail and Teams source types are communication. They are refused with
``not_context_source``. A value that is not a known source type is refused
with ``unknown_source_type``. The function never guesses a type from a
subject, a name or a metadata value.

Scope
=====

A :class:`FrozenSelection` binds one ``CollectedSelection`` to the Intake
scope and the workset under which it was frozen. The selection contract
has no workset, so this wrapper holds the binding. A bare selection is
refused. A :class:`ContextGrant` is the authority of the workset owner. It
names the Intake scope and the workset that it covers. It may also list
the conversations that accept context. A :class:`PublicationTarget` asks
for one destination. The scope guard allows the request only when:

* the target scope and the target workset equal the grant exactly;
* the grant source ID equals the identity of the record source scope;
* the grant stream is the stream of the context type;
* the grant scope and workset equal the scope and workset of the frozen
  selection. A missing or malformed binding is ``wrong_type``; a
  different one is ``binding_mismatch``;
* the target conversation, if any, is listed in the grant.

Two scopes that share a source ID or a consumer ID but differ in any other
part are different scopes. The guard never widens a scope.

What is published
=================

Only metadata: the exact source and source-scope references, a digest of
the semantic identity, a digest of the subject, the source time in whole
UTC seconds, counts, and limitation codes. A body, an attachment, a party,
a metadata value or a location is never published. Digests are not salted.
A reader can test a guess against them.

Limitations
===========

Every publication carries a sorted set of limitation codes:

* ``content_not_published``: the record has a body, an alternate body or
  an attachment. None is published.
* ``type_fields_unavailable``: always. The contracts hold no typed field for
  event time span, task state, file name or contact data.
* ``source_limited``: the record carries one or more source limitations.
* ``time_whole_seconds``: always. Source time is floored to seconds.

Failure handling
================

Any problem raises :exc:`ContextRefusal`. The message is fixed text for one
closed ``code``. It never carries an identifier, a subject, a scope or an
offset. Nothing is partly published.

PROVISIONAL, CANDIDATE/RESEARCH: ``ContextPublication`` is an in-process
record. It is not a wire kind and it has no header, no canonical bytes and
no schema ID. See ``docs/notes/a2-v2-parser-p3-06.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal, get_args

from msgloom.a2_kedro.contracts.codec import (
    MAX_TEXT_BYTES,
    A2ContractError,
    domain_sha256,
    has_control_character,
)
from msgloom.a2_kedro.contracts.relations import ScopeKind
from msgloom.contracts import ResultRef, VersionRef
from msgloom.preparation.records import PreparedSourceType
from msgloom.preparation_pipeline.intake_models import (
    INTAKE_KIND,
    INTAKE_SCHEMA_VERSION,
    IntakeScope,
)
from msgloom.sources.models import CollectedRecord, CollectedSelection

#: Provisional bounds. They are not production limits.
MAX_SUBJECT_BYTES = 8192
MAX_ITEMS = 256
MAX_CONVERSATIONS = 64
MAX_EPOCH_SECONDS = 2**40

IDENTITY_DOMAIN = "a2-context-identity@1"
TITLE_DOMAIN = "a2-context-title@1"

_CONVERSATION_KINDS = frozenset(get_args(ScopeKind))

#: Closed vocabularies for the fields of a publication.
ContextStream = Literal["outlook_calendar", "todo", "onedrive", "contacts"]
LimitationCode = Literal[
    "content_not_published",
    "source_limited",
    "time_whole_seconds",
    "type_fields_unavailable",
]


class ContextType(StrEnum):
    """Closed set of context types. Order is not meaningful."""

    CALENDAR_EVENT = "calendar_event"
    TODO_ITEM = "todo_item"
    ONEDRIVE_FILE = "onedrive_file"
    CONTACT = "contact"


_TYPE_OF_SOURCE: dict[PreparedSourceType, ContextType] = {
    PreparedSourceType.OUTLOOK_CALENDAR: ContextType.CALENDAR_EVENT,
    PreparedSourceType.TODO: ContextType.TODO_ITEM,
    PreparedSourceType.ONEDRIVE: ContextType.ONEDRIVE_FILE,
    PreparedSourceType.CONTACT: ContextType.CONTACT,
}
_COMMUNICATION: frozenset[PreparedSourceType] = frozenset(
    {
        PreparedSourceType.OUTLOOK_EMAIL,
        PreparedSourceType.TEAMS_CHANNEL_MESSAGE,
        PreparedSourceType.TEAMS_CHAT_MESSAGE,
    }
)
#: The Intake stream name that carries each context type.
STREAM_OF_TYPE: dict[ContextType, ContextStream] = {
    ContextType.CALENDAR_EVENT: "outlook_calendar",
    ContextType.TODO_ITEM: "todo",
    ContextType.ONEDRIVE_FILE: "onedrive",
    ContextType.CONTACT: "contacts",
}

_MESSAGES: dict[str, str] = {
    "wrong_type": "context input has the wrong type",
    "unknown_source_type": "source type is not known",
    "not_context_source": "source type is communication, not context",
    "stream_mismatch": "grant stream does not carry this context type",
    "out_of_scope": "publication target is outside the granted scope",
    "source_mismatch": "grant source does not match the record source scope",
    "binding_mismatch": "grant scope or workset does not match the frozen record",
    "oversized": "context input exceeds a bound",
    "unsafe_text": "context text is empty, unencodable or has a control character",
    "inconsistent_record": "selection and record disagree",
    "invalid_time": "source time is outside the accepted range",
}


class ContextRefusal(A2ContractError):
    """
    The function refused to publish. ``code`` is one closed reason.

    The message is fixed text for ``code``. It holds no input value.
    """

    def __init__(self, code: str) -> None:
        super().__init__(_MESSAGES[code])
        self.code = code


@dataclass(frozen=True, slots=True)
class ConversationScope:
    """One conversation that may accept context (existing scope kinds)."""

    kind: ScopeKind
    scope_id: str


@dataclass(frozen=True, slots=True)
class FrozenSelection:
    """
    One selection bound to the scope and workset that froze it.

    The freezing stage makes this value. ``scope`` and ``workset`` are
    required and have no default. The guard refuses a missing or
    malformed value, and a grant that names other values. This module
    cannot prove that the stage made the binding; see the P3-06 note.
    """

    selection: CollectedSelection
    scope: IntakeScope
    workset: ResultRef


@dataclass(frozen=True, slots=True)
class ContextGrant:
    """
    The authority of the workset owner for one frozen record.

    ``scope`` and ``workset`` name where the record was frozen.
    ``conversations`` lists the conversations that accept its context.
    """

    scope: IntakeScope
    workset: ResultRef
    conversations: tuple[ConversationScope, ...] = ()


@dataclass(frozen=True, slots=True)
class PublicationTarget:
    """One requested destination: a workset scope and maybe a conversation."""

    scope: IntakeScope
    workset: ResultRef
    conversation: ConversationScope | None = None


@dataclass(frozen=True, slots=True)
class ContextPublication:
    """Metadata-level context. In-process only; not a wire record."""

    context_type: ContextType
    stream: ContextStream
    workset: ResultRef
    conversation: ConversationScope | None
    source: VersionRef
    source_scope: VersionRef
    identity_sha256: str
    title_sha256: str | None
    source_time: int
    attachment_count: int
    metadata_count: int
    limitations: tuple[LimitationCode, ...]


def _text(value: object) -> str:
    """Return ``value`` when it is bounded, clean, exact text."""
    if type(value) is not str:
        raise ContextRefusal("wrong_type")
    try:
        size = len(value.encode())
    except UnicodeEncodeError:
        raise ContextRefusal("unsafe_text") from None
    if size > MAX_TEXT_BYTES:
        raise ContextRefusal("oversized")
    if not value or has_control_character(value):
        raise ContextRefusal("unsafe_text")
    return value


def _version_ref(value: object) -> VersionRef:
    if not isinstance(value, VersionRef):
        raise ContextRefusal("wrong_type")
    _text(value.kind)
    _text(value.identity)
    _text(value.version)
    return value


def _result_ref(value: object) -> ResultRef:
    if not isinstance(value, ResultRef):
        raise ContextRefusal("wrong_type")
    _text(value.result_id)
    _text(value.kind)
    _text(value.schema_version)
    if (value.kind, value.schema_version) != (INTAKE_KIND, INTAKE_SCHEMA_VERSION):
        raise ContextRefusal("wrong_type")
    return value


def _intake_scope(value: object) -> IntakeScope:
    if not isinstance(value, IntakeScope):
        raise ContextRefusal("wrong_type")
    _text(value.catalog.catalog_identity)
    _text(value.source_id)
    _text(value.stream)
    _text(value.consumer_id)
    return value


def _conversation(value: object) -> ConversationScope:
    if not isinstance(value, ConversationScope):
        raise ContextRefusal("wrong_type")
    if _text(value.kind) not in _CONVERSATION_KINDS:
        raise ContextRefusal("out_of_scope")
    _text(value.scope_id)
    return value


def context_type_of(source_type: object) -> ContextType:
    """
    Return the closed context type of a source type.

    Raise :exc:`ContextRefusal` with ``unknown_source_type`` for a value
    outside :class:`~msgloom.preparation.records.PreparedSourceType` and
    ``not_context_source`` for a communication source.
    """
    if type(source_type) is not PreparedSourceType:
        raise ContextRefusal("unknown_source_type")
    if source_type in _COMMUNICATION:
        raise ContextRefusal("not_context_source")
    if (context_type := _TYPE_OF_SOURCE.get(source_type)) is None:
        raise ContextRefusal("unknown_source_type")
    return context_type


def _check_scope(
    context_type: ContextType,
    grant: ContextGrant,
    target: PublicationTarget,
    record_scope: VersionRef,
    frozen: FrozenSelection,
) -> None:
    """
    Refuse every target that the grant does not allow. The only guard.

    The grant ``source_id`` must equal the identity of the record
    ``source_scope`` (kind ``source_scope``). Equal stream and kind are not
    enough: a record of source A never publishes under a grant for source B.
    The grant scope and workset must also equal the binding of ``frozen``,
    so a grant for workset B never publishes a record frozen under A.
    """
    if _intake_scope(grant.scope).stream != STREAM_OF_TYPE[context_type]:
        raise ContextRefusal("stream_mismatch")
    if (
        _intake_scope(target.scope) != grant.scope
        or _result_ref(target.workset) != grant.workset
    ):
        raise ContextRefusal("out_of_scope")
    if (
        _version_ref(record_scope).kind != "source_scope"
        or record_scope.identity != grant.scope.source_id
    ):
        raise ContextRefusal("source_mismatch")
    if (
        _intake_scope(frozen.scope) != grant.scope
        or _result_ref(frozen.workset) != grant.workset
    ):
        raise ContextRefusal("binding_mismatch")
    if target.conversation is None:
        return
    if not isinstance(grant.conversations, tuple):
        raise ContextRefusal("wrong_type")
    if len(grant.conversations) > MAX_CONVERSATIONS:
        raise ContextRefusal("oversized")
    allowed = {_conversation(item) for item in grant.conversations}
    if _conversation(target.conversation) not in allowed:
        raise ContextRefusal("out_of_scope")


def _record_of(selection: object) -> CollectedRecord:
    if not isinstance(selection, CollectedSelection):
        raise ContextRefusal("wrong_type")
    record = selection.record
    if not isinstance(record, CollectedRecord):
        raise ContextRefusal("wrong_type")
    if _version_ref(selection.source) != _version_ref(record.source):
        raise ContextRefusal("inconsistent_record")
    return record


def _source_seconds(value: object) -> int:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ContextRefusal("wrong_type")
    seconds = int(value.timestamp() // 1)
    if not 0 <= seconds <= MAX_EPOCH_SECONDS:
        raise ContextRefusal("invalid_time")
    return seconds


def _title_digest(subject: object) -> str | None:
    if subject is None:
        return None
    if type(subject) is not str:
        raise ContextRefusal("wrong_type")
    try:
        size = len(subject.encode())
    except UnicodeEncodeError:
        raise ContextRefusal("unsafe_text") from None
    if size > MAX_SUBJECT_BYTES:
        raise ContextRefusal("oversized")
    return domain_sha256(TITLE_DOMAIN, subject)


def _count(items: object) -> int:
    if not isinstance(items, tuple):
        raise ContextRefusal("wrong_type")
    if len(items) > MAX_ITEMS:
        raise ContextRefusal("oversized")
    return len(items)


def _has_body(record: CollectedRecord) -> bool:
    return record.body is not None or _count(record.alternate_bodies) > 0


def publish_context(
    frozen: FrozenSelection,
    grant: ContextGrant,
    target: PublicationTarget,
) -> ContextPublication:
    """
    Classify one frozen source record and publish its context into ``target``.

    The result depends only on the arguments. Raise :exc:`ContextRefusal`
    for a communication or unknown source, a target outside the grant, a
    grant that does not match the frozen binding, an oversized input,
    unsafe text or a wrong type. Nothing is partly built.
    """
    if not isinstance(grant, ContextGrant) or not isinstance(target, PublicationTarget):
        raise ContextRefusal("wrong_type")
    if not isinstance(frozen, FrozenSelection):
        raise ContextRefusal("wrong_type")
    record = _record_of(frozen.selection)
    context_type = context_type_of(record.source_type)
    _check_scope(context_type, grant, target, record.source_scope, frozen)
    identity = _text(record.semantic_identity)
    attachments = _count(record.attachments)
    metadata = _count(record.metadata)
    limits: set[LimitationCode] = {"type_fields_unavailable", "time_whole_seconds"}
    if _has_body(record) or attachments:
        limits.add("content_not_published")
    if _count(record.limitations):
        limits.add("source_limited")
    return ContextPublication(
        context_type=context_type,
        stream=STREAM_OF_TYPE[context_type],
        workset=grant.workset,
        conversation=target.conversation,
        source=_version_ref(record.source),
        source_scope=_version_ref(record.source_scope),
        identity_sha256=domain_sha256(IDENTITY_DOMAIN, [context_type.value, identity]),
        title_sha256=_title_digest(record.subject),
        source_time=_source_seconds(record.source_time),
        attachment_count=attachments,
        metadata_count=metadata,
        limitations=tuple(sorted(limits)),
    )

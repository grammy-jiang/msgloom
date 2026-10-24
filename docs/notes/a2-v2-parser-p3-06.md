# A2 v2 P3-06: typed, scoped context for non-communication sources (PROVISIONAL)

Code: `msgloom/a2_kedro/semantics/context_types.py`.
Tests: `tests/a2_kedro/test_p3_06.py`, `test_p3_06_scope.py`,
`test_p3_06_binding.py`. Helper: `p3_06_bound.py`.

Status: PROVISIONAL, CANDIDATE/RESEARCH. The function layer is pure. It reads
no provider, network, file, clock or database. It depends only on the typed
contracts at base `95a9eeb`.

## Result

`publish_context(frozen, grant, target)` takes one `FrozenSelection`
(a `CollectedSelection` plus the Intake scope and workset that froze it),
one `ContextGrant` and one `PublicationTarget`. It returns one
`ContextPublication` or raises `ContextRefusal`.

| Context type     | Source type        | Intake stream      |
|------------------|--------------------|--------------------|
| `calendar_event` | `outlook_calendar` | `outlook_calendar` |
| `todo_item`      | `todo`             | `todo`             |
| `onedrive_file`  | `onedrive`         | `onedrive`         |
| `contact`        | `contact`          | `contacts`         |

Mail and Teams source types give `not_context_source`. A value outside
`PreparedSourceType` gives `unknown_source_type`.

## Scope rule

The grant names the Intake scope and the workset of the frozen record. It
may list conversations. The guard `_check_scope` allows a target only if:

1. the grant stream is the stream of the context type;
2. the target scope and workset equal the grant exactly;
3. the target conversation, if any, is listed in the grant;
4. the grant scope and workset equal the scope and workset of the
   `FrozenSelection` (F4 fix, see below).

Conversation kinds are the existing `ScopeKind` values (`mailbox`,
`thread`, `channel`). The same ID under another kind is another scope.

## Published fields (metadata only)

Context type, stream, workset ref, optional conversation, exact source and
source-scope refs, `identity_sha256`, `title_sha256`, `source_time` (whole
UTC seconds), attachment and metadata counts, sorted limitation codes. No
body, party, attachment, metadata value or location is published.

## PROVISIONAL decisions

- P-1: the output is an in-process dataclass. It is not a wire kind. No
  `context@1` entry exists in `schema_ids.STAGE_SCHEMAS`, and this task must
  not add one. It has no header, no canonical bytes and no digest of its own.
  A later task must decide the wire kind and its field names.
- P-2: `prepared@2` and `group_result@2` have no calendar, To Do, OneDrive
  or contact field and no non-conversation scope kind. This layer therefore
  publishes no event time span, task state, file name, size or contact data.
  It records the limitation `type_fields_unavailable` on every publication.
- P-3: the conversation scope reuses `relations.ScopeKind`. The contracts
  have no native link from a calendar event, task, file or contact to a
  conversation. The grant (workset owner authority) is the only source of
  that link. This layer does not infer it from a relationship, a subject or
  a time.
- P-4: `title_sha256` and `identity_sha256` follow the digest style of
  `prepared@2` (`text_sha256`, `identity_sha256`). Domains are
  `a2-context-title@1` and `a2-context-identity@1`. They are unsalted.
- P-5: `source_time` is whole UTC seconds in `0..2**40`, the range of
  `prepared@2.sent_at`. The precision decision of C0-07 is still open.
- P-6: bounds `MAX_SUBJECT_BYTES=8192`, `MAX_ITEMS=256`,
  `MAX_CONVERSATIONS=64` are provisional. Text bound is
  `codec.MAX_TEXT_BYTES`.
- P-7: limitation codes (`content_not_published`, `type_fields_unavailable`,
  `source_limited`, `time_whole_seconds`) are a local vocabulary.

## Limitations and gaps

- The guard trusts the grant. This layer cannot prove that the grant came
  from the workset owner. A later stage (P3-09 review, orchestration) must
  bind it to the frozen selection.
- Text checks match `A2Model`: no control, line-separator or unencodable
  text. Format characters such as bidi overrides (`Cf`) are not refused.
- A subject or semantic identity is hashed, so it may hold control
  characters. Only the unencodable form and the size are refused.
- Scope text is validated inside `_check_scope`. Disabling the guard also
  disables that check. The mutation test covers this on purpose.
- A record `source_scope` is published as given. Review fix 1 compares its
  identity to the grant `source_id`. No other link to the Intake scope exists.
- Record and source limitations are counted (`source_limited`). Their codes
  and details are not copied.
- Many records, a batch API and ordering across records are out of scope.

## Review fixes

- Cross-source leak fixed. `_check_scope` now compares the identity of the
  record `source_scope` (kind `source_scope`) with `grant.scope.source_id`.
  A mismatch raises `ContextRefusal("source_mismatch")`. The message is
  fixed text and holds no input value. The comparison is strict equality,
  the same rule as `historical_baseline`. The check runs after the target
  equals the grant, so a hostile scope text still gives `unsafe_text`.
- New tests are in `tests/a2_kedro/test_p3_06_scope.py`: source mismatch
  for all four types, one differing part at a time (consumer, catalog,
  stream, source), a positive case, and a sentinel that never appears in
  `str` or `repr` of a refusal. Removing the new check fails these tests.
- `test_p3_06.py` fixtures: the record `source_scope` identity is now
  `src-1`, equal to the fixture grant. Another test uses the fixture source.
- Closed types: `ConversationScope.kind` is `ScopeKind`,
  `ContextPublication.stream` is `ContextStream` and
  `ContextPublication.limitations` is `tuple[LimitationCode, ...]`. These are
  `Literal` types for the type checker only. Dataclasses do not check them
  at run time. `ConversationScope.kind` is still checked at run time.
- Still open: the guard trusts the grant (see Limitations).

## Review fix F4: grant bound to the frozen record workset

`CollectedSelection` and `CollectedRecord` live outside this task and have
no workset field. A new frozen dataclass `FrozenSelection(selection, scope,
workset)` in `context_types.py` carries the binding. `publish_context` now
takes it as the first argument. A bare `CollectedSelection` gives
`wrong_type`. `_check_scope` compares the grant scope and workset to the
binding. A different value gives `binding_mismatch`. A missing, `None` or
malformed value (also a workset of another kind) gives `wrong_type`. The
binding check runs after the source check, so earlier codes are unchanged.
The new tests are in `test_p3_06_binding.py`. The older tests call
`p3_06_bound.publish_context`, a wrapper that freezes the selection under
the grant binding so that they keep testing their own rule.

What remains trusted (owner decision needed):

- The `FrozenSelection` binding is made by the caller. This module cannot
  prove that the freezing stage made it. A caller that builds both the
  binding and the grant for workset B still publishes a record that was
  frozen under workset A.
- The grant, and its `conversations` list, is still caller-supplied.
- Closing both gaps needs a signed or stored binding (for example a
  workset-owner signature over scope, workset and selection ref, or a
  lookup in the Intake store). That needs a contract outside this task.
  Decision for the owner: is a signature or store lookup required before
  wiring, or is a binding made by the trusted freezing stage enough?

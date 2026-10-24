# A2 v2 P3-09: independent read-only review of P3 relations (PROVISIONAL)

Reviewer: an independent agent. It did not write the reviewed code.
Method: source reading only. No test was run. No claim here rests on a
test result or on an author note.

Goal under review: unexplained links stay unknown. No false cross-Workset
association. Limits propagate completely.

All file paths below are relative to the root of the named worktree.
Worktree names are shortened: `p3-02` means
`a2-v2-p3-02-relsafety-20261025`, and so on.

## 1. Targets

Base for each diff: `895fc40`. Every worktree HEAD matched the requested
SHA. There was no mismatch.

| Task | Worktree | Requested SHA | Verified HEAD (full) |
| --- | --- | --- | --- |
| P3-02, P3-05 | p3-02 | `2a411bd68e` | `2a411bd68ecc97e96f12d6e250ea2930bdbaf1e4` |
| P3-03 | p3-03 | `9fedae24fb` | `9fedae24fb746f49edea00fe45bac4fa28ac4a10` |
| P3-04 | p3-04 | `f70a0d7927` | `f70a0d7927270fc0bfcd1387e845f8ae7e157501` |
| P3-06 | p3-06 | `b52e427` | `b52e4272fc0e21a2457ec156e451e4647e2d31bf` |
| P3-07 | p3-07 | `db4cc80` | `db4cc8055b7cf8d07df52c88745f23e2f881fa88` |
| P3-08 | p3-08 | `0c6a92d` | `0c6a92df1b3842382beeb4f15fdab95771dba877` |

`895fc40` is an ancestor of every HEAD. The P3-02, P3-03 and P3-04 trees
also contain P3-01 (`semantics/relations.py`, identical blob in all
three). The P3-06, P3-07 and P3-08 trees do not contain P3-01.

Files read: `contracts/relations.py`, `contracts/transition.py`,
`contracts/codec.py`, `contracts/results.py`, `contracts/result_base.py`,
and the P3 modules `semantics/relations.py`, `relation_safety.py`,
`teams_grouping.py`, `filters.py`, `outlook_grouping.py`,
`outlook_index.py`, `context_types.py`, `replay_policy.py`,
`transitions.py`, plus the notes in `docs/notes/`.

## 2. Verdict per question

### Q1. Unexplained link to confirmed relation: PASS (with F6, F8)

- P3-01 never creates a relation from an unresolved target, an ambiguous
  target, a self reference, a conversation mismatch or a cycle. Each case
  gives a limitation and no edge (p3-02 `semantics/relations.py:248-267`).
  Subject, time and author are not inputs.
- P3-04 produces only `candidate` groups with the `candidate_only`
  limitation (`outlook_grouping.py:153`, `380-397`). An unresolved
  Message-ID gives no edge (`337-353`). A subject gives a `SubjectHint`
  with `can_merge: Literal[False]` (`172-179`). The hint is computed from
  messages in one scope only (`399-420`).
- P3-02 gives `CONFIRMED` only for a closed basis set and only when no
  reason applies (`relation_safety.py:105-111`, `288-307`). The check
  trusts the basis text that the producer wrote (see F8).
- P3-03 treats a missing field as `unknown`, not as a match
  (`filters.py:203-224`, `245-265`).

### Q2. Cross Workset or scope boundary: FINDING (F4, F5, F9)

- Pass: P3-01 `NodeRef` and `Relation` carry scope. A cross-scope
  relation is rejected by the contract (`contracts/relations.py:94-97`).
  P3-02 keys every node, cycle edge and duplicate check by
  `(scope_kind, scope_id, node_id)` (`relation_safety.py:259-260`,
  `280-281`, `291-296`). P3-05 maps a channel to
  `<byte length of team_id>:<team_id><channel_id>`, which is injective
  (`teams_grouping.py:142-147`). P3-04 partitions by workset, then by
  scope, before any edge (`outlook_grouping.py:456-473`). P3-04 `group_id`
  covers workset, kind, scope and members (`386-388`). P3-08 compares
  `ScopeRef` and the entry catalog for every record
  (`transitions.py:256-262`). No module keeps a cache or mutable state
  between calls.
- Finding: P3-06 does not bind the grant to the frozen record or workset
  (F4). P3-07 keys carry no scope field (F5). `NodeRef` has no source
  field (F9). `identity_sha256` in P3-06 has no scope (F10).

### Q3. Limits, caps and held states propagate: FINDING (F1, F3, F13)

- Pass: P3-03 raises `INCOMPLETE` plus limitations for every unknown rule,
  also when the verdict is `exclude` (`filters.py:296-308`, `332`).
  P3-04 reports `hints_truncated` (`481-485`) and fails closed on the
  message cap (`454-455`). P3-08 fails closed on every count cap
  (`253-254`, `396-398`). P3-01 records a limitation for every cap it
  applies.
- Finding: P3-08 `to_batch` drops the partial-enumeration limitation
  (F1). P3-02 `from_native` drops every P3-01 limitation (F3). Limitation
  lists can exceed the stage cap of 64 (F13).

### Q4. Unbounded loops, recursion, regex, O(n^2): PASS (with F12, F13)

- No recursion. Every graph walk is iterative: P3-01 Tarjan
  (`relations.py:337-377`), P3-02 Kosaraju (`relation_safety.py:207-253`),
  contract `_find_cycle` (`contracts/relations.py:105-124`).
- The only regex is `^\s*(?:re|fw|fwd)\s*:\s*` (`outlook_grouping.py:88`).
  It is anchored and has no nested quantifier. The subject is at most
  2048 bytes. The strip loop is O(n) per step on a bounded string.
- Minor costs: F12 (list membership in a loop) and F13 (input not bounded
  before the scan).

### Q5. Leak of message text, address or subject: FINDING (F10, F15)

- Pass: errors use fixed text. `ResultPart` sets `hide_input_in_errors`
  (`result_base.py:75-78`). `TransitionSemanticsError` and
  `ContextRefusal` hold a code and at most a position
  (`transitions.py:131-146`, `context_types.py:165-174`). `Limitation`
  details are field names or counts only (`filters.py:303-306`,
  `transitions.py:389-393`).
- Finding: `repr` of several input models shows IDs and a subject (F15a).
  P3-06 digests are unsalted (F10).

### Q6. Authority, deletion, rename: FINDING (F2, F14)

- Pass: a deletion marker must come from a record of the same
  `ScopeRef` and the same catalog (`transitions.py:256-262`). The marker
  authority must equal the scope authority (`286-294`). A content
  record needs a hash. A marker must not have one. A membership record
  must not have a hash (`274-283`). A partial enumeration gives
  `UnprovenAbsence`, never `absence` or `deletion` (`364-366`). A
  membership exit is `membership_removal`, not `deletion` (`367-370`).
  Duplicate, conflicting and fact-sharing records are refused.
- Rename: no rename transition kind exists in any of the six trees
  (`TransitionKind` in `contracts/transition.py:62-64`). A rename shows
  as two unlinked facts. The code does not guess a link. This is safe.
- Finding: a membership scope still emits `deletion` for a marker (F2).
  The authority check compares two caller-supplied strings (F14).

### Q7. Contradictory definitions across branches: FINDING (section 4)

See section 4 for the concrete list. F6 and F7 come from it.

### Q8. AGENTS.md rules: PASS (minor note F15)

- `assert` statements: none in `msgloom/a2_kedro` or `tests/a2_kedro`
  in any of the six trees (grep for statement-form `assert`).
- Module length: every touched `.py` file is under 500 lines. Largest:
  `tests/a2_kedro/test_p3_06.py` 498, `outlook_grouping.py` 492 and the
  existing `contracts/source.py` 492. These have almost no headroom.
- Portability: the new P3 tests read no file, clock, path, environment,
  platform or subprocess. Seeded `random.Random` use is deterministic.
  `monkeypatch` is used only on module constants.

## 3. Findings

Severity scale: blocker means do not integrate. Major means fix before
integration or before wiring. Minor means fix when convenient.
There is no blocker.

### Major

**F1. P3-08 `to_batch` drops the partial-enumeration limitation.**
p3-08 `msgloom/a2_kedro/semantics/transitions.py:422-435`, with
`TransitionOutcome` at `229-247`. `derive_transitions` records
`UnprovenAbsence` and an `absence_not_proven` limitation. `to_batch`
builds `TransitionBatch` from `outcome.transitions` only. The batch has
no limitation field. A batch from a partial scope looks the same as a
batch from a complete scope. Fix: `to_batch` must refuse a non-complete
outcome, or return the limitation with the batch, or the batch contract
must carry a limited state.

**F2. P3-08 membership scope emits `deletion`.**
p3-08 `transitions.py:319-321`. The module says a resource that leaves a
membership scope is not deleted (docstring lines 51-53). The code still
turns a provider marker in a membership scope into `deletion`, with the
folder scope as `scope_kind` and `scope_id`. The author lists this as an
open owner question (note `a2-v2-semantics-p3-08.md`). A consumer cannot
tell whether the deletion applies to the folder or to the content.
Decide before wiring. Safe default: refuse a marker in a membership
scope, or emit it as `membership_removal`.

**F3. P3-02 `from_native` drops P3-01 limitations and unresolved
relations.** p3-02 `semantics/relation_safety.py:159-173`. Input is a
`NativeRelations` record. That record has no limitation field
(`contracts/relations.py:127-134`). The P3-01 `RelationRecovery` carries
`unresolved` and `limitations` beside the record
(`semantics/relations.py:189-194`). A relation from a recovery that hit
`list_too_long`, `depth_exceeded`, `too_many_relations`,
`conflicting_parents` or `ambiguous_target` can still be `CONFIRMED`,
with no trace. Fix: accept `RelationRecovery` and add a per-relation or
per-call reason, or return the limitations with the review.

**F4. P3-06 grant is not bound to the frozen record or workset.**
p3-06 `semantics/context_types.py:297-330`, `391-395`. The guard compares
a caller-made `PublicationTarget` with a caller-made `ContextGrant`. The
only link to the record is `source_scope.identity == grant.scope.source_id`
(`317-321`). The record has no workset. A caller can build a grant for
workset B for a record frozen under workset A with the same source, and
the guard allows it. The `conversations` list is also self-declared. The
note admits this ("the guard trusts the grant"). The task goal is no
false cross-Workset association, so this is major. Fix: derive the grant
from the frozen selection or workset, or verify the grant against a signed
or stored workset binding.

**F5. P3-07 replay key has no scope or workset field.**
p3-07 `semantics/replay_policy.py:98-124`, `127-146`. The key covers
`input_digest` and the policy only. `input_digest` is any 64-character
hex string (`57-67`). If a caller passes a content digest, two worksets
with equal content share one key, and an idempotency store returns the
other workset's result. `StageIdentity` does contain `scope_key` and
`workset` (`contracts/identity.py:102-103`), but this module does not
require them. Fix: add an explicit `scope_key` and `workset` to the key
input, or accept only a `StageIdentity.logical_key`.

**F6. P3-04 branch carries a stale `relation_safety.py` and test.**
p3-04 `msgloom/a2_kedro/semantics/relation_safety.py` (287 lines) and
`tests/a2_kedro/test_p3_02.py` (356 lines). P3-04 branched from
`d207c5b`, before the P3-02 review fix `66be52b`. The stale file has no
`UNCONFIRMABLE_BASIS` and no `CONFIRMABLE_BASES`. It marks a relation
with any basis, such as a conversation ID, as `CONFIRMED`. P3-02
(`2a411bd`) adds the same paths with different content. The merge is an
add/add conflict. If the P3-04 side wins, a candidate-only basis can be
confirmed. Fix: drop both files from P3-04 and rebase on `2a411bd`.
P3-04 code does not import either file, so nothing else changes. The
P3-04 note also says "builds on P3-02", which the code does not do.

**F7. P3-03 verdict domain contradicts `filter_result@2`.**
p3-03 `semantics/filters.py:52-53`, `263-264` against
`contracts/results.py:93`, `251-252`, `277-279`. When no rule matches,
the contract requires `verdict == "no_match"`. P3-03 returns `unknown`
with a `no_rule_matched` limitation. A `FilterResult` built from that
evaluation fails with "verdict or reasons differ from evaluations". The
docstring (line 38) says the verdict follows the contract. It does not
for this case. No mapping function exists. Fix: define one mapping, in
one place, and test it against `FilterResult`.

### Minor

F8 to F15 are minor.

**F8. P3-02 trusts the basis text and does not pair it with the kind.**
p3-02 `relation_safety.py:105-111`, `297-298`. A `reply_to` with basis
`same_source:ancestor_list`, or a `reference` with basis
`same_source:reply_parent`, is `CONFIRMED`. The basis is free text from
the producer. Fix: map each kind to its one allowed basis.

**F9. `NodeRef` has no source field.** `contracts/relations.py:69-78`.
Scope is `(scope_kind, scope_id)` only. Outlook `thread` and Teams chat
`thread` share a kind. Two sources with equal scope IDs give equal
nodes. P3-01 and P3-05 avoid this by handling one source per call, and
by declaration only. Any later merge needs a source field.

**F10. P3-06 digests have no scope and no salt.** p3-06
`context_types.py:411-412`. `identity_sha256` covers the type and the
semantic identity only. Two worksets give the same digest for the same
identity. `title_sha256` is an unsalted digest of a subject, so a reader
can test guesses. The note admits the second point.

**F11. Oversized ID in a P3-01 list crashes recovery.** p3-02
`semantics/relations.py:222-228`. `A2Model` applies the 2048-byte bound
only to a top-level `str` (`contracts/codec.py:153-157`), not to items
inside a tuple. `reply_parent_ids` and `ancestor_ids` accept a long ID.
`UnresolvedRelation(target_id=...)` and `RelationLimitation` then reject
it and raise. The docstring says the function does not raise for bad
evidence. One hostile Message-ID drops all relations and limitations of
the source. It fails closed. It is not a false link. The `codec.py`
docstring (lines 118-137) also promises a bound for nested text.

**F12. P3-04 quadratic membership test.** p3-04
`outlook_grouping.py:363-367`. `e.left in names` tests a list for every
edge. Worst case is about 66,000 edges times 1,024 names, only in a
contradictory-conversation component. The input is capped by
`MAX_MESSAGES`, so the cost is bounded. Use a set.

**F13. P3-01 input is not length-bounded before the scan.** p3-02
`semantics/relations.py:140-155`, `292-298`. `SourceEvidence.messages`
and the ID tuples have no `max_length`. The caps cut the data after full
validation and a full dedupe. P3-02 uses `Field(max_length=...)` in
`relation_safety.py:147-150`, which is the better pattern. Also, the
P3-01 and P3-04 limitation tuples can reach tens of thousands of items,
while `check_limitations` allows 64 (`result_base.py:33`, `122-123`). A
later mapping to stage `Limitation` needs aggregation.

**F14. P3-08 authority is opaque and tautological.** p3-08
`transitions.py:286-294`. The marker authority is compared with
`ScopeObservation.authority`. Both come from the caller. The check
catches inconsistent input only. It does not prove that the scope may
delete. The note states that authority text is opaque.

**F15. Misc minor.**
(a) `repr` of input models shows IDs. `OutlookMessage` shows `subject`
and Message-IDs (p3-04 `outlook_grouping.py:124-134`, no `repr=False`).
P3-01 `MessageEvidence`, P3-02 `CandidateRelation` and P3-08
`ScopedTransition` show IDs. P3-03 and P3-05 hide them. Message-IDs often
contain host names.
(b) P3-04 does not flag a group whose would-be member was withdrawn by
`duplicate_message_id`, `conflicting_parents` or `parent_mismatch`
(`outlook_grouping.py:283-307`, `380-397`). The conflict is only in
`conflicts`.
(c) P3-05 `group_teams` flags two identical refresh entries as
`duplicate_message_id` (`teams_grouping.py:277-282`). This is
conservative, not unsafe.
(d) P3-03 `FilterEvaluation` does not recompute the verdict from the
evaluations (`filters.py:285-293`), unlike `FilterResult`. A forged
instance is accepted. A subject with a tab or newline raises
(A2Model control-character rule) instead of giving `unknown`.
(e) `STREAM_OF_TYPE` (p3-06 `context_types.py:144`) and `LIMITS`
(`contracts/header.py:40`) are public mutable dicts used as guard tables.
(f) Missing notes: no `docs/notes` file exists for P3-02, P3-03 or P3-05.
(g) `test_p3_06.py` has 498 lines and `outlook_grouping.py` has 492.
Any new code in them will break the 500-line rule.

## 4. Contradictory definitions that will collide on integration

1. `semantics/relation_safety.py` and `tests/a2_kedro/test_p3_02.py`
   differ between p3-02 and p3-04 (add/add conflict). See F6.
2. `semantics/__init__.py` is an empty file in p3-07 and p3-08. It has a
   docstring in p3-02, p3-03, p3-04 and p3-06. Trivial add/add conflict.
3. `LimitationCode` is defined three times with different members and
   types: a 13-member `StrEnum` in P3-01 `relations.py`, a 9-member
   `StrEnum` in P3-04 `outlook_grouping.py`, and a 4-member `Literal` in
   P3-06 `context_types.py`. P3-03 uses `FilterLimitationCode`. The
   contract uses open `Limitation(code, detail)`.
4. The same concept has different names. Unresolved target:
   `unresolved_target` and `ambiguous_target` (P3-01), `unresolved_reference`
   and `ambiguous_reference` (P3-04), `UnknownRelation.kind` values
   `unresolved`, `missing_parent`, `cross_scope`, `cycle`
   (`contracts/results.py:~312`), and `ReviewReason` values (P3-02, adds
   `duplicate_message_id`, `unconfirmable_basis`). Three record types hold
   "unknown link": `UnresolvedRelation` (P3-01), `UnresolvedEvidence`
   (P3-04), `UnknownRelation` (contract). `self_reference` and
   `duplicate_message_id` appear in P3-01, P3-02 and P3-04 with separate
   enums.
5. Evidence and status vocabularies differ. `Relation.kind`:
   `reply_to`, `ancestor`, `reference`. `GroupResult.Evidence.kind`:
   `native_thread`, `reply_to`, `ancestor` (`results.py:301`). P3-04
   `EvidenceKind`: `conversation_id`, `conversation_index`, `in_reply_to`,
   `references`. No module maps P3-04 evidence to `native_thread`. A
   future mapping must keep `candidate_only`. Status words differ:
   `hypothesis` (contract), `candidate` (P3-04), `confirmed` and
   `needs_review` (P3-02).
6. Filter verdict: `no_match` (contract) against `unknown` (P3-03). F7.
7. Scope vocabulary. Relation `ScopeKind`: `mailbox`, `thread`, `channel`.
   Teams scope kind: `chat`, `channel`, mapped to `thread`, `channel`
   with a length-prefixed channel ID that no other producer defines.
   Transition `scope_kind` is free `Text` in P3-08 and in
   `TransitionItem`. P3-06 reuses relation `ScopeKind` for conversations.
8. Workset identity type. P3-04 uses `workset_id: Text`. P3-06 and
   `TransitionBatch` use `workset: ResultRef`. P3-07 has none.
9. Digest and key formats. P3-04 `group_id` is a plain SHA-256 of
   canonical JSON with no domain (`outlook_grouping.py:386-388`). P3-06,
   P3-07 and the contracts use `domain_sha256` with a domain name. Replay
   keys use the `a2-replay:` prefix. Stage keys use `a2-accepted:`.
   `batch_sha256` is still not part of the stage key (deferred note).
10. `TransitionItem` has no resource kind or ID. P3-08
    `ScopedTransition` has both, and `to_items` drops them
    (`transitions.py:404-419`). The item binds the resource through
    `fact_id` only.

## 5. Decisions

| Target | Decision | Condition |
| --- | --- | --- |
| P3-02 / P3-05 (`2a411bd`) | ACCEPT_WITH_FINDINGS | Fix F3 before the review feeds a confirm step. F8 recommended. |
| P3-03 (`9fedae2`) | ACCEPT_WITH_FINDINGS | Define the `no_match` mapping (F7) before building `FilterResult`. |
| P3-04 (`f70a0d7`) | ACCEPT_WITH_FINDINGS | Do not merge its `relation_safety.py` or `test_p3_02.py` (F6). |
| P3-06 (`b52e427`) | ACCEPT_WITH_FINDINGS | Bind the grant to the frozen workset (F4) before wiring. |
| P3-07 (`db4cc80`) | ACCEPT_WITH_FINDINGS | Add scope to the key input (F5) before wiring. |
| P3-08 (`0c6a92d`) | ACCEPT_WITH_FINDINGS | Fix F1 and decide F2 before wiring. Nothing calls this module yet. |

No target gets REJECT. No finding produces a false link or a false
deletion in the code as it stands. The major findings are gaps that
become unsafe when the modules are wired or merged.

This review is a source reading. It does not replace a test run.

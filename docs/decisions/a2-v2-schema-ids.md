# A2 v2 schema IDs and header (C0-00): PROVISIONAL / RESEARCH

Status: PROVISIONAL. Research only. This record freezes the identifiers
that the code defines today. The freeze is provisional. It is not a
production acceptance. Production freeze needs the F0 production gate, a
real v2 finalizer, a reviewed `triage_input@2` and C0-20c.

Rule: a later worker may not change an identifier in this record without a
new reviewed decision. See "Change procedure".

Code: `msgloom/a2_kedro/contracts/header.py`,
`msgloom/a2_kedro/contracts/schema_ids.py`.
Golden fixture: `tests/a2_kedro/golden/c0_00_provisional.json`.
Tests: `tests/a2_kedro/test_c0_00_header.py`.

## Decision

The system writes each A2 v2 payload with a header. The header names the
kind, the version and the wire profile. A reader will check the header before it
decodes the body. No reader code exists yet.

| Item | Provisional value |
| --- | --- |
| Header fields | `kind`, `version`, `profile` |
| Profile | `a2-c0-provisional-1` |
| Header digest domain | `a2-payload-header@1` |
| Encoding | Canonical JSON, sorted keys, strict decode, no duplicate keys |
| Model rules | Frozen, `extra="forbid"`, closed `(kind, version)` allowlist |

A change to the profile is an incompatible wire change.

## Kinds and versions

Each kind has one approved version.

| Kind | Version |
| --- | --- |
| `frozen_source_selection` | 1 |
| `extracted_components` | 1 |
| `parsed_parts` | 1 |
| `normalized_content` | 1 |
| `zones` | 1 |
| `native_relations` | 1 |
| `prepared` | 2 |
| `filter_result` | 2 |
| `group_result` | 2 |
| `prepared_transitions` | 2 |
| `a2_input_disposition` | 1 |
| `a2_result_manifest` | 1 |
| `a2_completion_receipt` | 2 |
| `triage_input` | 2 |

The pairs `prepared@1`, `filter_result@1` and `group_result@1` stay
read-only history. The system does not write them. `triage_input@1` stays a
historical A3 format. Its header is rejected by this allowlist.

## Limits

| Limit | Value |
| --- | --- |
| Canonical payload bytes | 4 MiB (4194304) |
| One text field | 2048 bytes |
| Nesting depth | 32 |
| Roots per workset | 1024 |
| Transitions per workset | 1024 |

The root and transition counts equal the A1 Intake entry bound. Per-kind
limits are PROVISIONAL (field 2).

## Transition identity

A `prepared_transitions@2` stage holds the full ordered transition batch of
one workset. The logical key uses the domain `a2-stage-accepted-input@1`
over the frozen inputs only. The inputs include every transition in order:
entry, fact ID, kind, resource and scope. The key excludes output digest,
time, attempt and node name. Reversing the order gives a different key.
Dropping one transition gives a different key. The golden fixture holds the
ordered and the reversed key. That key has no authority input. See
unresolved field 3.

The root role vocabulary is `primary`, `component` and `baseline`. The
A1 evidence proves the role. The header does not carry it.

## Cross-reference: schema IDs and transitions

The pair `prepared_transitions@2` is in `schema_ids.STAGE_SCHEMAS`. The
header accepts it through `approved_pairs()`. Two different digests
describe one transition batch:

- `StageIdentity.logical_key()` (domain `a2-stage-accepted-input@1`)
  names the accepted stage. It covers the ordered `transitions` tuple of
  `IntakeTransition` values. See `msgloom/a2_kedro/contracts/identity.py`.
- `TransitionBatch.batch_sha256` (domain `a2-transition-batch@1`) proves
  the stored batch body. It covers the Workset Ref, code version, policy
  version, count and every item digest. See
  `msgloom/a2_kedro/contracts/transition.py`.

The stage key does not yet bind `batch_sha256`. That binding is a
deferred dependency. See `docs/notes/a2-v2-contract-deferred.md`.

## Direction and ordering rules

- `native_relations@1`: `reply_to` and `ancestor` both point from the
  later node (`source`) to the earlier node (`target`). `reference` has no
  time direction. The cycle check joins `reply_to` and `ancestor`. Nodes
  and relations must arrive sorted; the validator rejects unsorted input.
- `extracted_components@1`: `components` keeps the producer order. The
  code does not sort it, and the bytes depend on that order.
- `prepared_transitions@2`: `items` keep the batch order. Ordinals must
  equal the position. Reordering changes both digests.

## Text rules

Every contract string is an exact `str`. A `str` subclass is rejected.
No contract field is body text, so no field accepts a control character:
no C0 or C1 control, NUL, tab, newline, DEL, U+0085, U+2028 or U+2029.
A future body-text field needs its own decision record. Tests:
`tests/a2_kedro/test_text_rules.py`.

## Frozen identifier tables (PROVISIONAL)

Each table below is checked by `tests/a2_kedro/test_c0_00.py` against the
code. A row label names the check:

- `Module`: the Python module that holds the names.
- `Kind` and `Version`: the pair must be in the approved header pairs.
- `Fields X`: the ordered field names of class `X`.
- `Literal X`: the closed values of constant `X`, or of field `Class.field`.
- `Enum X`: the values of enum `X`.
- `Const X`: the value of module constant `X`.
- `Dict X`: the `key=value` items of module dict `X`.

### header

| Item | Values |
| --- | --- |
| Module | `msgloom.a2_kedro.contracts.header` |
| Fields StageHeader | `kind`, `version`, `profile` |
| Const WIRE_PROFILE | `a2-c0-provisional-1` |
| Const HEADER_DOMAIN | `a2-payload-header@1` |
| Dict LIMITS | `max_canonical_bytes=4194304`, `max_text_bytes=2048`, `max_depth=32`, `max_roots=1024`, `max_transitions=1024` |

### frozen_source_selection@1

The record is a `FrozenRoot` per selected occurrence. It has no header yet.
The kind and version come from `schema_ids.STAGE_SCHEMAS`.

| Item | Values |
| --- | --- |
| Module | `msgloom.a2_kedro.contracts.source` |
| Kind | `frozen_source_selection` |
| Version | `1` |
| Fields FrozenRoot | `selected`, `workset_index`, `role`, `selection_sha256`, `ordinal`, `a1_ordinal_proof`, `entry`, `baseline_source`, `baseline_approval` |
| Literal FrozenRoot.role | `primary`, `component`, `baseline` |

### extracted_components@1

| Item | Values |
| --- | --- |
| Module | `msgloom.a2_kedro.contracts.extract` |
| Kind | `extracted_components` |
| Version | `1` |
| Const KIND | `extracted_components` |
| Const VERSION | `1` |
| Fields ExtractedComponents | `header`, `components` |
| Fields ComponentEntry | `component_id`, `role`, `status`, `reference`, `sha256`, `metadata` |
| Literal ComponentRole | `primary`, `alternate`, `attachment`, `embedded` |
| Literal ComponentStatus | `present`, `missing`, `partial`, `unsupported` |
| Const MAX_COMPONENTS | `256` |
| Const MAX_METADATA_ITEMS | `32` |
| Const MAX_METADATA_KEY_BYTES | `64` |
| Const MAX_METADATA_VALUE_BYTES | `256` |
| Const MAX_METADATA_BYTES | `4096` |

### native_relations@1

| Item | Values |
| --- | --- |
| Module | `msgloom.a2_kedro.contracts.relations` |
| Kind | `native_relations` |
| Version | `1` |
| Const KIND | `native_relations` |
| Const VERSION | `1` |
| Fields NativeRelations | `header`, `nodes`, `relations` |
| Fields NodeRef | `scope_kind`, `scope_id`, `node_id` |
| Fields Relation | `kind`, `source`, `target`, `status`, `basis` |
| Literal ScopeKind | `mailbox`, `thread`, `channel` |
| Literal RelationKind | `reply_to`, `ancestor`, `reference` |
| Literal Relation.status | `hypothesis` |
| Const MAX_NODES | `1024` |
| Const MAX_RELATIONS | `4096` |

### prepared_transitions@2

| Item | Values |
| --- | --- |
| Module | `msgloom.a2_kedro.contracts.transition` |
| Kind | `prepared_transitions` |
| Version | `2` |
| Const KIND | `prepared_transitions` |
| Const VERSION | `2` |
| Fields TransitionBatch | `header`, `workset`, `code_version`, `policy_version`, `items`, `batch_sha256` |
| Fields TransitionItem | `ordinal`, `entry`, `fact_id`, `scope_kind`, `scope_id`, `kind`, `authority` |
| Fields ItemProof | `batch_sha256`, `ordinal`, `count`, `item_sha256` |
| Literal TransitionKind | `presence`, `absence`, `membership_removal`, `deletion`, `context_refresh` |
| Const ITEM_DOMAIN | `a2-transition-item@1` |
| Const BATCH_DOMAIN | `a2-transition-batch@1` |

The item count is 1 to `max_transitions` (1024). The field `authority` is
unresolved field 3.

### a2_input_disposition@1

| Item | Values |
| --- | --- |
| Module | `msgloom.a2_kedro.contracts.held` |
| Kind | `a2_input_disposition` |
| Version | `1` |
| Const KIND | `a2_input_disposition` |
| Const VERSION | `1` |
| Fields InputDisposition | `selected`, `workset_index`, `selection_sha256`, `reason`, `configuration_version`, `code_version`, `repair_class`, `entry`, `baseline_source`, `baseline_approval` |
| Enum HeldReason | `role_unverifiable`, `source_evidence_unavailable`, `parser_unsupported`, `input_limit`, `proof_missing` |
| Literal InputDisposition.repair_class | `operator_repair` |

### a2_completion_receipt@2

The receipt class `TransitionBatch` in `receipt.py` is a summary of the
accepted batch result. It is not the `prepared_transitions@2` record.

| Item | Values |
| --- | --- |
| Module | `msgloom.a2_kedro.contracts.receipt` |
| Kind | `a2_completion_receipt` |
| Version | `2` |
| Const RECEIPT_DOMAIN | `a2-completion-receipt@2` |
| Fields CompletionReceipt | `workset`, `status`, `policy_version`, `roots`, `transition_batch`, `intake_held_count`, `acceptance_index_sha256`, `claim_proofs` |
| Fields TerminalRoot | `workset_selection_index`, `result`, `disposition`, `status`, `limitations`, `selection`, `baseline_selection`, `baseline_source` |
| Fields ResultClaimProof | `result`, `proof` |
| Const INDEX_DOMAIN | `a2-acceptance-index@1` |
| Fields TransitionBatch | `transitions`, `result`, `status` |
| Literal TerminalRoot.disposition | `prepared`, `held` |

### triage_input@2

Only the header pair is fixed. The body and its binding digest are
unresolved field 6.

| Item | Values |
| --- | --- |
| Module | `msgloom.a2_kedro.contracts.header` |
| Kind | `triage_input` |
| Version | `2` |

### stage identity (no wire kind)

| Item | Values |
| --- | --- |
| Module | `msgloom.a2_kedro.contracts.identity` |
| Fields StageIdentity | `scope_key`, `workset`, `partition_ordinal`, `stage_kind`, `schema_version`, `selected`, `transitions`, `upstream`, `configuration_version`, `code_version`, `parser_version`, `rule_version`, `partition_policy_version` |
| Fields AttemptProof | `execution_id`, `attempt_id`, `claim_key`, `claim_token_sha256` |
| Fields StageMetadata | `result_id`, `kind`, `schema_version`, `status`, `limitations_digest`, `lineage_digest`, `input_refs`, `configuration_version`, `code_version`, `versions`, `optional_versions`, `semantic_data_id`, `semantic_kind`, `semantic_schema_version`, `semantic_sha256`, `semantic_byte_count` |
| Const KEY_DOMAIN | `a2-stage-accepted-input@1` |
| Const LINEAGE_DOMAIN | `a2-stage-lineage@1` |
| Const LIMITATIONS_DOMAIN | `a2-stage-status-limitations@1` |
| Const METADATA_DOMAIN | `a2-stage-metadata@1` |

### Kinds with body contracts in other modules

The body contracts of `parsed_parts@1`, `normalized_content@1` and
`zones@1` live in their own modules. Their field lists are not repeated
here.

The bodies of `prepared@2`, `filter_result@2`, `group_result@2` and
`a2_result_manifest@1` are PROVISIONAL (C0-07). See
`docs/notes/a2-v2-contract-c0-07.md` and
`msgloom/a2_kedro/contracts/results.py`.

## Provisional wire field decisions

These nine decisions are PROVISIONAL. The identifiers above are frozen as
provisional values only. The decisions below stay open until the production
freeze.

| No. | Status | Decision |
| --- | --- | --- |
| 1 | PROVISIONAL | Body fields of every kind except the header. Only the header is fixed. C0-03, C0-06 and C0-08 add research bodies. |
| 2 | PROVISIONAL | Per-kind byte and count limits. The values in the tables are research values. |
| 3 | PROVISIONAL | Authority per transition. `IntakeTransition` has no authority field. The A1 released fact carries `authority_revision`. Decision D4 asks for it in the batch identity. The C0-08 note models it as `authority` text. |
| 4 | PROVISIONAL | Whether `prepared_transitions@2` is a root stage. The current code requires an upstream accepted result. D4 says the batch makes no message. |
| 5 | PROVISIONAL | Name and shape of the attempt record kind. |
| 6 | PROVISIONAL | The `triage_input@2` body and its binding digest. |
| 7 | PROVISIONAL | Part state, zone, relation and span-map field names (C0-03 to C0-07). |
| 8 | PROVISIONAL | Final table names, migration and schema marker (C0-11a to C0-11e). |
| 9 | PROVISIONAL | Whether the header sits inside the canonical bytes or beside them in the SQL row. The golden fixture assumes it is inside. |

## Change procedure

A later worker may not change any identifier in this record. The
identifiers are the kinds, versions, field names, role and status values,
size bounds, digest domains and the wire profile.

To change one identifier:

1. Write a new decision record under `docs/decisions/`. Name the old and the
   new value and the reason.
2. Get an independent review of the new record.
3. In one change, update the code, this record, the golden fixture
   `tests/a2_kedro/golden/c0_00_provisional.json` and the notes.
4. Run `tests/a2_kedro/test_c0_00.py` and `tests/a2_kedro/test_c0_00_header.py`.
   Both must pass with the new values.
5. If the change alters the wire form, change the wire profile name.

Do not edit a test only to make it pass. A failing test in this area means
the code and this record disagree. Report the conflict.

## Not claimed

- No production acceptance.
- No Kedro dependency or import.
- No dispatch, autoload or A1 reader change.

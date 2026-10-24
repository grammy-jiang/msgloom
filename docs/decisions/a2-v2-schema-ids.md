# A2 v2 schema IDs and header (C0-00): PROVISIONAL / RESEARCH

Status: PROVISIONAL. Research only. This record is not a production
acceptance. It does not freeze any wire format. Production freeze needs the
F0 production gate, a real v2 finalizer, a reviewed `triage_input@2` and
C0-20c.

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
limits are not decided.

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

## Unresolved wire fields

These fields are not decided. They stay open until production freeze.

1. Body fields of every kind except the header. Only the header is fixed.
2. Per-kind byte and count limits.
3. Authority per transition. `IntakeTransition` has no authority field.
   The A1 released fact carries `authority_revision`. Decision D4 asks for
   it in the batch identity.
4. Whether `prepared_transitions@2` is a root stage. The current code
   requires an upstream accepted result. D4 says the batch makes no
   message.
5. Name and shape of the attempt record kind.
6. The `triage_input@2` body and its binding digest.
7. Part state, zone, relation and span-map field names (C0-03 to C0-07).
8. Final table names, migration and schema marker (C0-11a to C0-11e).
9. Whether the header sits inside the canonical bytes or beside them in the
   SQL row. The golden fixture assumes it is inside.

## Not claimed

- No production acceptance.
- No Kedro dependency or import.
- No dispatch, autoload or A1 reader change.

# A2 v2 contract C0-07: prepared@2, filter_result@2, group_result@2 (PROVISIONAL)

Code: `msgloom/a2_kedro/contracts/results.py`,
`msgloom/a2_kedro/contracts/result_base.py`,
`msgloom/a2_kedro/contracts/result_manifest.py`.
Tests: `tests/a2_kedro/test_c0_07.py`, `test_c0_07_group.py` (fixtures in
`tests/a2_kedro/result_fixtures.py`).

All names and limits below are PROVISIONAL. The pinned-field test fails on
any change. Schema IDs come from `schema_ids.STAGE_SCHEMAS`. No ID was added.
Every record has a required `header` with its approved `(kind, version)`.
`decode_result` reads the header first and refuses `prepared@1`,
`filter_result@1` and `group_result@1` as historical read-only formats.

## prepared@2

- Fields: `header`, `root` (a `FrozenRoot`), `status`, `limitations`,
  `parsed`, `normalized`, `zones`, `relations`, `lineage_sha256`, `parts`,
  `blocks`, `sent_at`, `participants`, `rule_version`.
- The four lineage fields are accepted refs of `parsed_parts@1`,
  `normalized_content@1`, `zones@1` and `native_relations@1`. They are
  distinct. `lineage_sha256` must equal `identity.lineage_digest` of them.
- `parts`: `part_id`, `role`, `status`, `sha256`. One entry per parsed part,
  including attachments. `validate_against(parsed, zones)` proves nothing
  was dropped.
- `parts` are sorted by `part_id`. A block never names a body part whose
  status is `missing`. A `partial` body part keeps its blocks.
- `blocks`: `part_id`, `zone_id`, `kind`, `original` span, `text_sha256`.
  One entry per zone. No text is stored.
- `participants`: `role`, `identity_sha256`. A digest, never an address.
- `sent_at`: whole seconds since the epoch, or null.
- Required limitation codes: `<role>_<status>` for each part that is not
  `present` (for example `attachment_missing`), `body_absent` (no blocks),
  `time_unknown`, `participants_unknown`.
- COMPLETE if and only if there is no limitation. Limitations are a sorted
  set.

## filter_result@2

- Fields: `header`, `prepared`, `policy_id`, `policy_version`,
  `evaluations`, `matched`, `verdict`, `reasons`, `status`, `limitations`.
- `evaluations`: `rule_id`, `rule_version`, `outcome`
  (`matched`, `not_matched`, `unknown`), `effect` (`include`, `exclude`,
  only for a matched rule). Sorted by `rule_id`, no duplicate.
- `matched` must equal every matched rule in order. `verdict` and `reasons`
  must equal the values that the evaluations imply. Verdicts: `conflict`
  (include and exclude both matched), `exclude`, `unknown`, `include`,
  `no_match`. Reason codes: `conflict`, `excluded`, `unknown_rule`. Each
  reason lists all of its rule IDs.

## group_result@2

- Fields: `header`, `scope_kind`, `scope_id`, `rule_version`, `relations`,
  `members`, `evidence`, `unknown`, `status`, `limitations`.
- `members`: `node` (scope kind, scope ID, node ID) and `prepared` ref.
  Every member node must sit in the group scope. Sorted by node. No
  duplicate node or result.
- `evidence`: `kind` (`native_thread`, `reply_to`, `ancestor`), `source`,
  `target`, `basis`. Both ends are members. The evidence must connect all
  members. There is no `subject` kind and no subject field.
- `unknown`: `kind` (`missing_parent`, `cross_scope`, `cycle`,
  `unresolved`) and `node`. A non-empty list needs the limitation
  `unknown_relations`.

## a2_result_manifest@1

- Fields: `header`, `workset`, `entries`, `configuration_version`,
  `code_version`, `policy_version`, `limitations`.
- `entries`: `workset_index`, `ref`, `metadata_sha256`, `status`,
  `limitations`. Allowed kinds: `prepared`, `a2_input_disposition`,
  `filter_result`, `group_result`, `prepared_transitions`.
- Each occurrence has exactly one terminal (`prepared` or
  `a2_input_disposition`). A held occurrence has no filter or group entry.
  Manifest limitations equal the union of the entry limitations.

## Limits

64 limitations, 256 parts, 1024 blocks, 256 participants, 1024 rules, 1024
members, 4096 evidence items, 4096 manifest entries, 4 MiB per payload.

## Open

- The manifest has no digest of its own and no transition batch binding yet.
- `group_result` evidence `basis` and `unknown.kind` vocabularies are not
  decided. A `cross_scope` relation is kept as unknown, never merged.
- `sent_at` precision and time zone handling are not decided.
- Limitation code vocabulary (`<role>_<status>`) is a convention here.
- Per-member `filter_result` binding in a group is not required yet.

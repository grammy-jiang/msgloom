# Phase 1 acceptance mapping

## Scope and evidence

This lane is an integration-test and review lane. It changes no production
code, shared helper, default registry, delivery implementation, or CLI
implementation. All new inputs are synthetic. No provider, model, network,
tenant, credential, or
private-data access is used.

The composed gate is:

```text
.venv/bin/python -m pytest tests/phase1_e2e -q
7 passed in 74.09s
```

The reused isolated evidence gate is:

```text
15 passed in 38.45s
```

That second gate ran the exact existing test IDs cited below for saved-source
history, restart/projection change, move handling, repeated paging, and native
Excel/PDF/Word evidence locations.

The deterministic `FakeRunner` is injected only at the A3 model boundary.
`TriageHandler` still owns the real `EvidenceSession`, durable request and
response evidence, reconciliation, and final publication. These tests establish
mechanical composition and lineage. They do not establish model semantic
quality.

## P5 case mapping

### P5-01: same subject, different work

Implemented by
`tests/phase1_e2e/test_cross_stage_chain.py::
test_same_subject_independent_work_stays_separate_through_report`.
Two independent pre-semantics records share the display subject. Actual A2
grouping keeps two `NONE` groups, A3 retains distinct topic identities, and A5
retains both topics.

### P5-02: same conversation, multiple topics

Implemented by
`tests/phase1_e2e/test_cross_stage_chain.py::
test_saved_a1_chain_survives_restart_with_exact_lineage_and_order`.
The reviewed saved A1 Outlook fixture supplies a parent and reply. Actual A2
source-native grouping is confirmed, one A3 part yields two allocated topics,
and A5 preserves both exact topic identities.

### P5-03: ambiguous deadline

Covered in the same saved-A1 composed test. Both topics carry the original
synthetic deadline wording and `ambiguous=True`; the saved report preserves the
ambiguity and renders the original wording. No production interpretation
threshold is invented.

### P5-04: conflicting deterministic rules

Implemented by
`tests/phase1_e2e/test_failures.py::
test_conflict_and_malformed_model_never_create_false_report`.
Conflicting required priorities produce explicit review disposition, no topic,
and no low-value fallback. The dependent report build fails rather than
claiming
complete analysis.

### P5-05: missing attachment or memory file

Implemented by
`tests/phase1_e2e/test_failures.py::
test_missing_attachment_and_memory_remain_explicit_in_saved_chain`.
The saved A1 attachment is removed only after selection capture. A2 retains a
`saved-content-unavailable` limitation. A selected missing memory file is
persisted in the real working-context snapshot. A3 and A5 retain the attachment
limitation instead of claiming complete understanding.

### P5-06: malformed AI output

Implemented by the conflict/malformed test above. Transport-complete but
schema-invalid structured output ends A3 `INCOMPLETE`, publishes no accepted
`triage@1`, and cannot become a report.

### P5-07: many important topics

Implemented by
`tests/phase1_e2e/test_cross_stage_chain.py::
test_many_important_topics_keep_actions_deadlines_and_report_coverage`.
Twelve important topics are produced by A3. A5 is forced into multipart output
and preserves every topic plus every action, deadline, and risk in canonical
report semantics and rendered coverage.

### P5-08: unknown submission outcome

Pending the parallel delivery repair lane. This acceptance lane does not own
delivery, effect reconciliation, or resend behavior and therefore does not
duplicate or pre-judge that gate.

### P5-09: restart during collection

Composed restart is covered by the saved-A1 chain test, which closes and
reopens
default `Phase1Persistence` and compares immutable A2/A3/A5 results. Existing
collection/source evidence is also cited from:

`tests/source_reader/test_saved_source_reader_r3.py::
test_restart_replay_preserves_locations_kinds_metadata_and_byte_identity`

and

`tests/source_reader/test_selection_semantic_persistence.py::
test_selection_replays_after_restart_and_source_projection_change`.

The latter was included in the 15-test reused evidence gate.

### P5-10: move, edit, or repeated page

Existing exact tests are reused instead of duplicated:

`tests/source_reader/test_saved_source_reader.py::
test_outlook_old_version_does_not_fall_forward`

`tests/test_outlook_mail_presence.py::
test_folder_removal_observation_does_not_imply_global_message_absence`

`tests/test_outlook_mail_delta.py::
test_message_delta_follows_nextlink_then_emits_checkpoint_candidate`.

All three were included in the reused evidence gate.

### P5-11: changed prompt version

Implemented by
`tests/phase1_e2e/test_replay_recovery.py::
test_changed_prompt_replay_uses_saved_context_and_preserves_old_result`.
A v2 prompt creates a new assessment result while the v1 result remains byte
and
identity stable. Replay uses the saved working-context dependency and does not
recapture mutable current context.

### P5-12: report generation and recipient checks

Report generation is implemented by the saved-A1, same-subject,
missing-evidence,
and many-topic composed tests. Recipient/effect acceptance remains pending the
parallel delivery lane because this lane cannot own destination or transport
behavior.

## Async and recovery acceptance

`tests/phase1_e2e/test_replay_recovery.py::
test_application_cancellation_is_persisted_and_blocks_downstream_complete`
runs `Application` inside an already-running event loop. A controlled
`asyncio.Event` barrier proves the A3 model boundary is active before
cancellation. The cancelled Application outcome is durably saved, and a
dependent A5 build using an unavailable triage result is durably `FAILED`.

The malformed-model case also proves an incomplete A3 outcome is saved. No test
uses tiny arbitrary sleeps to establish ownership or ordering.

## Existing native evidence mapping

The reused evidence gate includes:

`tests/test_native_parser_integration.py::
test_production_parser_preserves_content_and_provenance_in_sandbox`

for MIME, PDF, and Word production dispatch,

`tests/test_native_parser_integration.py::
test_production_excel_route_retains_numeric_cell_coordinates`

for native Excel cell coordinates, and

`tests/triage_contracts/test_evidence.py::
test_mime_pdf_and_word_text_block_locations_resolve`

for exact retained MIME/PDF/Word evidence locations.

## Semantic fixture proposal

`docs/fixtures/phase1-semantic-proposal.json` is entirely synthetic and is
explicitly not owner-reviewed or accepted. It records proposed observations for
missed important work, wrong grouping, lost actions/deadlines, report coverage,
and usage/duration where a future accepted model fixture exposes them. It sets
no production threshold.

External Contacts consent, a Teams tenant fixture, an owner-reviewed semantic
fixture, real-model acceptance, delivery acceptance, and CLI/operator
acceptance
remain pending. The manager owns those integration and live-acceptance gates.

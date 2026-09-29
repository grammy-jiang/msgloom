# Phase 1 acceptance mapping

## Scope and evidence

This note maps each acceptance case in
[Phase 1 design section 7](../phase-1/design.md#7-acceptance-cases) to the
tests that exercise it. The case numbers follow the design table order. All
inputs are synthetic. No provider, model, network, tenant, credential, or
private-data access is used.

The composed gate is:

```text
.venv/bin/python -m pytest tests/phase1_e2e -q
```

The deterministic `FakeRunner` is injected only at the A3 model boundary.
`TriageHandler` still owns the real `EvidenceSession`, durable request and
response evidence, reconciliation, and final publication. These tests establish
mechanical composition and lineage. They do not establish model semantic
quality.

## Case mapping

### Case 1: restart during collection

The saved-A1 chain test closes and reopens default `Phase1Persistence` and
compares immutable A2, A3, and A5 results:

`tests/phase1_e2e/test_cross_stage_chain.py::
test_saved_a1_chain_survives_restart_with_exact_lineage_and_order`

Collection and source evidence after restart are covered by:

`tests/source_reader/test_saved_source_reader_r3.py::
test_restart_replay_preserves_locations_kinds_metadata_and_byte_identity`

`tests/source_reader/test_selection_semantic_persistence.py::
test_selection_replays_after_restart_and_source_projection_change`

### Case 2: message edit, move, or repeated page

`tests/source_reader/test_saved_source_reader.py::
test_outlook_old_version_does_not_fall_forward`

`tests/test_outlook_mail_presence.py::
test_folder_removal_observation_does_not_imply_global_message_absence`

`tests/test_outlook_mail_delta.py::
test_message_delta_follows_nextlink_then_emits_checkpoint_candidate`

### Case 3: same subject, different work

`tests/phase1_e2e/test_cross_stage_chain.py::
test_same_subject_independent_work_stays_separate_through_report`

Two independent records share the display subject. Actual A2 grouping keeps two
`NONE` groups, A3 retains distinct topic identities, and A5 retains both
topics.

### Case 4: several topics in one group

`tests/phase1_e2e/test_cross_stage_chain.py::
test_saved_a1_chain_survives_restart_with_exact_lineage_and_order`

The saved A1 Outlook fixture supplies a parent and a reply. Actual A2
source-native grouping is confirmed. One A3 part yields two allocated topics,
and A5 preserves both topic identities, their actions, and their deadlines.
Both topics keep the original deadline wording with `ambiguous=True`.

The fixture includes a current attachment or alternate MIME selection. Its
saved A1 `captured-current-component-selection` caveat reaches only the topics
that cite the affected source and the saved report limitations. A5 therefore
ends `INCOMPLETE` instead of presenting the caveated evidence as complete.

### Case 5: conflicting rules or malformed AI output

`tests/phase1_e2e/test_failures.py::
test_conflict_and_malformed_model_never_create_false_report`

Conflicting required priorities produce an explicit review disposition, no
topic, and no low-value fallback. Transport-complete but schema-invalid
structured output ends A3 `INCOMPLETE`, publishes no accepted `triage@1`, and
cannot become a report.

### Case 6: missing memory or attachment content

`tests/phase1_e2e/test_failures.py::
test_missing_attachment_and_memory_remain_explicit_in_saved_chain`

The saved A1 attachment is removed only after selection capture. A2 retains a
`saved-content-unavailable` limitation. The fake model omits every limitation.
A3 still merges the saved source gap into the affected topic and derives the
missing working-context file from the saved snapshot. A5 retains both gaps and
ends `INCOMPLETE`.

### Case 7: many important topics

`tests/phase1_e2e/test_cross_stage_chain.py::
test_many_important_topics_keep_actions_deadlines_and_report_coverage`

Twelve important topics are produced by A3. A5 is forced into multipart output
and preserves every topic and every action, deadline, and risk in canonical
report semantics and rendered coverage.

### Case 8: timeout after submission

Pending integration of the reviewed delivery lane. The persistence contracts
that the delivery lane composes are covered by:

`tests/phase1_foundation/test_persistence.py::
test_unknown_external_effect_blocks_blind_retry`

`tests/persistence_fences/test_claim_fencing.py::
test_expired_submission_cannot_start_effect_but_can_reconcile_pending`

### Case 9: replay with a changed prompt

`tests/phase1_e2e/test_replay_recovery.py::
test_changed_prompt_replay_uses_saved_context_and_preserves_old_result`

A v2 prompt creates a new assessment result while the v1 result remains byte
and identity stable. Replay uses the saved working-context dependency and does
not recapture mutable current context.

### Case 10: common attachments

`tests/test_native_parser_integration.py::
test_production_parser_preserves_content_and_provenance_in_sandbox`

`tests/test_native_parser_integration.py::
test_production_excel_route_retains_numeric_cell_coordinates`

`tests/triage_contracts/test_evidence.py::
test_mime_pdf_and_word_text_block_locations_resolve`

Native MIME, PDF, Word, and Excel routes keep source mappings. Numeric XLSB
cells remain an explicit coverage gap of the qualified parser dependency.

### Case 11: ordered execution

`tests/phase1_foundation/test_persistence.py::
test_dependent_claim_requires_durable_acceptable_input`

`tests/phase1_foundation/test_contracts_application.py::
test_non_cli_caller_awaits_application_in_existing_loop`

`tests/phase1_e2e/test_replay_recovery.py::
test_application_cancellation_is_persisted_and_blocks_downstream_complete`

A dependent claim requires a durable acceptable input. The application runs
inside an already-running event loop, and a cancelled A3 outcome is saved
before a dependent A5 build is durably `FAILED`. The saved-A1 chain test also
requires every stage outcome to be awaited and saved.

### Case 12: scheduler-free invocation

Pending integration of the reviewed application CLI lane. The package has no
scheduler runtime dependency. The CLI lane owns manual finite commands and the
check that repeated invocation cannot bypass delivery reconciliation.

## Semantic fixture proposal

`docs/fixtures/phase1-semantic-proposal.json` is entirely synthetic and is
explicitly not owner-reviewed or accepted. It records proposed observations for
missed important work, wrong grouping, lost actions and deadlines, report
coverage, and usage or duration where a future accepted model fixture exposes
them. It sets no production threshold.

External Contacts consent, a Teams tenant fixture, an owner-reviewed semantic
fixture, and real-model acceptance remain pending outside this repository.

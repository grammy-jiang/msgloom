# A2 Kedro v2 — 完整任务依赖及文件责任

**仅设计方案；NOT STARTED。** [原实施计划](2026-10-23-a2-kedro-v2-execution-plan.md) 与 [机器 Task DAG](2026-10-23-a2-kedro-v2-task-manifest.json) 已核对 151 个任务。

所有文件同一时刻只允许一个负责写入者，必须展开通配符并获取实际文件锁。外部门禁包括安全 owner 批准、最终 C0 验收和生产 cutover；独占 Pi benchmark 不与其他重 CPU 工作并行。每项时间盒不是交付 ETA。

| Task/timebox | 依赖 | 外部门禁 | 计划文件责任 |
| --- | --- | --- | --- |
| CR-01 (15m) | 无 | 无 | docs/plans/2026-10-23-a2-kedro-c0-contract-candidate.md |
| CR-02 (20m) | 无 | 无 | tests/research/test_c0_contract_prototype.py |
| CR-03 (20m) | 无 | 无 | tests/research/test_c0_contract_prototype.py |
| CR-04 (20m) | 无 | 无 | docs/plans/2026-10-23-a2-kedro-c0-contract-candidate.md |
| CR-05 (15m) | 无 | 无 | tests/research/test_c0_native_a1_exact_handoff.py |
| CR-06 (15m) | 无 | 无 | tests/research/test_c0_atomic_acceptance.py, tests/research/test_c0_phase1_storage_integration.py, tests/research/test_c0_contract_prototype.py |
| CR-07 (20m) | CR-02, CR-03, CR-05 | 无 | tests/research/test_c0_contract_prototype.py, tests/research/test_c0_phase1_storage_integration.py |
| CR-08 (20m) | 无 | 无 | docs/plans/2026-10-23-a2-kedro-c0-contract-candidate.md |
| CR-09 (20m) | CR-01, CR-02, CR-03, CR-04, CR-05, CR-06, CR-07, CR-08 | 无 | docs/notes/a2-kedro-c0-r2-qualification.md |
| CR-10 (20m) | CR-09 | 无 | docs/notes/a2-kedro-c0-independent-review-r2.txt |
| F0-01 (15m) | 无 | 无 | docs/notes/a2-kedro-f0-version-provenance.md |
| F0-02 (25m) | F0-01 | 无 | docs/notes/a2-kedro-f0-cve-reachability.md |
| F0-03 (20m) | F0-01 | 无 | docs/notes/a2-kedro-f0-dataset-security.md |
| F0-04 (20m) | F0-01 | 无 | docs/notes/a2-kedro-f0-telemetry-networks.md |
| F0-05a (20m) | F0-01 | 无 | docs/notes/a2-kedro-f0-linux-wheel.md |
| F0-05b (20m) | F0-05a | 无 | docs/notes/a2-kedro-f0-coinstall.md |
| F0-05c (20m) | F0-05b | 无 | docs/notes/a2-kedro-f0-types-tests.md |
| F0-06 (20m) | F0-05b | 无 | docs/notes/a2-kedro-f0-portability.md |
| F0-07 (15m) | F0-02, F0-05b | 无 | docs/notes/a2-kedro-f0-audit-baselines.md |
| F0-08 (20m) | F0-02, F0-03, F0-04, F0-05c, F0-06, F0-07 | 无 | docs/notes/a2-kedro-f0-independent-review.md |
| F0-09 (20m) | F0-08 | F0_PRODUCTION_ADMISSION | docs/notes/a2-kedro-f0-dependency-admission.md |
| C0-00 (15m) | CR-10 | 无 | docs/decisions/a2-v2-schema-ids.md |
| C0-01 (20m) | C0-00 | 无 | msgloom/a2_kedro/contracts/source.py |
| C0-02 (20m) | C0-01 | 无 | msgloom/a2_kedro/source_resolution.py |
| C0-03 (20m) | C0-00 | 无 | msgloom/a2_kedro/contracts/extract.py |
| C0-04 (20m) | C0-03 | 无 | msgloom/a2_kedro/contracts/parse.py |
| C0-05 (20m) | C0-04 | 无 | msgloom/a2_kedro/contracts/zones.py |
| C0-06 (20m) | C0-00 | 无 | msgloom/a2_kedro/contracts/relations.py |
| C0-07 (20m) | C0-05, C0-06 | 无 | msgloom/a2_kedro/contracts/results.py |
| C0-08 (20m) | C0-00 | 无 | msgloom/a2_kedro/contracts/transition.py |
| C0-09 (20m) | C0-01 | 无 | msgloom/a2_kedro/contracts/held.py |
| C0-10 (20m) | C0-07, C0-08, C0-09 | 无 | msgloom/a2_kedro/contracts/receipt.py |
| C0-11a (20m) | C0-00 | 无 | docs/decisions/a2-v2-schema-migration.md |
| C0-11b (20m) | C0-11a | 无 | msgloom/persistence/a2_schema.py |
| C0-11c (20m) | C0-11b | 无 | msgloom/persistence/schema_store.py, msgloom/cli/a2_schema_migration.py |
| C0-11d (20m) | C0-11c | 无 | tests/persistence/test_a2_schema_migrations.py |
| C0-12a (20m) | C0-00 | 无 | msgloom/persistence/a2_acceptance_models.py |
| C0-12b (20m) | C0-11b, C0-12a | 无 | msgloom/persistence/a2_store.py |
| C0-12c (20m) | C0-12b | 无 | msgloom/persistence/async_store.py |
| C0-12d (20m) | C0-12c | 无 | tests/persistence/test_a2_acceptance.py |
| C0-13 (20m) | C0-11b, C0-09 | 无 | msgloom/persistence/a2_held_store.py |
| C0-14a (20m) | C0-10, C0-12d | 无 | msgloom/persistence/a2_receipt_store.py |
| C0-14b (20m) | C0-14a, C0-11c | 无 | msgloom/persistence/intake_store.py, msgloom/persistence/intake_completion.py |
| C0-14c (20m) | C0-14b | 无 | msgloom/persistence/a2_producer_binding.py |
| C0-14d (25m) | C0-14c | 无 | tests/persistence/test_a2_v2_finalization.py |
| C0-15 (20m) | C0-00 | 无 | msgloom/a2_kedro/application_contract.py |
| C0-16 (20m) | C0-00 | 无 | msgloom/a2_kedro/partition_policy.py |
| C0-17a (20m) | C0-07 | 无 | msgloom/triage_input/models_v2.py |
| C0-17b (20m) | C0-17a | 无 | msgloom/triage_input/codec_v2.py |
| C0-17c (20m) | C0-17b | 无 | msgloom/triage_pipeline/handler.py, msgloom/triage_input/adapter_v2.py |
| C0-17d (20m) | C0-17c | 无 | tests/triage_input/test_a2_v2_compat.py |
| C0-18 (20m) | C0-15, C0-13 | 无 | msgloom/cli/a2_scope_status.py |
| C0-19 (20m) | C0-00, C0-07, C0-08, C0-10, C0-17b | 无 | tests/a2_kedro/test_c0_schema_goldens.py |
| C0-20a (20m) | C0-11d, C0-12d, C0-13, C0-14d, C0-17d, C0-18, C0-19 | 无 | docs/notes/a2-v2-c0-integration-audit.md |
| C0-20b (20m) | C0-20a, C0-02 | 无 | tests/a2_kedro/integration/test_a1_workset_v2_receipt_a3.py |
| C0-20c (20m) | C0-20b, F0-08 | F0_PRODUCTION_ADMISSION | docs/notes/a2-v2-c0-independent-acceptance.md |
| P1-01 (20m) | C0-20c | F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | msgloom/a2_kedro/graph.py |
| P1-02 (20m) | C0-20c | F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | msgloom/a2_kedro/catalog.py |
| P1-03 (20m) | P1-02, C0-02 | F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | msgloom/a2_kedro/datasets/handoff.py |
| P1-04 (20m) | P1-03 | F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | msgloom/a2_kedro/datasets/evidence.py |
| P1-05 (25m) | P1-04 | F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | msgloom/a2_kedro/datasets/parser.py |
| P1-06 (20m) | P1-02 | F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | msgloom/a2_kedro/bridge.py |
| P1-07 (20m) | P1-01, P1-06 | F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | msgloom/a2_kedro/runner.py |
| P1-08 (20m) | P1-06, C0-12c | F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | msgloom/a2_kedro/datasets/semantic.py |
| P1-09 (20m) | P1-08, C0-08 | F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | msgloom/a2_kedro/datasets/transitions.py |
| P1-10 (25m) | P1-07, P1-08 | F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | msgloom/a2_kedro/resume.py |
| P1-11 (20m) | P1-02 | F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | msgloom/a2_kedro/security.py |
| P1-12a (20m) | P1-05, P1-07 | F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | tests/a2_kedro/test_native_child_cgroup.py |
| P1-12b (20m) | P1-12a, P2-10 | F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | docs/notes/a2-v2-p1-exclusive-benchmark.md |
| P1-13 (25m) | P1-01, P1-03, P1-04, P1-05, P1-07, P1-08, P1-09, P1-10, P1-11, P1-12b | F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | docs/notes/a2-v2-p1-independent-review.md |
| P2-01 (20m) | C0-03, C0-04 | 无 | msgloom/a2_kedro/parsers/mime_html.py |
| P2-02 (20m) | C0-03, C0-04 | 无 | msgloom/a2_kedro/parsers/plain_json.py |
| P2-03 (20m) | C0-03, C0-04 | 无 | msgloom/a2_kedro/parsers/pdf.py |
| P2-04 (20m) | C0-03, C0-04 | 无 | msgloom/a2_kedro/parsers/docx.py |
| P2-05 (20m) | C0-03, C0-04 | 无 | msgloom/a2_kedro/parsers/spreadsheets.py |
| P2-06 (20m) | C0-03, C0-04 | 无 | msgloom/a2_kedro/parsers/attachments.py |
| P2-07 (20m) | C0-05, P2-02 | 无 | msgloom/a2_kedro/normalize.py |
| P2-08 (25m) | P2-07 | 无 | msgloom/a2_kedro/zones.py |
| P2-09 (20m) | P2-01, P2-02, P2-03, P2-04, P2-05, P2-06 | 无 | msgloom/a2_kedro/parsers/failure_policy.py |
| P2-10 (25m) | P2-09 | 无 | docs/notes/a2-v2-p2-extraction-benchmarks.md |
| P3-01 (20m) | C0-06 | 无 | msgloom/a2_kedro/semantics/relations.py |
| P3-02 (20m) | P3-01 | 无 | msgloom/a2_kedro/semantics/relation_safety.py |
| P3-03 (20m) | C0-07 | 无 | msgloom/a2_kedro/semantics/filters.py |
| P3-04 (20m) | P3-02 | 无 | msgloom/a2_kedro/semantics/outlook_grouping.py |
| P3-05 (20m) | P3-02 | 无 | msgloom/a2_kedro/semantics/teams_grouping.py |
| P3-06 (20m) | C0-07 | 无 | msgloom/a2_kedro/semantics/context_types.py |
| P3-07 (20m) | C0-12a | 无 | msgloom/a2_kedro/semantics/replay_policy.py |
| P3-08 (20m) | C0-08 | 无 | msgloom/a2_kedro/semantics/transitions.py |
| P3-09 (25m) | P3-02, P3-03, P3-04, P3-05, P3-06, P3-07, P3-08 | 无 | docs/notes/a2-v2-p3-independent-review.md |
| T0-01 (20m) | 无 | 无 | tests/a2_kedro/gold/t0_01.json |
| T0-02 (20m) | 无 | 无 | tests/a2_kedro/gold/t0_02.json |
| T0-03 (20m) | 无 | 无 | tests/a2_kedro/gold/t0_03.json |
| T0-04 (20m) | 无 | 无 | tests/a2_kedro/gold/t0_04.json |
| T0-05 (20m) | 无 | 无 | tests/a2_kedro/gold/t0_05.json |
| T0-06 (20m) | C0-09, C0-10 | 无 | tests/a2_kedro/gold/t0_06.json |
| T0-07 (20m) | C0-12b | 无 | tests/a2_kedro/gold/t0_07.json |
| T0-08 (20m) | C0-17a | 无 | tests/a2_kedro/gold/t0_08.json |
| T0-09 (20m) | 无 | 无 | tests/a2_kedro/gold/t0_09.json |
| T0-10 (20m) | 无 | 无 | tests/a2_kedro/gold/t0_10.json |
| T0-11 (25m) | T0-01, T0-02, T0-03, T0-04, T0-05, T0-06, T0-07, T0-08, T0-09, T0-10 | 无 | docs/notes/a2-v2-t0-independent-gold-review.md |
| E0-01 (25m) | P1-13, C0-20c | C0_FINAL_ACCEPTED | msgloom/a2_kedro/integration/claim_topology.py |
| E0-02 (20m) | E0-01, P2-09, P3-09 | C0_FINAL_ACCEPTED | msgloom/a2_kedro/integration/full_pipeline.py |
| E0-03a (20m) | E0-02 | 无 | tests/a2_kedro/test_save_faults.py |
| E0-03b (20m) | E0-03a | 无 | tests/a2_kedro/test_crash_recovery.py |
| E0-04 (25m) | E0-01 | 无 | tests/a2_kedro/integration/test_claim_concurrency.py |
| E0-05 (20m) | E0-03b | 无 | tests/a2_kedro/integration/test_postcommit_cancel.py |
| E0-06 (25m) | E0-02 | 无 | msgloom/a2_kedro/integration/workset_completion.py |
| E0-07 (20m) | E0-06 | 无 | tests/a2_kedro/integration/test_held_pending.py |
| E0-08 (20m) | E0-02 | 无 | tests/a2_kedro/integration/test_unverifiable_role.py |
| E0-09 (20m) | E0-06, C0-17d | 无 | tests/a2_kedro/integration/test_a3_v2_lineage.py |
| E0-10 (20m) | E0-02 | C0_FINAL_ACCEPTED | msgloom/cli/composition.py |
| E0-11 (25m) | E0-09, E0-10, T0-11 | 无 | tests/a2_kedro/integration/test_multi_stream_e2e.py |
| E0-12 (25m) | E0-03b, E0-04, E0-05, E0-07, E0-08, E0-11 | 无 | docs/notes/a2-v2-e0-independent-review.md |
| I0-01 (20m) | C0-18 | 无 | msgloom/a2_kedro/activation/status_policy.py |
| I0-02 (20m) | C0-18 | 无 | msgloom/cli/a2_scope_status.py |
| I0-03 (20m) | I0-01 | 无 | msgloom/a2_kedro/activation/prefect_flow.py |
| I0-04 (20m) | I0-02, I0-03 | 无 | msgloom/a2_kedro/activation/launcher.py |
| I0-05 (20m) | I0-04 | 无 | msgloom/a2_kedro/activation/catchup.py |
| I0-06 (20m) | I0-05 | 无 | msgloom/a2_kedro/activation/coalesce.py |
| I0-07 (25m) | E0-12, I0-06 | F0_PRODUCTION_ADMISSION | tests/a2_kedro/activation/test_staging_autowakeup.py |
| I0-08 (25m) | I0-07 | 无 | docs/notes/a2-v2-i0-cutover-audit.md |
| I0-09 (20m) | I0-08 | 无 | docs/runbooks/a2-v2-activation.md |
| I0-10 (20m) | I0-09, V0-14c | OWNER_EXPLICIT_CUTOVER_APPROVAL | docs/notes/a2-v2-i0-owner-approval.md |
| V0-01 (20m) | E0-02 | 无 | tests/a2_kedro/acceptance/test_v0_01.py |
| V0-02 (20m) | C0-00 | 无 | tests/a2_kedro/acceptance/test_v0_02.py |
| V0-03 (20m) | E0-11 | 无 | tests/a2_kedro/acceptance/test_v0_03.py |
| V0-04 (20m) | P2-09, T0-11 | 无 | tests/a2_kedro/acceptance/test_v0_04.py |
| V0-05 (20m) | P3-09, T0-11 | 无 | tests/a2_kedro/acceptance/test_v0_05.py |
| V0-06 (20m) | P1-12b, E0-05 | 无 | tests/a2_kedro/acceptance/test_v0_06.py |
| V0-07 (25m) | C0-11d, E0-12 | 无 | tests/a2_kedro/acceptance/test_v0_07.py |
| V0-08 (20m) | C0-20c, E0-12 | 无 | tests/a2_kedro/acceptance/test_v0_08.py |
| V0-09 (20m) | E0-09 | 无 | tests/a2_kedro/acceptance/test_v0_09.py |
| V0-10 (20m) | I0-06 | 无 | tests/a2_kedro/acceptance/test_v0_10.py |
| V0-11 (20m) | V0-11a, E0-12 | 无 | tests/a2_kedro/acceptance/test_v0_11.py |
| V0-11a (20m) | C0-00 | 无 | .github/workflows/ci.yml |
| V0-12 (20m) | E0-12, F0-09 | F0_PRODUCTION_ADMISSION | tests/a2_kedro/acceptance/test_v0_12.py |
| V0-15 (20m) | E0-12, P1-12b | 无 | tests/a2_kedro/acceptance/test_v0_15.py |
| V0-16 (20m) | E0-12, P1-13 | 无 | tests/a2_kedro/acceptance/test_v0_16.py |
| V0-17 (20m) | I0-06, E0-12 | 无 | tests/a2_kedro/acceptance/test_v0_17.py |
| V0-13 (20m) | F0-08, P1-11 | 无 | tests/a2_kedro/acceptance/test_v0_13.py |
| V0-14a (20m) | V0-01, V0-02, V0-03, V0-04, V0-05, V0-06, V0-07, V0-08, V0-09, V0-10, V0-11, V0-11a, V0-12, V0-13, V0-15, V0-16, V0-17 | 无 | docs/notes/a2-v2-independent-review-r1.md |
| V0-14b (20m) | V0-14a | 无 | docs/notes/a2-v2-independent-review-r2.md |
| V0-14c (20m) | V0-14b | 无 | docs/notes/a2-v2-final-go-no-go.md |
| R0-01 (20m) | V0-14c | 无 | docs/notes/a2_v2_r0_01.md |
| R0-02 (20m) | R0-01 | 无 | docs/notes/a2_v2_r0_02.md |
| R0-03 (20m) | R0-02, I0-09 | 无 | docs/notes/a2_v2_r0_03.md |
| R0-04 (20m) | R0-03, I0-10 | OWNER_EXPLICIT_CUTOVER_APPROVAL, STAGED_DB_BACKUP_AND_OLD_PENDING_ZERO | docs/notes/a2-v2-r0-schema-activation-receipt.md |
| R0-05 (20m) | R0-04 | 无 | docs/notes/a2_v2_r0_05.md |
| R0-06 (20m) | R0-05 | 无 | msgloom/preparation_pipeline/handler.py, msgloom/preparation_pipeline/scheduled.py |
| R0-07 (20m) | R0-06 | 无 | docs/notes/a2-v2-r0-merge-cleanup-audit.md |
| R0-08 (20m) | R0-07 | 无 | docs/notes/a2_v2_r0_08.md |

**验收原则**：每个任务报告 exact Git SHA、真实测试退出码、审查证据；所有未批准 gate 保持 BLOCKED。

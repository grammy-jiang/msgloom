# A2 Kedro v2 — 可调度任务依赖与文件所有权

**状态：仅设计候选（NOT STARTED），未经用户批准不得执行。**

任务数量：**151**；最长名义依赖链：**875 分钟 / 42 项**，仅作为发现串行瓶颈的指标，**不等于日历工期或交付时间估计**。审批、CI、资源锁、网络/安全决定可能显著增加实际周期。

本表是 [可机器读取 JSON 清单](2026-10-23-a2-kedro-v2-task-manifest.json) 的可读视图。JSON 对每个任务都包含依赖、文件所有权、预计产出、验收和模型 effort。以下路径是**计划中的文件**，未创建不等于当前任务已运行。所有子 Agent 要先核实实际 Git SHA/依赖版本。

## 独立门禁和共享资源

- **F0_PRODUCTION_ADMISSION**：安全审查 F0-08、Kedro 风险处理、owner 明确决定、共装 CI；绿色 OSV baseline 并不能消除 Snyk 风险。
- **C0_FINAL_ACCEPTED**：真实 A1 Workset + v2 acceptance/receipt/finalizer + A3 triage_input@2 的确切 SHA 经独立 reviewer ACCEPT；provisional models 不算。
- **OWNER_EXPLICIT_CUTOVER_APPROVAL**：只有用户授权后才可实际迁移生产 SQLite、启用 Prefect、切换引擎。
- **STAGED_DB_BACKUP_AND_OLD_PENDING_ZERO**：数据库备份恢复演练已验证，旧 pending workset 归零，held-only 历史已审计。
- **独占 benchmark slot**：真实 Pi RSS/CPU/GIL/claim margin 测量时停止其他 P1/P2 重负载，不得与普通并行开发混测。
- **共享文件锁**：CR-02/03/06/07 等研究测试即使可并行分析，也必须按文件单 owner 串行提交；C0-11/12/14、CI 和 parser registry 同理。

## 全部任务

| Task | Owner / effort | depends_on；门禁 | 独占编辑路径 | 明确产出与测试 |
| --- | --- | --- | --- | --- |
| CR-01 (15m) | c0-research-docs-owner / high | 无；gates: 无 | `docs/plans/2026-10-23-a2-kedro-c0-contract-candidate.md` | docs/plans/2026-10-23-a2-kedro-c0-contract-candidate.md; Sonnet High |
| CR-02 (20m) | c0-research-tests-owner / medium | 无；gates: 无 | `tests/research/test_c0_contract_prototype.py` | tests/research/test_c0_contract_prototype.py; Sonnet Medium |
| CR-03 (20m) | c0-research-tests-owner / medium | 无；gates: 无 | `tests/research/test_c0_contract_prototype.py` | tests/research/test_c0_contract_prototype.py; Sonnet Medium |
| CR-04 (20m) | c0-research-docs-owner / high | 无；gates: 无 | `docs/plans/2026-10-23-a2-kedro-c0-contract-candidate.md` | docs/plans/2026-10-23-a2-kedro-c0-contract-candidate.md; Sonnet High |
| CR-05 (15m) | c0-a1-fixture-owner / medium | 无；gates: 无 | `tests/research/test_c0_native_a1_exact_handoff.py` | tests/research/test_c0_native_a1_exact_handoff.py; Sonnet Medium |
| CR-06 (15m) | c0-research-tests-owner / medium | 无；gates: 无 | `tests/research/test_c0_atomic_acceptance.py`, `tests/research/test_c0_phase1_storage_integration.py`, `tests/research/test_c0_contract_prototype.py` | tests/research/test_c0_atomic_acceptance.py, tests/research/test_c0_contract_prototype.py, tests/research/test_c0_ph |
| CR-07 (20m) | c0-research-tests-owner / medium | CR-02, CR-03, CR-05；gates: 无 | `tests/research/test_c0_contract_prototype.py`, `tests/research/test_c0_phase1_storage_integration.py` | tests/research/test_c0_contract_prototype.py, tests/research/test_c0_phase1_storage_integration.py; Sonnet Medium |
| CR-08 (20m) | c0-research-docs-owner / high | 无；gates: 无 | `docs/plans/2026-10-23-a2-kedro-c0-contract-candidate.md` | docs/plans/2026-10-23-a2-kedro-c0-contract-candidate.md; Sonnet High |
| CR-09 (20m) | c0-research-owner / medium | CR-01, CR-02, CR-03, CR-04, CR-05, CR-06, CR-07, CR-08；gates: 无 | `docs/notes/a2-kedro-c0-r2-qualification.md` | tests/research/test_c0_*.py, docs/notes/a2-kedro-c0-ci-evidence-r2.md; Sonnet Medium |
| CR-10 (20m) | independent-reviewer / high | CR-09；gates: 无 | `docs/notes/a2-kedro-c0-independent-review-r2.txt` | docs/notes/a2-kedro-c0-independent-review-r2-*.txt; Sonnet High |
| F0-01 (15m) | security-dependency-owner / medium | 无；gates: 无 | `docs/notes/a2-kedro-f0-version-provenance.md` | docs/notes/a2-kedro-f0-wheel-identity.md; Sonnet Medium |
| F0-02 (25m) | security-dependency-owner / high | F0-01；gates: 无 | `docs/notes/a2-kedro-f0-cve-reachability.md` | docs/notes/a2-kedro-f0-cve-reachability.md; Sonnet High |
| F0-03 (20m) | security-dependency-owner / high | F0-01；gates: 无 | `docs/notes/a2-kedro-f0-dataset-security.md` | scripts/research/f0_catalog_guard.py, docs/notes/a2-kedro-f0-catalog-security.md; Sonnet High |
| F0-04 (20m) | security-dependency-owner / high | F0-01；gates: 无 | `docs/notes/a2-kedro-f0-telemetry-networks.md` | scripts/research/f0_telemetry_imports.py, docs/notes/a2-kedro-f0-telemetry.md; Sonnet High |
| F0-05a (20m) | security-dependency-owner / medium | F0-01；gates: 无 | `docs/notes/a2-kedro-f0-linux-wheel.md` | docs/notes/a2-kedro-f0-scratch-lock.json; Sonnet Medium |
| F0-05b (20m) | security-dependency-owner / medium | F0-05a；gates: 无 | `docs/notes/a2-kedro-f0-coinstall.md` | docs/notes/a2-kedro-f0-pi-matrix.json; Sonnet Medium |
| F0-05c (20m) | security-dependency-owner / medium | F0-05b；gates: 无 | `docs/notes/a2-kedro-f0-types-tests.md` | docs/notes/a2-kedro-f0-full-wheel-install.md; Sonnet High |
| F0-06 (20m) | security-dependency-owner / medium | F0-05b；gates: 无 | `docs/notes/a2-kedro-f0-portability.md` | docs/notes/a2-kedro-f0-platform-matrix.md; Sonnet Medium |
| F0-07 (15m) | security-dependency-owner / high | F0-02, F0-05b；gates: 无 | `docs/notes/a2-kedro-f0-audit-baselines.md` | docs/notes/a2-kedro-f0-vulnerability-delta.md; Sonnet High |
| F0-08 (20m) | independent-reviewer / high | F0-02, F0-03, F0-04, F0-05c, F0-06, F0-07；gates: 无 | `docs/notes/a2-kedro-f0-independent-review.md` | docs/notes/a2-kedro-f0-independent-review.md; Sonnet High |
| F0-09 (20m) | dependency-lock-single-owner / medium | F0-08；gates: F0_PRODUCTION_ADMISSION | `docs/notes/a2-kedro-f0-dependency-admission.md` | docs/plans/a2-kedro-f0-dependency-pr-checklist.md; Sonnet Medium |
| C0-00 (15m) | c0-contract-owner / medium | CR-10；gates: 无 | `docs/decisions/a2-v2-schema-ids.md` | docs/decisions/a2-v2-schema-ids.md; Sonnet Medium |
| C0-01 (20m) | c0-contract-owner / medium | C0-00；gates: 无 | `msgloom/a2_kedro/contracts/source.py` | msgloom/a2_kedro/contracts/source.py; Sonnet Medium |
| C0-02 (20m) | c0-contract-owner / medium | C0-01；gates: 无 | `msgloom/a2_kedro/source_resolution.py` | msgloom/a2_kedro/source_resolution.py; Sonnet Medium |
| C0-03 (20m) | c0-contract-owner / medium | C0-00；gates: 无 | `msgloom/a2_kedro/contracts/extract.py` | msgloom/a2_kedro/contracts/extract.py; Sonnet Medium |
| C0-04 (20m) | c0-contract-owner / medium | C0-03；gates: 无 | `msgloom/a2_kedro/contracts/parse.py` | msgloom/a2_kedro/contracts/parse.py; Sonnet Medium |
| C0-05 (20m) | c0-contract-owner / medium | C0-04；gates: 无 | `msgloom/a2_kedro/contracts/zones.py` | msgloom/a2_kedro/contracts/zones.py; Sonnet Medium |
| C0-06 (20m) | c0-contract-owner / medium | C0-00；gates: 无 | `msgloom/a2_kedro/contracts/relations.py` | msgloom/a2_kedro/contracts/relations.py; Sonnet Medium |
| C0-07 (20m) | c0-contract-owner / medium | C0-05, C0-06；gates: 无 | `msgloom/a2_kedro/contracts/results.py` | msgloom/a2_kedro/contracts/results.py; Sonnet Medium |
| C0-08 (20m) | c0-contract-owner / medium | C0-00；gates: 无 | `msgloom/a2_kedro/contracts/transition.py` | msgloom/a2_kedro/contracts/transition.py; Sonnet Medium |
| C0-09 (20m) | c0-contract-owner / medium | C0-01；gates: 无 | `msgloom/a2_kedro/contracts/held.py` | msgloom/a2_kedro/contracts/held.py; Sonnet Medium |
| C0-10 (20m) | c0-contract-owner / medium | C0-07, C0-08, C0-09；gates: 无 | `msgloom/a2_kedro/contracts/receipt.py` | msgloom/a2_kedro/contracts/receipt.py; Sonnet Medium |
| C0-11a (20m) | db-schema-single-owner / high | C0-00；gates: 无 | `docs/decisions/a2-v2-schema-migration.md` | msgloom/persistence/schema_store.py; Sonnet High |
| C0-11b (20m) | db-schema-single-owner / high | C0-11a；gates: 无 | `msgloom/persistence/a2_schema.py` | msgloom/persistence/a2_schema.py; Sonnet High |
| C0-11c (20m) | db-schema-single-owner / high | C0-11b；gates: 无 | `msgloom/persistence/schema_store.py`, `msgloom/cli/a2_schema_migration.py` | msgloom/persistence/schema_store.py; Sonnet High |
| C0-11d (20m) | db-schema-single-owner / medium | C0-11c；gates: 无 | `tests/persistence/test_a2_schema_migrations.py` | tests/persistence/test_a2_schema_migrations.py; Sonnet High |
| C0-12a (20m) | db-schema-single-owner / high | C0-00；gates: 无 | `msgloom/persistence/a2_acceptance_models.py` | msgloom/persistence/a2_acceptance_models.py; Sonnet High |
| C0-12b (20m) | db-schema-single-owner / high | C0-11b, C0-12a；gates: 无 | `msgloom/persistence/a2_store.py` | msgloom/persistence/a2_store.py; Sonnet High |
| C0-12c (20m) | db-schema-single-owner / high | C0-12b；gates: 无 | `msgloom/persistence/async_store.py` | msgloom/persistence/async_store.py; Sonnet High |
| C0-12d (20m) | db-schema-single-owner / medium | C0-12c；gates: 无 | `tests/persistence/test_a2_acceptance.py` | tests/persistence/test_a2_acceptance.py; Sonnet High |
| C0-13 (20m) | db-schema-single-owner / medium | C0-11b, C0-09；gates: 无 | `msgloom/persistence/a2_held_store.py` | msgloom/persistence/a2_held_store.py; Sonnet Medium |
| C0-14a (20m) | db-schema-single-owner / high | C0-10, C0-12d；gates: 无 | `msgloom/persistence/a2_receipt_store.py` | msgloom/persistence/a2_receipt_store.py; Sonnet High |
| C0-14b (20m) | db-schema-single-owner / high | C0-14a, C0-11c；gates: 无 | `msgloom/persistence/intake_store.py`, `msgloom/persistence/intake_completion.py` | msgloom/persistence/intake_store.py, intake_completion.py; Sonnet High |
| C0-14c (20m) | db-schema-single-owner / high | C0-14b；gates: 无 | `msgloom/persistence/a2_producer_binding.py` | msgloom/persistence/a2_producer_binding.py; Sonnet High |
| C0-14d (25m) | db-schema-single-owner / medium | C0-14c；gates: 无 | `tests/persistence/test_a2_v2_finalization.py` | tests/persistence/test_a2_v2_finalization.py; Sonnet High |
| C0-15 (20m) | c0-contract-owner / high | C0-00；gates: 无 | `msgloom/a2_kedro/application_contract.py` | msgloom/a2_kedro/application_contract.py; Sonnet Medium |
| C0-16 (20m) | c0-contract-owner / medium | C0-00；gates: 无 | `msgloom/a2_kedro/partition_policy.py` | msgloom/a2_kedro/partition_policy.py; Sonnet Medium |
| C0-17a (20m) | a3-single-owner / high | C0-07；gates: 无 | `msgloom/triage_input/models_v2.py` | msgloom/a2_kedro/contracts/*.py, msgloom/persistence/a2_*.py, tests/persistence/test_a2_*.py; Sonnet Medium |
| C0-17b (20m) | a3-single-owner / medium | C0-17a；gates: 无 | `msgloom/triage_input/codec_v2.py` | msgloom/triage_input/codec_v2.py; Sonnet Medium |
| C0-17c (20m) | a3-single-owner / high | C0-17b；gates: 无 | `msgloom/triage_pipeline/handler.py`, `msgloom/triage_input/adapter_v2.py` | msgloom/triage_pipeline/handler.py; Sonnet Medium |
| C0-17d (20m) | a3-single-owner / medium | C0-17c；gates: 无 | `tests/triage_input/test_a2_v2_compat.py` | tests/triage_input/test_a2_v2_compat.py; Sonnet Medium |
| C0-18 (20m) | c0-contract-owner / medium | C0-15, C0-13；gates: 无 | `msgloom/cli/a2_scope_status.py` | msgloom/a2_kedro/contracts/*.py, msgloom/persistence/a2_*.py, tests/persistence/test_a2_*.py; Sonnet Medium |
| C0-19 (20m) | c0-contract-owner / medium | C0-00, C0-07, C0-08, C0-10, C0-17b；gates: 无 | `tests/a2_kedro/test_c0_schema_goldens.py` | tests/a2_kedro/test_v2_schema_golden.py; Sonnet Medium |
| C0-20a (20m) | c0-contract-owner / medium | C0-11d, C0-12d, C0-13, C0-14d, C0-17d, C0-18, C0-19；gates: 无 | `docs/notes/a2-v2-c0-integration-audit.md` | docs/notes/a2-kedro-c0-merge-evidence.md; Sonnet Medium |
| C0-20b (20m) | c0-contract-owner / high | C0-20a, C0-02；gates: 无 | `tests/a2_kedro/integration/test_a1_workset_v2_receipt_a3.py` | tests/a2_kedro/test_c0_v2_e2e.py; Sonnet High |
| C0-20c (20m) | independent-reviewer / high | C0-20b, F0-08；gates: F0_PRODUCTION_ADMISSION | `docs/notes/a2-v2-c0-independent-acceptance.md` | docs/notes/a2-kedro-c0-independent-final.md; Sonnet High |
| P1-01 (20m) | kedro-runtime-owner / medium | C0-20c；gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `msgloom/a2_kedro/graph.py` | msgloom/a2_kedro/graph.py; Sonnet Medium |
| P1-02 (20m) | kedro-runtime-owner / medium | C0-20c；gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `msgloom/a2_kedro/catalog.py` | msgloom/a2_kedro/catalog.py; Sonnet Medium |
| P1-03 (20m) | kedro-runtime-owner / medium | P1-02, C0-02；gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `msgloom/a2_kedro/datasets/handoff.py` | msgloom/a2_kedro/datasets/handoff.py; Sonnet Medium |
| P1-04 (20m) | kedro-runtime-owner / medium | P1-03；gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `msgloom/a2_kedro/datasets/evidence.py` | msgloom/a2_kedro/datasets/evidence.py; Sonnet Medium |
| P1-05 (25m) | kedro-runtime-owner / medium | P1-04；gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `msgloom/a2_kedro/datasets/parser.py` | msgloom/a2_kedro/datasets/parser.py; Sonnet Medium |
| P1-06 (20m) | kedro-runtime-owner / high | P1-02；gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `msgloom/a2_kedro/bridge.py` | msgloom/a2_kedro/bridge.py; Sonnet Medium |
| P1-07 (20m) | kedro-runtime-owner / high | P1-01, P1-06；gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `msgloom/a2_kedro/runner.py` | msgloom/a2_kedro/runner.py; Sonnet Medium |
| P1-08 (20m) | kedro-runtime-owner / high | P1-06, C0-12c；gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `msgloom/a2_kedro/datasets/semantic.py` | msgloom/a2_kedro/datasets/semantic.py; Sonnet Medium |
| P1-09 (20m) | kedro-runtime-owner / medium | P1-08, C0-08；gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `msgloom/a2_kedro/datasets/transitions.py` | msgloom/a2_kedro/datasets/transitions.py; Sonnet Medium |
| P1-10 (25m) | kedro-runtime-owner / medium | P1-07, P1-08；gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `msgloom/a2_kedro/resume.py` | msgloom/a2_kedro/resume.py; Sonnet Medium |
| P1-11 (20m) | kedro-runtime-owner / medium | P1-02；gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `msgloom/a2_kedro/security.py` | msgloom/a2_kedro/security.py; Sonnet Medium |
| P1-12a (20m) | kedro-runtime-owner / medium | P1-05, P1-07；gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `tests/a2_kedro/test_native_child_cgroup.py` | tests/a2_kedro/test_real_parser_child_cgroup.py; Sonnet Medium |
| P1-12b (20m) | kedro-runtime-owner / high | P1-12a, P2-10；gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `docs/notes/a2-v2-p1-exclusive-benchmark.md` | docs/notes/a2-kedro-pi-lease-benchmark.json; Sonnet High |
| P1-13 (25m) | independent-reviewer / high | P1-01, P1-03, P1-04, P1-05, P1-07, P1-08, P1-09, P1-10, P1-11, P1-12b；gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `docs/notes/a2-v2-p1-independent-review.md` | docs/notes/a2-kedro-p1-independent-review.md; Sonnet High |
| P2-01 (20m) | format-parsing-owner / medium | C0-03, C0-04；gates: 无 | `msgloom/a2_kedro/parsers/mime_html.py` | msgloom/a2_kedro/parsing/mime_html.py; Sonnet Medium |
| P2-02 (20m) | format-parsing-owner / medium | C0-03, C0-04；gates: 无 | `msgloom/a2_kedro/parsers/plain_json.py` | msgloom/a2_kedro/parsing/plain_json.py; Sonnet Medium |
| P2-03 (20m) | format-parsing-owner / medium | C0-03, C0-04；gates: 无 | `msgloom/a2_kedro/parsers/pdf.py` | msgloom/a2_kedro/parsing/pdf.py; Sonnet Medium |
| P2-04 (20m) | format-parsing-owner / medium | C0-03, C0-04；gates: 无 | `msgloom/a2_kedro/parsers/docx.py` | msgloom/a2_kedro/parsing/docx.py; Sonnet Medium |
| P2-05 (20m) | format-parsing-owner / medium | C0-03, C0-04；gates: 无 | `msgloom/a2_kedro/parsers/spreadsheets.py` | msgloom/a2_kedro/parsing/spreadsheet.py; Sonnet Medium |
| P2-06 (20m) | format-parsing-owner / medium | C0-03, C0-04；gates: 无 | `msgloom/a2_kedro/parsers/attachments.py` | msgloom/a2_kedro/parsing/surface_inventory.py; Sonnet Medium |
| P2-07 (20m) | format-parsing-owner / medium | C0-05, P2-02；gates: 无 | `msgloom/a2_kedro/normalize.py` | msgloom/a2_kedro/parsing/normalization.py; Sonnet Medium |
| P2-08 (25m) | format-parsing-owner / medium | P2-07；gates: 无 | `msgloom/a2_kedro/zones.py` | msgloom/a2_kedro/parsing/zones.py; Sonnet Medium |
| P2-09 (20m) | format-parsing-owner / medium | P2-01, P2-02, P2-03, P2-04, P2-05, P2-06；gates: 无 | `msgloom/a2_kedro/parsers/failure_policy.py` | msgloom/a2_kedro/parsing/failure_policy.py; Sonnet Medium |
| P2-10 (25m) | format-parsing-owner / medium | P2-09；gates: 无 | `docs/notes/a2-v2-p2-extraction-benchmarks.md` | tests/a2_kedro/test_parser_resource_pi.py; Sonnet Medium |
| P3-01 (20m) | native-semantic-owner / medium | C0-06；gates: 无 | `msgloom/a2_kedro/semantics/relations.py` | msgloom/a2_kedro/native/relations.py; Sonnet Medium |
| P3-02 (20m) | native-semantic-owner / medium | P3-01；gates: 无 | `msgloom/a2_kedro/semantics/relation_safety.py` | msgloom/a2_kedro/native/validations.py; Sonnet Medium |
| P3-03 (20m) | native-semantic-owner / medium | C0-07；gates: 无 | `msgloom/a2_kedro/semantics/filters.py` | msgloom/a2_kedro/native/filtering.py; Sonnet Medium |
| P3-04 (20m) | native-semantic-owner / medium | P3-02；gates: 无 | `msgloom/a2_kedro/semantics/outlook_grouping.py` | msgloom/a2_kedro/native/outlook_grouping.py; Sonnet Medium |
| P3-05 (20m) | native-semantic-owner / medium | P3-02；gates: 无 | `msgloom/a2_kedro/semantics/teams_grouping.py` | msgloom/a2_kedro/native/teams_grouping.py; Sonnet Medium |
| P3-06 (20m) | native-semantic-owner / medium | C0-07；gates: 无 | `msgloom/a2_kedro/semantics/context_types.py` | msgloom/a2_kedro/native/contextual_sources.py; Sonnet Medium |
| P3-07 (20m) | native-semantic-owner / medium | C0-12a；gates: 无 | `msgloom/a2_kedro/semantics/replay_policy.py` | msgloom/a2_kedro/native/replay_policy.py; Sonnet Medium |
| P3-08 (20m) | native-semantic-owner / medium | C0-08；gates: 无 | `msgloom/a2_kedro/semantics/transitions.py` | msgloom/a2_kedro/native/transitions.py; Sonnet Medium |
| P3-09 (25m) | independent-reviewer / medium | P3-02, P3-03, P3-04, P3-05, P3-06, P3-07, P3-08；gates: 无 | `docs/notes/a2-v2-p3-independent-review.md` | tests/a2_kedro/test_native_gold.py; Sonnet Medium |
| T0-01 (20m) | independent-gold-owner / medium | 无；gates: 无 | `tests/a2_kedro/gold/t0_01.json` | tests/a2_kedro/gold/a1_release.py; Sonnet Medium |
| T0-02 (20m) | independent-gold-owner / medium | 无；gates: 无 | `tests/a2_kedro/gold/t0_02.json` | tests/a2_kedro/gold/mail_quotes.py; Sonnet Medium |
| T0-03 (20m) | independent-gold-owner / medium | 无；gates: 无 | `tests/a2_kedro/gold/t0_03.json` | tests/a2_kedro/gold/teams_chat_channel.py; Sonnet Medium |
| T0-04 (20m) | independent-gold-owner / medium | 无；gates: 无 | `tests/a2_kedro/gold/t0_04.json` | tests/a2_kedro/gold/contextual_streams.py; Sonnet Medium |
| T0-05 (20m) | independent-gold-owner / medium | 无；gates: 无 | `tests/a2_kedro/gold/t0_05.json` | tests/a2_kedro/gold/hostile_formats.py; Sonnet Medium |
| T0-06 (20m) | independent-gold-owner / medium | C0-09, C0-10；gates: 无 | `tests/a2_kedro/gold/t0_06.json` | tests/a2_kedro/gold/held_transitions.py; Sonnet Medium |
| T0-07 (20m) | independent-gold-owner / medium | C0-12b；gates: 无 | `tests/a2_kedro/gold/t0_07.json` | tests/a2_kedro/gold/crash_claims.py; Sonnet Medium |
| T0-08 (20m) | independent-gold-owner / medium | C0-17a；gates: 无 | `tests/a2_kedro/gold/t0_08.json` | tests/a2_kedro/gold/a3_legacy.py; Sonnet Medium |
| T0-09 (20m) | independent-gold-owner / medium | 无；gates: 无 | `tests/a2_kedro/gold/t0_09.json` | tests/a2_kedro/gold/prefect_wakeup.py; Sonnet Medium |
| T0-10 (20m) | independent-gold-owner / medium | 无；gates: 无 | `tests/a2_kedro/gold/t0_10.json` | tests/a2_kedro/gold/security.py; Sonnet Medium |
| T0-11 (25m) | independent-reviewer / medium | T0-01, T0-02, T0-03, T0-04, T0-05, T0-06, T0-07, T0-08, T0-09, T0-10；gates: 无 | `docs/notes/a2-v2-t0-independent-gold-review.md` | tests/a2_kedro/gold/independent_gold_review.md; Sonnet Medium |
| E0-01 (25m) | integration-owner / medium | P1-13, C0-20c；gates: C0_FINAL_ACCEPTED | `msgloom/a2_kedro/integration/claim_topology.py` | Workset PREPARE + partition PREPARE + transition PREPARE 真实 claim；每个 claim owner/required_inputs 清晰 |
| E0-02 (20m) | integration-owner / medium | E0-01, P2-09, P3-09；gates: C0_FINAL_ACCEPTED | `msgloom/a2_kedro/integration/full_pipeline.py` | Full Kedro DAG K0–K11 从 Workset@1 端到 v2 receipt；不走 legacy A2 控制环 |
| E0-03a (20m) | integration-owner / medium | E0-02；gates: 无 | `tests/a2_kedro/test_save_faults.py` | `tests/a2_kedro/test_save_faults.py` 预置每个 Dataset save 注入点；完成/失败/部分结果和摘要准确 |
| E0-03b (20m) | integration-owner / medium | E0-03a；gates: 无 | `tests/a2_kedro/test_crash_recovery.py` | `tests/a2_kedro/test_crash_recovery.py` 真实 restart/read-back；首段 accepted prefix 不丢、没有重复 |
| E0-04 (25m) | integration-owner / high | E0-01；gates: 无 | `tests/a2_kedro/integration/test_claim_concurrency.py` | 两合法 claim 键碰撞、过期/替换、并发前后 start barrier；数据库只有一个 logical output |
| E0-05 (20m) | integration-owner / high | E0-03b；gates: 无 | `tests/a2_kedro/integration/test_postcommit_cancel.py` | Postcommit cancellation：返回 CancelledError 而数据已存，下一轮 query/reconcile 不重复 parser |
| E0-06 (25m) | integration-owner / medium | E0-02；gates: 无 | `msgloom/a2_kedro/integration/workset_completion.py` | Workset-aggregate v2 receipt：一个选中 occurrence 一个 outcome + transition batch + intake-held |
| E0-07 (20m) | integration-owner / medium | E0-06；gates: 无 | `tests/a2_kedro/integration/test_held_pending.py` | Held-only 被标记 terminal INCOMPLETE；pending index 无永续 spin；operator replay append-only |
| E0-08 (20m) | integration-owner / medium | E0-02；gates: 无 | `tests/a2_kedro/integration/test_unverifiable_role.py` | Wrong role/ambiguous release re-read → A2-held，A1 原结果/cursor 字节不变 |
| E0-09 (20m) | integration-owner / medium | E0-06, C0-17d；gates: 无 | `tests/a2_kedro/integration/test_a3_v2_lineage.py` | A3 所有 typed prepared@2 +历史 prepared@1 与 limitation，A5 仍读取恰当 triage output |
| E0-10 (20m) | integration-owner / medium | E0-02；gates: C0_FINAL_ACCEPTED | `msgloom/cli/composition.py` | 按现有 Application async invocation 和 CLI `prepare-scheduled` 做一条真正 release→prepare 流 |
| E0-11 (25m) | integration-owner / medium | E0-09, E0-10, T0-11；gates: 无 | `tests/a2_kedro/integration/test_multi_stream_e2e.py` | 格式 × 来源 × scope 集成，断流后重放、无已提交 entry 时 no-op、跨源全局序列 gap |
| E0-12 (25m) | independent-reviewer / high | E0-03b, E0-04, E0-05, E0-07, E0-08, E0-11；gates: 无 | `docs/notes/a2-v2-e0-independent-review.md` | 失效清单、可追溯完整引用和清理边界；独立 reviewer 只读 exact SHA |
| I0-01 (20m) | activation-owner / medium | C0-18；gates: 无 | `msgloom/a2_kedro/activation/status_policy.py` | 独立纯逻辑 scheduler 状态机：pending/busy/held/BLOCKED/FAILED/CANCELLED 不混淆 |
| I0-02 (20m) | activation-owner / medium | C0-18；gates: 无 | `msgloom/cli/a2_scope_status.py` | `scope-status` allowlisted CLI，scope hash / cursor digest / pending/held counts / last receipt，不含 PII |
| I0-03 (20m) | activation-owner / medium | I0-01；gates: 无 | `msgloom/a2_kedro/activation/prefect_flow.py` | Prefect（或外部启动器）无 payload finite wakeup 定义，只发提示不修改 A1 |
| I0-04 (20m) | activation-owner / medium | I0-02, I0-03；gates: 无 | `msgloom/a2_kedro/activation/launcher.py` | real command wrapper 调用既有 `prepare-scheduled`，锁定稳定 consumer/catalog pin，不读私有 SQL |
| I0-05 (20m) | activation-owner / medium | I0-04；gates: 无 | `msgloom/a2_kedro/activation/catchup.py` | A1 完成/部分失败/重复通知/失联提醒后，依照 committed release 和 durable cursor 恢复 |
| I0-06 (20m) | activation-owner / medium | I0-05；gates: 无 | `msgloom/a2_kedro/activation/coalesce.py` | 同 scope 重叠 invocation coalesce、claim-busy 退避、no-progress 上限，无无限循环 |
| I0-07 (25m) | activation-owner / high | E0-12, I0-06；gates: F0_PRODUCTION_ADMISSION | `tests/a2_kedro/activation/test_staging_autowakeup.py` | Disabled/staging 部署验证及一条真实 A1→Kedro A2 流，先不放大并发 |
| I0-08 (25m) | activation-owner / medium | I0-07；gates: 无 | `docs/notes/a2-v2-i0-cutover-audit.md` | 旧 pending workset 清零核查、旧 engine 过渡与稳定回滚 anchor、历史 A3 读路径 |
| I0-09 (20m) | activation-owner / medium | I0-08；gates: 无 | `docs/runbooks/a2-v2-activation.md` | 生产启动 runbook、停止/恢复/报警分支、消除双引擎自动 fallback |
| I0-10 (20m) | activation-owner / high | I0-09, V0-14c；gates: OWNER_EXPLICIT_CUTOVER_APPROVAL | `docs/notes/a2-v2-i0-owner-approval.md` | 用户明确确认后才可启用生产 Prefect、执行 DB schema migration 或正式 switch |
| V0-01 (20m) | independent-qa-owner / medium | E0-02；gates: 无 | `tests/a2_kedro/acceptance/test_v0_01.py` | DAG Graph 测试：验证 extract/parse/normalize/zone/native/filter/group/semantic save 全由 Kedro 依赖连接 |
| V0-02 (20m) | independent-qa-owner / medium | C0-00；gates: 无 | `tests/a2_kedro/acceptance/test_v0_02.py` | 原 A1 20 Spider/13 Task15 scenarios/28 gates 的源代码不动，单独跑只读兼容检查 |
| V0-03 (20m) | independent-qa-owner / medium | E0-11；gates: 无 | `tests/a2_kedro/acceptance/test_v0_03.py` | A1 release/selection/ordinal/role/byte digest：七 stream、历史 baseline 和多 occurrence |
| V0-04 (20m) | independent-qa-owner / medium | P2-09, T0-11；gates: 无 | `tests/a2_kedro/acceptance/test_v0_04.py` | MIME/PDF/Word/Excel/JSON/HTML 和 span/limitation golden，独立 gold reviewer |
| V0-05 (20m) | independent-qa-owner / medium | P3-09, T0-11；gates: 无 | `tests/a2_kedro/acceptance/test_v0_05.py` | 关系/规则/分组异常：无法归属、跨 scope、重复 ID、source-native context |
| V0-06 (20m) | independent-qa-owner / medium | P1-12b, E0-05；gates: 无 | `tests/a2_kedro/acceptance/test_v0_06.py` | async cancel、CPU/GIL、parser cgroup、child cleanup、max RSS、无 orphan、无 writer after claim expiry |
| V0-07 (25m) | independent-qa-owner / medium | C0-11d, E0-12；gates: 无 | `tests/a2_kedro/acceptance/test_v0_07.py` | 数据库迁移 v2/3/4→v5、旧结构/trigger/占用表/legacy hash 拒绝、失败原子回滚 |
| V0-08 (20m) | independent-qa-owner / medium | C0-20c, E0-12；gates: 无 | `tests/a2_kedro/acceptance/test_v0_08.py` | 完整 v2 acceptance/receipt/held-index、conflicting SHA/attempt、并发和 late crash 恢复 |
| V0-09 (20m) | independent-qa-owner / medium | E0-09；gates: 无 | `tests/a2_kedro/acceptance/test_v0_09.py` | A3/A5 老数据加载、新输入 typed 适配、限制贯穿，历史不重写 |
| V0-10 (20m) | independent-qa-owner / medium | I0-06；gates: 无 | `tests/a2_kedro/acceptance/test_v0_10.py` | Prefect hint 丢失/重复/partial failure、cursor 不漂移、pending backpressure |
| V0-11 (20m) | independent-qa-owner / medium | V0-11a, E0-12；gates: 无 | `tests/a2_kedro/acceptance/test_v0_11.py` | Python 3.12/3.13/3.14、Pi aarch64 和 x86/Linux、Mac/Windows smoke；不能把 `-O` synthetic 冒充全量 |
| V0-11a (20m) | ci-workflow-single-owner / medium | C0-00；gates: 无 | `.github/workflows/ci.yml` | `.github/workflows/ci.yml` 中增加/确认 Linux x86_64 真实 runner + wheel/pytest targeted gate；原 CI 仅 ARM Linux + Mac/Windows |
| V0-12 (20m) | independent-qa-owner / medium | E0-12, F0-09；gates: F0_PRODUCTION_ADMISSION | `tests/a2_kedro/acceptance/test_v0_12.py` | GitHub 全部必需 checks：`ruff check` / `ruff format --check` / Pyright / pre-commit / gitleaks / pytest / cgroup-v2 / whe |
| V0-15 (20m) | independent-qa-owner / medium | E0-12, P1-12b；gates: 无 | `tests/a2_kedro/acceptance/test_v0_15.py` | **保留 D4 V13**：完全相同 A1 frozen Workset 在相同 Pi / supported host 下测 old vs new 的 wall/RSS，超过 10% 的实质回归需查明并复审（绝对量可忽略情形记录证 |
| V0-16 (20m) | independent-qa-owner / medium | E0-12, P1-13；gates: 无 | `tests/a2_kedro/acceptance/test_v0_16.py` | **保留 D4 V14**：计数 Kedro 图依赖、bridge/adapter、图外控制器分支/LOC，禁止重建第二套自制 A2 ETL 调度器 |
| V0-17 (20m) | independent-qa-owner / medium | I0-06, E0-12；gates: 无 | `tests/a2_kedro/acceptance/test_v0_17.py` | **保留 D4 V16**：按原 D4 [AUTO-01–AUTO-25] 全部单独执行，尤其 missing wakeup、held-only、postcommit、CVE 和 history cutover |
| V0-13 (20m) | independent-qa-owner / medium | F0-08, P1-11；gates: 无 | `tests/a2_kedro/acceptance/test_v0_13.py` | 无新增 CVE ignore/telemetry、未授权网络、隐私 canary；完整锁及版本 hash 审计 |
| V0-14a (20m) | independent-reviewer / high | V0-01, V0-02, V0-03, V0-04, V0-05, V0-06, V0-07, V0-08, V0-09, V0-10, V0-11, V0-11a, V0-12, V0-13, V0-15, V0-16, V0-17；gates: 无 | `docs/notes/a2-v2-independent-review-r1.md` | 独立 reviewer 对生产代码和边界的 exact-SHA 一轮只读验证；保留初始 REVISE 原文 |
| V0-14b (20m) | independent-reviewer / high | V0-14a；gates: 无 | `docs/notes/a2-v2-independent-review-r2.md` | 独立 reviewer 对可复现 test/CI/安全/性能/自动触发矩阵核验，分工与作者独立 |
| V0-14c (20m) | independent-reviewer / high | V0-14b；gates: 无 | `docs/notes/a2-v2-final-go-no-go.md` | 汇总两个只读 reviewer + 必须通过的 CI/owner decisions，在确切 SHA 归档正式 GO/NO-GO，而非每阶段本人签字 |
| R0-01 (20m) | release-integration-owner / medium | V0-14c；gates: 无 | `docs/notes/a2_v2_r0_01.md` | 归档旧 A2 Git SHA、历史 schema/compat fixture、行为负面测试并检查最新 A3 reader，确定临时双读范围 |
| R0-02 (20m) | release-integration-owner / medium | R0-01；gates: 无 | `docs/notes/a2_v2_r0_02.md` | 只读 audit 旧 pending Workset 必须清零，另审计旧 held-only 曾被标为 COMPLETE 的历史，不得将其当成新正确 receipt |
| R0-03 (20m) | release-integration-owner / medium | R0-02, I0-09；gates: 无 | `docs/notes/a2_v2_r0_03.md` | **切换前**校验 DB 备份/恢复演练、旧 schema4 binary 与新兼容 binary 的开关、迁移 runbook；不能仅靠 git revert |
| R0-04 (20m) | release-integration-owner / high | R0-03, I0-10；gates: OWNER_EXPLICIT_CUTOVER_APPROVAL, STAGED_DB_BACKUP_AND_OLD_PENDING_ZERO | `docs/notes/a2-v2-r0-schema-activation-receipt.md` | 收到用户明确迁移/安全/cutover 授权后在维护窗口执行显式 schema/producer binding 操作，保持单一 A2 dispatch |
| R0-05 (20m) | release-integration-owner / medium | R0-04；gates: 无 | `docs/notes/a2_v2_r0_05.md` | 小范围 source/stream/consumer 验证 read-only status、结果/A3 限制、无失败回退再决定扩展；无产出证明不放大 |
| R0-06 (20m) | release-integration-owner / high | R0-05；gates: 无 | `msgloom/preparation_pipeline/handler.py`, `msgloom/preparation_pipeline/scheduled.py` | 确认 v2 成功且旧 Handler 不再生产后，按依赖扫描删除 legacy RecordSteps/StageSteps/旧 dispatch 冗余实现，保留原历史测试/数据 |
| R0-07 (20m) | release-integration-owner / medium | R0-06；gates: 无 | `docs/notes/a2-v2-r0-merge-cleanup-audit.md` | GitHub required checks / 历史 A3/A5 regression 后单 owner 合并与只清理已合并、无将来用途 worktrees/远程分支 |
| R0-08 (20m) | release-integration-owner / medium | R0-07；gates: 无 | `docs/notes/a2_v2_r0_08.md` | Final acceptance index：代码/迁移/CI/安全决定/回滚演练/自动 Prefect 状态，确认不再长期双引擎或后台假作业 |

## 派发前不可省的动作

1. 必须由 Manager 真实检查 task 的全部 `depends_on` exact SHA 验收结果及 required_gates；任务文档不自动授权。
2. 只分配 `edit_paths` 拥有的文件。其他子 Agent 对相同文件的写入必须排队；Git worktree 和 remote branch 不得相互覆盖。
3. 输入是冻结源码和计划中对应的 typed shape；输出既要有可复现的成功用例，也要有负面测试、实际退出码和 commit SHA。
4. 安全风险、A1 权威、生产数据库迁移、最终 Prefect/engine 切换必须由用户明确决定，不接受 Agent 自签。
5. 任务结束后无真实 PID/job/持续任务则写 STOPPED，不能暗示后台开发仍在继续。

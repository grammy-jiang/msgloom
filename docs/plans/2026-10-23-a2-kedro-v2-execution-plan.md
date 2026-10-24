# msgloom A2 v2 — 全量实施、并行任务与验收计划

> **状态：仅供讨论与批准的执行蓝图。** 本文件不表示任何本地 Task Manager 已启动，也不授权修改生产部署。
> 目标环境：Raspberry Pi 5 上的 msgloom Git worktrees；可选 Sextant 仅在真实工具与仓库/凭据前置验证通过后使用。
> 关联：[完整架构设计](2026-10-23-a2-kedro-v2-architecture.md)、[Supervisor/Agent 执行协议](2026-10-23-a2-kedro-v2-agent-handoff.md)。
> 用户偏好：中文沟通、CLI/远程无头执行、Claude Code Task Manager + 子 Agent 并行、避免无意义询问、任务尽量 ≤30 分钟、按复杂度选模型与 thinking effort、明确停止/运行状态。

## 0. 进度基线及可核实状态

| 阶段 | 当前判定 | 证据 / 剩余事项 |
| --- | --- | --- |
| A1 | **冻结、已接受** | 原 Task15 28/28，SHA `34057c6c9f85688fd2bd1868d90302ab5a61205f`；不再改 A1 |
| D0–D4 Kedro 主架构 | **设计 ACCEPT** | [PR #68](https://github.com/grammy-jiang/msgloom/pull/68)，R6 ACCEPT 于 `878121fa9ab7ca35754b36d824440a77e92f5f4d`；草稿未合并 |
| Q0 Kedro 1.7 Pi synthetic | **隔离 ACCEPT** | [PR #69](https://github.com/grammy-jiang/msgloom/pull/69)，R2 ACCEPT 于 `5f1050a4939f1ec44e3326df10d83fc686f72721`，Python 3.12/13/14 × 普通和 `-O` 共 120 条检查，CI 10/10；**不等于生产安全验收** |
| F0 依赖、安全和共装 | **OPEN** | Kedro 1.7.0 版本路径 guard 的 exact wheel 证据已采集，但 Snyk CVE-2026-3840 仍与上游公告冲突；完整项目共装、可达性、安全决策未完成 |
| C0 研究 | **R1 REVISE** | [PR #70](https://github.com/grammy-jiang/msgloom/pull/70)，研究 SHA `0eb8fe6d2e5d301c359b60292c1852bbe7558c6d`，19/19 本地测试；第一轮审查五个 P1；该 commit GitHub CI 9/10（Pyright 九个类型错误）；Pi 工作区已有**未提交**局部整改 |
| C0 生产契约冻结 | **NOT STARTED / NO-GO** | 正式 Pydantic/Codec、schema v5 候选迁移、A2-acceptance + receipt/held 表、真实 roots/claims、A3 reader 尚未实现和验收 |
| P1 / P2 / P3 / T0 | **尚未正式启动** | Kedro 生产 DAG / parser/zones / relations/rules/grouping / 独立黄金集 |
| E0 / I0 / V0 / R0 | **尚未正式启动** | 全链路/交易与 A3、Prefect 触发、全矩阵验证、旧 A2 退役 |
| 本地任务状态 | **无专用持续运行的 C0 Task Manager** | 不能将远程常驻 Claude/Codex 服务视为 C0 子 Agent 正在工作 |

**唯一推荐路线：** F0 与 C0-R1（CR）非生产研究并行。CR R2 通过后可以继续 **Kedro-free C0 合同/SQL 候选**，甚至无 Kedro 依赖的纯 P2/P3 fixtures；但不得称其生产冻结，也不得合并、运行生产 Kedro，直至安全 F0 gate 与新持久化/receipt gate 均成立。F0 缺乏修复结论不应阻塞离线纯逻辑研究，但绝不代表隐含安全豁免。

### 0.1 Gate 有向无环图及 F0 准入定义

```text
A1 ACCEPT -> D4 R6 ACCEPT -> Q0 synthetic ACCEPT
                          |
               +----------+-----------+
               |                      |
          CR R1 fixes/R2      F0: independent security/co-install
               |                      |
               v                      | [F0-08 peer review; owner risk
        C0 schemas + SQL             |  disposition still required]
        design/prototype              |
        (Kedro-free)                  |
               |                      |
               +----------+-----------+
                          v
      C0 v2 proof + migration design exact SHA / provisional freeze
               |                 |
               |                 +--> P2/P3 pure fixtures / T0 independent gold
               |                         (can begin earlier, not ship)
               v
      F0 OWNER-APPROVED PRODUCTION ADMISSION
      + C0 FINAL code/contracts/migration acceptance
               |
        P1 actual Kedro main DAG + P2/P3/T0 production integration
               |
               v
        E0 -> I0 staging -> V0 all checks including V13–V16
               |
      explicit user cutover/migration authorization
               |
               v
        R0 controlled schema migration/dispatch, then retire old A2
```

**F0 review acceptance** = F0-01..08 完整证据、独立 reviewer 对 exact wheel/可达性/共装 tests 的判定；若剩余 Snyk 风险，不能仅用技术 reviewer `ACCEPT` 替代 owner 的安全决定。**F0 production admission** = 上述技术门禁通过、可接受的依赖/CI 方案，以及用户对无法排除的安全残余风险作出的明确决定。F0-09 仅准备依赖 PR，F0-10 在受审查锁文件与共装 CI 通过后，才可提交正式合并决策，不预授权合并。

**C0 provisional freeze** = 可以用不依赖 Kedro 的纯 A2 契约、数据模型和 SQLite 临时测试稳定字段名；**C0 final freeze** = F0 生产准入 + 对真实 A1 Workset/Claims 的 v2 receipt/finalizer、正式迁移方案、A3 triage_input@2 兼容、独立 exact-SHA review 全部通过。允许在实测 parser/DAG 反馈后通过明确版本增量修订 *provisional* 协议；已发布结果的 wire version 不能静默改写。

资源预算是一项**任务拆分约束而非完成时间承诺**：全计划 169 项细分任务，确切数量和关键路径随 R1 回归及安全决策变化；预计 serial risk chain 为 `CR→C0 DB+finalizer→Kedro E0→V0→owner cutover`，F0 安全在前半段并行但其 owner decision 可使全线暂停。Manager 不得依据表内 20m 累加后向用户承诺交付时刻。

### 0.2 直接可执行的任务依赖 DAG

另附 [169 项人类可读任务 DAG](2026-10-23-a2-kedro-v2-task-dag.md) 与 [机器可读任务清单](2026-10-23-a2-kedro-v2-task-manifest.json)：169 条独立 task，每项含 `id`、`depends_on`、`edit_paths`、`required_gates`、`timebox_minutes`、model/effort、预计拆分窗口及需要验证的明确产出。清单所有内部依赖已经完成无环检验；`gate:...` 是需经授权或 CI 验收的**外部门禁**，不是可以自动划成完成的普通任务。

每项以 ≤25 分钟**拆分目标**估计，而非用户可依赖的完成时间承诺。一个所有者拥有一组精确文件；多个 task 对同一路径、目录通配符或 central schema 的写入必须序列化。新包名/路径只是建议实施位置，不能声称已存在。Manager 把 task 映射成单人 owner 的绝对路径、branch 和 SHA 后才可调度。

临界路径包含：`CR-10 → C0-00 → C0-11a–d / C0-12a–d / C0-14a–d → C0-20c → P1-13 → E0-12 → I0-07 → V0-14c → user cutover`。F0 可与 CR/C0 provisional 研究并行，但任何 unresolved owner security gate 可延缓后续正式 Kedro dependency/cutover。测量任务 `P1-12b`、`P2-10`、`V0-15` 必须取得 Pi 独占性能测量锁。

## 1. Task Manager 的必需运行方式

### 1.1 角色、模型与 effort（正式启动前只作计划）

| 角色 | 推荐选择 | 理由与限制 |
| --- | --- | --- |
| Supervisor（当前聊天/监督者） | 以当前会话实际可用模型为准；审查和质量验收 | 审阅任务 DAG、失败、预算、PR/CI 证据；不虚称后台运行 |
| 本地 Task Manager | Claude Code **Sonnet / High**（如实际 CLI 支持该 effort） | 任务分解、依赖调度、冲突仲裁、及时自动恢复、验收门禁归档；不亲自持有所有文件 |
| 通用 coding worker | Claude Code **Sonnet / Medium** | 一个封闭任务/一份文件所有权/一个针对性测试；不滥用 High |
| SQL/security/async 关键 worker | Claude Code Sonnet / High | migration、CVE、claim/commit/cancel、A3 version boundary |
| 机械校验/fixture worker | 实际 CLI 已安装的轻量模型（如果已核实可用）或 Sonnet / Low | 仅无架构裁量的 lint/fixtures/docs 小改动；未验证模型不自动假设可用 |
| 独立 Reviewer | 与实现者不同的 Claude Code Sonnet / High 或可用的 Codex / Medium-High | 必须只读 exact SHA；同一 Agent 不能自我签署 ACCEPT |

不使用 Opus 作为默认资源；优先选择用户确认的 Sonnet 方案。Codex 实际支持的 model/effort 必须在该机器上查询后选，不假设任何过期或未来专用型号一定可用。

### 1.2 并发策略与所有权

- `max_workers` 是运行时配置项，不写死。**Pi 先建议 2 个真实 CPU/IO heavy workers + 1 个轻量 review/fixtures workers**；随 measured RSS、load、token 和 API 429 调整，并非保证吞吐。
- 真正可并行的任务使用 **不同 git worktree/branch + 不重叠的代码文件所有权**。单一 integration manager 负责 rebase/merge、schema 文件、`pyproject.toml`/`uv.lock`、GitHub workflow、最终 A3 接口整合，避免并发写同一锁文件。
- 每个 worker 只取得：明确目标、必须读的少数源文件、允许编辑路径、不可编辑路径、完整负例、预算、完成标准和 commit/PR 返回协议。
- 独立 reviewer 必须对一个不可变精确 SHA，只能读；一旦代码变化，必须重新出具新 SHA 审查。每一次 REVISE 保留原文档，不覆写历史。
- 经理自行处理普通 import、格式、测试失败、branch rebase、工具临时不可用、子 Agent 失败再试；**安全残余风险接受、改变 A1 权威、真实数据/凭据操作、生产 cutover 才升级给用户**。
- 长任务分割为估计 **10–25 分钟内**可完成的小项。一个任务超过 30 分钟时，经理拆为新的子项，记录阻塞原因，不催生无限重试或无界长 prompt。

### 1.3 用户最关注的运行状态诚实性

任意一次 `Status` 查询必须重新检查：本地 worker PID/job ID、状态、worktree 和 Git SHA、最近 heartbeat/日志、GitHub PR/CI、当前失败项。报告 `RUNNING / QUEUED / BLOCKED / COMPLETED / STOPPED`，区分“远程服务常驻”与“一个任务正在做事”。如果没有活的 task process 或自动化安排，明确回答 **STOPPED**；绝不写“我会持续监控/自动推进”但事实上消息结束后没有执行者。

## 2. Wave CR — 先修复 C0-R1 的五项缺陷与 GitHub CI

独立 R1 原文保存在 C0 Pi 工作区 `docs/notes/a2-kedro-c0-independent-review-r1-20261023.txt`；受审查 SHA `0eb8fe6` 不得改名为 ACCEPT。保留已在 C0 工作区完成但**尚未提交**的局部类型修复，不得 `git reset --hard`、`git clean -fd`。

| ID / 估时 | Depends on | 依赖和文件所有权 | 具体改动 / **必须通过的测试** | 模型 | Owner files / worker |
| --- | --- | --- | --- | --- | --- |
| CR-01 / 15m | 无 | R1 文档审阅；`docs/plans/2026-10-23-a2-kedro-c0-contract-candidate.md` | 正确陈述旧 `intake_completion.py` 对 held-only **可能 COMPLETE** 且 aggregate 未强制纳入 `workset.held`；写清是新 v2 policy change，不能改 A1 | Sonnet High | `docs/plans/2026-10-23-a2-kedro-c0-contract-candidate.md`; Sonnet / high |
| CR-02 / 20m | 无 | C0 prototype tests | 修正三项由于 `model_dump()` + strict dataclass dict 导致的假阳性；用有效 instance/`model_validate_json`，逐个验证 extra field、stage XOR、policy version 等实际被测 predicate | Sonnet Medium | `tests/research/test_c0_contract_prototype.py`; Sonnet / medium |
| CR-03 / 20m | 无 | C0 fixture/test | 生成两个不同 ReleaseEntry occurrence 但指向相同 ResultRef 的结构合法 Workset，验证 `selection_refs` 去重、receipt 仍要求两个结果；注明真实 A1 hash 含 entry，正常不会生成该冲突，纯防御案例 | Sonnet Medium | `tests/research/test_c0_contract_prototype.py`; Sonnet / medium |
| CR-04 / 20m | 无 | C0 docs/security | 明确研究索引绕过旧 plan 的真因是 claim key **不以 `prepare:` 开头**；空 `required_inputs` 是另一个缺口。逐项列出未验证的 status/limitations、upstream refs、attempt vs claim、workset scope、batch transition identity、kind/version 允许表、同步 facade 绕过 | Sonnet High | `docs/plans/2026-10-23-a2-kedro-c0-contract-candidate.md`; Sonnet / high |
| CR-05 / 15m | 无 | Native A1 test + doc | 目前错误 candidate 只触发 `not in workset`。增加“Workset 内已选 root 但 ordinal/key 不一致”、“已保存 selection 内容不同”的真实负例，或明确降级宣称；不篡改真实 A1 | Sonnet Medium | `tests/research/test_c0_native_a1_exact_handoff.py`; Sonnet / medium |
| CR-06 / 15m | 无 | Pyright | 逐个修复 CI 9 项 可空 `SemanticDataRef` / 可选 selection/batch 访问，显式 guard + `pytest.fail`，**不能加 ignore/type: ignore 规避** | Sonnet Medium | `tests/research/test_c0_atomic_acceptance.py`, `tests/research/test_c0_phase1_storage_integration.py`, `tests/research/test_c0_contract_prototype.py`; Sonnet / medium |
| CR-07 / 20m | CR-02, CR-03, CR-05 | Python tests & docs | 把 “Expected C0 test condition at line N” 换为真实断言说明；避免过短 3 秒 lease 在高负载 Pi 形成 flake；准备重复测试 x3 | Sonnet Low/Medium | `tests/research/test_c0_contract_prototype.py`, `tests/research/test_c0_phase1_storage_integration.py`; Sonnet / medium |
| CR-08 / 20m | 无 | Research prototype + docs | 在文档明确 `_store` private + `asyncio.to_thread` 取消不受保护、large semantic decode 在 writer lock 内、临时 SQL `create_all` 仅供实验，不允许移植至生产；强化不相同 claim-key 的并发测试描述 | Sonnet High | `docs/plans/2026-10-23-a2-kedro-c0-contract-candidate.md`; Sonnet / high |
| CR-09 / 20m | CR-01, CR-02, CR-03, CR-04, CR-05, CR-06, CR-07, CR-08 | 单人集成 owner | 针对性 pytest、Ruff/format、Pyright（实际 CI 同命令）、pre-commit/gitleaks。只归入与 CR 相关文件；保留审查报告与变更 SHA | Sonnet Medium | `docs/notes/a2-kedro-c0-r2-qualification.md`; Sonnet / medium |
| CR-10 / 20m | CR-09 | Reviewer | 独立只读 R2 exact SHA → `ACCEPT` 才关闭研究门禁；有 REVISE 则新 CR-N 任务，不自动称 production C0 ready | Sonnet High | `docs/notes/a2-kedro-c0-independent-review-r2.txt`; Sonnet / high |

**先决验收：** GitHub PR #70 当前 9/10，其中唯一失败是 Pyright；修复后必须重新触发 PR 的完整质量矩阵，**所有 required checks 通过**。本地 19/19 不替代 GitHub Pyright。CR-01/04/08 同属文档文件，必须串行合并或由一个文档 owner 一次完成；CR-02/03/05/06 的测试文件也必须以 worktree ownership 避免写冲突。

## 3. Wave F0 — Kedro 1.7 安全与依赖资格（与 CR 同步）

| ID / 估时 | Depends on | 输入、操作和目标证据 | 验收与 Stop 条件 | 模型 | Owner files / worker |
| --- | --- | --- | --- | --- | --- |
| F0-01 / 15m | 无 | 再核对 PyPI Kedro 1.7 wheel（SHA `488701a27c7d595b62a611cb23596953a9929fe5cc42a376c28abe26654c2438`）、源码版本、当前 Pi py312/313/314 环境和 Q0 矩阵 | 来源日期、可重跑 wheel hash；不能无核验更换候选版本 | Sonnet Medium | `docs/notes/a2-kedro-f0-version-provenance.md`; Sonnet / medium |
| F0-02 / 25m | F0-01 | 独立看 GHSA-6326、CVE-2026-35167、CVE-2026-3840、Snyk + 当前 source `_get_versioned_path/_is_unsafe_version`，建立 method/API reachability matrix | 明确“上游报告已修复”和“Snyk 仍报告受影响”的**未决差异**；不推出无依据的安全结论 | Sonnet High | `docs/notes/a2-kedro-f0-cve-reachability.md`; Sonnet / high |
| F0-03 / 20m | F0-01 | 静态 Dataset allowlist：禁用 Kedro CLI、`DataCatalog.from_config`、`load_versions`、versioned FS datasets、动态插件；环境和代码测试 | malicious `../` / absolute、unknown dataset、untrusted import/PII 不落日志；生产代码门禁可实现 | Sonnet High | `docs/notes/a2-kedro-f0-dataset-security.md`; Sonnet / high |
| F0-04 / 20m | F0-01 | telemetry：`kedro-telemetry` 强制依赖，真实 plugin consent 与 programmatic hooks，stderr/stdout import、socket/real network deny 控制 | 不只是 null plugin 假测试；任何未预期网络/标识上传则 STOP | Sonnet High | `docs/notes/a2-kedro-f0-telemetry-networks.md`; Sonnet / high |
| F0-05a / 20m | F0-01 | 仅 scratch lock 包，共装完整 `msgloom+Kedro` wheel（不改生产锁） | 依赖树精确 delta、wheel SHA、版本保持；不得运行 sdists build 作为研究探测 | Sonnet Medium | `docs/notes/a2-kedro-f0-linux-wheel.md`; Sonnet / medium |
| F0-05b / 20m | F0-05a | Pi aarch64 Python 3.12/3.13/3.14 scratch install | 各自 `uv pip check`、Kedro+msgloom imports、Pyright/target tests；保留原始退出码 | Sonnet Medium | `docs/notes/a2-kedro-f0-coinstall.md`; Sonnet / medium |
| F0-05c / 20m | F0-05b | 真实项目 wheel/sdist 和 source-boundary tests | 依赖、wheel、tests 可复现；若安装引入已有包升级停止并写风险报告 | Sonnet High | `docs/notes/a2-kedro-f0-types-tests.md`; Sonnet / medium |
| F0-06 / 20m | F0-05b | Linux x86_64 和 Mac/Windows portability smoke（通过 CI matrix/配置，不要求物理 GUI） | 有真实 runner 或明确 NOT TESTED；不把 Pi 验证冒充全部平台 | Sonnet Medium | `docs/notes/a2-kedro-f0-portability.md`; Sonnet / medium |
| F0-07 / 15m | F0-02, F0-05b | Audit 策略：记录原有 `PYSEC-2017-83`、`GHSA-8pqf-f4m5-798g` 的受审查 CI policy；新 Kedro CVE 不添加隐性 ignore | baseline 与 candidate 的新增漏洞 delta 可复现；保留 non-green 的原始无忽略审计证据 | Sonnet High | `docs/notes/a2-kedro-f0-audit-baselines.md`; Sonnet / high |
| F0-08 / 20m | F0-02, F0-03, F0-04, F0-05c, F0-06, F0-07 | 安全 reviewer 独立 R1/R2，冻结精确 SHA、真实风险适用性与操作决策候选 | reviewer ACCEPT 对象仅限可复现评估；如仍不能排除 residual risk → 用户安全决定/STOP | Sonnet High | `docs/notes/a2-kedro-f0-independent-review.md`; Sonnet / high |
| F0-09 / 20m | F0-08; gates: F0_PRODUCTION_ADMISSION | lock 单人 owner 制定候选生产依赖 PR（先草稿，不改 master）与门禁说明 | owner security signoff、共装跨版本 CI 和回滚计划齐备才申请合并；默认保留 Draft | Sonnet Medium | `docs/notes/a2-kedro-f0-dependency-admission.md`; Sonnet / medium |
| F0-10 / 20m | F0-09; gates: F0_PRODUCTION_ADMISSION | 单一依赖/锁文件 owner | 精确版本和 wheel hash、锁文件、Python/CI、owner signoff 后引入 Kedro 正式依赖；不得更改既有安全 ignore 或直接合并 master | Sonnet High | `pyproject.toml`, `uv.lock`; Sonnet / high |

**新观察到的依赖审计变化（2026-10-24，CI run 39979506772，质量任务 120502768333）：** 原 `Brotli==1.2.0` 报出 `PYSEC-2026-4322`，`brotlicffi==1.2.0.2` 报出 `PYSEC-2026-4323`；审计报告的目标修复版本分别为 1.2.1 / 1.2.1.0。这使文档 PR 的质量检查也失败，属于随时间变化的现有 lock 安全阻塞，**不是文档本身的语法失败**。F0-07 必须登记新公告，依赖 owner 决定独立修复/完整回归；不能添加 ignore 冒充 CI 全绿。此前 Q0 原始审计只看到两项已知基线问题，不可据此否认新公告。PR #71 的当前 CI 最终状态应以每次真实查询为准。\n\n安全残余风险是明确的人为审批点。Agent 不能替用户签署安全豁免。即便 F0 风险被接受，也不能绕开 C0 事务/receipt 证明。F0-05 可以在 scratch 环境与 CR 任务并行，F0-09 不会未经同意提交运行时依赖。

## 4. Wave C0 — 生产契约、持久化与 A3 adapter 设计冻结

CR 研究 R2 ACCEPT 后，可启动 **Kedro-free C0 候选实现**；F0 安全风险未解决时仍可做纯合同/临时 DB 研究，但不能合并正式 Kedro 依赖或宣称生产 C0 通过。先执行 C0-00 字段/版本 provisional freeze，最后通过 F0 production admission + C0-20c 才能 final freeze。任务表的估时是单个产出设计限额；若某项确实需要更长，则先拆为子 task 再开工，不能一次让 Agent 实施多日范围。

| ID / 估时 | Depends on | 拥有文件/接口 | 具体落地和验收 | Owner files / worker |
| --- | --- | --- | --- | --- |
| C0-00 / 15m | CR-10 | `docs/decisions/a2-v2-schema-ids.md` + minimal golden (contract owner) | 冻结 provisional kind/version/field-name/size/role/transition batch/triage_input@2 header；其后 worker 不可自由自定义不兼容 wire 格式 | `docs/decisions/a2-v2-schema-ids.md`; Sonnet / medium |
| C0-01 / 20m | C0-00 | `msgloom/a2_kedro/contracts/source.py`，A1 verifier adapter | FrozenSourceSelection：entry/workset 及 approved baseline 的互斥结构、occurrence index/ordinal/role、saved SHA、scope；拒绝 forged hash/role | `msgloom/a2_kedro/contracts/source.py`, `tests/a2_kedro/test_c0_01.py`, `msgloom/a2_kedro/__init__.py`, `msgloom/a2_kedro/contracts/__init__.py`; Sonnet / medium |
| C0-02 / 20m | C0-01 | `msgloom/a2_kedro/source_resolution.py` | 使用精确 ReleaseReader 重新验证 ordinal/byte equality；component/context/transition-only + global sequence gaps；源读取错误 typed A2-held | `msgloom/a2_kedro/source_resolution.py`, `tests/a2_kedro/test_c0_02.py`; Sonnet / medium |
| C0-03 / 20m | C0-00 | `msgloom/a2_kedro/contracts/extract.py` | ExtractedComponents：primary/alternate/attachment/embedded 保存引用、digest、missing/partial/unsupported，有限 metadata codec | `msgloom/a2_kedro/contracts/extract.py`, `tests/a2_kedro/test_c0_03.py`; Sonnet / medium |
| C0-04 / 20m | C0-03 | `msgloom/a2_kedro/contracts/parse.py` | ParsedParts：part/page/sheet/cell 和 parser worker receipt，断言 actual-format 和 byte source link | `msgloom/a2_kedro/contracts/parse.py`, `tests/a2_kedro/test_c0_04.py`; Sonnet / medium |
| C0-05 / 20m | C0-04 | `msgloom/a2_kedro/contracts/zones.py` | NormalizedContent / ContentZones，原始 span 精确映射及 quote-occurrence vs quote-author；不可逆限制 | `msgloom/a2_kedro/contracts/zones.py`, `tests/a2_kedro/test_c0_05.py`; Sonnet / medium |
| C0-06 / 20m | C0-00 | `msgloom/a2_kedro/contracts/relations.py` | NativeRelations：回复/祖先/引用假设的 typed scope；unknown/cycle/duplicate 负例 | `msgloom/a2_kedro/contracts/relations.py`, `tests/a2_kedro/test_c0_06.py`; Sonnet / medium |
| C0-07 / 20m | C0-05, C0-06 | `msgloom/a2_kedro/contracts/results.py` | prepared@2、filter_result@2、group_result@2 和 manifest；all-matched-rules，分组无跨作用域静默连接 | `msgloom/a2_kedro/contracts/results.py`, `tests/a2_kedro/test_c0_07.py`; Sonnet / medium |
| C0-08 / 20m | C0-00 | `msgloom/a2_kedro/contracts/transition.py` | scoped transition batch identity 绑定 Workset Ref + **每条 exact fact ID/scope/kind/authority** 的完整有序列表及 code/policy；单项事实证明和批次身份均不可丢 | `msgloom/a2_kedro/contracts/transition.py`, `tests/a2_kedro/test_c0_08.py`; Sonnet / medium |
| C0-09 / 20m | C0-01 | `msgloom/a2_kedro/contracts/held.py` | a2_input_disposition@1 和显式 repair_class；held-only、context-only、approved baseline 并不强制做 body | `msgloom/a2_kedro/contracts/held.py`, `tests/a2_kedro/test_c0_09.py`; Sonnet / medium |
| C0-10 / 20m | C0-07, C0-08, C0-09 | `msgloom/a2_kedro/contracts/receipt.py` | a2_completion_receipt@2 **结构完整性**；同一 frozen occurrence 恰好一份结果，intake-held 强制 INCOMPLETE | `msgloom/a2_kedro/contracts/receipt.py`, `tests/a2_kedro/test_c0_10.py`; Sonnet / medium |
| C0-11a / 20m | C0-00 | `msgloom/persistence/schema_store.py` / new schema model (DB owner) | 原 schema4 digest/revision/legacy DDL 先做 pinned 迁移方案，比较 schema-main-version vs metadata revision；显式 operator gate，不准 open 自动建表 | `docs/decisions/a2-v2-schema-migration.md`; Sonnet / high |
| C0-11b / 20m | C0-11a | `msgloom/persistence/a2_schema.py` (DB owner) | 精确 A2 受约束 DDL、FK/index/unique/size bounds 与 versioned producer marker；依赖 C0-11a 审阅 | `msgloom/persistence/a2_schema.py`, `tests/a2_kedro/test_c0_11b.py`; Sonnet / high |
| C0-11c / 20m | C0-11b | `msgloom/persistence/schema_store.py` + migration CLI (DB owner) | 普通 Phase1Store.open 同时兼容旧/新但绝不自动升级；显式 maintenance CLI + schema version activation，回滚预案 | `msgloom/persistence/schema_store.py`, `msgloom/cli/a2_schema_migration.py`, `tests/a2_kedro/test_c0_11c.py`; Sonnet / high |
| C0-11d / 20m | C0-11c | `tests/persistence/test_a2_schema_migrations.py` | v2/v3/v4→新 revision、错误表名/索引/触发器、DDL 失败回滚、旧 binary 拒新结构时备份恢复 | `tests/persistence/test_a2_schema_migrations.py`; Sonnet / medium |
| C0-11e / 20m | C0-11c | 兼容阶段真实数据测试 | schema4 的现有 Phase1Store.open 不得修改表或版本；显式迁移必须有受审查命令及 A1/CLI 开库冒烟测试 | `tests/persistence/test_a2_compat_open.py`; Sonnet / high |
| C0-12a / 20m | C0-00 | `msgloom/persistence/a2_acceptance_models.py` | closed kind/version allowlist + input-only logical key / StageResult metadata SHA / payload sha 长度、旧 prepared@1 拒绝 | `msgloom/persistence/a2_acceptance_models.py`, `tests/a2_kedro/test_c0_12a.py`; Sonnet / high |
| C0-12b / 20m | C0-11b, C0-12a | `msgloom/persistence/a2_store.py` (DB owner) | `BEGIN IMMEDIATE` 内 live claim+required_inputs+plan 验证，原始 publisher receipt 绑定，单条唯一键 insert | `msgloom/persistence/a2_store.py`, `tests/a2_kedro/test_c0_12b.py`; Sonnet / high |
| C0-12c / 20m | C0-12b | `msgloom/persistence/a2_acceptance_async.py` (DB owner) | 公开受控 async facade：写入通过现有 semaphore、cancel drain、close 机制，禁止研究版私有 _store/to_thread 直连 | `msgloom/persistence/a2_acceptance_async.py`, `tests/a2_kedro/test_c0_12c.py`, `msgloom/persistence/async_store.py`; Sonnet / high |
| C0-12d / 20m | C0-12c | `tests/persistence/test_a2_acceptance.py` | 同 key 跨 attempts 重放、不同 status/limitations/metadata sha 冲突、两个合法 claim 并发、post-commit cancel/read-back，无重复 accepted | `tests/persistence/test_a2_acceptance.py`; Sonnet / medium |
| C0-13 / 20m | C0-11b, C0-09 | `msgloom/persistence/a2_held_store.py` | 可查询 bounded A2-held index，workset-scoped，幂等冲突拒绝，用户隐私 safe status | `msgloom/persistence/a2_held_store.py`, `tests/a2_kedro/test_c0_13.py`; Sonnet / medium |
| C0-13a / 20m | C0-13, C0-12c | Held/receipt 受控 async facade | 新公开 adapter 通过 Phase1Persistence 的 bounded semaphore、cancel drain、close 安全路径；不用私有 _store/to_thread 直写 | `msgloom/persistence/a2_held_receipt_async.py`, `tests/persistence/test_a2_held_receipt_async.py`; Sonnet / high |
| C0-14a / 20m | C0-10, C0-12d, C0-13 | `msgloom/persistence/a2_receipt_store.py` (DB owner) | SQL 外 bounded receipt/source payload proof；root/基线/transition 逐项覆盖 + publisher 原始 claim history | `msgloom/persistence/a2_receipt_store.py`, `tests/a2_kedro/test_c0_14a.py`; Sonnet / high |
| C0-14b / 20m | C0-14a, C0-11c | `msgloom/persistence/a2_workset_finalize.py` / `intake_completion.py` (DB owner) | **新版本 v2 finalize**：从真实 pending Workset 在单事务里写新 receipt + 更新旧 intake_worksets terminal/status/refs，metadata-only recheck | `msgloom/persistence/a2_workset_finalize.py`, `msgloom/persistence/intake_completion.py`, `tests/a2_kedro/test_c0_14b.py`; Sonnet / high |
| C0-14c / 20m | C0-14b | `msgloom/persistence/a2_producer_binding.py` (DB owner) | v1/v2 双向 writer fence；一个 Workset 不得由 legacy+Kedro 两边同时终结；混合 attempts 的 accepted-stage history 允许，但受 v2 proof 限制 | `msgloom/persistence/a2_producer_binding.py`, `tests/a2_kedro/test_c0_14c.py`, `msgloom/persistence/intake_store.py`; Sonnet / high |
| C0-14d / 25m | C0-14c, C0-13, C0-13a | `tests/persistence/test_a2_v2_finalization.py` | held-only→terminal INCOMPLETE、pending queue 消失、v1/v2 竞争、缺 root/伪造 refs、claim 丢失与 crash between update/receipt 原子回滚 | `tests/persistence/test_a2_v2_finalization.py`; Sonnet / medium |
| C0-14e / 20m | C0-14b, C0-14c, C0-13a | v2 finalizer 的 async facade | 小型委托方法/新模块，真实 SQLite postcommit cancel 读回；原有 async_store.py 保持少于 500 行 | `msgloom/persistence/a2_finalize_async.py`, `tests/persistence/test_a2_finalize_async.py`, `msgloom/persistence/async_store.py`; Sonnet / high |
| C0-15 / 20m | C0-00 | `msgloom/a2_kedro/application_contract.py` | 公开 `async def prepare(...)`，前置输入/authority pin 检查，CancelledError/timeout/status 分类，不创建 loop | `msgloom/a2_kedro/application_contract.py`, `tests/a2_kedro/test_c0_15.py`; Sonnet / high |
| C0-16 / 20m | C0-00 | `msgloom/a2_kedro/partition_policy.py` | 有版本、有限 partition/workset scope，避免跨 Workset 不合理 merge；资源上限由 P1/P2 profiling 修正 | `msgloom/a2_kedro/partition_policy.py`, `tests/a2_kedro/test_c0_16.py`; Sonnet / medium |
| C0-17a / 20m | C0-07 | `msgloom/triage_input/` models/codec (A3 owner) | **明确新 `triage_input@2`**，v1 不能读 @2 refs；设计新 selected roles、binding/snapshot digest/part state；A3 fixture 原样历史保留 | `msgloom/triage_input/models_v2.py`, `tests/a2_kedro/test_c0_17a.py`; Sonnet / high |
| C0-17b / 20m | C0-17a | `msgloom/triage_input/codec_v2.py` (A3 owner) | 规范化编码、新 binding hash 和 prepared/filter/group@2 kind/version 白名单；strict canonical round-trip；未知版本拒绝 | `msgloom/triage_input/codec_v2.py`, `tests/a2_kedro/test_c0_17b.py`; Sonnet / medium |
| C0-17c / 20m | C0-17b | `msgloom/triage_pipeline/handler.py` + v2 adapter (A3 owner) | A3 runner 能处理 verified triage_input@2 和 prepared@2/limitations；旧 triage_input@1/PreparedRecord 仍可读，任何 lossy projection 不默许 | `msgloom/triage_pipeline/handler.py`, `msgloom/triage_input/adapter_v2.py`, `tests/a2_kedro/test_c0_17c.py`; Sonnet / high |
| C0-17d / 20m | C0-17c | `tests/triage_input/test_a2_v2_compat.py` | v1/v2 digest/parts/selected roles、A3/A5 历史与新版本 golden、partial/held 不丢失 | `tests/triage_input/test_a2_v2_compat.py`; Sonnet / medium |
| C0-17e / 20m | C0-17c | A3 io_mixin 支持 v2 | triage_pipeline/io_mixin.py 读取 prepared@2 和历史 prepared@1，以新 codec/adapter 校验来源限制 | `msgloom/triage_pipeline/io_mixin.py`, `tests/triage_pipeline/test_v2_io.py`; Sonnet / high |
| C0-17f / 20m | C0-17e | A3 plan/models 来源版本 | triage_pipeline/models.py 的 typed plan 与 A3 selection binding 接收 triage_input@2、旧 @1 不变，完整 golden | `msgloom/triage_pipeline/models.py`, `tests/triage_pipeline/test_v2_plan_versions.py`; Sonnet / high |
| C0-17g / 20m | C0-17f | A3 limitations 和 terminal proof | triage_pipeline/limitations.py 与 finalize_mixin.py 传播 INCOMPLETE、held 和原始 provenance；不改历史结果 | `msgloom/triage_pipeline/limitations.py`, `msgloom/triage_pipeline/finalize_mixin.py`, `tests/triage_pipeline/test_v2_limitations.py`; Sonnet / high |
| C0-18 / 20m | C0-15, C0-13 | `msgloom/cli/` 只读 status 类型定义 | trusted scoped progress + typed exceptions：BLOCKED source/reference/cat、busy INCOMPLETE、claim loss FAILED、held terminal | `msgloom/cli/a2_scope_status.py`, `tests/a2_kedro/test_c0_18.py`; Sonnet / medium |
| C0-19 / 20m | C0-00, C0-07, C0-08, C0-10, C0-17b | dedicated golden fixture/tests | 确保 wire field name、codec canonical bytes、SHA/ID、扩展缺失、max bytes、未知版本拒绝、历史解码不变 | `tests/a2_kedro/test_c0_schema_goldens.py`; Sonnet / medium |
| C0-20a / 20m | C0-11d, C0-12d, C0-13, C0-14d, C0-17d, C0-18, C0-19, C0-14e, C0-17g, C0-21b, C0-22, C0-11e, C0-13a, C0-16 | Integration owner | 依冻结 schema 合并 C0 codecs/sql/facade/A3，核实一个 reviewer 没有同时改其它所有者文件；运行 focused SQL 回归 | `docs/notes/a2-v2-c0-integration-audit.md`; Sonnet / medium |
| C0-20b / 20m | C0-20a, C0-02, C0-21b, C0-22 | Integration owner | 真实 A1 frozen Workset→v2 accepted-stage→terminal receipt finalizer→A3 triage_input@2 的端到端 SQLite fixture；不借用研究空 required_inputs claim | `tests/a2_kedro/integration/test_a1_workset_v2_receipt_a3.py`; Sonnet / high |
| C0-20c / 20m | C0-20b, F0-08, C0-21b, C0-22; gates: F0_PRODUCTION_ADMISSION | Independent reviewer | exact SHA C0 v2 full production contract review + required CI；此前 R2 的 research ACCEPT 不代表 final C0 ACCEPT | `docs/notes/a2-v2-c0-independent-acceptance.md`; Sonnet / high |
| C0-21a / 20m | C0-00, C0-07, C0-08, C0-09, C0-10 | 新 A2 v2 registry factory | new ResultSchemaRegistry/SemanticDataRegistry factory with explicit closed all kind@version allowlist；不得悄悄修改 phase1() 旧 codec | `msgloom/persistence/a2_registry.py`, `tests/persistence/test_a2_registry_schema.py`, `msgloom/cli/composition.py`; Sonnet / high |
| C0-21b / 20m | C0-21a | v2 registry golden 和负面测试 | 所有新增 kind/version 有严格 canonical round-trip、错误 payload/未知 schema 拒绝，旧 registry 行为不变 | `tests/persistence/test_a2_registry_compat.py`; Sonnet / medium |
| C0-22 / 20m | C0-11a, C0-12a, C0-03 | 中间 Stage 存储预算/保留政策 | per-artifact/per-workset 有限 bytes/条目数，单写入者、备份权限、PII retention 与历史兼容；安全 reviewer 审核 | `docs/decisions/a2-v2-storage-budgets.md`, `tests/persistence/test_a2_stage_budgets.py`; Sonnet / high |

**特别重要的失败类别：** 当前 C0 研究索引用 `c0-a2:` claim key，绕开旧 `prepare:` plan binding；`required_inputs=()` 另使其无真实 A1 lineage。这两个缺口必须同时关闭，不能只是把研究表接进 `schema_store`。生产版本必须只接受从可信 Workset/Reader 生成、已证明 upstream stage 的计划。

C0-11a–e、12a–d、14a–e 的 SQL 及迁移必须由一个 DB owner 受控串行整合；C0-01–10 可按独立 schema 文件并行，但必须在 C0-00 provisional header 后对接。C0-17a–g 是独立 A3 owner 的串行小步，而非单个“大改”。C0-20a–c 是唯一 final gate；C0-21a/b 的新 registry 以及 C0-22 的保留政策不可省略，不得用纯模型自证代替真实 SQLite 端到端。

### 4.1 C0 的代码体积、Registry 与 v1/v2 竞争约束

**500 行限制是硬门禁。** 当前旧 `intake_store.py` 与 `store.py` 已接近项目模块上限；C0-14b 以新 `a2_workset_finalize.py` 为主，C0-14c 仅在旧 v1 finalizer 中留下几行分流/互斥检查，其余逻辑放新模块；必须运行独立的 Python 模块行数门禁（逐个读取本轮修改的 .py，不超过 500 行）及 Ruff、Pyright；不能把 Ruff 检查误当作行数检查。`async_store.py` 也只容许小型委托，新的受控 facade 主要落在 C0-12c/C0-13a/C0-14e 各自的新模块。

**工作单生产者围栏：** A1 只完成 admission；在第一次合法 **v2 PREPARE claim acquisition** 的同一数据库事务里创建唯一工作单 producer binding，不能由 A1 写 v2 标志。旧 v1 finalizer 在数据库 writer transaction 内读到 v2 binding 时直接拒绝，反之 v2 遇到 v1-owned Workset 时拒绝。Schema4 普通打开无表则维持原 v1 行为；生产新表仅显式 schema activation 后可用。一个 Workset 只能有一个 terminal 历史。

**Codec/Registry：** C0-21a/b 建立所有新 kind@version 的可信新 registry factory；独立于历史 `ResultSchemaRegistry.phase1()` / `SemanticDataRegistry.phase1()`。在 E0-10 的单一 Composition owner 中接入该工厂和新的 v2 backend dispatch。不可在源码导入时注册动态插件或改变旧 v1 Codec。

**安全与保留：** C0-22 对 canonical stage 的 bytes/count/aggregate/retention 限制与备份读权限给出独立书面决议，C0-20c 不得在未知磁盘增长上界时验收。

### 4.2 K0–K11 至 implementation owner 的覆盖表

| Kedro 主节点 | 实现任务（代码，不是纯 contract） | 依赖 |
| --- | --- | --- |
| K0 source/role/A2-held | C0-02、C0-09、P1-03 | accepted A1 Workset、C0 root codec、受控 reader |
| K1 extract | P1-04、P2-01–06 | K0 verified saved refs、C0-03 |
| K2 parser | P1-05、P1-17、P2-11 | K1 accepted ref、static registry、sandbox child |
| K3 normalize | P2-07 | K2 accepted parsed ref |
| K4 zones | P2-08 | K3 normalized source spans |
| K5 native relations | P3-01/P3-02 | K0 released facts + K4 zone refs |
| K6 prepared@2 assembly | **P1-14** | accepted K2/K3/K4/K5 refs |
| K7 filter all-match | P3-03 | K6 accepted prepared refs |
| K8 scope grouping | P3-04/P3-05/P3-06 | K5 relations、K7 filter |
| K9 transition batch | P1-09、P3-08 | exact Workset transitions + separate claim |
| K10 result manifest | **P1-15** | all prior accepted or A2-held/transition refs |
| K11 receipt/finalize | **P1-16**、C0-14a–e | manifest, live Workset claim, v2 durable finalizer |
| Static graph factory/runner | P1-01、P1-02、P1-07 | signatures/topology may be authored before K6/K11 implementation; full DAG cannot pass P1-13 until every node is wired |
| Complete graph integration | E0-02 | P1-13, K0–K11 and P2/P3/T0 accepted outputs |

**P1-01 是拓扑和 typed Dataset 接口任务，不要求所有节点已实现；P1-18 将真实 K3/K4/K5/K7/K8 节点函数经受审查的 graph_bindings 注入 P1-01 的静态图；P1-13 则必须以真实节点执行 K0–K11 全链。** 每个阶段的持久化在自己的 Dataset.save 边完成，不允许推迟到末端 K10 的集中伪写入。

## 5. Wave P1 — Kedro Core/Dataset/async 主链

| ID / 估时 | Depends on | 源文件边界 | 必须交付 / 针对性证明 | Owner files / worker |
| --- | --- | --- | --- | --- |
| P1-01 / 20m | C0-20c, F0-10, C0-16; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `msgloom/a2_kedro/graph.py` | 完整 K0–K11 拓扑，Kedro 是全 DAG authority；不存在外部旧 Handler 绕行 | `msgloom/a2_kedro/graph.py`, `tests/a2_kedro/test_p1_01.py`; Sonnet / medium |
| P1-02 / 20m | C0-20c, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `catalog.py` | 编程方式 DataCatalog 明确封闭 dataset allowlist；拒绝未知 dataset 和动态 YAML 配置 | `msgloom/a2_kedro/catalog.py`, `tests/a2_kedro/test_p1_02.py`; Sonnet / medium |
| P1-03 / 20m | P1-02, C0-02, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `datasets/handoff.py` | ExactHandoffDataset 只读 Workset + selection + exact A1 reread，外部 URI/path 不可接受 | `msgloom/a2_kedro/datasets/handoff.py`, `tests/a2_kedro/test_p1_03.py`, `msgloom/a2_kedro/datasets/__init__.py`; Sonnet / medium |
| P1-04 / 20m | P1-03, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `datasets/evidence.py` | VerifiedEvidenceDataset 访问已签名 saved refs，SHA、边界、missing evidence 处理 | `msgloom/a2_kedro/datasets/evidence.py`, `tests/a2_kedro/test_p1_04.py`; Sonnet / medium |
| P1-05 / 25m | P1-04, P2-11, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `datasets/parser.py` | Parser request save/load 走隔离 child service，真实超时、worker termination、partial 的限制 | `msgloom/a2_kedro/datasets/parser.py`, `tests/a2_kedro/test_p1_05.py`, `msgloom/a2_kedro/parsers/registry.py`; Sonnet / medium |
| P1-06 / 20m | P1-02, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `bridge.py` | 同步 worker 到 async loop 的 bounded `run_coroutine_threadsafe`：拒绝 wrong-thread/无限待 | `msgloom/a2_kedro/bridge.py`, `tests/a2_kedro/test_p1_06.py`; Sonnet / high |
| P1-07 / 20m | P1-01, P1-06, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `runner.py` | 受控 `SequentialRunner(is_async=False)`，每个正在执行的线程和 coroutine 有 owner；repeated cancel drain | `msgloom/a2_kedro/runner.py`, `tests/a2_kedro/test_p1_07.py`; Sonnet / high |
| P1-08 / 20m | P1-06, C0-12c, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `datasets/semantic.py` | ClaimFencedSemanticDataset，发布前后均查 live token、返回 durable ref，而非原地假结果 | `msgloom/a2_kedro/datasets/semantic.py`, `tests/a2_kedro/test_p1_08.py`; Sonnet / high |
| P1-09 / 20m | P1-08, C0-08, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `datasets/transitions.py` | 单独 scoped transition claim，context refresh 不成为 message | `msgloom/a2_kedro/datasets/transitions.py`, `tests/a2_kedro/test_p1_09.py`; Sonnet / medium |
| P1-10 / 25m | P1-07, P1-08, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `resume.py` | 保存每个已接受 stage/progress；重启 read-back、跳过已验证 parse/save；冲突停机 | `msgloom/a2_kedro/resume.py`, `tests/a2_kedro/test_p1_10.py`; Sonnet / medium |
| P1-11 / 20m | P1-02, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | `security.py` / test | 无 Kedro CLI/telemetry/network、隐私安全 logging、静态 node/dataset 名 | `msgloom/a2_kedro/security.py`, `tests/a2_kedro/test_p1_11.py`; Sonnet / medium |
| P1-12a / 20m | P1-05, P1-07, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | Pi Linux delegated cgroup-v2 实验 | 原生 parser children 超时 kill/wait、CPU/GIL、无孤儿进程；不是 Q0 synthetic spin | `tests/a2_kedro/test_native_child_cgroup.py`; Sonnet / medium |
| P1-12b / 20m | P1-12a, P2-10, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | 独占 benchmark slot | 记录真实 RSS/timing/jitter/lease E/L 与 cleanup margin，禁止并发负载污染实测 | `docs/notes/a2-v2-p1-exclusive-benchmark.md`; Sonnet / high |
| P1-13 / 25m | P1-01, P1-03, P1-04, P1-05, P1-07, P1-08, P1-09, P1-10, P1-11, P1-12b, P1-14, P1-15, P1-16, P1-17, F0-10, P1-18, P2-08, P3-09; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | reviewer | 真实冻结 A1 selection → 完整 Kedro graph → durable v2 results，独立审查并要求 CI | `docs/notes/a2-v2-p1-independent-review.md`; Sonnet / high |
| P1-14 / 20m | P1-08, C0-07, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | K6 prepared@2 组装节点 | 从已接受的 Parsed/Zones/Native refs 组装 verified prepared@2 和保存节点，失败/缺失仍 INCOMPLETE | `msgloom/a2_kedro/stages/prepare.py`, `tests/a2_kedro/test_k6_prepared_node.py`, `msgloom/a2_kedro/stages/__init__.py`; Sonnet / medium |
| P1-15 / 20m | P1-14, P1-09, P1-10, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | K10 manifest 节点 | 只依赖已接受 stage refs/held/scoped transition batch 构造 immutable a2_result_manifest@1，不在外层 Handler 偷编排 | `msgloom/a2_kedro/stages/manifest.py`, `tests/a2_kedro/test_k10_manifest_node.py`; Sonnet / medium |
| P1-16 / 20m | P1-15, C0-14e, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | K11 receipt/finalize 节点 | 从 Manifest 和 frozen roots 触发真实 v2 finalizer，claim 失效或 root 缺失不得 COMPLETE | `msgloom/a2_kedro/stages/finalize.py`, `tests/a2_kedro/test_k11_receipt_node.py`; Sonnet / high |
| P1-17 / 20m | P1-05, P1-10, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | Parser 子进程前 accepted-key gate | 只有无已接受输入键才 spawn parser child；读回旧 accepted StageResult/metadata SHA 后跳过重复计算 | `msgloom/a2_kedro/stages/parse_gate.py`, `tests/a2_kedro/test_parser_resume_skip.py`; Sonnet / high |
| P1-18 / 20m | P1-01, P1-14, P1-15, P1-16, P2-08, P2-09, P3-09, F0-10; gates: F0_PRODUCTION_ADMISSION, C0_FINAL_ACCEPTED | K3/K4/K5/K7/K8 真实图绑定 | 在独立 graph_bindings.py 把已实现的 normalize/zones/native-relations/filter/group nodes 注入 K0–K11 的静态 Kedro graph，保存边与 accepted refs 明确、无 legacy Handler 外部执行 | `msgloom/a2_kedro/graph_bindings.py`, `tests/a2_kedro/test_k3_k4_k5_k7_k8_bindings.py`; Sonnet / high |

每一个任务先在其独立 worktree 用合成可信小输入验证，再做真实 tmp SQLite 接入。P1-12 可以与 P2 真实 parser profile 并行，但最终资源阈值只有实测方可确认。

## 6. Wave P2 — 提取、格式解析、标准化和 Zoning

| ID / 估时 | Depends on | 可并行工作域 | 最小独立验收 | Owner files / worker |
| --- | --- | --- | --- | --- |
| P2-01 / 20m | C0-03, C0-04 | MIME/HTML | 多 part、inline reply、编码损坏、原文位置、缺正文，原字节可追溯 | `msgloom/a2_kedro/parsers/mime_html.py`, `tests/a2_kedro/test_p2_01.py`, `msgloom/a2_kedro/parsers/__init__.py`; Sonnet / medium |
| P2-02 / 20m | C0-03, C0-04 | JSON/plain | 字段/纯文本位置信息、NULL/空、exact saved body 与部分响应 | `msgloom/a2_kedro/parsers/plain_json.py`, `tests/a2_kedro/test_p2_02.py`; Sonnet / medium |
| P2-03 / 20m | C0-03, C0-04 | PDF | page/text/layout、扫描/encrypted/限额，不能把空读取误判 COMPLETE | `msgloom/a2_kedro/parsers/pdf.py`, `tests/a2_kedro/test_p2_03.py`; Sonnet / medium |
| P2-04 / 20m | C0-03, C0-04 | DOCX | 段落/表格顺序、unsupported embedding、source block ID | `msgloom/a2_kedro/parsers/docx.py`, `tests/a2_kedro/test_p2_04.py`; Sonnet / medium |
| P2-05 / 20m | C0-03, C0-04 | XLSX/XLSM/XLSB/ODS | sheet/cell/公式 vs cached 值、hidden、实际 parser 支持边界 | `msgloom/a2_kedro/parsers/spreadsheets.py`, `tests/a2_kedro/test_p2_05.py`; Sonnet / medium |
| P2-06 / 20m | C0-03, C0-04 | 额外附件/保存字节 | 附件缺失、parent/role、嵌套 MIME，不能默默丢附件 | `msgloom/a2_kedro/parsers/attachments.py`, `tests/a2_kedro/test_p2_06.py`; Sonnet / medium |
| P2-07 / 20m | C0-05, P2-02 | NormalizedContent | 严格 offset map、重复片段、不可逆 transform 标记限制 | `msgloom/a2_kedro/normalize.py`, `tests/a2_kedro/test_p2_07.py`; Sonnet / medium |
| P2-08 / 25m | P2-07 | ContentZones | 自述/引用/转发/签名/未知，重复引用与 attribution 独立测试 | `msgloom/a2_kedro/zones.py`, `tests/a2_kedro/test_p2_08.py`; Sonnet / medium |
| P2-09 / 20m | P2-01, P2-02, P2-03, P2-04, P2-05, P2-06, P2-11, P2-08 | 类型与 parser failure policy | detected MIME mismatch、unknown/partial/unsupported、闭合 reason / held | `msgloom/a2_kedro/parsers/failure_policy.py`, `tests/a2_kedro/test_p2_09.py`; Sonnet / medium |
| P2-10 / 25m | P2-09, P2-11 | profiling | 真实 Pi child RSS/timeout/进程数，资源上限写入受审查配置而非硬编码 | `docs/notes/a2-v2-p2-extraction-benchmarks.md`; Sonnet / medium |
| P2-11 / 20m | P2-01, P2-02, P2-03, P2-04, P2-05, P2-06 | 唯一 static parser registry owner | trusted format/profile dispatch 与 allowlist，无 provider 控制动态 import；P1-05 通过其绑定 parser | `msgloom/a2_kedro/parsers/registry.py`, `tests/a2_kedro/test_parser_registry.py`; Sonnet / medium |

P2 不得自动引入云端 OCR、LLM 纠错、主观文本改写或外部网络补全。任何丢失来源证据的中间结果只能 INCOMPLETE/held。

## 7. Wave P3 — 保守原生关系、过滤与分组

| ID / 估时 | Depends on | 工作域 | 最小独立验收 | Owner files / worker |
| --- | --- | --- | --- | --- |
| P3-01 / 20m | C0-06 | 关系恢复 | 同源确证 reply-parent/ancestor/quote-source 各自分开记录 | `msgloom/a2_kedro/semantics/relations.py`, `tests/a2_kedro/test_p3_01.py`, `msgloom/a2_kedro/semantics/__init__.py`; Sonnet / medium |
| P3-02 / 20m | P3-01 | 关系审查 | cycle、missing parent、重复 Message-ID、跨 scope 不自动确认 | `msgloom/a2_kedro/semantics/relation_safety.py`, `tests/a2_kedro/test_p3_02.py`; Sonnet / medium |
| P3-03 / 20m | C0-07 | 规则过滤 | all-matching rule IDs、有版本评估、include/exclude/conflict/unknown | `msgloom/a2_kedro/semantics/filters.py`, `tests/a2_kedro/test_p3_03.py`; Sonnet / medium |
| P3-04 / 20m | P3-02 | Outlook native grouping | conversation only candidate，subject similarity 不直接合并 | `msgloom/a2_kedro/semantics/outlook_grouping.py`, `tests/a2_kedro/test_p3_04.py`; Sonnet / medium |
| P3-05 / 20m | P3-02 | Teams grouping | Teams chat reply vs channel scope，component-only refresh 不造 body | `msgloom/a2_kedro/semantics/teams_grouping.py`, `tests/a2_kedro/test_p3_05.py`; Sonnet / medium |
| P3-06 / 20m | C0-07 | 非通信来源 | Calendar / To Do / OneDrive / Contacts 的上下文按类型/范围发布 | `msgloom/a2_kedro/semantics/context_types.py`, `tests/a2_kedro/test_p3_06.py`; Sonnet / medium |
| P3-07 / 20m | C0-12a | replay-policy | configuration/policy/code 变更形成明确新 key；同输入稳定 idempotency | `msgloom/a2_kedro/semantics/replay_policy.py`, `tests/a2_kedro/test_p3_07.py`; Sonnet / medium |
| P3-08 / 20m | C0-08 | scoped transitions | presence/absence/membership deletion/content refresh 保持正确 authority | `msgloom/a2_kedro/semantics/transitions.py`, `tests/a2_kedro/test_p3_08.py`; Sonnet / medium |
| P3-09 / 25m | P3-02, P3-03, P3-04, P3-05, P3-06, P3-07, P3-08 | reviewer | 未解释链接保留 unknown；无跨 Workset 假关联，完整限制传播 | `docs/notes/a2-v2-p3-independent-review.md`; Sonnet / medium |

P3 纯函数可与 P1/P2 并行，但必须依赖冻结的 C0 `NativeRelations`、`FilterDisposition`、`GroupingDisposition`。新 topic AI classification 不在本阶段。

## 8. Wave T0 — 独立黄金测试（与 P1/P2/P3 并行）

| ID / 估时 | Depends on | Gold fixture 主题 | 防止的自证循环 | Owner files / worker |
| --- | --- | --- | --- | --- |
| T0-01 / 20m | 无 | A1 20 spider / 7 streams / 原 Task15 固定行为 | 不由新 Kedro 作者重写 A1 接受规则 | `tests/a2_kedro/gold/t0_01.json`; Sonnet / medium |
| T0-02 / 20m | 无 | Mail 多 MIME/inline quote/duplicate Message-ID | 另人独立标注贡献/引用/祖先和缺失 | `tests/a2_kedro/gold/t0_02.json`; Sonnet / medium |
| T0-03 / 20m | 无 | Teams chat/channel/component-only/scope refresh | 不能凭同 thread ID 猜亲属关系 | `tests/a2_kedro/gold/t0_03.json`; Sonnet / medium |
| T0-04 / 20m | 无 | Calendar、To Do、OneDrive、Contacts | contextual 不强行进入通信 grouping | `tests/a2_kedro/gold/t0_04.json`; Sonnet / medium |
| T0-05 / 20m | 无 | PDF、Word、Excel + malformed/large/partial | 解析错误不得伪装完整内容 | `tests/a2_kedro/gold/t0_05.json`; Sonnet / medium |
| T0-06 / 20m | C0-09, C0-10 | A2-held/intake-held/transition-only | 要么有已接受 prepared@2，要么有 held，不能 missing/overlap | `tests/a2_kedro/gold/t0_06.json`; Sonnet / medium |
| T0-07 / 20m | C0-12b | crash/restart/late writes/cancel | accepted prefix 保存，未完成必须可重放 | `tests/a2_kedro/gold/t0_07.json`; Sonnet / medium |
| T0-08 / 20m | C0-17a | policy upgrade / A3 historical reader | 旧 prepared@1 可读、新 prepared@2 正确映射 | `tests/a2_kedro/gold/t0_08.json`; Sonnet / medium |
| T0-09 / 20m | 无 | Prefect lost/duplicate hint/partial A1 finish | 唯一 authority 是 committed release/cursor | `tests/a2_kedro/gold/t0_09.json`; Sonnet / medium |
| T0-10 / 20m | 无 | security/path/privacy/network | Node.run logger、PII canary、telemetry、非法 Dataset path | `tests/a2_kedro/gold/t0_10.json`; Sonnet / medium |
| T0-11 / 25m | T0-01, T0-02, T0-03, T0-04, T0-05, T0-06, T0-07, T0-08, T0-09, T0-10 | independent gold author/reviewer | Oracle 数据由未写算法的人审核，不允许从算法输出自动生成 expected | `docs/notes/a2-v2-t0-independent-gold-review.md`; Sonnet / medium |

T0 默认合成输入和本地 Graph fixture，不上传任何用户邮件/真实 provider 对话到 Agent 或第三方。

## 9. Wave E0 — 真正的 A2 跨阶段集成与 durable receipts

| ID / 估时 | Depends on | 交付内容与针对性门禁 | Owner files / worker |
| --- | --- | --- | --- |
| E0-01 / 25m | P1-13, C0-20c, C0-16; gates: C0_FINAL_ACCEPTED | Workset PREPARE + partition PREPARE + transition PREPARE 真实 claim；每个 claim owner/required_inputs 清晰 | `msgloom/a2_kedro/integration/claim_topology.py`, `tests/a2_kedro/test_e0_01.py`, `msgloom/a2_kedro/integration/__init__.py`; Sonnet / medium |
| E0-02 / 20m | E0-01, P2-09, P3-09, P1-16, P1-18; gates: C0_FINAL_ACCEPTED | Full Kedro DAG K0–K11 从 Workset@1 端到 v2 receipt；不走 legacy A2 控制环 | `msgloom/a2_kedro/integration/full_pipeline.py`, `tests/a2_kedro/test_e0_02.py`; Sonnet / medium |
| E0-03a / 20m | E0-02 | `tests/a2_kedro/test_save_faults.py` 预置每个 Dataset save 注入点；完成/失败/部分结果和摘要准确 | `tests/a2_kedro/test_save_faults.py`; Sonnet / medium |
| E0-03b / 20m | E0-03a | `tests/a2_kedro/test_crash_recovery.py` 真实 restart/read-back；首段 accepted prefix 不丢、没有重复 | `tests/a2_kedro/test_crash_recovery.py`; Sonnet / medium |
| E0-04 / 25m | E0-01 | 两合法 claim 键碰撞、过期/替换、并发前后 start barrier；数据库只有一个 logical output | `tests/a2_kedro/integration/test_claim_concurrency.py`; Sonnet / high |
| E0-05 / 20m | E0-03b | Postcommit cancellation：返回 CancelledError 而数据已存，下一轮 query/reconcile 不重复 parser | `tests/a2_kedro/integration/test_postcommit_cancel.py`; Sonnet / high |
| E0-06 / 25m | E0-02, P1-16 | Workset-aggregate v2 receipt：一个选中 occurrence 一个 outcome + transition batch + intake-held | `msgloom/a2_kedro/integration/workset_completion.py`, `tests/a2_kedro/test_e0_06.py`; Sonnet / medium |
| E0-07 / 20m | E0-06 | Held-only 被标记 terminal INCOMPLETE；pending index 无永续 spin；operator replay append-only | `tests/a2_kedro/integration/test_held_pending.py`; Sonnet / medium |
| E0-08 / 20m | E0-02 | Wrong role/ambiguous release re-read → A2-held，A1 原结果/cursor 字节不变 | `tests/a2_kedro/integration/test_unverifiable_role.py`; Sonnet / medium |
| E0-09 / 20m | E0-06, C0-17d | A3 所有 typed prepared@2 +历史 prepared@1 与 limitation，A5 仍读取恰当 triage output | `tests/a2_kedro/integration/test_a3_v2_lineage.py`; Sonnet / medium |
| E0-10 / 20m | E0-02; gates: C0_FINAL_ACCEPTED | 按现有 Application async invocation 和 CLI `prepare-scheduled` 做一条真正 release→prepare 流 | `msgloom/cli/composition.py`, `tests/a2_kedro/test_e0_10.py`; Sonnet / medium |
| E0-11 / 25m | E0-09, E0-10, T0-11 | 格式 × 来源 × scope 集成，断流后重放、无已提交 entry 时 no-op、跨源全局序列 gap | `tests/a2_kedro/integration/test_multi_stream_e2e.py`; Sonnet / medium |
| E0-12 / 25m | E0-03b, E0-04, E0-05, E0-07, E0-08, E0-11 | 失效清单、可追溯完整引用和清理边界；独立 reviewer 只读 exact SHA | `docs/notes/a2-v2-e0-independent-review.md`; Sonnet / high |

## 10. Wave I0 — 外部 wakeup、CLI 与受控切换

| ID / 估时 | Depends on | 具体交付与验收 | Owner files / worker |
| --- | --- | --- | --- |
| I0-01 / 20m | C0-18 | 独立纯逻辑 scheduler 状态机：pending/busy/held/BLOCKED/FAILED/CANCELLED 不混淆 | `msgloom/a2_kedro/activation/status_policy.py`, `tests/a2_kedro/test_i0_01.py`, `msgloom/a2_kedro/activation/__init__.py`; Sonnet / medium |
| I0-02 / 20m | C0-18 | `scope-status` allowlisted CLI，scope hash / cursor digest / pending/held counts / last receipt，不含 PII | `msgloom/cli/a2_scope_status.py`, `tests/a2_kedro/test_i0_02.py`; Sonnet / medium |
| I0-03 / 20m | I0-01 | Prefect（或外部启动器）无 payload finite wakeup 定义，只发提示不修改 A1 | `msgloom/a2_kedro/activation/prefect_flow.py`, `tests/a2_kedro/test_i0_03.py`; Sonnet / medium |
| I0-04 / 20m | I0-02, I0-03 | real command wrapper 调用既有 `prepare-scheduled`，锁定稳定 consumer/catalog pin，不读私有 SQL | `msgloom/a2_kedro/activation/launcher.py`, `tests/a2_kedro/test_i0_04.py`; Sonnet / medium |
| I0-05 / 20m | I0-04 | A1 完成/部分失败/重复通知/失联提醒后，依照 committed release 和 durable cursor 恢复 | `msgloom/a2_kedro/activation/catchup.py`, `tests/a2_kedro/test_i0_05.py`; Sonnet / medium |
| I0-06 / 20m | I0-05 | 同 scope 重叠 invocation coalesce、claim-busy 退避、no-progress 上限，无无限循环 | `msgloom/a2_kedro/activation/coalesce.py`, `tests/a2_kedro/test_i0_06.py`; Sonnet / medium |
| I0-07 / 25m | E0-12, I0-06; gates: F0_PRODUCTION_ADMISSION | Disabled/staging 部署验证及一条真实 A1→Kedro A2 流，先不放大并发 | `tests/a2_kedro/activation/test_staging_autowakeup.py`; Sonnet / high |
| I0-08 / 25m | I0-07 | 旧 pending workset 清零核查、旧 engine 过渡与稳定回滚 anchor、历史 A3 读路径 | `docs/notes/a2-v2-i0-cutover-audit.md`; Sonnet / medium |
| I0-09 / 20m | I0-08 | 生产启动 runbook、停止/恢复/报警分支、消除双引擎自动 fallback | `docs/runbooks/a2-v2-activation.md`; Sonnet / medium |
| I0-10 / 20m | I0-09, V0-14c, I0-11; gates: OWNER_EXPLICIT_CUTOVER_APPROVAL | 用户明确确认后才可启用生产 Prefect、执行 DB schema migration 或正式 switch | `docs/notes/a2-v2-i0-owner-approval.md`; Sonnet / high |
| I0-11 / 20m | C0-11e, E0-12; gates: OWNER_EXPLICIT_COMPAT_DEPLOY_APPROVAL | 兼容二进制部署前验证 —— 在 staging 以新兼容 binary 打开旧 schema4 不创建表/不写入；现场 rollout 需用户独立批准且仍旧 A2 dispatch | `docs/runbooks/a2-v2-compatible-open.md`, `tests/a2_kedro/test_compat_deploy.py`; Sonnet / high |

I0-10 是不允许 Agent 自行做出的生产授权；即使用户先前同意开发，也不能当成对真实生产数据迁移与安全例外的自动批准。

## 11. Wave V0 — 完整质量矩阵与独立验收

| ID / 估时 | Depends on | 完成的客观证据 | Owner files / worker |
| --- | --- | --- | --- |
| V0-01 / 20m | E0-02 | DAG Graph 测试：验证 extract/parse/normalize/zone/native/filter/group/semantic save 全由 Kedro 依赖连接 | `tests/a2_kedro/acceptance/test_v0_01.py`; Sonnet / medium |
| V0-02 / 20m | C0-00 | 原 A1 20 Spider/13 Task15 scenarios/28 gates 的源代码不动，单独跑只读兼容检查 | `tests/a2_kedro/acceptance/test_v0_02.py`; Sonnet / medium |
| V0-03 / 20m | E0-11 | A1 release/selection/ordinal/role/byte digest：七 stream、历史 baseline 和多 occurrence | `tests/a2_kedro/acceptance/test_v0_03.py`; Sonnet / medium |
| V0-04 / 20m | P2-09, T0-11, P2-08 | MIME/PDF/Word/Excel/JSON/HTML 和 span/limitation golden，独立 gold reviewer | `tests/a2_kedro/acceptance/test_v0_04.py`; Sonnet / medium |
| V0-05 / 20m | P3-09, T0-11 | 关系/规则/分组异常：无法归属、跨 scope、重复 ID、source-native context | `tests/a2_kedro/acceptance/test_v0_05.py`; Sonnet / medium |
| V0-06 / 20m | P1-12b, E0-05 | async cancel、CPU/GIL、parser cgroup、child cleanup、max RSS、无 orphan、无 writer after claim expiry | `tests/a2_kedro/acceptance/test_v0_06.py`; Sonnet / medium |
| V0-07 / 25m | C0-11d, E0-12 | 数据库迁移 v2/3/4→经 C0-11a 决议的 schema/revision、旧结构/trigger/占用表/legacy hash 拒绝、失败原子回滚 | `tests/a2_kedro/acceptance/test_v0_07.py`; Sonnet / medium |
| V0-08 / 20m | C0-20c, E0-12 | 完整 v2 acceptance/receipt/held-index、conflicting SHA/attempt、并发和 late crash 恢复 | `tests/a2_kedro/acceptance/test_v0_08.py`; Sonnet / medium |
| V0-09 / 20m | E0-09 | A3/A5 老数据加载、新输入 typed 适配、限制贯穿，历史不重写 | `tests/a2_kedro/acceptance/test_v0_09.py`; Sonnet / medium |
| V0-10 / 20m | I0-06 | Prefect hint 丢失/重复/partial failure、cursor 不漂移、pending backpressure | `tests/a2_kedro/acceptance/test_v0_10.py`; Sonnet / medium |
| V0-11 / 20m | V0-11a, E0-12 | Python 3.12/3.13/3.14、Pi aarch64 和 x86/Linux、Mac/Windows smoke；不能把 `-O` synthetic 冒充全量 | `tests/a2_kedro/acceptance/test_v0_11.py`; Sonnet / medium |
| V0-11a / 20m | C0-00 | `.github/workflows/ci.yml` 中增加/确认 Linux x86_64 真实 runner + wheel/pytest targeted gate；原 CI 仅 ARM Linux + Mac/Windows smoke | `.github/workflows/ci.yml`; Sonnet / medium |
| V0-12 / 20m | E0-12, F0-09, F0-10; gates: F0_PRODUCTION_ADMISSION | GitHub 全部必需 checks：`ruff check` / `ruff format --check` / Pyright / pre-commit / gitleaks / pytest / cgroup-v2 / wheel install | `tests/a2_kedro/acceptance/test_v0_12.py`; Sonnet / medium |
| V0-15 / 20m | E0-12, P1-12b | **保留 D4 V13**：完全相同 A1 frozen Workset 在相同 Pi / supported host 下测 old vs new 的 wall/RSS，超过 10% 的实质回归需查明并复审（绝对量可忽略情形记录证据） | `tests/a2_kedro/acceptance/test_v0_15.py`; Sonnet / medium |
| V0-16 / 20m | E0-12, P1-13 | **保留 D4 V14**：计数 Kedro 图依赖、bridge/adapter、图外控制器分支/LOC，禁止重建第二套自制 A2 ETL 调度器 | `tests/a2_kedro/acceptance/test_v0_16.py`; Sonnet / medium |
| V0-17 / 20m | I0-06, E0-12, T0-09, I0-07 | **保留 D4 V16**：按原 D4 [AUTO-01–AUTO-25] 全部单独执行，尤其 missing wakeup、held-only、postcommit、CVE 和 history cutover | `tests/a2_kedro/acceptance/test_v0_17.py`; Sonnet / medium |
| V0-18 / 20m | V0-17, V0-15, V0-16 | D4 真实验收 crosswalk —— [PR #68] 原始 V01–V16 + AUTO-01–25 每项有 exact SHA/具体新测试/CI/负责 task，缺任何项 FAIL | `docs/notes/a2-v2-d4-v01-v16-crosswalk.md`; Sonnet / high |
| V0-13 / 20m | F0-08, P1-11 | 无新增 CVE ignore/telemetry、未授权网络、隐私 canary；完整锁及版本 hash 审计 | `tests/a2_kedro/acceptance/test_v0_13.py`; Sonnet / medium |
| V0-14a / 20m | V0-01, V0-02, V0-03, V0-04, V0-05, V0-06, V0-07, V0-08, V0-09, V0-10, V0-11, V0-11a, V0-12, V0-13, V0-15, V0-16, V0-17, V0-18, I0-07, I0-08, I0-09 | 独立 reviewer 对生产代码和边界的 exact-SHA 一轮只读验证；保留初始 REVISE 原文 | `docs/notes/a2-v2-independent-review-r1.md`; Sonnet / high |
| V0-14b / 20m | V0-14a, I0-07 | 独立 reviewer 对可复现 test/CI/安全/性能/自动触发矩阵核验，分工与作者独立 | `docs/notes/a2-v2-independent-review-r2.md`; Sonnet / high |
| V0-14c / 20m | V0-14b, I0-07 | 汇总两个只读 reviewer + 必须通过的 CI/owner decisions，在确切 SHA 归档正式 GO/NO-GO，而非每阶段本人签字 | `docs/notes/a2-v2-final-go-no-go.md`; Sonnet / high |

**测试执行效率策略**：子任务先跑相关 1–3 个测试文件 → 每个集成 PR 跑 impacted boundary / Pyright → 每阶段一次必要矩阵/CI → V0 才跑完全量，避免每修一个小问题就重复跑全部耗时测试。不允许用 skipped/insecure mock 替代硬 gate。

## 12. Wave R0 — 旧 A2 正式退役、发布与恢复

| ID / 估时 | Depends on | 动作与界限 | Owner files / worker |
| --- | --- | --- | --- |
| R0-01 / 20m | V0-14c | 归档旧 A2 Git SHA、历史 schema/compat fixture、行为负面测试并检查最新 A3 reader，确定临时双读范围 | `docs/notes/a2_v2_r0_01.md`; Sonnet / medium |
| R0-02 / 20m | R0-01 | 只读 audit 旧 pending Workset 必须清零，另审计旧 held-only 曾被标为 COMPLETE 的历史，不得将其当成新正确 receipt | `docs/notes/a2_v2_r0_02.md`; Sonnet / medium |
| R0-03 / 20m | R0-02, I0-09, I0-11 | **切换前**校验 DB 备份/恢复演练、旧 schema4 binary 与新兼容 binary 的开关、迁移 runbook；不能仅靠 git revert | `docs/notes/a2_v2_r0_03.md`; Sonnet / medium |
| R0-04 / 20m | R0-03, I0-10, I0-11; gates: OWNER_EXPLICIT_CUTOVER_APPROVAL, STAGED_DB_BACKUP_AND_OLD_PENDING_ZERO | 收到用户明确迁移/安全/cutover 授权后在维护窗口执行显式 schema/producer binding 操作，保持单一 A2 dispatch | `docs/notes/a2-v2-r0-schema-activation-receipt.md`; Sonnet / high |
| R0-05 / 20m | R0-04 | 小范围 source/stream/consumer 验证 read-only status、结果/A3 限制、无失败回退再决定扩展；无产出证明不放大 | `docs/notes/a2_v2_r0_05.md`; Sonnet / medium |
| R0-06 / 20m | R0-05; gates: OWNER_EXPLICIT_LEGACY_RETIREMENT_APPROVAL | 确认 v2 成功且旧 Handler 不再生产后，按依赖扫描删除 legacy RecordSteps/StageSteps/旧 dispatch 冗余实现，保留原历史测试/数据 | `msgloom/preparation_pipeline/handler.py`, `msgloom/preparation_pipeline/scheduled.py`, `tests/a2_kedro/test_r0_06.py`; Sonnet / high |
| R0-07 / 20m | R0-06; gates: OWNER_EXPLICIT_BRANCH_CLEANUP_APPROVAL | GitHub required checks / 历史 A3/A5 regression 后单 owner 合并与只清理已合并、无将来用途 worktrees/远程分支 | `docs/notes/a2-v2-r0-merge-cleanup-audit.md`; Sonnet / medium |
| R0-08 / 20m | R0-07 | Final acceptance index：代码/迁移/CI/安全决定/回滚演练/自动 Prefect 状态，确认不再长期双引擎或后台假作业 | `docs/notes/a2_v2_r0_08.md`; Sonnet / medium |

## 13. 具体 PR / 分支 / 资源与集成顺序

建议采用细小、可审计 PR，而不是一个庞大未审查的功能分支。默认命名、具体 SHA/owner 应在启动时读取 GitHub 当前状态再填，不复用历史 SHA 推定已经在 master。

| 推荐 PR | 独立责任人 | 可并行性 / 先决条件 |
| --- | --- | --- |
| CR: C0-R1/Pyright research corrections | C0 owner + R2 reviewer | 可与 F0 并行，不与 C0 同文件多人并写 |
| F0: Exact version/security/coinstall qualification | security/dependency owner | 与 CR 并行；正式 lock 修改须单 owner + user 风险决定 |
| C0 contracts-only freeze | schema/domain owner | CR R2 + F0 核查完成，先 gold types/field names |
| C0 schema+async persistence | DB owner | 在契约冻结后串行迁移与接受索引 |
| C0 A3 compatibility | A3 owner | 独立 branch 可研究；合并在真实 schema 后 |
| P1 Kedro core | Runtime owner | C0 accepted 后，与 P2/T0 并行 |
| P2 source parsing/zoning | Parser owner | C0 accepted 后，与 P1/P3/T0 并行 |
| P3 native/group/filter | Semantic owner | C0 relations/filter shapes accepted 后并行 |
| E0 A1→A2→A3 integration | Integration owner | 上游 P1/P2/P3 确认后串行 |
| I0 Prefect/wakeup | Orchestration owner | 纯状态机早期可写；启用/部署在 E0/V0 后 |
| V0 + R0 | Independent reviewer + release owner | 必须最后按 exact SHA 全门禁 |

CI 工作流自带三 Python versions、FastMCP 兼容矩阵、Linux delegated cgroup-v2、macOS/Windows smoke。对实际正式依赖引入，仅在受审查锁文件上运行完整轮次。**不要推到 master 后再“看看是否坏了”。**

## 14. 自动恢复、停止条件与风险矩阵

| 触发 | Agent Manager 可自动处理 | 必须停止或升级 |
| --- | --- | --- |
| 类型错误、格式、单项测试失败 | 按失败行定位，一次一任务、重跑针对性 case；保留 first failure logs | 若无法确定设计语义或开始导致数据不一致，则开 REVIEW |
| Git 冲突/同文件并写 | 锁定 owner、撤回多余分支、在 integration worktree 依赖序合并并重跑测试 | 严禁直接 force push master、覆盖他人 worktree |
| 子 Agent/CLI 停止、429/网络错误 | 记录 session/exit/retry 的真实证据，有限退避、可从 Git SHA 重启只做未完成项 | 不允许空转无限重试或声称没有 PID 仍在运行 |
| 研究结果与文档矛盾 | 保留原 REVISE，更新测试+文档，新 commit、新只读 review | 不擦掉旧失败，也不“改措辞”而继续生产 |
| 漏洞意见冲突/无固定版 | 继续独立 source/test 和 reachability；给用户一页风险证据 | **不得自行添加忽略，也不得部署 Kedro 生产** |
| A1 证明不一致/role 不可判 | 保存 A2-held/停止本输入，不访问 live source 补齐 | 不改 A1 ledger/Intake/cursor |
| 后提交取消 / 真实 worker leak | 冻结新任务并调查 durable key/worker，验证是否有 late save | 无法证明 bounded cleanup、claim margin 则 P1/E0 NO-GO |
| A3 无法消费 prepared@2 或旧 pending 未清零 | 保持旧生产 A2，不执行切换 | 需要单独审查数据迁移/兼容方案 |
| 无真实任务在运行 | 状态报告 STOPPED | 不承诺“后台继续” |

## 15. Supervisor 可见里程碑与审查包

每个完成的阶段提交一个小型、可复制的验收包，包含：

- 任务 ID / frozen input SHA / base SHA / branch / commit SHA / PR / 文件所有权清单。
- 成功与失败的运行命令、平台、Python/依赖版本、真实退出码、必要日志 hash（去标识）、已跑和未跑的测试。
- 最新独立只读 reviewer 判定（REVISE/ACCEPT）、审阅精确 SHA、未解决 P0/P1/P2 与下一步单一 owner。
- 本地 manager/worker 真实进程/任务 job_id、RUNNING/STOPPED 等状态；本地后台进程和远程常驻控制台不混为一谈。
- 假设与残余风险、是否需要用户决定；若还没签署 F0 风险和真实部署，不得写 production accepted。

### 15.1 任务 DAG 质量与文件独占门禁

- Markdown 的 169 个 task ID 必须和机器 JSON task IDs 一一对应，且每一个内部依赖存在、无循环；外部门禁需要真实证据与审批主体。
- 每个任务的 `owner_files` 在 worktree 具体展开，冲突文件分给单个写入者；具有相同文件所有权的任务必须串行，不能同时运行。
- 每个任务的时间窗口 ≤25 分钟是细分要求，复杂 SQL/迁移/review 已拆为多项；预算并非服务等级承诺或阶段 ETA。
- 复审 CR-10 / F0-08 / C0-20c / P1-13 / E0-12 / V0-14a–c 对每个精确 SHA 单独归档；不允许作者自签 ACCEPT。

### 15.2 本轮文档交付的退出条件

本轮结束前只要求：三份主体 Markdown 文档、完整 task DAG/JSON、现状核查、格式/链接/表格检查、单独 docs-only Git commit/草稿 PR（如连接正常），以及对文档本身的独立只读复审或清晰说明审查尚未完成。

**本轮不执行 CR、F0、C0、P1、P2、P3 代码实现，也不启动持续性本地 AI Task Manager。** 用户阅读三份文档并讨论执行顺序、并发、资源/安全批准后，再正式授权执行。这样“现在不用人工接触设备”也不再被误解为“Agent 已经在后台工作”。

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

**唯一推荐路线：** 先把 F0 和 C0-R1 研究整改作为两条可并行的非生产工作流；两边各自通过独立 gate 后，串行冻结生产 C0；然后才允许 P1/P2/P3/T0 大规模并行。不要把现有 Q0 合成 ACCEPT 当作生产安全签字。

### 0.1 Gate 有向无环图

```text
[Existing A1 ACCEPT] -> [D4 ACCEPT] -> [Q0 synthetic ACCEPT]
                                         |
                  +----------------------+--------------------+
                  |                                           |
          F0 Security/dependency                        CR C0-R1 fix
          full co-install qualification                 + Pyright + R2 review
                  |                                           |
                  +----------------------+--------------------+
                                         v
                         C0 production schema/codec/SQL
                            exact root + receipt freeze
                                         |
                    +--------------------+--------------------+
                    |                    |                    |
              P1 Kedro DAG        P2 Parse/Zone       T0 independent fixtures
                    |                    |                    |
                    +----------- P3 relations/rules/group -----+
                                         |
                                   E0 integration
                                         |
                               I0 manual/scheduled + A3
                                         |
                         I0 Prefect hint + recovery gate
                                         |
                       V0 full tests/security/portability
                                         |
                       R0 controlled cutover / old A2 retire
```

生产依赖 PR 的可合并门禁包括 F0 owner safety disposition，不应为了等锁文件而停止独立的 C0 测试和 schema 设计研究；**但生产 C0 接受签字不能越过 F0**。

## 1. Task Manager 的必需运行方式

### 1.1 角色、模型与 effort（正式启动前只作计划）

| 角色 | 推荐选择 | 理由与限制 |
| --- | --- | --- |
| Supervisor（本 ChatGPT 会话） | 当前 GPT-6；只读核查并给出决策建议 | 审阅任务 DAG、失败、预算、PR/CI 证据；不虚称后台运行 |
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

| ID / 估时 | 依赖和文件所有权 | 具体改动 / **必须通过的测试** | 模型 |
| --- | --- | --- | --- |
| CR-01 / 15m | R1 文档审阅；`docs/plans/2026-10-23-a2-kedro-c0-contract-candidate.md` | 正确陈述旧 `intake_completion.py` 对 held-only **可能 COMPLETE** 且 aggregate 未强制纳入 `workset.held`；写清是新 v2 policy change，不能改 A1 | Sonnet High |
| CR-02 / 20m | C0 prototype tests | 修正三项由于 `model_dump()` + strict dataclass dict 导致的假阳性；用有效 instance/`model_validate_json`，逐个验证 extra field、stage XOR、policy version 等实际被测 predicate | Sonnet Medium |
| CR-03 / 20m | C0 fixture/test | 生成两个不同 ReleaseEntry occurrence 但指向相同 ResultRef 的结构合法 Workset，验证 `selection_refs` 去重、receipt 仍要求两个结果；注明真实 A1 hash 含 entry，正常不会生成该冲突，纯防御案例 | Sonnet Medium |
| CR-04 / 20m | C0 docs/security | 明确研究索引绕过旧 plan 的真因是 claim key **不以 `prepare:` 开头**；空 `required_inputs` 是另一个缺口。逐项列出未验证的 status/limitations、upstream refs、attempt vs claim、workset scope、batch transition identity、kind/version 允许表、同步 facade 绕过 | Sonnet High |
| CR-05 / 15m | Native A1 test + doc | 目前错误 candidate 只触发 `not in workset`。增加“Workset 内已选 root 但 ordinal/key 不一致”、“已保存 selection 内容不同”的真实负例，或明确降级宣称；不篡改真实 A1 | Sonnet Medium |
| CR-06 / 15m | Pyright | 逐个修复 CI 9 项 可空 `SemanticDataRef` / 可选 selection/batch 访问，显式 guard + `pytest.fail`，**不能加 ignore/type: ignore 规避** | Sonnet Medium |
| CR-07 / 20m | Python tests & docs | 把 “Expected C0 test condition at line N” 换为真实断言说明；避免过短 3 秒 lease 在高负载 Pi 形成 flake；准备重复测试 x3 | Sonnet Low/Medium |
| CR-08 / 20m | Research prototype + docs | 在文档明确 `_store` private + `asyncio.to_thread` 取消不受保护、large semantic decode 在 writer lock 内、临时 SQL `create_all` 仅供实验，不允许移植至生产；强化不相同 claim-key 的并发测试描述 | Sonnet High |
| CR-09 / 20m | 单人集成 owner | 针对性 pytest、Ruff/format、Pyright（实际 CI 同命令）、pre-commit/gitleaks。只归入与 CR 相关文件；保留审查报告与变更 SHA | Sonnet Medium |
| CR-10 / 20m | Reviewer | 独立只读 R2 exact SHA → `ACCEPT` 才关闭研究门禁；有 REVISE 则新 CR-N 任务，不自动称 production C0 ready | Sonnet High |

**先决验收：** GitHub PR #70 当前 9/10，其中唯一失败是 Pyright；修复后必须重新触发 PR 的完整质量矩阵，**所有 required checks 通过**。本地 19/19 不替代 GitHub Pyright。CR-01/04/08 同属文档文件，必须串行合并或由一个文档 owner 一次完成；CR-02/03/05/06 的测试文件也必须以 worktree ownership 避免写冲突。

## 3. Wave F0 — Kedro 1.7 安全与依赖资格（与 CR 同步）

| ID / 估时 | 输入、操作和目标证据 | 验收与 Stop 条件 | 模型 |
| --- | --- | --- | --- |
| F0-01 / 15m | 再核对 PyPI Kedro 1.7 wheel（SHA `488701a27c7d595b62a611cb23596953a9929fe5cc42a376c28abe26654c2438`）、源码版本、当前 Pi py312/313/314 环境和 Q0 矩阵 | 来源日期、可重跑 wheel hash；不能无核验更换候选版本 | Sonnet Medium |
| F0-02 / 25m | 独立看 GHSA-6326、CVE-2026-35167、CVE-2026-3840、Snyk + 当前 source `_get_versioned_path/_is_unsafe_version`，建立 method/API reachability matrix | 明确“上游报告已修复”和“Snyk 仍报告受影响”的**未决差异**；不推出无依据的安全结论 | Sonnet High |
| F0-03 / 20m | 静态 Dataset allowlist：禁用 Kedro CLI、`DataCatalog.from_config`、`load_versions`、versioned FS datasets、动态插件；环境和代码测试 | malicious `../` / absolute、unknown dataset、untrusted import/PII 不落日志；生产代码门禁可实现 | Sonnet High |
| F0-04 / 20m | telemetry：`kedro-telemetry` 强制依赖，真实 plugin consent 与 programmatic hooks，stderr/stdout import、socket/real network deny 控制 | 不只是 null plugin 假测试；任何未预期网络/标识上传则 STOP | Sonnet High |
| F0-05 / 25m | **仅隔离 worktree/scratch lock** 完整 `msgloom + kedro` wheel/co-install；Linux Pi aarch64、Python 3.12/13/14，核对所有原依赖版本 | `uv pip check`、new vs old lock 变更表、wheel/source hash、pytest smoke；不触碰实际 `uv.lock` | Sonnet Medium |
| F0-06 / 20m | Linux x86_64 和 Mac/Windows portability smoke（通过 CI matrix/配置，不要求物理 GUI） | 有真实 runner 或明确 NOT TESTED；不把 Pi 验证冒充全部平台 | Sonnet Medium |
| F0-07 / 15m | Audit 策略：记录原有 `PYSEC-2017-83`、`GHSA-8pqf-f4m5-798g` 的受审查 CI policy；新 Kedro CVE 不添加隐性 ignore | baseline 与 candidate 的新增漏洞 delta 可复现；保留 non-green 的原始无忽略审计证据 | Sonnet High |
| F0-08 / 20m | 安全 reviewer 独立 R1/R2，冻结精确 SHA、真实风险适用性与操作决策候选 | reviewer ACCEPT 对象仅限可复现评估；如仍不能排除 residual risk → 用户安全决定/STOP | Sonnet High |
| F0-09 / 20m | lock 单人 owner 制定候选生产依赖 PR（先草稿，不改 master）与门禁说明 | owner security signoff、共装跨版本 CI 和回滚计划齐备才申请合并；默认保留 Draft | Sonnet Medium |

安全残余风险是明确的人为审批点。Agent 不能替用户签署安全豁免。即便 F0 风险被接受，也不能绕开 C0 事务/receipt 证明。F0-05 可以在 scratch 环境与 CR 任务并行，F0-09 不会未经同意提交运行时依赖。

## 4. Wave C0 — 生产契约、持久化与 A3 adapter 设计冻结

CR 研究 R2 ACCEPT 与 F0 准入后的工作；**先冻结 schema/header/golden 再大规模分配 P1/P2/P3**。下面是精细任务，单项不跨 30 分钟。

| ID / 估时 | 拥有文件/接口 | 具体落地和验收 |
| --- | --- | --- |
| C0-01 / 20m | `msgloom/a2_kedro/contracts/source.py`，A1 verifier adapter | FrozenSourceSelection：entry/workset 及 approved baseline 的互斥结构、occurrence index/ordinal/role、saved SHA、scope；拒绝 forged hash/role |
| C0-02 / 20m | `msgloom/a2_kedro/source_resolution.py` | 使用精确 ReleaseReader 重新验证 ordinal/byte equality；component/context/transition-only + global sequence gaps；源读取错误 typed A2-held |
| C0-03 / 20m | `msgloom/a2_kedro/contracts/extract.py` | ExtractedComponents：primary/alternate/attachment/embedded 保存引用、digest、missing/partial/unsupported，有限 metadata codec |
| C0-04 / 20m | `msgloom/a2_kedro/contracts/parse.py` | ParsedParts：part/page/sheet/cell 和 parser worker receipt，断言 actual-format 和 byte source link |
| C0-05 / 20m | `msgloom/a2_kedro/contracts/zones.py` | NormalizedContent / ContentZones，原始 span 精确映射及 quote-occurrence vs quote-author；不可逆限制 |
| C0-06 / 20m | `msgloom/a2_kedro/contracts/relations.py` | NativeRelations：回复/祖先/引用假设的 typed scope；unknown/cycle/duplicate 负例 |
| C0-07 / 20m | `msgloom/a2_kedro/contracts/results.py` | prepared@2、filter_result@2、group_result@2 和 manifest；all-matched-rules，分组无跨作用域静默连接 |
| C0-08 / 20m | `msgloom/a2_kedro/contracts/transition.py` | scoped transition **batch identity** 定义在 Workset Ref + 有序 fact/scope + code/policy，单项与 batch 不混淆 |
| C0-09 / 20m | `msgloom/a2_kedro/contracts/held.py` | a2_input_disposition@1 和显式 repair_class；held-only、context-only、approved baseline 并不强制做 body |
| C0-10 / 20m | `msgloom/a2_kedro/contracts/receipt.py` | a2_completion_receipt@2 **结构完整性**；同一 frozen occurrence 恰好一份结果，intake-held 强制 INCOMPLETE |
| C0-11 / 25m | `msgloom/persistence/a2_schema.py` + `schema_store.py`（DB owner） | 从 schema 4 迁移到 reviewed v5 候选；精确 DDL/index/constraint、历史 v2–v4 可升级、错误 schema/占用 name/trigger 不修改、断电回滚 |
| C0-12 / 25m | `msgloom/persistence/a2_store.py` + facade | 原子 logical key append-or-verify、ClaimToken/required_inputs/plan、canonical SHA、metadata-only recheck、并发和 postcommit cancel；**从零建立安全公开 async 方法** |
| C0-13 / 20m | `msgloom/persistence/a2_held_store.py` | 可查询 bounded A2-held index，workset-scoped，幂等冲突拒绝，用户隐私 safe status |
| C0-14 / 25m | `msgloom/persistence/a2_receipt_store.py` | 新 v2 completion 与准确 claim/attempt history 验证；prepared@2 / held + transition batch；不存在“结构通过但数据库未接受” |
| C0-15 / 20m | `msgloom/a2_kedro/application_contract.py` | 公开 `async def prepare(...)`，前置输入/authority pin 检查，CancelledError/timeout/status 分类，不创建 loop |
| C0-16 / 20m | `msgloom/a2_kedro/partition_policy.py` | 有版本、有限 partition/workset scope，避免跨 Workset 不合理 merge；资源上限由 P1/P2 profiling 修正 |
| C0-17 / 25m | `msgloom/triage_input/` / `msgloom/triage_pipeline/` 单 owner | A3 读取 prepared@1（历史）和 prepared@2（新），zone/limitation/relational provenance 正确流入 A3；无旧 API 假兼容 |
| C0-18 / 20m | `msgloom/cli/` 只读 status 类型定义 | trusted scoped progress + typed exceptions：BLOCKED source/reference/cat、busy INCOMPLETE、claim loss FAILED、held terminal |
| C0-19 / 20m | dedicated golden fixture/tests | 确保 wire field name、codec canonical bytes、SHA/ID、扩展缺失、max bytes、未知版本拒绝、历史解码不变 |
| C0-20 / 25m | integration owner/reviewer | 合并 C0 所有接口、真实 A1 root/Claim/SQLite E2E、typed A3 回归，独立审查接受精确 SHA 才宣告 C0 FROZEN |

**特别重要的失败类别：** 当前 C0 研究索引用 `c0-a2:` claim key，绕开旧 `prepare:` plan binding；`required_inputs=()` 另使其无真实 A1 lineage。这两个缺口必须同时关闭，不能只是把研究表接进 `schema_store`。生产版本必须只接受从可信 Workset/Reader 生成、已证明 upstream stage 的计划。

C0-11/12/14 的 SQL 及迁移有唯一所有者，顺序串行。C0-01–10 可分并行包，但只在字段/版本 header 冻结后互相对接；C0-17 可先研究/fixture，再按确定 schema 适配。C0-20 是串行集成门禁，不能跳过。

## 5. Wave P1 — Kedro Core/Dataset/async 主链

| ID / 估时 | 源文件边界 | 必须交付 / 针对性证明 |
| --- | --- | --- |
| P1-01 / 20m | `msgloom/a2_kedro/graph.py` | 完整 K0–K11 拓扑，Kedro 是全 DAG authority；不存在外部旧 Handler 绕行 |
| P1-02 / 20m | `catalog.py` | 编程方式 DataCatalog 明确封闭 dataset allowlist；拒绝未知 dataset 和动态 YAML 配置 |
| P1-03 / 20m | `datasets/handoff.py` | ExactHandoffDataset 只读 Workset + selection + exact A1 reread，外部 URI/path 不可接受 |
| P1-04 / 20m | `datasets/evidence.py` | VerifiedEvidenceDataset 访问已签名 saved refs，SHA、边界、missing evidence 处理 |
| P1-05 / 25m | `datasets/parser.py` | Parser request save/load 走隔离 child service，真实超时、worker termination、partial 的限制 |
| P1-06 / 20m | `bridge.py` | 同步 worker 到 async loop 的 bounded `run_coroutine_threadsafe`：拒绝 wrong-thread/无限待 |
| P1-07 / 20m | `runner.py` | 受控 `SequentialRunner(is_async=False)`，每个正在执行的线程和 coroutine 有 owner；repeated cancel drain |
| P1-08 / 20m | `datasets/semantic.py` | ClaimFencedSemanticDataset，发布前后均查 live token、返回 durable ref，而非原地假结果 |
| P1-09 / 20m | `datasets/transitions.py` | 单独 scoped transition claim，context refresh 不成为 message |
| P1-10 / 25m | `resume.py` | 保存每个已接受 stage/progress；重启 read-back、跳过已验证 parse/save；冲突停机 |
| P1-11 / 20m | `security.py` / test | 无 Kedro CLI/telemetry/network、隐私安全 logging、静态 node/dataset 名 |
| P1-12 / 25m | Pi test fixtures | 原生 parser cgroup-v2 和 native GIL 占用实验；RSS、CPU、deadline、lease + cleanup margin、孤儿子进程数 |
| P1-13 / 25m | reviewer | 真实冻结 A1 selection → 完整 Kedro graph → durable v2 results，独立审查并要求 CI |

每一个任务先在其独立 worktree 用合成可信小输入验证，再做真实 tmp SQLite 接入。P1-12 可以与 P2 真实 parser profile 并行，但最终资源阈值只有实测方可确认。

## 6. Wave P2 — 提取、格式解析、标准化和 Zoning

| ID / 估时 | 可并行工作域 | 最小独立验收 |
| --- | --- | --- |
| P2-01 / 20m | MIME/HTML | 多 part、inline reply、编码损坏、原文位置、缺正文，原字节可追溯 |
| P2-02 / 20m | JSON/plain | 字段/纯文本位置信息、NULL/空、exact saved body 与部分响应 |
| P2-03 / 20m | PDF | page/text/layout、扫描/encrypted/限额，不能把空读取误判 COMPLETE |
| P2-04 / 20m | DOCX | 段落/表格顺序、unsupported embedding、source block ID |
| P2-05 / 20m | XLSX/XLSM/XLSB/ODS | sheet/cell/公式 vs cached 值、hidden、实际 parser 支持边界 |
| P2-06 / 20m | 额外附件/保存字节 | 附件缺失、parent/role、嵌套 MIME，不能默默丢附件 |
| P2-07 / 20m | NormalizedContent | 严格 offset map、重复片段、不可逆 transform 标记限制 |
| P2-08 / 25m | ContentZones | 自述/引用/转发/签名/未知，重复引用与 attribution 独立测试 |
| P2-09 / 20m | 类型与 parser failure policy | detected MIME mismatch、unknown/partial/unsupported、闭合 reason / held |
| P2-10 / 25m | profiling | 真实 Pi child RSS/timeout/进程数，资源上限写入受审查配置而非硬编码 |

P2 不得自动引入云端 OCR、LLM 纠错、主观文本改写或外部网络补全。任何丢失来源证据的中间结果只能 INCOMPLETE/held。

## 7. Wave P3 — 保守原生关系、过滤与分组

| ID / 估时 | 工作域 | 最小独立验收 |
| --- | --- | --- |
| P3-01 / 20m | 关系恢复 | 同源确证 reply-parent/ancestor/quote-source 各自分开记录 |
| P3-02 / 20m | 关系审查 | cycle、missing parent、重复 Message-ID、跨 scope 不自动确认 |
| P3-03 / 20m | 规则过滤 | all-matching rule IDs、有版本评估、include/exclude/conflict/unknown |
| P3-04 / 20m | Outlook native grouping | conversation only candidate，subject similarity 不直接合并 |
| P3-05 / 20m | Teams grouping | Teams chat reply vs channel scope，component-only refresh 不造 body |
| P3-06 / 20m | 非通信来源 | Calendar / To Do / OneDrive / Contacts 的上下文按类型/范围发布 |
| P3-07 / 20m | replay-policy | configuration/policy/code 变更形成明确新 key；同输入稳定 idempotency |
| P3-08 / 20m | scoped transitions | presence/absence/membership deletion/content refresh 保持正确 authority |
| P3-09 / 25m | reviewer | 未解释链接保留 unknown；无跨 Workset 假关联，完整限制传播 |

P3 纯函数可与 P1/P2 并行，但必须依赖冻结的 C0 `NativeRelations`、`FilterDisposition`、`GroupingDisposition`。新 topic AI classification 不在本阶段。

## 8. Wave T0 — 独立黄金测试（与 P1/P2/P3 并行）

| ID / 估时 | Gold fixture 主题 | 防止的自证循环 |
| --- | --- | --- |
| T0-01 / 20m | A1 20 spider / 7 streams / 原 Task15 固定行为 | 不由新 Kedro 作者重写 A1 接受规则 |
| T0-02 / 20m | Mail 多 MIME/inline quote/duplicate Message-ID | 另人独立标注贡献/引用/祖先和缺失 |
| T0-03 / 20m | Teams chat/channel/component-only/scope refresh | 不能凭同 thread ID 猜亲属关系 |
| T0-04 / 20m | Calendar、To Do、OneDrive、Contacts | contextual 不强行进入通信 grouping |
| T0-05 / 20m | PDF、Word、Excel + malformed/large/partial | 解析错误不得伪装完整内容 |
| T0-06 / 20m | A2-held/intake-held/transition-only | 要么有已接受 prepared@2，要么有 held，不能 missing/overlap |
| T0-07 / 20m | crash/restart/late writes/cancel | accepted prefix 保存，未完成必须可重放 |
| T0-08 / 20m | policy upgrade / A3 historical reader | 旧 prepared@1 可读、新 prepared@2 正确映射 |
| T0-09 / 20m | Prefect lost/duplicate hint/partial A1 finish | 唯一 authority 是 committed release/cursor |
| T0-10 / 20m | security/path/privacy/network | Node.run logger、PII canary、telemetry、非法 Dataset path |
| T0-11 / 25m | independent gold author/reviewer | Oracle 数据由未写算法的人审核，不允许从算法输出自动生成 expected |

T0 默认合成输入和本地 Graph fixture，不上传任何用户邮件/真实 provider 对话到 Agent 或第三方。

## 9. Wave E0 — 真正的 A2 跨阶段集成与 durable receipts

| ID / 估时 | 交付内容与针对性门禁 |
| --- | --- |
| E0-01 / 25m | Workset PREPARE + partition PREPARE + transition PREPARE 真实 claim；每个 claim owner/required_inputs 清晰 |
| E0-02 / 20m | Full Kedro DAG K0–K11 从 Workset@1 端到 v2 receipt；不走 legacy A2 控制环 |
| E0-03 / 25m | 每个 Dataset 保存点故障注入；前面已提交的接受记录不丢、后续阶段不出现 |
| E0-04 / 25m | 两合法 claim 键碰撞、过期/替换、并发前后 start barrier；数据库只有一个 logical output |
| E0-05 / 20m | Postcommit cancellation：返回 CancelledError 而数据已存，下一轮 query/reconcile 不重复 parser |
| E0-06 / 25m | Workset-aggregate v2 receipt：一个选中 occurrence 一个 outcome + transition batch + intake-held |
| E0-07 / 20m | Held-only 被标记 terminal INCOMPLETE；pending index 无永续 spin；operator replay append-only |
| E0-08 / 20m | Wrong role/ambiguous release re-read → A2-held，A1 原结果/cursor 字节不变 |
| E0-09 / 20m | A3 所有 typed prepared@2 +历史 prepared@1 与 limitation，A5 仍读取恰当 triage output |
| E0-10 / 20m | 按现有 Application async invocation 和 CLI `prepare-scheduled` 做一条真正 release→prepare 流 |
| E0-11 / 25m | 格式 × 来源 × scope 集成，断流后重放、无已提交 entry 时 no-op、跨源全局序列 gap |
| E0-12 / 25m | 失效清单、可追溯完整引用和清理边界；独立 reviewer 只读 exact SHA |

## 10. Wave I0 — 外部 wakeup、CLI 与受控切换

| ID / 估时 | 具体交付与验收 |
| --- | --- |
| I0-01 / 20m | 独立纯逻辑 scheduler 状态机：pending/busy/held/BLOCKED/FAILED/CANCELLED 不混淆 |
| I0-02 / 20m | `scope-status` allowlisted CLI，scope hash / cursor digest / pending/held counts / last receipt，不含 PII |
| I0-03 / 20m | Prefect（或外部启动器）无 payload finite wakeup 定义，只发提示不修改 A1 |
| I0-04 / 20m | real command wrapper 调用既有 `prepare-scheduled`，锁定稳定 consumer/catalog pin，不读私有 SQL |
| I0-05 / 20m | A1 完成/部分失败/重复通知/失联提醒后，依照 committed release 和 durable cursor 恢复 |
| I0-06 / 20m | 同 scope 重叠 invocation coalesce、claim-busy 退避、no-progress 上限，无无限循环 |
| I0-07 / 25m | Disabled/staging 部署验证及一条真实 A1→Kedro A2 流，先不放大并发 |
| I0-08 / 25m | 旧 pending workset 清零核查、旧 engine 过渡与稳定回滚 anchor、历史 A3 读路径 |
| I0-09 / 20m | 生产启动 runbook、停止/恢复/报警分支、消除双引擎自动 fallback |
| I0-10 / 20m | 用户明确确认后才可启用生产 Prefect、执行 DB schema migration 或正式 switch |

I0-10 是不允许 Agent 自行做出的生产授权；即使用户先前同意开发，也不能当成对真实生产数据迁移与安全例外的自动批准。

## 11. Wave V0 — 完整质量矩阵与独立验收

| ID / 估时 | 完成的客观证据 |
| --- | --- |
| V0-01 / 20m | DAG Graph 测试：验证 extract/parse/normalize/zone/native/filter/group/semantic save 全由 Kedro 依赖连接 |
| V0-02 / 20m | 原 A1 20 Spider/13 Task15 scenarios/28 gates 的源代码不动，单独跑只读兼容检查 |
| V0-03 / 20m | A1 release/selection/ordinal/role/byte digest：七 stream、历史 baseline 和多 occurrence |
| V0-04 / 20m | MIME/PDF/Word/Excel/JSON/HTML 和 span/limitation golden，独立 gold reviewer |
| V0-05 / 20m | 关系/规则/分组异常：无法归属、跨 scope、重复 ID、source-native context |
| V0-06 / 20m | async cancel、CPU/GIL、parser cgroup、child cleanup、max RSS、无 orphan、无 writer after claim expiry |
| V0-07 / 25m | 数据库迁移 v2/3/4→v5、旧结构/trigger/占用表/legacy hash 拒绝、失败原子回滚 |
| V0-08 / 20m | 完整 v2 acceptance/receipt/held-index、conflicting SHA/attempt、并发和 late crash 恢复 |
| V0-09 / 20m | A3/A5 老数据加载、新输入 typed 适配、限制贯穿，历史不重写 |
| V0-10 / 20m | Prefect hint 丢失/重复/partial failure、cursor 不漂移、pending backpressure |
| V0-11 / 20m | Python 3.12/3.13/3.14、Pi aarch64 和 x86/Linux、Mac/Windows smoke；不能把 `-O` synthetic 冒充全量 |
| V0-12 / 20m | GitHub 全部必需 checks：`ruff check` / `ruff format --check` / Pyright / pre-commit / gitleaks / pytest / cgroup-v2 / wheel install |
| V0-13 / 20m | 无新增 CVE ignore/telemetry、未授权网络、隐私 canary；完整锁及版本 hash 审计 |
| V0-14 / 25m | 生产前独立 exact SHA R1/R2 逐项审查；保存 rejected 历史；真正 ACCEPT 才允许 R0 |

**测试执行效率策略**：子任务先跑相关 1–3 个测试文件 → 每个集成 PR 跑 impacted boundary / Pyright → 每阶段一次必要矩阵/CI → V0 才跑完全量，避免每修一个小问题就重复跑全部耗时测试。不允许用 skipped/insecure mock 替代硬 gate。

## 12. Wave R0 — 旧 A2 正式退役、发布与恢复

| ID / 估时 | 动作与界限 |
| --- | --- |
| R0-01 / 20m | 归档旧 A2 Git SHA、历史 schema/compat fixtures、错误行为负面测试，确认新 pipeline 已接受 |
| R0-02 / 20m | 最后一次 audit：有旧 pending Workset 则阻止切换；不能原地重诠释 frozen code/config |
| R0-03 / 20m | 清点 obsolete Handler/RecordSteps/StageSteps、旧 CLI dispatch、重复 dependencies；只删除明确可替代代码 |
| R0-04 / 20m | A1/A3/A5 逆向依赖扫描、旧功能负面测试和安全回归通过 |
| R0-05 / 20m | 生产备份、迁移与 activation 详细证据日志，保证停止时可恢复旧快照；不虚称数据库 git rollback |
| R0-06 / 20m | 用户签署 cutover 决策后，小范围 scope 验证、read-only 指标确认，再配置下一个 scope |
| R0-07 / 20m | GitHub 合并/工作树和远程分支清理，仅删除已经合并且不再使用的分支；保留审查证据 |
| R0-08 / 20m | Final acceptance index：版本、commit/PR、CI、风险声明和操作 runbook，明确不再长期双引擎 |

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

### 15.1 本轮文档交付的退出条件

本轮结束前只要求：三份 Markdown 文档、现状核查、格式/链接/表格检查、单独 docs-only Git commit/草稿 PR（如连接正常），以及对文档本身的独立只读复审或清晰说明审查尚未完成。

**本轮不执行 CR、F0、C0、P1、P2、P3 代码实现，也不启动持续性本地 AI Task Manager。** 用户阅读三份文档并讨论执行顺序、并发、资源/安全批准后，再正式授权执行。这样“现在不用人工接触设备”也不再被误解为“Agent 已经在后台工作”。

# msgloom A2 v2 — 本地 AI Task Manager 交接、监督与恢复协议

> **仅供审批后的执行使用。当前状态：NOT STARTED，不代表任何 Agent 已启动。**
> 架构：[2026-10-23-a2-kedro-v2-architecture.md](2026-10-23-a2-kedro-v2-architecture.md)。
> 任务和质量门禁：[实施计划](2026-10-23-a2-kedro-v2-execution-plan.md) 与 [151 条任务 DAG](2026-10-23-a2-kedro-v2-task-manifest.json)。
> 本协议必须在用户同意正式开始实施后才作为 Task Manager 的指令输入。

## 1. 用户批准前的必要信息

| 项目 | 预设 / 不可自行推断 |
| --- | --- |
| Manager 运行主机 | 第一选择现有 Raspberry Pi 5；Sextant/第二 Pi 只有在 repo/CLI 权限和 agent 连接被真实验证后可增加 |
| 本地 Manager | Claude Code Sonnet，High reasoning，受控的持久 OS session；从不假定 UI remote-control daemon 就是正在运行开发任务 |
| 默认工作模式 | Supervisor → Manager → 多个本地 subagents；Git branch/worktree 分离；CI 与 GitHub PR 归档 |
| 并行上限 | 配置 `max_workers`，建议 Pi 先 2 个重任务+1 轻任务，不以某个固定槽数作为永久约束 |
| 单任务时长目标 | 10–25 分钟；超过 30 分钟分拆，不在一个任务里做全项目调查 |
| 模型偏好 | Sonnet Medium 通常足够；重要安全/迁移/async 边界用 Sonnet High；轻量型号须先确认 CLI 确有该型号。默认不选 Opus |
| Git 操作 | 一任务一 branch/worktree，一 reviewer 只读；未经批准不修改 A1/master，也不自动合并或生产切换 |
| 保密 | 不把用户私有邮件、会话数据、token、credentials 放进 agent prompt、console report、PR 或模型外部服务 |
| 安全决定 | Kedro Snyk CVE-2026-3840 仍存在未决报告；不得自行签署 residual-risk 例外 |
| 本阶段授权边界 | 只在**后来用户明确批准执行后**，才运行下面的管理流程。本文档交付期间不启动长期 Agent |

## 2. Manager 只读前置核验（首轮，不允许直接实现）

1. 使用真实 MCP Pi 工具读出仓库和 worktree 的现在状态。记录 `git rev-parse HEAD`、`git status --short --branch`、已存在的 docs/design/Q0/C0 分支与待提交 C0 修改。不能在有未跟踪研究文件的主工作树执行粗暴 `git clean`。
2. 从 GitHub 实时取 PR #68、#69、#70 和当前实施蓝图草稿 PR，获取最新 base/head SHA/CI；不能把 2026-10-23 记录的历史 SHA 当作当前 HEAD。
3. 验证真实 Python：3.12/3.13/3.14、Scrapy 2.19.0、项目锁以及是否安装 Claude Code/Codex；只读确认 CLI 支持的 model/effort 参数，不假定 UI 名称是 CLI 参数。
4. 验证 `tmux` 或用户允许的持久作业服务存在；必须具备可查询 process ID、实际启动时间、stdout/stderr log、exit code、heartbeat 与终止/恢复手段。`claude --print` 的一次性退出**不等于**启动了持久 Task Manager。
5. 确定一个 integration owner、一个 dependency/SQL schema owner，锁定可编辑路径和每个 worker 的隔离 worktree。把重叠的 C0 测试编辑串行化。
6. 从 `2026-10-23-a2-kedro-v2-task-manifest.json` 的 151 条 `id/depends_on/edit_paths/required_gates/timebox_minutes/model/effort` 计算可运行队列，检验 gate 实际证据。CR 和 F0 可并行；CR R2 后可做不依赖 Kedro 的 provisional C0，但 C0 最终验收和正式 Kedro dependency 仍须 F0 技术证据及必要的用户安全决策。CR 与 F0 可以并行研究；生产 C0 的 freeze 不得越过 CR R2 和 F0 安全 gate。
7. 创建第一份本地 machine-readable 状态快照（不含敏感路径原文/凭据），证明 Manager 真正存在，再开始分派。
8. 最终向 Supervisor 报告：Manager 的 **真实 job_id/PID、host、state、branch、time started、已经分配的第一批 task IDs**。没有这些证据就必须写 `NOT STARTED` 或 `STOPPED`。

### 2.1 可以接受的持久执行器

首选有明确 PID + 可恢复 workspace 的 `tmux` 长期 session 或受限 local agent supervisor service。它可以在用户不打开 MacBook 屏幕时运行，但必须真实启动并可读日志。一个 MCP 工具启动后返回了 `job_id` 时，必须进一步核查 `job_status` 为 RUNNING。若模型 CLI 只能 one-shot，必须由真实的 manager-side daemon/queue 逐次派发新 one-shot 任务；不能把一条 `claude --print` 命令包装成“正在自动管理全部工作”。

当前机器上的 `claude remote-control`、`codex app-server` 常驻进程不自动证明具体 C0 工作在运行。

## 3. 启动时 Manager 必须阅读的最小入口

**必须：**

- 本目录架构、实施计划和本交接协议三份主体文档加机器任务 DAG 和 JSON。
- 根 `AGENTS.md`（<500 行模块、测试无 `assert`、任务范围限制）。
- [PR #68](https://github.com/grammy-jiang/msgloom/pull/68) 的已验收源架构，以及关联 ADR/handoff doc（若还未进入 master，从对应 worktree 或精确 SHA 读取）。
- [PR #69](https://github.com/grammy-jiang/msgloom/pull/69) 的 Q0 exact SHA/独立 R2 ACCEPT/6×20 raw matrix。
- [PR #70](https://github.com/grammy-jiang/msgloom/pull/70) 的 C0 R1 REVISE 和未提交整改状态。必须保留 reviewer transcript 和现有已修复内容。

**只由对应 worker 局部阅读：** CR 读 C0 prototype/tests/`intake_completion.py`；F0 读 exact wheel/source/security policy/`pyproject.toml`/`uv.lock`；C0 SQL owner 读 `schema_store.py`/`store.py`/`async_store.py`/`preparation_proof.py`；A3 owner 读 `triage_input/codec.py`/`triage_pipeline/handler.py`。不要让每个小 Agent 对整个 repo 再做一遍开放式“调查”。

### 3.1 与设计审查一致的两阶段授权

- F0-08 独立审查只负责 Kedro 候选风险适用性的**技术判断**；如果 Snyk 告警无法明确排除风险，`gate:F0-risk-owner` 必须由用户决定，AI 不得自动签署。
- C0-00 是 **provisional** 字段/版本冻结；研究性合同与临时 SQLite test 可在 F0 仍待批时进行。只有真实 v2 finalizer、受审查的 `triage_input@2` 和 C0-20c/F0 条件均成立才允许生产 C0 final freeze。
- 本轮交付仅生成文档与一次性只读 review。未来只有启动可核查的持久 Manager 服务、取得 PID/job/heartbeat 后才会向用户报告 `RUNNING`。

## 4. Task Manager 实际调度算法

每个任务状态是：

```text
BLOCKED  -- unmet dependency/security/owner decision
READY    -- preconditions resolved and files free
RUNNING  -- verified PID/job & owned worktree exist
REVIEW   -- focused tests succeeded, requires peer/exact-SHA review
ACCEPTED -- reviewer and CI confirmed for precisely this SHA
REVISE   -- independent reviewer found defects; spawn bounded new tasks
FAILED   -- failed with owned logs and reason; recover or escalate
STOPPED  -- process exited/no running worker; no invisible progress
```

伪实现步骤：

1. 读取当前 `READY` tasks，按最少阻塞下游的 critical path 优先：CR、F0、C0 core schema、A3 adapter；可同时准备 fixture。
2. 仅调度资源预算内的 tasks（CPU/RSS/API/network 使用项目默认上限；安全/DB 文件冲突锁比并发数优先）。
3. 为每个任务生成非共享 worktree/branch 和具体 worker prompt；记录 parent task、开始时间、预期产出、允许编辑路径和必须读取的源文件。
4. 捕获真实 stdout/stderr、exit code；每次作业结束必须先验证文件变更、针对性测试通过，再允许 Git commit。状态不是依据模型说“Done”。
5. 单个失败先执行有限、有证据的恢复：一次环境问题重试；若是真实测试红灯，直接提一个修复子任务。相同问题反复不进展时禁用盲重试并 escalate。
6. 先让测试最接近代码的小 PR 通过，再收敛 integration branch，顺序 rebase/squash 按用户规定。**不能为了省 CI 而把未审核代码直接绕过 required checks。**
7. 分派独立 reviewer 的 read-only review 对象是一个精确 SHA（无源码写权限）。REVISE 必须保留 transcript，再新 commit 复审。
8. 每个 gate ACCEPT 时才解除下游依赖；F0 风险处置与 DB migration/cutover 需要用户批准，不由 Manager 自助模拟批准。
9. 运行状态被 Supervisor 查询时立即刷新 process/job/PR/CI，不引用上一次缓存状态冒充“实时”。
10. 所有 workstreams 真正完成之后，经理产出最终 evidence index / branch cleanup proposal，等待用户批准生产切换。

### 4.1 排他文件 ownership 和独占基准资源

所有 `edit_paths` 要展开成实际受控路径，并由单个 writer owner 排他持有；共享 schema/async_store/intake_store/A3 codec 的冲突必须串行集成。一个子代理不能编辑其分配外的路径或污染另一个 worktree。独立 reviewer 只读且不能自审自己提交的 SHA。

Pi 上 P1/P2/V0 真实 RSS、native child、event-loop jitter、claim-lease 性能测试需要单独的 `exclusive-benchmark` 锁：暂停其它 CPU-heavy workers，保留运行平台、负载和上下界。否则这些测量不能用于配置生产租期。

### 4.2 持久任务是否真的在执行

Manager 必须由用户批准后建立真实的可恢复 OS process/service 和持久 queue，记录真实 PID、开始时刻、事件和 worker exit code；每次消息结束时如果没有活着的 task manager，就报告 STOPPED。常驻 `claude remote-control` 或 `codex app-server` 本身不能证明 C0 开发任务仍在运行。

## 5. 给每个本地 Coding Worker 的完整模板

下述占位符必须在分派前填入，不能直接把尖括号文本发给子 Agent。

```text
TASK_ID: <phase-task-id>
DEPENDS_ON: <evidence-for-every-required-task-or-gate>
PARENT: <manager-batch-id>
BASE_SHA: <pinned-integration-sha>
OWN_WORKTREE: <explicit-existing-or-allocated-path>
BRANCH: <owned-feature-branch>
MODEL: <verified-model>
THINKING: <verified-effort>
TIMEBOX: 20 minutes (split after 30 minutes)
OWNER_FILES: <exact allowlist>
PROTECTED_FILES: message_ingest/**, microsoft_graph/**, accepted A1 handoff;
                 master, pyproject.toml, uv.lock, schema_store.py unless owner
REQUIRED_READS:
  - <exact file paths and applicable fixed docs; no broad web/ChatGPT research>
GOAL:
  - <one observable contract-level behavior, not an architectural rewrite>
IMPLEMENTATION:
  - <specific new functions or test fixtures, migration rule, error path>
NEGATIVE_CASES:
  - <separate adversarial tests and expected outcomes>
VERIFY:
  - <exact targeted pytest files/command>
  - ruff check/format on changed paths
  - pyright for typed files when applicable
ACCEPT:
  - <measurable output, updated docs if behavior changes, no secrets>
REPORT:
  - commit SHA, changed files, actual test exit codes, CI URL, limitations
ESCALATE_ONLY:
  - owner security risk, A1 mutation, unapproved dependency, live DB migration,
    inability to reproduce exact frozen input
Do not ask user about minor implementation choices. Report BLOCKED with
evidence rather than guessing source, security, or schema semantics.
```

**Worker 工作风格：** 先验证少量权威代码签名，不重做全部前期 research。明确输入/输出；可复用旧 helper 只有在接口、安全和测试证明相容的情况下。所有测试必须通过真实 Python 运行而非“预计可通过”。每次 CR 修复至少带一个会在修复前失败的负面测试，以免假阳性。

## 6. 降低 token/时间开销但不牺牲质量

- 优先 **Sonnet Medium** 做限定的 Python 模块、纯转换、已冻结 schema codec；**High** 仅用于安全审查、SQLite migration、claim/cancellation、A3 版本边界与最终 reviewer。
- 轻量模型（如果当前安装）用于固定格式/对照 fixture/Markdown 表格，禁止决定安全、SQL/DB schema 或 A1 authority。
- 任务单元由 Manager 事先具体描述；避免每个 Agent 都索引全部 Git 历史、重新检索互联网、重新设计 Kedro。必要时 Manager 探索一次，给 worker 结论和精确文件名。
- 优先小范围 test → impacted CI → integration full CI，不要每一步都触发 10-job GitHub matrix；但每个正式合并候选必须最终获得 required full CI。
- 按依赖边界批量排队，不产生数十个可合并但未审查的小 PR。
- 允许理性的自主判断，不允许自动风险豁免、抢占他人修改或使用未授权代理账户/模型。若某模型额度不足，Manager 按真实可用模型降级，并记录不同模型对审查质量的影响。

## 7. Status 查询的最低可靠证据

每次向用户汇报时返回下面这些可验证字段；如果某字段不可查询，写 `UNKNOWN` 而不是想象。

```json
{
  "project": "msgloom-a2-kedro-v2",
  "supervisor_state": "ACTIVE_CHAT|STOPPED",
  "manager": {
    "state": "RUNNING|STOPPED|NOT_STARTED|UNKNOWN",
    "host": "raspberry-pi",
    "pid_or_job_id": null,
    "started_at": null,
    "last_heartbeat": null
  },
  "gate": "CR|F0|C0|P1|P2|P3|T0|E0|I0|V0|R0",
  "tasks": {
    "ready": [],
    "running": [],
    "review": [],
    "accepted": [],
    "blocked": []
  },
  "repo": {
    "branch": null,
    "head_sha": null,
    "dirty": null,
    "pr_urls": [],
    "ci_state": "PASS|FAIL|IN_PROGRESS|UNKNOWN"
  },
  "stops": [],
  "next_unblocked_task_ids": [],
  "needs_user_action": false
}
```

- `pid_or_job_id` 为 `null` 时，不能直接说 Manager 正在运行。
- `last_heartbeat` 只用于判断是否需要真实进程核查；历史 heartbeat 不等于进程仍活着。
- Reviewer ACCEPT 只覆盖它读到的 exact SHA；后续 bookkeeping-only commit 必须说明源码未变。
- R1/R2 每轮 REVISE/FAIL 都必须进入日志索引，不可隐藏后仅显示最新绿色。
- 无后台自动化或常驻 manager 时，Supervisor 一旦结束当前回复，必须坦白 **没有自动继续执行**。

## 8. 用户决策与操作权限清单

以下问题经理可以在既定计划内自行解决：

- 修复 Pyright/ruff/pre-commit；
- 明确 canonical codec / input-only accepted SHA 细节；
- 独立 SQLite test fixture；
- 有监督的 Git rebase/PR draft/功能测试；
- 子 Agent 失败任务重试及文件冲突。

但以下必须升级并停止对应危险路径：

1. Snyk CVE-2026-3840 的最终风险适用性仍无法消除，需要新增 Kedro 安全豁免。
2. 修改已接受 A1 output、ReleaseReader/Intake 语义或 release ledger / cursor。
3. 生产 `pyproject.toml`/`uv.lock` 添加未批准存在漏洞的依赖，或改变安全 CI 忽略策略。
4. 对生产数据库进行真实 schema migration、删除历史记录、强制清理未处理 workset。
5. 触及用户真实 Graph credentials、网络授权、包含私有内容的测试数据。
6. 切换生产 A2、部署/启用 Prefect、删除旧 A2 运行分支、不可逆数据清理。

**本用户轮次的已授权工作仅为文档设计与审查。** 即使本文件作为 Manager prompt 写好了，也不可据此直接运行实施。

## 9. 启动前讨论建议

推荐用户明确决定：A. 使用 Pi 上 Claude Code Sonnet High 作为真实长期 Task Manager（优先建议）；B. 先串行由 Supervisor 用远程命令做少量 C0 修复（并不满足用户已选 Agent 工作流）。

建议采用 **A**，但在启动前先审批本设计和实施计划、经理资源上限、是否引入 Sextant 作为第二 worker 主机，以及安全报告冲突时的升级策略。正式启动命令/进程必须在那一轮工具真实执行后向用户回报，**不能在这份文档里提前宣告已经启动**。

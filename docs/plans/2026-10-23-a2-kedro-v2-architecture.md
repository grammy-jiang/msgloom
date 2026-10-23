# msgloom A2 v2 — Kedro 主导 ETL 完整架构设计

> **状态：实施前设计候选，不是生产验收或变更授权。**
> 修订基线：2026-10-23（Australia/Sydney）；源代码基线：`master` = `895fc40a0ec889bd96f620df8c62491787218217`。
> 用户既定决策：Kedro 作为 **A2 整条 ETL DAG 的主框架**；淘汰错误的旧 A2，而不重写已验收的 A1。
> 关联文档：[实施与验收计划](2026-10-23-a2-kedro-v2-execution-plan.md)、[本地 Agent 执行协议](2026-10-23-a2-kedro-v2-agent-handoff.md)。
> 本文件在全新的 **documentation-only** 分支上编写；不导入 Kedro、不修改生产模式、不启动 Agent 或切换生产服务。

## 1. 本次重设计的权威依据与已知事实

| 依据 / 证据 | 已确认 | **没有**证明 |
| --- | --- | --- |
| 已验收 A1：SHA `34057c6c9f85688fd2bd1868d90302ab5a61205f`；Task15 28 项门禁 | ReleaseGroup、ReleaseEntryRef、真实来源证据、冻结 Intake/cursor/held 的既有边界 | 新 Kedro A2 的正确性 |
| [PR #68](https://github.com/grammy-jiang/msgloom/pull/68)：架构 D4 R6 ACCEPT，审查 SHA `878121fa9ab7ca35754b36d824440a77e92f5f4d` | Kedro 主 ETL、A1→A2 自然衔接和 A3 适配方向 | 生产 Kedro、Prefect 已部署 |
| [PR #69](https://github.com/grammy-jiang/msgloom/pull/69)：Q0 R2 ACCEPT，SHA `5f1050a4939f1ec44e3326df10d83fc686f72721`，CI 全绿 | Kedro 1.7.0 在 Pi aarch64、Python 3.12/3.13/3.14 下的 **隔离合成 DAG/异步桥** 可行 | 真实 SQLite claim、真实 parser child/cgroup、生产安全批准 |
| [PR #70](https://github.com/grammy-jiang/msgloom/pull/70)：C0 R1 REVISE，SHA `0eb8fe6d2e5d301c359b60292c1852bbe7558c6d` | 19 项隔离研究测试：真实 A1 Mail 单条 release、Phase1Persistence 和临时接受索引；旧 V1 机制限制得到证实 | C0 契约冻版、生产持久化迁移、全流/全角色验证。该 SHA 的 CI 为 9/10，Pyright 失败 |
| 代码：`msgloom/persistence/schema_store.py` | 当前持久化 schema 版本为 **4**；有固定 legacy schema 指纹和严格迁移约束 | 能直接在当前表上增列/自建表或把研究临时表带入生产 |

以上三项 PR 目前都是 **draft、未合并**。C0 工作区存在 R1 之后未提交的改动，不能将其视为 PR #70 已通过整改。旧 A2 在正式切换前仍是生产路径；旧实现只作为 **行为核查、负面测试和回归基线**，不是新架构的运行方式。

### 1.1 设计权威优先级和 D4 差异

**权威顺序：** 用户 Kedro-primary 决策 > 已接受 A1 入口/证据 > D4 R6 的架构和 AUTO-01–25 > 本轮补充候选。本三文件在单独 docs-only 分支，原 [PR #68](https://github.com/grammy-jiang/msgloom/pull/68) D4 及 A1 automatic-handoff 内容不会因本分支未复制而失效。与 D4 冲突的行为必须列入独立审查，而不是静默覆盖。

| 增量细化 | D4 差异处理 |
| --- | --- |
| v2 transition 批次接收 | 整个有序列表进入 input-only batch key，**逐条包含并验证 D4 要求的原始 fact ID、scope、kind 与 authority** |
| 新 A2 v2 finalizer | 新增原子 pending→terminal 与 v1/v2 互斥围栏；只影响 A2 downstream completion，不改 A1 admission |
| A3 输入 | 建议新 `triage_input@2` 绑定 `prepared@2`、`filter_result@2`、`group_result@2`；历史 v1 必须仍可读 |
| 部署/安全 | 正式数据库迁移只能由操作者显式执行，不得因启动新二进制而自动发生 |
| 验收 | 完整保留 D4 V01–V16、V13 相同输入性能不得无理由退化超过 10%、V14 DAG/bridge 复杂度、V16 AUTO-01–25 |
| 例外映射 | 保留 `scheduled-invalid-authority`；intake/preflight 原始可信 SourceReferenceError → BLOCKED，post-intake 已选证据丢失 → A2-held |

若 C0/F0 尚未获准，则此处只表示架构提案；D4 既有验收独立有效。

### 1.2 不可改变的前提

1. A1 只负责 provider 采集、原始证据、权威事实、原子 ReleaseGroup/Entry 与 checkpoint；A2 不再抓取 Graph、枚举 mutable 表或重做 intake。
2. 保留原有 `ReleaseSourceReader`、`PreparationIntakeService`、`PreparationIntakeWorkset@1`、消费者 cursor、pending/held、公认的历史 baseline 和 source-scoped transition 语义。**不能因为代码目前放在 preparation_pipeline/ 就误判它属于可淘汰的旧 A2。**
3. 消费的是 **冻结且可验证的 A1 结果**。ReleaseEntry 的全局 sequence 允许按 source/stream 出现不连续；同一 source VersionRef 在两个 release 中可能是两个不同的 occurrence。
4. Kedro `Pipeline`、`DataCatalog` 和 `SequentialRunner(is_async=False)` 必须完整拥有 A2 各计算/保存节点的依赖图。禁止“旧 Handler 先处理 90%，然后调用两节点 Kedro”。
5. Application 保持 `async def`。Kedro 同步 runner 只能在受控、可回收且计数的工作线程内执行；SQLite claim、交易、parser 子进程等业务权威归 msgloom，而非 Kedro。
6. 不擅自增加跨源 AI topic joining、OCR 云服务、Graph 写权限、A1 行为改动或永久的 `A2_ENGINE` 双运行模式。
7. 本设计描述的 v2 类型/表名只是**待验证方案**；实际迁移、pin 和切换须经过独立 exact-SHA 审查。

## 2. 架构及责任边界

```text
A1 native Scrapy acquisition -> committed immutable ReleaseEntry/evidence
  -> existing ReleaseSourceReader + IntakeService
  -> frozen Workset@1 / CollectedSelection@1 / cursor / held
  -> async Application verifies authority and saved workset shape ONLY
  -> Kedro SequentialRunner off-event-loop, closed DataCatalog
       K0 exact ReleaseReader/selection/role verifier inside Kedro graph
       K1..K9 extract/parse/normalize/zones/native/filter/group
         every stage output -> ClaimFencedSemanticDataset.save()
         immediate accepted ref -> downstream stage input/key
       scoped transitions -> one separately fenced accepted batch
       K10 manifest from already-accepted stage refs
       K11 v2 receipt -> atomic A2 v2 workset finalizer
  -> existing pending Workset becomes terminal COMPLETE or INCOMPLETE
  -> A3 triage_input@2; historical prepared@1/triage_input@1 still readable
  -> A5 through verified A3 outputs

External Prefect/launcher -> finite prepare-scheduled and scope-status
               (hint only: not release authority or alternate checkpoint)
```

| 子系统 | 唯一所有者 | 禁止的跨界行为 |
| --- | --- | --- |
| A1 Spider、HTTP 与 Release、raw evidence | 原生 A1/Scrapy 2.19.0 | Kedro 节点不能处理 Spider 信号或自行 publish A1 |
| A1→A2 admission / cursor / held | 现有 ReleaseSourceReader + IntakeService | A2 不能回退或推进 intake cursor；另有独立 v2 finalizer 结束 Workset pending |
| DAG 节点依赖、拓扑和内存节点值 | Kedro 1.7.0 | Kedro Dataset 不能绕过 msgloom 交易、claim、内存/文件防护 |
| 语义模型、canonical codec、接受索引、ClaimToken | 新 A2 domain + `Phase1Persistence` 新受审查 API | 不能用外部 get-then-insert 冒充原子接受 |
| parser 子进程、CPU/RSS/timeout/cgroup 限制 | msgloom trusted isolation | 不能依赖无法终止的 CPU 线程实现强制资源隔离 |
| A3/A5 消费与历史兼容 | 显式版本读取适配层 | 新 `prepared@2` 不能强行被旧 `prepared@1` Codec 解码 |
| 外部触发/定期对账 | Prefect/launcher 调用有限 CLI | 不能依赖 workflow 状态或 Spider close 当 release 真相 |

## 3. A1 冻结输入与角色恢复

### 3.1 两层不可混淆的身份

- **Workset identity**：`ResultRef(kind="preparation_intake_workset", schema_version="1")`；A2 永远先读已持久化 Workset，验证关联 SemanticDataRef SHA、catalog/consumer/source/stream 和原始 code/config 版本。
- **选中 occurrence identity**：`(workset_ref, workset_selection_index, release_entry_ref, per_entry_ordinal, saved_collected_selection_ref)`。`workset_selection_index` 与 `per_entry_ordinal` 是两个不同维度；不能用 `selection_refs` 的去重结果替代 occurrences。历史 baseline 没有 ReleaseEntryRef，走明确批准的另一种身份。

### 3.2 增量 Release 的完整验证流程

1. 对 Workset 每个 `IntakeSelection` 调用 `ReleaseSourceReader.read_entry(selection.entry)`，要求其 `ReleasedInput.reference` 与原始冻结 `ReleaseEntryRef` **完全一致**，不可使用当前 provider 表。
2. 从已验收的 `released.facts` 原样取得有序 `(fact_id, role)`；枚举 `(released.selection, *released.components)`，忽略 `None`。`released.contexts` 不允许误变为新 message。
3. 对每一候选 ordinal，重建 A1 已验收的有版本身份输入：scope claim key + entry 的 JSON 模型 + 有序 fact/role 对 + 原始 config/code + ordinal。比对保存的 `intake-selection:<sha256>` ID，匹配数必须恰好等于 1。
4. 使用 `CollectedSelectionCodec` 比对 canonical bytes / 已保存 SHA（不能只按 source ID、subject 或 Python equality 猜角色）。匹配的第 0 个值是 primary（前提是 released.selection 存在），其余是 component。
5. 上下文、scoped transition 及 component_observation 触发的 context_refresh 要按同一 ReleaseEntry 的 fact/scope 保留；不能合成 parent body，也不能凭 role 之外的启发式扩大权威。
6. 证据缺失、ordinal 不匹配、关联歧义或不可验证字节：经 Kedro K0 的可信 Dataset.save() 新建 **持久化 A2-held disposition**，而不是修改 IntakeWorkset 或凭空生成 prepared。

生产实现必须从既有 A1 codec/identity 的**版本锁定公开只读 verifier** 获得结果。当前 C0 研究中复制的私有哈希算法，只能证明单条 Mail primary 合成夹具符合既有编码，不能当作长期 API。

### 3.3 历史 baseline 与全流保护

- `baseline_approval`、`baseline_sources`、`baseline_selections` 原样绑定 Workset；baseline root 使用 `role="baseline"`、批准标识及 exact `VersionRef`，**不得伪造 ReleaseEntryRef**。
- 验证 `read_baseline_selection(source)` 实际允许的源类型及保存 bytes；不能把它对某些类型的 manual reader fallback 默认为已批准历史。
- T0 fixture 要包括 Outlook Mail/Calendar、Teams chat/channel、To Do、OneDrive、Contacts 七种 stream 的 primary、component、context、transition、held-only、context-only、transition-only 以及全局 sequence gap。
- 验证只读不改变 A1 catalog、fact membership、release checksum、cursor、历史状态；重复 selected source VersionRef 不得跨 release 去重。

## 4. 版本化 A2 语义契约

以下是推荐的 **closed schema set**；最终字段在 C0 小 PR 中通过 canonical wire fixtures、严格 Pydantic/Codec 与独立审查冻结。序号后缀是建议且必须与依赖消费方一起确认，不允许静默换名。

| Artifact kind@version | 最小不可省字段 / 语义边界 |
| --- | --- |
| `frozen_source_selection@1` | workset ref、saved selection ref/sha、workset_index、entry/per-entry ordinal/role **或**批准 baseline 关联、scope |
| `extracted_components@1` | 原始保存字节引用、页面/MIME part/sheet/Word block 清单、格式依据、missing/unsupported/partial 明细和限制 |
| `parsed_parts@1` | parser profile/version、verified source hash、typed content blocks/tables、source spans、parse limitation、child worker exit |
| `normalized_content@1` | 原始 ↔ 规范化的可验证 span map；不可逆操作必须显式 LIMITATION，不可伪造 byte offset |
| `zones@1` | contribution、quote-occurrence、forward、signature、footer、unknown；区分“引用出现”与“引用作者归属” |
| `native_relations@1` | reply parent、ancestor、quoted-source hypothesis、证据与 scope；缺 parent、cycle、跨 scope 保留 unknown |
| `prepared@2` | 源/selection/role/ref、zone/relation/parsed lineage、结构化内容、时间/参与者、全部 limitations；不丢 body/attachment |
| `filter_result@2` | 所有命中规则和 policy/version、冲突/未知/排除原因；不得只保留最佳一条 |
| `group_result@2` | 来源原生 thread/reply 证据、exact scope、成员 ResultRefs、规则版本、未知关系，不以 subject 自动合并 |
| `prepared_transitions@2` | 同一个 workset 的 **有序完整 transition batch**、fact/scope/kind/reason、上下文引用；不生成虚假的 message |
| `a2_input_disposition@1` | 精确 workset selection occurrence/baseline、原始 SHA、失败原因、明确 operator_repair；不含虚构内容 |
| `a2_result_manifest@1` | 已接受 stage refs/digests、roots 与 transitions 覆盖、code/config/policy、限制和 provenance |
| `a2_completion_receipt@2` | 固定 workset Ref、所有 occurrence 的唯一 terminal disposition、transition batch、intake-held 强制不完整、接受索引与 claim 证明 |
| `a2_attempt_audit@1` | 执行/尝试/claim token、状态、时间戳和安全失败码；独立于逻辑接受身份 |
| `triage_input@2` | A3 typed prepared/filter/group@2 和 snapshot binding hash 的独立 v2 codec，历史 triage_input@1 不变 |

### 4.1 必须由模型级别和存储级别双重确保

- 所有导出对象严格 frozen、`extra="forbid"`、明确 max count/bytes、schema-version allowlist、canonical encode/decode 验证。测试不得利用 `model_copy(update=...)` 未重新验证而形成假阳性。
- 不允许动态 user-provided `kind`、module path、Kedro Dataset 类型或任意远程路径。
- 所有 acceptable stage 的 output SHA 和 byte count 是**独立输出证明**，不参与 logical input key。还必须保存 canonical StageResult metadata SHA（包括 status、limitations、input_refs、source_versions、config/code/policy）；重试时逐项校验，不仅是 payload SHA 一样。
- 明确以 `(kind, version)` 组成 allowlist：例如 `prepared@2` 才是新版准备完成；`prepared@1` 是历史读取格式。不能让任意 stage_kind 任意选 1/2。
- 用户可控制的 source metadata、邮箱地址、subject 和完整字节都不应进入 log、Kedro node name、DataCatalog dataset name 或 safe failure reason。
- 过去按 v1 保存的 `StageResult`、Codec 和 A3 结果不迁移覆盖、不重编码。

### 4.2 Held、baseline 和 v2 completion 业务规则

对增量 Workset，**每个按顺序冻结的 workset.selections occurrence** 必须恰好有一个实际持久化接受的 terminal：`prepared@2`（COMPLETE 或限制明确的 INCOMPLETE），或 `a2_input_disposition@1`（INCOMPLETE，operator_repair）。不可只使用去重后的 `selection_refs`。

**历史 baseline 例外**：此时 `workset.selections` 为空，roots 是按原批准顺序逐项对应的 `baseline_sources` 与 `baseline_selections`；必须验证批准的 exact VersionRef，不可伪造 ReleaseEntryRef。baseline/增量不能混合暗中转换。

`workset.transitions` 非空时必须完整保留有序 fact ID、scope、kind 与 authority，且恰好有一个已接受 `prepared_transitions@2` batch。context-only/transition-only 不需要制造 prepared body。`workset.held` 是冻结 intake-held，不可被新 A2 写回。

**COMPLETE** 只在：所有增量或 baseline roots 已真正 SQL 接受且完整、所有 transitions 完整、没有 intake-held 或 A2-held、v2 receipt 与 claims/历史执行凭证验证成功。任一 held 或 partial → **terminal INCOMPLETE**，不能成为无界 pending。

> **有意改变旧行为：** `intake_completion.py` 允许 held-only 且空 refs 的旧 Workset 被标成 COMPLETE；有 selected output 时也可能忽略 `workset.held`。新 v2 的强制 INCOMPLETE 不是旧版已实现的功能。不得修改历史 Workset@1 或 A1 admission。

结构完整的 Receipt 不代表结果已保存。v2 finalizer 要从数据库验证每一个保存的 StageResult、canonical SHA、input-only accepted key、stage metadata hash、status/limitations、published claim/plan 和 attempt 历史。跨执行/attempt 的已接受前缀可以被新 attempt 重用，但每项必须带原始可验证的 durable publication proof，**不能沿用旧 v1 所有 stage 必须同一 attempt 的限制**。

### 4.3 唯一 pending → terminal Writer（新增硬门禁）

现有唯一的 Workset terminal writer 是 `msgloom/persistence/intake_store.py:finalize_preparation_intake_workset`，其完成证明依赖 v1-only `intake_completion.py`。**新建明确版本化的 `finalize_a2_intake_workset_v2` 公共 async facade / 同步 SQL writer，并且设计必要的 v1/v2 双向围栏**；这属于 A2 下游处理，**不改现有 A1 IntakeService、Workset@1 字节、Release/consumer cursor**。

1. 在 writer lock 外读取确切 Workset@1 与 v2 receipt，验证数量、大小、source scope、每个 root/transition/held 和所有引用 payload 的 canonical 编码、历史 publisher receipts；不能仅用 caller-provided 结构。
2. 在受限 `BEGIN IMMEDIATE` 中对持有 Workset 的 PREPARE claim、plan/source required_inputs、每个 accepted-result metadata、原始发布 claim/attempt、当前 terminal status 做再次检验；只在锁内做 bounded metadata recheck。
3. **同一事务**更新现有 `phase1_preparation_intake_worksets` 的 `state="terminal"`、terminal_status、claim token、result_refs，并写 v2 receipt/producer-version 侧表；任何一步失败都回滚，仍是 pending。完成后现有 `select_preparation_intake_worksets` 不再返回它。
4. 旧 v1 finalizer 遇见 v2-marked Workset 必须拒绝；v2 finalizer 遇见 v1-owned/已 terminal 行也必须拒绝。此标记由受审查 schema/计划绑定生成，不由 provider 或用户传入。**同一 Workset 不能被 v1 与 v2 两条路径共同终结。**
5. 旧 terminal 历史不可变；显式 operator replay 只创建新的 append-only A2 attempt/receipt 并引用原 Workset，不覆写原 terminal row。held-only -> terminal INCOMPLETE；缺 refs/失效 claim 不能伪造成功。
6. 针对性真实 SQLite 负例必须覆盖：v1/v2 race、held-only、缺失/伪造 receipt、部分已提交、writer crash/post-COMMIT cancellation、重复终结、替代 claim、pending SELECT 与 schema migration。

生产 C0 契约未通过这条真实 finalizer/claim/receipt 的端到端测试前不能冻结或开始 E0。

## 5. 可重放的确定性接受键与 SQL 事务

### 5.1 输入身份公式

```text
logical_key = "a2-accepted:" + SHA256(
    domain_separator("a2-stage-accepted-input@1") ||
    canonical_json({
      trusted_scope_digest, workset_ref, partition_ordinal,
      ordered_resolved_selected_occurrences_or_exact_transition_batch,
      stage_kind, schema_version, ordered_accepted_upstream_result_refs,
      frozen_configuration_version, frozen_code_version,
      frozen_parser_version, frozen_filter_rule_version,
      frozen_group_policy_version, partition_policy_version
    })
)
```

允许基于同一 key 多个 execution/attempt/worker 重试；**不要**将 output digest、时间戳、执行尝试或 Kedro node name 纳入。transition key 必须绑定 **整个有序 batch** 及 workset scope，并逐项绑定 D4 要求的每一个确切 fact ID/scope/kind/authority；batch 身份并不替代单项事实完整性证明。

Accepted record 独立保存 `(logical_key, result_ref, canonical_output_sha256, canonical_byte_count, semantic_data_ref, canonical_stage_metadata_sha256, original_writer_claim_proof, frozen_lineage_digest)`；stage metadata SHA 覆盖 status、limitations、input_refs、版本及 lineage，不允许同数据但不同安全分类被视作等价。重放按 key 找到的输出必须同时验证保存的 StageResult 和 semantic data；相同输入不同字节（包括状态/限制元数据冲突）应 **fail closed**，原始记录不变。

### 5.2 现有 SQLite 限制、迁移门禁与唯一引擎路由

已验证：`Phase1Store.append_result_with_data()` 在 `BEGIN IMMEDIATE` 内校验 live claim 和 canonical data，但 `StageResult` 把 execution 与 attempt 锁在不可变元数据里。跨尝试重新 append 同一个 ID 即使字节相同也可能报 `ImmutableRecordError`；旧 `preparation_proof.py` 的 `prepare:` namespace 只支持 v1。不能只在 Registry 里添加 `prepared@2`。

**建议新增 A2-owned sidecar/schema v5 候选，最终是否使用元数据 revision 轴或 schema 主版本 5 要由 DB owner 独立决定**（现有 `schema_store.py` 的 legacy digest 和 `preparation_proof_revision` 是不可跳过的先例）：

- `phase1_a2_accepted_stages`：唯一 logical key、ResultRef、canonical bytes SHA/长度、StageResult metadata SHA、冻结 input/plan。
- `phase1_a2_stage_attempts`：尝试、错误/冲突、claim 与安全审计，独立于首个接受结果的 execution/attempt。
- `phase1_a2_input_dispositions`：索引 Workset/selection occurrence/baseline、held reason、修复策略。
- `phase1_a2_completion_receipts`：Workset+producer version 的真实完成凭证、claim/attempt 和 terminal digest，与旧 Workset terminal 更新在**同一事务**。
- `phase1_a2_producer_bindings`（可与 receipts 合并）：为每个 workset 标明可信 v1/v2 处理权，v1/v2 finalizer 必须互相拒绝重叠的写入权。

**绝对不能隐式迁移：** 当前 `Phase1Store.__init__` 会调用 `initialize_schema()`，如果把新 DDL 塞进该路径，**部署含新代码就可能自动升级生产数据库**；旧二进制会因为陌生的 owned table set 而拒绝读取。必须两阶段部署：

1. **Compatibility stage**：先提供能读取旧 schema4、也能识别未来 v2 schema 的新 binary；默认生产 dispatch 仍执行旧 A2。`initialize_schema` 在普通打开时不得创建新 A2 表或修改 schema marker；没有显式迁移就将新 v2 写功能拒绝。部署前检查 old pending、已终结但 held-only 被误标 COMPLETE 的历史、备份/恢复演练。
2. **Operator-gated maintenance**：经安全/C0/V0 审查与用户授权，停止接受新 A2 写入，拍摄并校验可恢复数据库快照，使用**专门的 migration CLI/受限操作** 显式执行结构、唯一索引与 schema/producer revision 迁移。验证只读旧结果、老 schema 迁移、失败回滚和 v1/v2 finalizer 互斥。再通过**受信任的单一 composition/backend binding** 切换 dispatch 至 Kedro v2。这个开关只是阶段性部署配置，切换成功后移除旧路径；不得长期保留公共 `A2_ENGINE` 和自动 fallback。
3. **Rollback**：还没迁移时可回滚兼容 binary；迁移后旧 binary 无法直接打开新 schema，故不能只靠 `git revert`。仅能按预先演练的 **数据库备份恢复 + 原 schema4 binary** 或经过审核的 forward-fix 恢复，须考虑迁移后的新写入和窗口状态；不承诺无损自动降级。

生产迁移要验证历史 schema V2/V3/V4 的精确 pin、表名碰撞/触发器拒绝、DDL 错误无半提交、大小写与只读老 ResultRef。禁止研究原型的 `MetaData.create_all()` 在生产对象初始化时偷偷创建新表。

### 5.3 原子接受/复用事务（伪代码）

```python
# preflight OUTSIDE SQLite write lock:
# - read accepted A1 Workset + verified source/role/ordered occurrences
# - canonicalize output and StageResult metadata, bound decoded bytes
# - resolve required upstream refs/plan and stage kind/version
# - ensure no unjoined worker from the last invocation
def append_or_verify_a2_stage(plan, expected_claim, encoded):
    with writer.begin_immediate() as tx:
        tx.require_live_claim(exact_token=expected_claim)
        tx.require_claim_attempt_and_frozen_required_inputs(plan)
        tx.require_schema_status_lineage_and_stage_kind(plan)
        accepted = tx.find_accepted_key(plan.input_only_logical_key)
        if accepted:
            tx.verify_metadata_sha_and_payload_digest(
                accepted, encoded.stage_metadata_sha, encoded.payload_sha
            )
            tx.verify_saved_immutable_result_and_claim_receipt(accepted)
            tx.append_idempotent_attempt_audit(...)
            return accepted.existing_result_ref
        tx.insert_canonical_bytes_and_stage(...)
        tx.insert_unique_accepted_key_and_original_claim_proof(...)
        tx.append_attempt_audit(...)
        tx.require_live_claim(exact_token=expected_claim)
    return new_accepted_result_ref
```

新 A2 每个 publish 在同一个事务内验证 required_inputs、原始发布 claim 归属、status/limitations/版本和 metadata hash。已接受前缀可能由不同历史 attempts 写入，需在 **v2 计划证明** 下保留各自的接受 history，而不能用旧 v1 的同 attempt 检查误杀合法重放。

写事务里的 metadata recheck 必须是 bounded O(number of refs) 且不重复解码大型 payload；复杂 canonical encoding/bytes 比较在锁外，锁内只比较可信 hash/length/immutable row 与受约束的索引。旧研究方案在锁内 decode 64 MiB payload 和直接访问私有 `_store` / `asyncio.to_thread`，不允许复制到生产；请新增正式 `Phase1Persistence` async facade 并通过其 semaphore、drain/close 路径执行所有数据库操作。

同一分区只能取得一个确定性 PREPARE claim；不同合法 claim 偶然尝试同 logical key 时，DB UNIQUE/BEGIN IMMEDIATE 必须阻止双 accepted。Postcommit cancel 不等于 rollback：下次先按 key 读取 StageResult/semantic metadata+data 验证，再跳过已有 stage；不得无限重试或重跑消耗性的 parser。

## 6. Kedro 主 DAG、即时阶段持久化和安全异步边界

**Graph 外只允许：** 受信任 CLI/Application authority preflight、保存 Workset@1 的只读元数据与图规模上限、唯一 workset claim/lease 的取得、静态闭合 DataCatalog 构造。不允许在图外完成 source role 还原、解析、过滤、分组、发布 A2-held/semantic StageResult。角色判定是在 **K0 dataset/node** 内通过 frozen Reader 验证而来。

**接受键要求所有 upstream 已接受 ResultRef，因此每条需要持久化的 stage 边必须立即保存，不存在末端统一 K10 之后才 publish 的设计。** 每个 stage 输出一个 typed `(semantic_value, accepted_ref, metadata_digest)`，其保存由该 stage 对应 `ClaimFencedSemanticDataset.save` 通过正式 facade 完成；下游节点从 `Dataset.load` 得到已验证的 accepted Ref 才能形成自己的 logical key。重跑时 dataset 首先查 durable accepted ref，验证 lineage 后复用并跳过受控解析。

| 阶段 | 真正 Kedro stage 与依赖 | 需要持久化的边/输出 |
| --- | --- | --- |
| K0 | `resolve_exact_frozen_roots`：从冻结 Workset + exact Reader 还原 role/ordinal/context 或安全 A2-held | `frozen_source_selection@1` **或** `a2_input_disposition@1` 的已接受 ref |
| K1 | `extract_saved_surfaces`：仅 K0 已验证的 source bytes、primary/alternate/attachment | `extracted_components@1` accepted ref |
| K2 | `parse_with_trusted_children`：K1 verified source refs -> child parser (sandbox/cgroup) | `parsed_parts@1` accepted ref |
| K3 | `normalize_with_span_map`：K2 parsed block refs | `normalized_content@1` accepted ref |
| K4 | `assign_content_zones`：K3 accepted ref, exact location/scope | `zones@1` accepted ref |
| K5 | `decode_native_relations`：K0 immutable facts + K4 zone refs | `native_relations@1` accepted ref |
| K6 | `make_prepared_v2`：K2/K3/K4/K5 已接受 refs | `prepared@2` accepted ref |
| K7 | `evaluate_all_filters`：K6 accepted prepared ref + frozen policy | `filter_result@2` accepted ref |
| K8 | `group_with_native_scope`：K5/K6/K7 accepted refs, bounded Workset context | `group_result@2` accepted ref |
| K9 | `persist_scoped_transition_batch`：Workset exact ordered transition facts + own claim | `prepared_transitions@2` batch accepted ref |
| K10 | `build_a2_result_manifest`：所有被接受的 stage refs、held 和 transition refs | `a2_result_manifest@1` accepted ref |
| K11 | `accept_a2_receipt_and_finish`：K10 + full frozen roots + claim/attempt history | durable `a2_completion_receipt@2` + 版本化 Workset pending→terminal finalizer |

所有 K0–K11 是 **Kedro Pipeline/DataCatalog 的真实节点和 Dataset I/O 关系**，held-only 时依然执行必需的 held/manifest/receipt 分支，而不伪造不存在的 body。对不需要的分支用静态 validated partition shape/typed abstention，而不是在图外由旧 A2 处理。K9 transition-only 也必须有完备 Graph 输出依赖。

Dataset 闭合集合检验在创建/运行前执行：所有 graph input/output dataset names 均已预注册，禁止 Kedro 自行 fallback 到隐式 MemoryDataset；各节点名不含原始 provider/source identity。程序只使用 pinned `Kedro 1.7.0 SequentialRunner(is_async=False)` 的编程 API，禁止通过 Kedro CLI/YAML/session 动态创建 Dataset。

### 6.1 同步 Runner 到异步 Application 的有限桥接协议

- 每个有界 Workset 只能有 **一个被记录的 owner runner worker**；在上一个 worker join/cleanup 未确认完成时拒绝新一次该 scope 的 runner admission。Runner 使用受限线程槽，不在 asyncio event loop 执行同步 DAG。
- 自定义 Dataset.save/load 在 worker 线程中执行，通过受控 `run_coroutine_threadsafe` 向 Application loop 提交可信 service coroutine；桥接在 loop owner 线程被调用时直接拒绝；所有 future、worker 和 parser child 受到统一 cancellation/deadline。
- 取消时先设置 **bridge-closed/cooperative stop flag**，拒绝后续节点与新的保存，再 drain in-flight service、终止或 join bounded child、join runner。Kedro runner 本身没有安全可中断线程 API；不能因调用方 CancelledError 就把正在运行的线程丢到后台。
- 真实依赖使用当前 `E = configured execution_timeout`、`L = claim lease`，已验收旧约束 **L > E + 1 秒，且没有自动续租**；必须在独立实验中测量 `parser wall + native CPU/GIL + event-loop jitter + thread join + DB close + claim finalization` 的上界，并预留安全 margin。剩余 margin 不足就拒绝 admission，不能延长无人监管的 writer。
- 原生 CPU/GIL 被持续持有时，简单 pure Python threaded spin 的 Q0 heartbeat 不是证明。复杂解析必须在受限 child 进程中做；对于 K3–K9 CPU-bound node，也须在真实性能实验中确认其不会阻塞 Application loop/使受控线程停不下来；必要时拆分受限独立 executor。
- 如果 worker 失联、无法在 lease 窗口内 join、出现 detached child、重复 cancellation 导致 cleanup 失败：**P1 NO-GO**，保存安全停机和观察状态，不允许继续计算出假 receipt。

### 6.2 资源和锁保护

- A2 stage 的每个 canonical payload 与同 Workset 已接受 aggregate 都必须有 C0 证明的 bytes/count cap、已审查 retention 及查询索引，不允许把所有解析中间件无界写进单 writer SQLite。
- 大型 parser 数据在 writer lock 外 encode/verify；SQLite 事务内只核对 bounded metadata。读回 accepted semantic payload 可在退出锁后另起 read transaction 校验 SHA。
- Pi 性能基准使用 **独占 benchmark slot**，与其他 P1/P2 CPU worker 不并发运行；否则 RSS/时间/lease margin 测量可能被污染。任何性能阈值是验收数据，不是本次文档中的固定魔法值。
- 禁止未验证的 versioned filesystem datasets、网络、Kedro telemetry 及危险 logging；所有 node/dataset names 经过静态 allowlist，用户内容不会进入名字/异常文本。

## 7. 解析、语义与资源策略

**格式范围**：现有 A1 已保存 MIME、HTML、JSON、plain，以及附件中可验证的 PDF、DOCX、XLSX/XLSM/XLSB/ODS 等。若某种格式在实际锁定依赖中不可用，则可发布 typed unsupported/held，而不是未经审核安装随机 parser。

- MIME：primary、alternate、inline reply、header/encoding、multipart 和 attachment 顺序，保留 source span。
- PDF：页号、文本/布局、扫描空白、加密和部分可读单独分类。**OCR 不是默认自动扩展**。
- DOCX：段落/表格/顺序/脚注或 embedded object limitations。
- 表格：sheet/range/cell、公式与 cached 值区别、隐藏单元格以及原始字节位置；不推断作者没有留下的值。
- 内容 normalization：无损原字节 provenance 与 reversible offset map；不可逆转换在限制中声明。
- 区域与关系：quote-occurrence 与 quote-source 不同；原生 reply/ancestor 不等于“标题相似”，Teams chat/channel 要分别验证原生 scope。
- 来源上下文（Calendar/To Do/OneDrive/Contacts）：作为相应 scoped evidence/transition，不强制归入邮件 communication group。
- 每次分析输入/输出的 parser 子进程数量、RSS、时间和挂起任务个数受配置上限与资源测量约束；清理超时即停止上线，不静默丢失 detached worker。

## 8. A3/A5 向后兼容、状态与自动触发

### 8.1 A3 新快照必须版本化，而不是只适配一个 PreparedRecord

现有 `msgloom/triage_input/codec.py` 的 `TRIAGE_INPUT_SCHEMA_VERSION="1"` 对 `prepared@1`、`filter_result@1`、`group_result@1` 做了**严格 refs allowlist**，并将该约束纳入 selection_binding_hash 与 snapshot_hash。`triage_pipeline/handler.py` 也使用具体 `PreparedRecord`。

本轮建议冻结 **`triage_input@2`**：新的 typed snapshot/codec/selection binding 和必要的 part state/version adapter，匹配 `prepared@2`、`filter_result@2`、`group_result@2`，必须重新定义并独立测试所有 binding digest、完整性、limitation、source version、selective held 与 A3 契约；保留原 `triage_input@1` + 历史 `PreparedRecord` 的原样只读能力。不得把 @2 refs 塞进 v1 codec，更不能以“忽略新增 zones/relations/limitations”的有损投影假冒兼容。

工作分成：A3 contract decision/fixture → triage_input@2 codec+digest golden → A3 pipeline typed reader/runner → A3/A5 historical/new cross-stage regression。假如独立研究证明可以安全使用已有形状，必须单列证据和 exact SHA review；**默认不选择 lossy projection**，所以不得把本边界看作单个 25 分钟任务。

### 8.2 公开 scheduled Outcome 策略

| 条件 | TerminalStatus / 安全 code | 自动动作 |
| --- | --- | --- |
| 无新 release/pending | COMPLETE / none | 不做任何处理，等待下一次提示 |
| 有限队列尚有 pending | INCOMPLETE / `scheduled-work-pending` | 仅在 progress 有变化时 bounded backoff |
| intake consumer claim 忙 | INCOMPLETE / `scheduled-consumer-busy` | 合并并发通知，延期再试 |
| 已终结 intake-held 或 A2-held | INCOMPLETE / `scheduled-work-held` | 保留 durable disposition，人工 repair/replay，不自动无限重试 |
| trusted catalog pin 不符 | BLOCKED / `scheduled-catalog-mismatch` | 停止当前 scope |
| intake/preflight `SourceReferenceError` | BLOCKED / `scheduled-source-reference-invalid` | 不解析异常字符串，不擅自重置 cursor |
| 未授权/未受信任的 secure host 或 authority | BLOCKED / `scheduled-invalid-authority` | 停止，不读写 source 或重新绑定权限 |
| post-intake exact dataset 证据缺失 | INCOMPLETE held / `scheduled-work-held` | 写 A2-owned disposition；不修改 intake |
| live claim 丢失/失效 | FAILED / `scheduled-claim-lost` | 阻止新 save，read-back 调和 |
| 相同 logical key 的不同 canonical output | FAILED / `scheduled-acceptance-conflict` | 停止自动重试并保留原结果 |
| parser 有可信 partial | INCOMPLETE / `scheduled-preparation-incomplete` | 保存 limitations；终结而非 pending spin |
| unexpected persistence exception | FAILED / `scheduled-persistence-failed` | 已接受前缀不回滚虚构；报警 |
| 用户取消 | CANCELLED / `scheduled-cancelled` | 先 drain 受控资源/查询已接受结果 |

### 8.3 Prefect 无业务权威

Prefect 只在**有限 A1 collection attempt 之后**（不依赖 Spider close 的结果）给 `msgloom prepare-scheduled` 一个无 payload wakeup；再定期调用有限 catch-up，避免丢失唤醒。唯一合法的 eligible work 来自 committed A1 entries + existing Intake cursor/workset/pending/held。禁止让 Prefect 直读用户私有 SQLite。设计一个 `scope-status` allowlisted CLI 输出 scope hash、cursor anchor digest、pending/held counts、last accepted progress digest 和可信安全 code，不输出 source IDs/body/credentials。

## 9. F0 安全及依赖资格门禁

当前 Q0 候选是 **Kedro 1.7.0**（PyPI wheel SHA-256 `488701a27c7d595b62a611cb23596953a9929fe5cc42a376c28abe26654c2438`）。隔离项目 lock 试算从 146 个包增长至 166 个，新增 20、旧版本没有变化；**未修改实际 `pyproject.toml` / `uv.lock`**。这些只证明依赖求解和合成运行，不是完整项目共装测试。

官方 [GHSA-6326-w46w-ppjw](https://github.com/kedro-org/kedro/security/advisories/GHSA-6326-w46w-ppjw) / [GitLab CVE-2026-35167](https://advisories.gitlab.com/pkg/pypi/kedro/CVE-2026-35167/) 将 traversal 修复指向 Kedro 1.3.0，精确 1.7 wheel 确有 `_is_unsafe_version` guard；[Snyk CVE-2026-3840](https://security.snyk.io/vuln/SNYK-PYTHON-KEDRO-17752561) 仍标记 1.7.0 无修复版本。**不是“已安全”**。两组报告描述的可疑行为高度重叠：`_get_versioned_path()` 对外部提供的 version string 构造路径，尤其可由 Kedro CLI `--load-versions` 以及 DataCatalog 中的 `load_versions` 到达；可能导致目录跳转后的越权读取和内容污染。D4 Q0 在 **1.7.0 精确 wheel** 上验证了路径版本 guard，并限制生产只能走程序化显式 catalog、不用 CLI/动态加载版本，因此当前最重要的是证明 Snyk 对 **所有版本** 的持续标记是否仍适用于这份精确 wheel。两者属于**重叠的 attack surface**，但尚未有上游明确证据可以宣称这两个 CVE 是完全相同记录、也不能仅靠 OSV 扫描没有新项就宣布修复。

官方固定源及核验日期（以最终 F0 重新读取为准）：[GitLab CVE-2026-35167](https://advisories.gitlab.com/pkg/pypi/kedro/CVE-2026-35167/) 写明 <1.3.0、1.3.0 已修复；[Snyk CVE-2026-3840](https://security.snyk.io/vuln/SNYK-PYTHON-KEDRO-17752561) 写明 `[0,)` 全部受影响且无 fixed version；[PyPI Kedro 1.7.0](https://pypi.org/project/kedro/1.7.0/) wheel 哈希是本方案记录的精确值。先由独立安全 reviewer 建立可重复的 exact-wheel reachability 证据、OSV/Snyk 报告日期及版本归属；若残余安全问题不能解决，则 production NO-GO，必须请 repo owner 明确处置（不自动添加 waiver/ignore）。

当前项目 CI 对 `PYSEC-2017-83`（Scrapy）、`GHSA-8pqf-f4m5-798g`（Twisted）已有单独审查的 `--ignore-until-fixed` 例外（见 `.github/workflows/ci.yml` / 既有 policy）。它们是**历史已接受例外**，绝不能移作 Kedro 新漏洞的豁免。如果 owner 最终批准新增安全例外，也必须用明确的 advisory ID、适用代码路径、期限/到期重审、额外运行时缓解及 `docs/dependency-vulnerability-policy.md` 中可审计的独立决策记录；不能只在 CI 中静默添加忽略。完整安装、Python 3.12–3.14、Pi Linux aarch64、Linux x86、Mac/Windows smoke、telemetry/no-network、cgroup 组合测试及 owner security disposition 通过前，不提交正式依赖 PR。

## 10. 切换、失败回滚与剩余决策

### 10.1 上线前置条件

- 旧版 pending Workset 必须清零且经人工确认；否则阻止切换，不能把同一 Workset 在旧新生产引擎里暗中重演。
- C0 完整 schema/codec、v2 acceptance/receipt + A3 adapter、C0 对真实 A1 全 stream fixture、F0 security/dependencies、P1/P2/P3、T0、E0/I0 及 V0 全部有具体 commit/CI/独立审查证明。
- 预留系统备份与原始数据库 schema 4 快照；迁移升级前保持老生产路径。数据库迁移不能在新 binary 首次打开库时自动发生，必须先部署兼容期 binary、保持旧 A2、在受控维护窗口显式迁移。旧 binary 默认拒绝新表：**迁移后回退只可走演练过的备份恢复/经审核的前向修复，不是 git revert**，不可宣称直接 `git revert` 能退 DB。
- Prefect flow 先 disabled/staging 验证；启动后仅 finite bounded calls，对 duplicate/missed hints 和 partial A1 failure 做安全补偿。
- 历史数据和已发布旧结果必须只读可查询；删除旧运行代码也要在 final cutover 验收后进行，保留 Git/QA 历史。

### 10.2 仍需作出的明确工程决策

1. **安全**：Snyk/CVE-2026-3840 与上游 patch 证据矛盾；若无法核实不存在相关可达风险，生产是否暂停/是否正式接受 residual risk，由 owner 决定，不由 Agent 自动豁免。
2. **Migration**：最终 schema 名称、物理约束、接受索引中的 lineage/receipt proof 格式必须先通过 C0 transaction review。
3. **Worker 实际资源**：Pi 的 parser child 预算、timeout/lease 安全 margin、最大并发由测量定标，不以“合成 CPU 0.23 秒流畅”推定生产可用。
4. **A3 typed 版本**：默认设计是 triage_input@2 + 新 binding digest、保留 triage_input@1 原样历史读取；如果需跨版本投影，先做独立不丢重要来源的证明并复审。新 A3 限制及 metadata 必须写入黄金测试。
5. **生产首次启用**：选哪个 source/stream/consumer 范围灰度、何时安排 migration 和是否启用 Prefect；安全和切换的最终决定由用户确认。

本文件的所有新增接口与 SQL DDL 都是 **设计候选**。其下一步不是直接启动全量 P1/P2/P3，而是先解决 C0 R1/CI 缺陷并取得独立验收，同时完成 F0，随后对生产级 C0 做第二阶段完整验收；顺序见实施计划。

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

### 1.1 不可改变的前提

1. A1 只负责 provider 采集、原始证据、权威事实、原子 ReleaseGroup/Entry 与 checkpoint；A2 不再抓取 Graph、枚举 mutable 表或重做 intake。
2. 保留原有 `ReleaseSourceReader`、`PreparationIntakeService`、`PreparationIntakeWorkset@1`、消费者 cursor、pending/held、公认的历史 baseline 和 source-scoped transition 语义。**不能因为代码目前放在 preparation_pipeline/ 就误判它属于可淘汰的旧 A2。**
3. 消费的是 **冻结且可验证的 A1 结果**。ReleaseEntry 的全局 sequence 允许按 source/stream 出现不连续；同一 source VersionRef 在两个 release 中可能是两个不同的 occurrence。
4. Kedro `Pipeline`、`DataCatalog` 和 `SequentialRunner(is_async=False)` 必须完整拥有 A2 各计算/保存节点的依赖图。禁止“旧 Handler 先处理 90%，然后调用两节点 Kedro”。
5. Application 保持 `async def`。Kedro 同步 runner 只能在受控、可回收且计数的工作线程内执行；SQLite claim、交易、parser 子进程等业务权威归 msgloom，而非 Kedro。
6. 不擅自增加跨源 AI topic joining、OCR 云服务、Graph 写权限、A1 行为改动或永久的 `A2_ENGINE` 双运行模式。
7. 本设计描述的 v2 类型/表名只是**待验证方案**；实际迁移、pin 和切换须经过独立 exact-SHA 审查。

## 2. 架构及责任边界

```text
Scrapy / native A1 authority and fact ledger
        |
        | committed ReleaseEntryRef + exact saved evidence (immutable)
        v
ReleaseSourceReader + existing IntakeService  [A1→A2 accepted boundary]
        |          |                 |
        | saved CollectedSelection@1 / Workset@1 / cursor / held
        v
Application.prepare / prepare-scheduled   [async, trusted identity]
        |
        v
Workset + exact-reader verifier [verified occurrence, role, bytes, scopes]
        |
        v
Kedro SequentialRunner (off asyncio event loop; closed DataCatalog)
        |
        +--> extract -> parse -> normalize -> zones ------------------+
        |                                                           |
        +--> native relations -> filter -> group -> scoped transition+
        |                                                           |
        +--> trusted ClaimFencedSemanticDataset.save() <------------+
        |        |
        |        +--> Phase1Persistence v2 append-or-verify / exact result receipt
        v
A2ResultManifest + A2CompletionReceipt@2 + A2-held index
        |
        +--> A3 versioned reader: prepared@1 historical / prepared@2 new
        +--> A5 existing typed downstream outputs (no A5 rewrite)
        |
External Prefect wakeup/catch-up -> finite prepare-scheduled / scope-status
        (hint only; A1 release ledger and durable A2 state are authoritative)
```

| 子系统 | 唯一所有者 | 禁止的跨界行为 |
| --- | --- | --- |
| A1 Spider、HTTP 与 Release、raw evidence | 原生 A1/Scrapy 2.19.0 | Kedro 节点不能处理 Spider 信号或自行 publish A1 |
| A1→A2 admission / cursor / held | 现有 ReleaseSourceReader + IntakeService | 不能用 A2 完成进度倒退/推进 intake cursor |
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
6. 证据缺失、ordinal 不匹配、关联歧义或不可验证字节：在 A2 新建 **持久化 A2-held disposition**，而不是修改 IntakeWorkset 或凭空生成 prepared。

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

### 4.1 必须由模型级别和存储级别双重确保

- 所有导出对象严格 frozen、`extra="forbid"`、明确 max count/bytes、schema-version allowlist、canonical encode/decode 验证。测试不得利用 `model_copy(update=...)` 未重新验证而形成假阳性。
- 不允许动态 user-provided `kind`、module path、Kedro Dataset 类型或任意远程路径。
- 所有 acceptable stage 的 output SHA 和 byte count 是**独立输出证明**，不参与 logical input key。
- 明确以 `(kind, version)` 组成 allowlist：例如 `prepared@2` 才是新版准备完成；`prepared@1` 是历史读取格式。不能让任意 stage_kind 任意选 1/2。
- 用户可控制的 source metadata、邮箱地址、subject 和完整字节都不应进入 log、Kedro node name、DataCatalog dataset name 或 safe failure reason。
- 过去按 v1 保存的 `StageResult`、Codec 和 A3 结果不迁移覆盖、不重编码。

### 4.2 Held 与 completion 的强制语义

每一个 **冻结的 workset.selections occurrence** 必须恰好有一个受持久化验证的 terminal：
`prepared@2`（COMPLETE 或限制明确的 INCOMPLETE），**或** `a2_input_disposition@1`（INCOMPLETE、不可自动重试）。同一 occurrence 不能同时拥有两种结果。

`workset.transitions` 非空时，还须有 **一个** `prepared_transitions@2`，以原样有序转换列表覆盖整个 batch；transition-only/context-only Workset 不必制造 prepared body。`workset.held` 是 intake 阶段已有的不可变集合，没有 selection root，也不可在 A2 追加。

**COMPLETE 的必要且充分业务条件**：所有 roots 完整且已被持久化接受、所有 transitions 完整且已被持久化接受、`workset.held` 为空，并且 v2 receipt 的事务与 claim 验证成功。任何 intake-held、A2-held 或 accepted partial 必须 **terminal INCOMPLETE**（不是无限 pending）。

> 与旧版差别：独立 C0 R1 审查证实，旧 `intake_completion.py` 在 held-only 时可无 refs 终结，且旧状态聚合可能忽略 `workset.held`。因此上述强制 INCOMPLETE 是**有意修正旧 A2 行为**，不能描述成旧代码已经保证；仅允许通过新 A2 v2 proof 实现，不编辑历史 Workset。

Receipt 的 **结构验证** 只是 preflight；在事务内必须验证每一个 referenced StageResult、semantic bytes SHA、accepted-key row、原始 ClaimToken、required_inputs 和 terminal status。直接把伪造的 `ResultRef` 放进结构上完整的 receipt，绝不能构成完整业务证明。

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

允许基于同一 key 多个 execution/attempt/worker 重试；**不要**将 output digest、时间戳、执行尝试或 Kedro node name 纳入。transition key 必须绑定 **整个有序 batch** 及 workset scope，不能只把单条 fact hash 成一个 batch receipt。

Accepted record 独立保存 `(logical_key, result_ref, canonical_output_sha256, canonical_byte_count, semantic_data_ref, original_writer_claim_proof, frozen_lineage_digest)`。重放按 key 找到的输出必须同时验证保存的 StageResult 和 semantic data；相同输入不同字节（包括状态/限制元数据冲突）应 **fail closed**，原始记录不变。

### 5.2 现有 SQLite 限制与建议迁移

已验证：`Phase1Store.append_result_with_data()` 在 `BEGIN IMMEDIATE` 内校验 live claim 和 canonical data，但 `StageResult` 把 execution 与 attempt 锁在 immutable result metadata。跨尝试重新 append 同一个 ID 即使字节相同也可能报 `ImmutableRecordError`；原来的 `preparation_proof.py` 还将 `prepare:` claim 专门绑定到 v1 kind。**不能只在 Registry 添加 `prepared@2` 就宣称支持新 A2**。

推荐数据库 schema 从现有版本 **4** 演进到经审查的 **v5 候选**（最终命名和迁移方式以独立评审为准）：

- `phase1_a2_accepted_stages`：唯一 logical key、结果 ref/sha/length、输入身份 SHA、接受 claim/plan snapshot。
- `phase1_a2_stage_attempts`：每次重试/失败/冲突独立审计；不篡改旧 accepted result。
- `phase1_a2_input_dispositions`：受 bounded scope 索引的 held-at-A2，精确 workset/result/ref。
- `phase1_a2_completion_receipts`：原 workset + 新 A2 receipt 关联、attempt/version、状态及 accepted digest；允许明确授权的 append-only replay，而不是第二次完成原 workset 的旧终结行。

必须在 `schema_store.initialize_schema` 的现有严格 owned-table / legacy digest 机制内**显式**升级：历史 schema V2/V3/V4 无损迁移、占用表/触发器拒绝、DDL 崩溃回滚、审计完整性、大小写名称安全、只读旧结果。绝不能像研究原型那样在生产构造对象时独立 `MetaData.create_all()` 偷建新表。

### 5.3 最小事务协议（伪代码，非可运行源）

```python
def accept_a2_stage(plan, expected_claim, canonical_encoded):
    # 1. Untrusted bytes canonicalized and measured OUTSIDE writer lock
    # 2. Validated workset/roots/upstream metadata proof assembled in advance
    with phase1_writer.BEGIN_IMMEDIATE() as tx:
        tx.require_current_unexpired_claim(expected_claim)
        tx.require_exact_plan_and_input_refs(plan)
        tx.require_expected_stage_schema_version_and_status(plan)
        current = tx.lookup_accepted_logical_key(plan.logical_key)
        if current:
            tx.verify_accepted_metadata_and_durable_ref(current, canonical_encoded)
            # Metadata-only comparisons while holding writer lock.
            # Large payload read-back/decoding is outside lock, before use.
            return current.accepted_ref
        tx.insert_canonical_semantic_bytes_and_new_stage_result(...)
        tx.insert_a2_unique_accepted_key_and_claim_receipt(...)
        tx.require_current_unexpired_claim(expected_claim)
    return accepted_ref
```

- 不可在事务外做非原子 get-then-insert；不可在 writer lock 内对几十 MiB bytes 做不受控 decode；事务内只做 bounded metadata 验证。
- 不可直接通过 `asyncio.to_thread(store._store...)` 绕过 `Phase1Persistence._call` 的 semaphore、取消 drain、close 保护。新增公开 async facade，内部有同步 txn owner。
- 如果两个并发任务提交 **同一 partition claim key**，第二个应该先在 claim acquisition 遇到 `ClaimUnavailableError`；如果不同资源的合法 claim 偶然遇到同一 logical key，SQLite UNIQUE/BEGIN IMMEDIATE 仍保护接受结果。
- worker 在 COMMIT 之后、返回之前被 cancel：调用方可能得到 `CancelledError`，而 DB 已接受。下一次必须按输入 key read-back、验证 SHA/lineage 后 resume；不能简单宣称 rollback 或重复 parse。
- result/status/limitations/claim attempt 与 v2 receipt 必须保持单一可信关联；不能因为 digest 一样却状态不同就认为 replay 等价。
- 底层 SQL schema 和 callback/claim 证明由独立 reviewer 在带有真实 A1 选入根、不同 claim/过期 claim、崩溃和并发的测试中验收。

## 6. Kedro 主 DAG 设计和 Dataset 边界

程序化构造单一、静态允许的 DAG；每个有限 workset 按已验证 occurrence 形成 deterministic partition，不跨 workset 恣意合并；每个节点有明确的 input/output Dataset：

| 顺序 | Kedro node / edge | Dataset I/O / 输出形状 |
| --- | --- | --- |
| K0 | `load_frozen_workset` | 闭源 `ExactHandoffDataset.load` → FrozenRoot/workset plan |
| K1 | `verify_evidence` | `VerifiedEvidenceDataset` → ExtractedComponents |
| K2 | `dispatch_isolated_parsers` | `IsolatedParseDataset.save/load` → ParsedParts |
| K3 | `normalize_content` | Frozen parsed → NormalizedContent + verified span map |
| K4 | `assign_content_zones` | NormalizedContent → ContentZones |
| K5 | `extract_native_relations` | Frozen A1 facts + zones → NativeRelations |
| K6 | `make_prepared_v2` | Parsed + zones + relations → Prepared@2 payload |
| K7 | `evaluate_filter_rules` | Prepared + frozen policy → FilterResult@2 |
| K8 | `group_bounded_records` | Prepared + native relations + filter → GroupResult@2 |
| K9 | `process_scoped_transitions` | Frozen ordered transitions → PreparedTransitions@2（独立 claim） |
| K10 | `publish_accepted_stages` | `ClaimFencedSemanticDataset.save/load` 逐阶段 durable refs |
| K11 | `build_manifest_and_receipt` | 明确依赖已接受 refs；完成 v2 receipt 持久化证明 |

约束：K0–K11 的顺序由 **Kedro 输入输出拓扑** 决定，不允许在外部旧 `PreparationHandler` 悄悄跑完 K1–K10。阶段存储可按必需 stage boundary 拆成更多 Dataset，以便 crash/restart；必须有静态 dataset key 闭合集合检查，缺失任何注册项直接拒绝，不能容许自动 fallback 到隐式 `MemoryDataset`。

Kedro 1.7.0 `SequentialRunner(is_async=False)` 是同步 API；必须放在受限 runner worker 中。`Dataset.save` 可以阻塞 **worker 线程**，通过 `run_coroutine_threadsafe` 调用 Application loop 上受控 async service；不能在 loop 线程做同步 `runner.run` 或 `asyncio.run` 嵌套。

解析 CPU 饥饿、被取消的 Python 线程和原生库占用 GIL 的行为未被 Q0 合成测试证明：需使用 isolated child process（必要时 Linux cgroup-v2）和 kill+wait 真实 cleanup，测 Pi 的时间与 RSS；只有具备可证明 timeout/lease 余量才能启动真实 stage。

配置：不调用 Kedro CLI/Session、不动态导入模块、不使用来自源数据的 Dataset 构造参数或 `load_versions`、不使用 versioned filesystem dataset；显示禁用 telemetry 并测试插件发现、import-time Rich stdout/日志、network attempt。Kedro 可以用 frozen MemoryDataset，但只在复制/不可变语义经过测试时用 `copy_mode="assign"`。

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

### 8.1 A3 adapter 必须同时识别旧/新结果

现有 `msgloom/triage_input/codec.py` 明确使用 `("prepared", "1")`，`msgloom/triage_pipeline/handler.py` 按 `PreparedRecord` 装载准备结果。生产切换必须提供 typed `prepared@2` reader/adapter，保留历史 `prepared@1` reader；新增 zones/limitations/relations 被 A3 真实消费或明确投影为安全限制，**不能只替换 schema 号**。A5 不读非原生的 A2 字节，沿已有 A3 evidence/limitations 传播完成度。

### 8.2 公开 scheduled Outcome 策略

| 条件 | TerminalStatus / 安全 code | 自动动作 |
| --- | --- | --- |
| 无新 release/pending | COMPLETE / none | 不做任何处理，等待下一次提示 |
| 有限队列尚有 pending | INCOMPLETE / `scheduled-work-pending` | 仅在 progress 有变化时 bounded backoff |
| intake consumer claim 忙 | INCOMPLETE / `scheduled-consumer-busy` | 合并并发通知，延期再试 |
| 已终结 intake-held 或 A2-held | INCOMPLETE / `scheduled-work-held` | 保留 durable disposition，人工 repair/replay，不自动无限重试 |
| trusted catalog pin 不符 | BLOCKED / `scheduled-catalog-mismatch` | 停止当前 scope |
| intake/preflight `SourceReferenceError` | BLOCKED / `scheduled-source-reference-invalid` | 不解析异常字符串，不擅自重置 cursor |
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

官方 [GHSA-6326-w46w-ppjw](https://github.com/kedro-org/kedro/security/advisories/GHSA-6326-w46w-ppjw) / [GitLab CVE-2026-35167](https://advisories.gitlab.com/pkg/pypi/kedro/CVE-2026-35167/) 将 traversal 修复指向 Kedro 1.3.0，精确 1.7 wheel 确有 `_is_unsafe_version` guard；[Snyk CVE-2026-3840](https://security.snyk.io/vuln/SNYK-PYTHON-KEDRO-17752561) 仍标记 1.7.0 无修复版本。**不是“已安全”**。先由独立安全 reviewer 建立可重复的 exact-wheel reachability 证据、OSV/Snyk 报告日期及版本归属；若残余安全问题不能解决，则 production NO-GO，必须请 repo owner 明确处置（不自动添加 waiver/ignore）。

当前项目 CI 对 `PYSEC-2017-83`（Scrapy）、`GHSA-8pqf-f4m5-798g`（Twisted）已有单独审查的 `--ignore-until-fixed` 例外（见 `.github/workflows/ci.yml` / 既有 policy）。它们是**历史已接受例外**，绝不能移作 Kedro 新漏洞的豁免。完整安装、Python 3.12–3.14、Pi Linux aarch64、Linux x86、Mac/Windows smoke、telemetry/no-network、cgroup 组合测试及 owner security disposition 通过前，不提交正式依赖 PR。

## 10. 切换、失败回滚与剩余决策

### 10.1 上线前置条件

- 旧版 pending Workset 必须清零且经人工确认；否则阻止切换，不能把同一 Workset 在旧新生产引擎里暗中重演。
- C0 完整 schema/codec、v2 acceptance/receipt + A3 adapter、C0 对真实 A1 全 stream fixture、F0 security/dependencies、P1/P2/P3、T0、E0/I0 及 V0 全部有具体 commit/CI/独立审查证明。
- 预留系统备份与原始数据库 schema 4 快照；迁移升级前保持老生产路径。数据库迁移通常不是自动回滚成旧 schema：**如已升级，恢复策略可能是停机从迁移前备份恢复或经审核的兼容旧 reader**，不可宣称直接 `git revert` 能退 DB。
- Prefect flow 先 disabled/staging 验证；启动后仅 finite bounded calls，对 duplicate/missed hints 和 partial A1 failure 做安全补偿。
- 历史数据和已发布旧结果必须只读可查询；删除旧运行代码也要在 final cutover 验收后进行，保留 Git/QA 历史。

### 10.2 仍需作出的明确工程决策

1. **安全**：Snyk/CVE-2026-3840 与上游 patch 证据矛盾；若无法核实不存在相关可达风险，生产是否暂停/是否正式接受 residual risk，由 owner 决定，不由 Agent 自动豁免。
2. **Migration**：最终 schema 名称、物理约束、接受索引中的 lineage/receipt proof 格式必须先通过 C0 transaction review。
3. **Worker 实际资源**：Pi 的 parser child 预算、timeout/lease 安全 margin、最大并发由测量定标，不以“合成 CPU 0.23 秒流畅”推定生产可用。
4. **A3 投影**：哪些准备产物以结构化新字段进入 A3，哪些以 limitation 映射，以及历史 prepared@1 reader 保留期限，需在 C0/W0 schema review 决定并附独立 fixture。
5. **生产首次启用**：选哪个 source/stream/consumer 范围灰度、何时安排 migration 和是否启用 Prefect；安全和切换的最终决定由用户确认。

本文件的所有新增接口与 SQL DDL 都是 **设计候选**。其下一步不是直接启动全量 P1/P2/P3，而是先解决 C0 R1/CI 缺陷并取得独立验收，同时完成 F0，随后对生产级 C0 做第二阶段完整验收；顺序见实施计划。

# Topic 01 第二轮研究总结

Topic 01 Round 2 已完成。成功的 Research Pipeline run ID 为 `fb483e38f452`，最终状态为 `complete`。

本轮没有重新做泛化的大规模论文搜索，而是按照上一轮 gap review 后的两个重点方向做 targeted research：

1. incomplete / incremental email reconstruction；
2. robust quotation → source-span alignment。

经过人工术语分析、候选筛选和严格 admission gate，最终只新增 3 篇真正有价值的论文：H01/H02 两篇 direct-email hidden-email reconstruction 论文，以及 T01 一篇 local text reuse/alignment transfer 论文。没有为了凑数量加入弱相关论文。

主要研究结论：

- H01/H02 是同一条 direct-email research line，不应当被视为两个独立 replication。
- 它们说明可以利用后续邮件中仍然存在的 quotation fragments 重建缺失邮件的部分内容，并用 precedence graph / partial order 表示可支持的相对顺序。
- 这不等于恢复了完整原邮件；没有被后续引用的缺失文字无法凭空恢复。
- 它们也没有验证 online late-arrival、missing-parent correction/retraction 或增量一致性。
- T01 说明 local passage alignment 可以处理嵌入在大量无关文本中的局部复用，并允许 mismatch/gap；但它不是 email benchmark，不能把论文中的 accuracy 当成邮件准确率。
- 一个单一 best local alignment 可能漏掉同一文档对中的第二段、顺序翻转或相距很远的有效匹配。
- H02 的 output-count stability 不能被解释成 reconstruction accuracy；其 Figure 6 的 recollected/reconstructed wording 冲突被保留。
- T01 Table 6 的 specificity 97.3% 与正文把 97.3% 称为 recall 的冲突被保留；“20-fold / 2900 train / 500 test”的 population 解释也没有被擅自修正。

Gap 变化：

- A1 指定 primary papers 的 acquisition gap 已关闭；剩余 complete-original/source-span accuracy 问题转成工程评估。
- A2 structural quotation alignment 有明显进展，但 markerless、nested HTML/table、paraphrased/edited、short fragment 和 ambiguous source 仍缺 direct-email evidence。
- A7 modern 2024–2026 / incremental / late-parent correction-retraction / LLM-assisted direct-email reconstruction 仍然开放。
- A5 和 A2 的 semantic response/agreement scope 移交 Topic 04。
- E1–E4 仍是最重要的工程验证：联合 gold annotation、decision-bearing preservation/source-span accuracy、late-arrival replay/correction、calibration/abstention。

最终 `gaps.json` 共 10 项：2 Academic、6 Engineering、2 Out-of-scope。不会自动开始 Topic 01 Round 3；未来是否继续 A2/A7 要再次根据项目价值决定。

这轮最大的流程经验也已经写入 `PROCESS_RETROSPECTIVE.execution.md`：semantic reasoning 与 artifact serialization 应尽量分离；deep synthesis 应拆成多个小型 xhigh semantic sections 再由确定性代码组装；worker hang 判断要同时看 CLI event 和 Codex rollout；独立 reviewer 必须能够真正 reject 并触发 bounded retry。本轮 reviewer 第一次确实发现了 Evidence Matrix 的语义标签错误，修复后第二个 fresh reviewer 才正式接受。

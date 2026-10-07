You are one worker inside an automated literature-review pipeline.
A script, not a person, reads your reply. Follow these rules exactly:
- Do the task completely in this single reply. Do not ask questions and do not
  wait for confirmation.
- Reply with the requested artifact block(s) only: no preamble, no commentary
  outside the blocks. Each block starts with a line `===BEGIN <name>===` and
  ends with a line `===END <name>===`; the content between those lines is
  written to a file verbatim.
- Never invent papers, identifiers, numbers, or quotes. Leave unknown fields
  out or mark them as unknown.
- Do not use your code tool, canvas, or connectors; plain text is enough.

# Task: independent review of the cross-paper synthesis

Research topic: **Direct enterprise email/chat studies of longitudinal cross-thread conversation or work-item linking, especially evidence for concrete business-event identity and for partial, evolving, subevent, or non-transitive continuity relations in organizational workflows.**

You did not write this synthesis and you are not reviewing your own work.
Your verdict decides whether the report may be written. Rejecting is a normal
outcome: reject when the evidence does not support the synthesis. Do not
soften a real problem into a note so that the work can pass.

Check five things against the analyses below, not against how well the
synthesis reads:

1. Faithfulness — every finding is traceable to at least one analysis, and no
   finding states more than its cited analyses support.
2. Citation integrity — every cited paper_id is one of: `1402.4417`, `1412.5687`, `1705.08500`, `1707.07344`, `1906.01753`, `2011.12249`, `2104.05022`, `2109.06417`, `2206.10009`, `2211.07342`, `2405.05160`, `2406.15990`, `2407.11988`, `2607.26384`, `doi-10-1002-asi-21264`, `doi-10-1002-sim-4780140510`, `doi-10-1007-978-3-030-33223-5-12`, `doi-10-1007-978-3-030-49461-2-23`, `doi-10-1007-978-3-540-27868-9-84`, `doi-10-1007-s00778-010-0203-9`, `doi-10-1007-s10115-019-01430-6`, `doi-10-1016-j-ipm-2025-104085`, `doi-10-1038-s41598-025-32765-6`, `doi-10-1038-s41598-026-40637-w`, `doi-10-1080-01621459-1969-10501049`, `doi-10-1109-access-2023-3284053`, `doi-10-1109-icpm57379-2022-9980684`, `doi-10-1109-tbdata-2022-3204207`, `doi-10-1145-1111449-1111471`, `doi-10-1145-1111449-1111472`, `doi-10-1145-1111449-1111473`, `doi-10-1145-290941-290953`, `doi-10-1145-290941-290954`, `doi-10-1145-354756-354843`, `doi-10-18653-v1-2020-coling-main-275`, `doi-10-18653-v1-2022-emnlp-main-58`, `doi-10-18653-v1-2023-emnlp-main-294`, `doi-10-18653-v1-2024-findings-emnlp-725`, `doi-10-18653-v1-2025-acl-long-1134`, `doi-10-2139-ssrn-7284343`, `doi-10-3115-1220575-1220591`, `doi-10-3115-v1-w14-2910`, `doi-10-3390-industries1010003`, `manual-03d6dfa532`, `manual-35bac66e3c`, `manual-5c20fb0229`, `manual-61a7e10e5f`, `manual-c43ffe3135`, `manual-e988e24127`, `manual-f56d02b8f9`.
3. Coherence — contradictions between papers are named, not averaged away.
4. Gap completeness — a gap this corpus cannot close is reported as open. A
   gap presented as closed without evidence is a rejection.
5. Overreach — transfer-domain or synthetic evidence is not presented as
   direct-domain evidence, and no production claim rests on it.

Synthesis under review:
{
 "topic": "Direct enterprise email/chat studies of longitudinal cross-thread conversation or work-item linking, especially evidence for concrete business-event identity and for partial, evolving, subevent, or non-transitive continuity relations in organizational workflows.",
 "paper_count": 50,
 "executive_summary": "The corpus strongly supports msgloom's central premise that conversation structure, lexical similarity, shared participants, and generated labels are evidence for continuity but are not themselves work-matter identity. Direct enterprise-email evidence shows that real work activities cross reply-thread boundaries and that participants alone can confuse concurrent activities. Event-coreference and process-correlation literature further supports combining action, entity, participant, temporal, structural, and domain-constraint evidence while guarding against superficial similarity. Equally important, partial identity, subevents, membership, evolving events, and spatiotemporal continuity cannot always be represented as transitive equivalence clusters. Online systems therefore need explicit rejection or uncertainty, incremental evidence accumulation, and repairable identity state. However, the corpus still lacks direct Outlook-plus-Teams production evidence and does not establish msgloom-specific decision thresholds, correction semantics, or mappings from partial-event relations to workplace Topic continuity.",
 "themes": [
  "Cross-thread enterprise work identity cannot be reduced to email-thread ancestry: content, participants, and threading provide complementary evidence, while the same participants may participate in several concurrent activities [doi-10-1145-1111449-1111471].",
  "Concrete identity is better supported by combinations of event action, arguments/entities, participants, time, discourse, and domain constraints than by surface lexical similarity alone [1906.01753] [2011.12249] [manual-61a7e10e5f] [doi-10-1038-s41598-025-32765-6].",
  "Partial, hierarchical, membership, subevent, and evolving continuity relations are materially different from full same-event identity and may be non-transitive [2109.06417] [manual-c43ffe3135] [manual-35bac66e3c] [2211.07342].",
  "New-event detection and online attachment are asymmetric decisions: detecting genuinely new matters is harder than tracking known ones, which supports an explicit uncertain or reject region instead of forced assignment [doi-10-1145-290941-290954] [doi-10-1145-354756-354843] [doi-10-1080-01621459-1969-10501049].",
  "Continuity representations should evolve as evidence arrives; adaptive tracking, iterative coreference, and incremental entity resolution can exploit facts that were unavailable at initial assignment [doi-10-1002-asi-21264] [1707.07344] [1402.4417].",
  "Incremental identity systems can preserve historical identifiers while supporting local repair, merge, split, emergence, and disappearance rather than recomputing history as if previous assignments never existed [doi-10-1007-978-3-030-49461-2-23] [doi-10-3390-industries1010003] [doi-10-1109-tbdata-2022-3204207].",
  "Enterprise process literature provides useful analogues for concrete work-matter identity: business entities and constraints can anchor cases, broadly shared resources can cause false merges, and incomplete executions can remain legitimate cases while evidence is still arriving [2607.26384] [2206.10009].",
  "Cross-corpus and distribution-shift results warn against assuming that confidence, thresholds, or feature importance learned on one benchmark will transfer unchanged to workplace streams [2011.12249] [2405.05160] [doi-10-18653-v1-2024-findings-emnlp-725] [manual-03d6dfa532]."
 ],
 "findings": [
  {
   "statement": "Direct enterprise-email evidence confirms that work-activity continuity can cross reply-thread boundaries, so Group or thread membership should be treated as evidence rather than Topic identity; participant identity is also insufficient because the same people can participate in multiple simultaneous activities.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1145-1111449-1111471",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-1145-1111449-1111472",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Across event-coreference and process-correlation studies, identity decisions improve when multiple dimensions are combined, including action semantics, resolved arguments/entities, participants, time, discourse context, data attributes, and domain constraints; no single shared name, participant, trigger, or similarity score is a reliable identity criterion.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "1906.01753",
     "section": "key_findings"
    },
    {
     "paper_id": "2011.12249",
     "section": "key_findings"
    },
    {
     "paper_id": "manual-61a7e10e5f",
     "section": "key_findings"
    },
    {
     "paper_id": "2206.10009",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-3115-1220575-1220591",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Surface lexical similarity is especially unsafe as an identity proxy: distinct events can share triggers or class vocabulary, while identical events can be paraphrased with very different triggers; argument-aware and contextual evidence helps counter both error modes.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2407.11988",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-1038-s41598-025-32765-6",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-18653-v1-2020-coling-main-275",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-1145-290941-290954",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "The literature establishes that longitudinal relation structure is richer than binary same-versus-different identity: membership, subevents, sister relations, and spatiotemporal continuity can represent partial or evolving relationships, and some such relations violate transitivity. Therefore ordinary equivalence-cluster closure is not a sound universal representation for all workplace continuity evidence.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2109.06417",
     "section": "key_findings"
    },
    {
     "paper_id": "manual-c43ffe3135",
     "section": "key_findings"
    },
    {
     "paper_id": "manual-35bac66e3c",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-3115-v1-w14-2910",
     "section": "key_findings"
    },
    {
     "paper_id": "2211.07342",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "For online operation, a no-confident-match outcome should not automatically mean NEW: record linkage, open-world recognition, and selective classification all support an explicit unresolved or rejected region, while TDT shows that genuinely new-event detection is substantially harder than tracking already represented events.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1080-01621459-1969-10501049",
     "section": "key_findings"
    },
    {
     "paper_id": "1412.5687",
     "section": "key_findings"
    },
    {
     "paper_id": "1705.08500",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-1145-354756-354843",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-1145-290941-290953",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Continuity assessment should be incremental because later evidence can materially change identity judgments: adaptive topic representations, propagated event arguments, newly linked entities, and newly inferred cross-organizational mappings all improve subsequent attachment decisions.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1002-asi-21264",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-1145-290941-290954",
     "section": "key_findings"
    },
    {
     "paper_id": "1707.07344",
     "section": "key_findings"
    },
    {
     "paper_id": "1402.4417",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-1109-access-2023-3284053",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Incremental identity maintenance need not make early assignments irreversible: local reclustering, historical-cluster merging, explicit stream merge/split actions, and historically dominant persistent identifiers demonstrate mechanisms for repair while preserving continuity of system identity.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "1402.4417",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-1007-978-3-030-49461-2-23",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-1109-tbdata-2022-3204207",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-3390-industries1010003",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Enterprise process evidence supports anchoring identity in concrete business objects and constraints rather than broadly shared contextual entities: resource-like objects can spuriously connect unrelated executions, whereas domain-selected primary and secondary entities can define coherent cases; incomplete cases may remain valid while later evidence is absent.",
   "confidence": "MEDIUM",
   "evidence": [
    {
     "paper_id": "2607.26384",
     "section": "key_findings"
    },
    {
     "paper_id": "2206.10009",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-1109-icpm57379-2022-9980684",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Phase 2 evidence seeking is technically plausible because retrieval-oriented coreference and broader discourse/context methods can recover identity evidence outside a local mention pair, but the corpus does not establish the optimal retrieval budget, stopping rule, latency-quality trade-off, or decision benefit for msgloom.",
   "confidence": "MEDIUM",
   "evidence": [
    {
     "paper_id": "doi-10-18653-v1-2022-emnlp-main-58",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-18653-v1-2023-emnlp-main-294",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-1016-j-ipm-2025-104085",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-18653-v1-2025-acl-long-1134",
     "section": "key_findings"
    }
   ]
  },
  {
   "statement": "Identity models, confidence rankings, and calibration do not transfer reliably across corpora or distribution shifts, so benchmark performance on news event coreference or generic selective classification cannot establish production reliability for longitudinal Outlook-plus-Teams work-matter linking.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2011.12249",
     "section": "key_findings"
    },
    {
     "paper_id": "2405.05160",
     "section": "key_findings"
    },
    {
     "paper_id": "doi-10-18653-v1-2024-findings-emnlp-725",
     "section": "key_findings"
    },
    {
     "paper_id": "manual-03d6dfa532",
     "section": "key_findings"
    }
   ]
  }
 ],
 "contradictions": [
  {
   "topic": "How much email metadata is sufficient for work-task identity",
   "papers": [
    "doi-10-1145-1111449-1111471",
    "doi-10-1145-1111449-1111473"
   ],
   "note": "The activity-classification study finds that threading alone is weak and that content materially strengthens cross-thread activity linking, whereas the predefined-task predictor reports high precision from sender, recipient, and subject features and no additional benefit from email-body words. The results are not directly incompatible because the tasks, labels, coverage regimes, and identity granularity differ; they show that feature sufficiency is task-dependent and should not be generalized."
  },
  {
   "topic": "Document topic pre-clustering as an identity aid versus a source of benchmark overfitting",
   "papers": [
    "1906.01753",
    "2011.12249",
    "2104.05022"
   ],
   "note": "Topic pre-clustering is a very strong continuity signal on ECB+, but cross-corpus evaluation warns that designs exploiting ECB+'s document-link distribution can generalize poorly. WEC deliberately allows corpus-wide coreference rather than restricting identity to predefined topic partitions. For msgloom, pre-clustering may be useful candidate generation but should not be treated as an identity boundary."
  },
  {
   "topic": "Transitive clustering versus non-transitive longitudinal relations",
   "papers": [
    "doi-10-18653-v1-2025-acl-long-1134",
    "2109.06417",
    "manual-c43ffe3135",
    "2211.07342"
   ],
   "note": "Conventional event coreference represents same-event identity as equivalence-style clusters, while dense partial-identity work shows that membership, subevent, and spatiotemporal-continuity relations may violate transitivity. MAVEN-ERE avoids part of this conflict by separating same-event coreference from subevent, temporal, and causal relations. The apparent contradiction is resolved only by preserving distinct relation semantics instead of applying transitive closure to every form of continuity."
  },
  {
   "topic": "Forced case assignment versus explicit rejection or unresolved identity",
   "papers": [
    "doi-10-1007-978-3-030-33223-5-12",
    "doi-10-1080-01621459-1969-10501049",
    "1412.5687",
    "1705.08500"
   ],
   "note": "The process-correlation method assigns every event to exactly one case, whereas record-linkage and selective/open-world methods explicitly preserve possible-link or rejected outcomes. These optimize different task contracts. For msgloom, whose design prioritizes avoiding false merges and preserving uncertainty, the forced-assignment assumption is not transferable without separate validation."
  },
  {
   "topic": "Semantic broadening improves recall but can reduce identity precision",
   "papers": [
    "manual-61a7e10e5f",
    "2407.11988",
    "doi-10-1038-s41598-025-32765-6"
   ],
   "note": "Semantic action similarity and paraphrase robustness are necessary to link lexically diverse mentions, but broader semantic matching can sharply reduce precision when distinct event instances share type-level meaning. Argument-centric evidence mitigates part of this tension by distinguishing same-trigger/different-event and different-trigger/same-event cases. The corpus therefore supports semantic broadening only when constrained by identity-specific evidence."
  }
 ],
 "gaps": [
  {
   "id": "gap-1",
   "description": "Which evidence combinations actually establish or refute continuity of a concrete work matter across independent workplace messages, conversations, attachments, email, and Teams remains open. The corpus contains direct cross-thread enterprise-email evidence and stronger process/event evidence, but it still does not validate the required combination of subject, customer/project names, conversation ancestry, referenced artifacts, commitments, state compatibility, attachments, and cross-source evidence for the target domain.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "(\"work item identity\" OR \"work matter identity\" OR \"business event coreference\" OR \"cross-document event coreference\") AND (email OR \"workplace communication\" OR enterprise) AND (cross-thread OR cross-document OR cross-source)"
  },
  {
   "id": "gap-2",
   "description": "The application-specific decision policy remains open: the relative cost of false merges versus false splits, thresholds for attachment versus rejection, and exact semantics/calibration of CONTINUE, NEW, and UNCERTAIN must be determined from msgloom requirements and empirical evaluation. The corpus supports reject options and risk-coverage trade-offs but does not establish msgloom's loss function or false-merge cost.",
   "classification": "ENGINEERING",
   "priority": "HIGH"
  },
  {
   "id": "gap-3",
   "description": "The msgloom correction and identity-state model remains open. Stable Topic IDs independent of generated labels or source thread IDs, versioned identity assessments, supersession links, immutable evidence lineage, and general MERGE/SPLIT correction require project-level design and testing. Incremental entity-resolution and stable-ID papers establish useful mechanisms but not msgloom's required history semantics.",
   "classification": "ENGINEERING",
   "priority": "HIGH"
  },
  {
   "id": "gap-4",
   "description": "There is still no direct production-domain evidence in this corpus for longitudinal work-matter identity across Outlook email and Microsoft Teams. The direct enterprise-email study and enterprise-process literature are useful adjacent evidence but do not establish production accuracy or representativeness for msgloom's Outlook-plus-Teams environment.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "(enterprise OR workplace OR organizational) AND (email OR \"Microsoft Teams\" OR \"enterprise chat\" OR \"workplace chat\") AND (cross-thread OR longitudinal OR cross-conversation) AND (\"topic identity\" OR \"task tracking\" OR \"case tracking\" OR \"event coreference\" OR \"conversation linking\")"
  },
  {
   "id": "gap-5",
   "description": "How partial, subevent, evolving, membership, or otherwise non-transitive relations should map onto workplace work-matter continuity remains unresolved. The corpus strongly establishes that these relations exist and can violate transitivity, but it does not define when they should mean CONTINUE, RELATED-BUT-SEPARATE, MERGE, SPLIT, or another workplace-specific relation.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "(\"partial event identity\" OR \"partial coreference\" OR \"subevent relation\" OR \"event evolution\" OR \"event membership\" OR \"non-transitive coreference\") AND (workflow OR task OR case OR workplace OR enterprise)"
  },
  {
   "id": "gap-6",
   "description": "The best operational strategy for Phase 2 evidence seeking remains unresolved. Retrieval-based event-coreference search and global-context models show that additional evidence can matter, but msgloom still needs engineering benchmarks for bounded historical retrieval, candidate generation, latency, retrieval stopping rules, and whether retrieved context actually changes identity decisions correctly.",
   "classification": "ENGINEERING",
   "priority": "MEDIUM"
  },
  {
   "id": "gap-7",
   "description": "Calibration under non-stationary workplace streams remains unresolved. The corpus provides substantial evidence that calibration deteriorates under distribution shift and that drift-aware, selective, or conformal approaches can help, but it does not establish reliable calibration, abstention thresholds, or coverage guarantees for longitudinal workplace coreference or clustering.",
   "classification": "ACADEMIC",
   "priority": "MEDIUM",
   "suggested_query": "(\"selective classification\" OR abstention OR \"confidence calibration\" OR \"selective prediction\") AND (\"distribution shift\" OR nonstationary OR streaming OR \"concept drift\") AND (text OR NLP OR coreference OR clustering)"
  }
 ],
 "actionable_insights": [
  "Keep Phase 1 conservative: CONTINUE only when explicit identity evidence is strong; otherwise preserve a separate candidate with UNCERTAIN rather than interpreting low match confidence as NEW [doi-10-1080-01621459-1969-10501049] [1705.08500].",
  "Implement identity evidence as multiple auditable feature families—conversation ancestry, action/object, participants/entities, time, references, artifacts, state compatibility, and source structure—rather than a single semantic-similarity score [1906.01753] [2011.12249] [2206.10009].",
  "Treat subject, project/customer names, participants, and thread IDs as candidate-generation or supporting features, never sufficient merge keys [doi-10-1145-1111449-1111471] [doi-10-3115-1220575-1220591] [2607.26384].",
  "Represent full SAME-MATTER identity separately from RELATED, SUBEVENT/MEMBER, and EVOLVING-CONTINUITY relations; do not apply transitive closure to relations whose semantics are not equivalence relations [2109.06417] [2211.07342] [manual-35bac66e3c].",
  "Make identity state append-only and repairable: retain stable Topic IDs, record each assessment with evidence and version, and express later merge/split corrections explicitly rather than rewriting history [doi-10-3390-industries1010003] [doi-10-1007-978-3-030-49461-2-23] [doi-10-1109-tbdata-2022-3204207].",
  "For Phase 2, retrieve bounded historical evidence only for ambiguous candidates and measure whether retrieval changes a wrong or uncertain decision to a correct one; retrieval quality alone is not the target metric [doi-10-18653-v1-2022-emnlp-main-58] [doi-10-18653-v1-2023-emnlp-main-294].",
  "Build adversarial evaluation sets with same customer/project but different matters, same participants but parallel requests, renamed subjects, paraphrased continuations, delayed evidence, and one message continuing multiple matters; these directly exercise failure modes exposed by enterprise-email, TDT, and event-coreference studies [doi-10-1145-1111449-1111471] [doi-10-1145-290941-290954] [2407.11988].",
  "Evaluate false merges and false splits separately and include an abstention coverage curve; average clustering F1 alone can hide the product-critical failure where an independent work matter disappears into another Topic [1705.08500] [2405.05160].",
  "Do not calibrate deployment confidence solely on ECB+, WEC, or another static benchmark; use held-out workplace-like temporal slices and explicit drift tests before assigning operational meaning to confidence thresholds [2011.12249] [manual-03d6dfa532] [doi-10-18653-v1-2024-findings-emnlp-725]."
 ],
 "confidence_summary": "Confidence is HIGH for the structural conclusions that thread membership is not identity, multiple evidence dimensions are needed, lexical or participant similarity can cause false merges, uncertainty should be representable, and incremental identity requires repair. Confidence is also HIGH that partial and evolving event relations cannot universally be collapsed into transitive equivalence clusters. Confidence is MEDIUM when transferring process-case mechanisms and news-event coreference evidence to concrete workplace Topics. Confidence is LOW for any claim about production accuracy, optimal thresholds, or relation semantics in Outlook-plus-Teams because no study in the corpus directly validates msgloom's target environment.",
 "limitations": [
  "Most identity evidence comes from news event coreference, TDT, entity resolution, or process mining rather than longitudinal Outlook-plus-Teams work communication [2011.12249] [2206.10009].",
  "The strongest direct enterprise-email study links messages to user work activities, which is highly relevant but does not fully establish the narrower semantics of a concrete business-event or work-matter identity [doi-10-1145-1111449-1111471].",
  "Several studies evaluate gold event mentions or otherwise simplified inputs, so their reported coreference scores do not measure an end-to-end system that must first identify candidate matters correctly [doi-10-1016-j-ipm-2025-104085].",
  "Benchmarks differ substantially in annotation ontology, topic partitioning, lexical diversity, and relation definitions, making raw metric comparisons unsuitable as evidence of method superiority for msgloom [2104.05022] [2407.11988] [2011.12249].",
  "Partial-identity annotation itself has lower agreement than full identity, so the exact boundary among continuation, subevent, and related-but-separate cases remains intrinsically difficult [2109.06417].",
  "Process-case identity can depend on a chosen case notion and may admit multiple plausible views, so process-mining correlations are analogues rather than direct ground truth for workplace Topic identity [doi-10-1007-s00778-010-0203-9] [doi-10-1007-s10115-019-01430-6].",
  "The supplied corpus includes duplicate analyses of the same underlying studies under different paper IDs, notably [1906.01753] with [manual-e988e24127] and [2109.06417] with [manual-c43ffe3135]; these should not be counted as independent replication.",
  "Selective-classification, open-world, and calibration papers establish useful decision mechanisms but do not themselves validate semantic work-matter identity features [1412.5687] [1705.08500] [2405.05160]."
 ],
 "gap_status": [
  {
   "id": "gap-1",
   "status": "open",
   "note": "Round 4 strengthens adjacent evidence: enterprise email demonstrates cross-thread work-activity linking, and process/event studies identify useful combinations of content, participants, objects, time, and constraints. No corpus paper validates the required evidence combination for concrete cross-message, attachment, email, and Teams work-matter identity in the target domain.",
   "evidence": [
    "doi-10-1145-1111449-1111471",
    "1906.01753",
    "2206.10009",
    "2607.26384"
   ]
  },
  {
   "id": "gap-2",
   "status": "open",
   "note": "Three-way linkage, open-world rejection, and selective-risk literature establishes mechanisms for abstention and thresholding, but no paper supplies msgloom's loss function, false-merge cost, or operational semantics for CONTINUE, NEW, and UNCERTAIN.",
   "evidence": [
    "doi-10-1080-01621459-1969-10501049",
    "1412.5687",
    "1705.08500",
    "2405.05160"
   ]
  },
  {
   "id": "gap-3",
   "status": "open",
   "note": "Incremental entity resolution, stream clustering, and StableID demonstrate local repair, merge/split handling, and persistent identifiers, but they do not specify msgloom's versioned assessment, supersession, immutable lineage, or correction contract.",
   "evidence": [
    "1402.4417",
    "doi-10-1007-978-3-030-49461-2-23",
    "doi-10-1109-tbdata-2022-3204207",
    "doi-10-3390-industries1010003"
   ]
  },
  {
   "id": "gap-4",
   "status": "open",
   "note": "The corpus now has direct enterprise-email evidence and cross-organizational process evidence, but no study establishes longitudinal work-matter identity accuracy or representativeness across production Outlook email and Microsoft Teams.",
   "evidence": [
    "doi-10-1145-1111449-1111471",
    "doi-10-1145-1111449-1111472",
    "doi-10-1109-access-2023-3284053"
   ]
  },
  {
   "id": "gap-5",
   "status": "open",
   "note": "The corpus strongly establishes partial identity, subevent, membership, hierarchy, spatiotemporal continuity, and possible non-transitivity, but no paper maps those relations to workplace decisions such as CONTINUE, RELATED-BUT-SEPARATE, MERGE, or SPLIT.",
   "evidence": [
    "2109.06417",
    "manual-c43ffe3135",
    "manual-35bac66e3c",
    "2211.07342",
    "doi-10-3115-v1-w14-2910"
   ]
  },
  {
   "id": "gap-6",
   "status": "open",
   "note": "Coreference search and discourse-context models show that external historical context can improve identity evidence, but no corpus paper determines msgloom-specific candidate generation, retrieval bounds, stopping rules, latency targets, or decision-change utility.",
   "evidence": [
    "doi-10-18653-v1-2022-emnlp-main-58",
    "doi-10-18653-v1-2023-emnlp-main-294",
    "doi-10-1016-j-ipm-2025-104085"
   ]
  },
  {
   "id": "gap-7",
   "status": "open",
   "note": "Cross-corpus and distribution-shift studies confirm that calibration and confidence ranking degrade under shift and provide candidate mitigation techniques, but reliable thresholds and coverage guarantees for non-stationary workplace coreference remain unvalidated.",
   "evidence": [
    "2011.12249",
    "2405.05160",
    "doi-10-18653-v1-2024-findings-emnlp-725",
    "manual-03d6dfa532",
    "doi-10-1038-s41598-026-40637-w"
   ]
  }
 ]
}

Per-paper analyses (reduced to questions and top findings to fit the size cap):
[
 {
  "paper_id": "1402.4417",
  "title": "Incremental Entity Resolution from Linked Documents",
  "research_question": "Can entity resolution exploit links between documents and update previously resolved entity clusters efficiently when new documents arrive without rerunning resolution over the complete historical collection?",
  "key_findings": [
   "Using links between documents in addition to attribute similarity improves entity-resolution recall on the synthetic residents data while preserving the reported perfect precision.",
   "The incremental procedure can combine new documents with previously resolved entities and can merge historical clusters when the new evidence changes the identity structure.",
   "Incremental resolution produces almost the same precision, recall, and F-measure as batch ERLD in the reported incremental experiments while processing only the affected portion of historical state.",
   "Locality-sensitive hashing and traversal substantially reduce candidate comparisons and execution time relative to an unblocked iterative match-merge process without materially sacrificing resolution quality in the reported tests.",
   "On the real company evaluation subset, incremental ERLD closely matches the quality of resolving the complete enlarged dataset while requiring less processing time for the new increment."
  ]
 },
 {
  "paper_id": "1412.5687",
  "title": "Towards Open World Recognition",
  "research_question": "How can a recognition system reject observations belonging to previously unseen classes and then incrementally incorporate newly labeled classes without retraining the complete classifier?",
  "key_findings": [
   "The paper gives an explicit formulation of open-world recognition in which unknown inputs must be rejected and subsequently labeled classes can be added incrementally.",
   "Thresholded recognition functions that decrease with distance can be constructed to control open-space risk under the conditions analyzed by the authors.",
   "NNO can add a new class by computing and storing its class mean rather than retraining the complete multiclass classifier.",
   "In the ImageNet open-world experiments, NNO consistently handles mixtures of known and unknown classes better than the open-set adaptation of Nearest Class Mean while retaining comparable closed-set behavior.",
   "For the largest reported comparison with 500 trained known classes and testing involving 500 known plus 500 unknown classes, the paper reports almost a 74 percent improvement for open-set NNO over open-set NCM."
  ]
 },
 {
  "paper_id": "1705.08500",
  "title": "Selective Classification for Deep Neural Networks",
  "research_question": "How can a pre-trained deep neural classifier be augmented with a rejection mechanism that guarantees, with high probability, a user-specified selective risk while retaining as much prediction coverage as possible?",
  "key_findings": [
   "The proposed procedure provides a high-probability selective-risk guarantee for a fixed classifier and confidence-ranking function, targeting Pr(R>r*) below the specified confidence parameter delta.",
   "Softmax response and Monte Carlo dropout produced similar risk-coverage profiles on CIFAR-10 and CIFAR-100, while softmax response was substantially better on ImageNet.",
   "On CIFAR-10, a target risk of 1% produced test risk 0.92% with test coverage 78.56% at delta=0.001.",
   "For ImageNet top-5 classification with ResNet-50, a target risk of 2% produced test risk 1.89% while retaining 59.35% coverage.",
   "Across the reported risk-control experiments, the observed test risks remained below the corresponding computed bounds."
  ]
 },
 {
  "paper_id": "1707.07344",
  "title": "Event Coreference Resolution by Iteratively Unfolding Inter-dependencies among Events",
  "research_question": "Can event coreference resolution be improved by iteratively exploiting dependencies among event mentions and their accumulating arguments, while treating within-document and cross-document coreference differently?",
  "key_findings": [
   "Iteratively propagating arguments across merged event clusters improves event coreference decisions because later comparisons can use information that was absent from an individual mention's local sentence.",
   "Using distinct classifiers for within-document and cross-document coreference is beneficial because the two settings depend on different evidence.",
   "The complete system achieves a cross-document CoNLL F1 of 63.6 on ECB+, compared with 58.7 for the reported HDDCRP baseline and 54.8 for the lemma baseline.",
   "For within-document coreference, the complete system reaches a CoNLL F1 of 68.9, exceeding the reported HDDCRP and lemma baselines.",
   "Second-order relations between event clusters resolve additional difficult links after the first iterative stage."
  ]
 },
 {
  "paper_id": "1906.01753",
  "title": "Revisiting Joint Modeling of Cross-document Entity and Event Coreference Resolution",
  "research_question": "Can jointly resolving cross-document entity and event coreference, with each event representation informed by its argument entities and each entity representation informed by related events, outperform disjoint cross-document coreference models?",
  "key_findings": [
   "Joint entity-event modeling improved event coreference by 1.0 CoNLL F1 over the otherwise comparable disjoint model and improved entity coreference by 1.2 points, with the joint-versus-disjoint differences reported as statistically significant.",
   "The joint model achieved 79.5 CoNLL F1 for event coreference, 10.5 points above the previously published KCP result and 3.0 points above the strong topic-clustered lemma baseline.",
   "Predicate-argument relationships provide useful cross-document identity evidence because event mentions can be compared partly through whether their participants resolve to the same entity clusters, and entity identity can similarly exploit related event clusters.",
   "Document-level topic clustering is itself a strong continuity signal: near-perfect topic clustering made a simple lemma-based event-coreference baseline outperform earlier published ECB+ systems, and adding topic pre-clustering improved KCP by 4.6 CoNLL points.",
   "ECB+ deliberately contains different events of the same type in paired subtopics, so the benchmark tests whether models avoid merging superficially similar but non-identical events."
  ]
 },
 {
  "paper_id": "2011.12249",
  "title": "Generalizing Cross-Document Event Coreference Resolution Across Multiple Corpora",
  "research_question": "How well do cross-document event-coreference systems and their learned signals generalize across heterogeneous corpora, and can multi-corpus evaluation and training improve robustness?",
  "key_findings": [
   "Systems trained on a single event-coreference corpus suffer substantial performance degradation when evaluated on unseen corpora.",
   "ECB+ can be modeled largely from event-action information, while FCC-T and GVC require a more balanced use of time, participants, and other contextual signals.",
   "The feature-based approach has lower peak performance in some settings but behaves more consistently across corpora than the evaluated neural system.",
   "Design choices tailored to ECB+, including exploiting its document-link distribution through preclustering, can overfit that corpus and generalize poorly elsewhere.",
   "Joint training on FCC-T and GVC obtains a harmonic-mean LEA F1 of 40.9 across the evaluated corpora, more than 4.5 points above the best corresponding single-corpus training result."
  ]
 },
 {
  "paper_id": "2104.05022",
  "title": "WEC: Deriving a Large-scale Cross-document Event Coreference dataset from Wikipedia",
  "research_question": "Can Wikipedia hyperlink structure be exploited to build a large corpus-wide cross-document event-coreference dataset efficiently and support models beyond the topic-partitioned setting of earlier corpora?",
  "key_findings": [
   "The WEC English training set contains 40,529 event mentions grouped into 7,042 clusters, providing substantially larger-scale supervision than earlier manually built datasets.",
   "Unlike topic-partitioned corpora, WEC permits mentions to corefer across the corpus rather than restricting links to predefined topic clusters.",
   "Manual checking of development and test data yielded estimated annotation precision of 0.95, recall of 0.96, and Cohen's kappa of 0.75 in the reported quality check.",
   "The proposed model achieves 62.3 CoNLL F1 on WEC compared with 53.1 for the lemma baseline, a 9.2-point improvement.",
   "On ECB+, the same modeling approach reaches 80.8 CoNLL F1, exceeding the cited Joint baseline at 79.5."
  ]
 },
 {
  "paper_id": "2109.06417",
  "title": "Cross-document Event Identity via Dense Annotation",
  "research_question": "How can cross-document event identity be densely annotated when events may be only partially identical because their participants, time, location, or evolving real-world state overlap incompletely?",
  "key_findings": [
   "Dense cross-document annotation reveals substantial partial or quasi-identity phenomena that would be obscured by a binary notion of exact event identity.",
   "About 32% of annotated coreference links are identified as candidates for partial identity based on annotators' responses about contextual overlap.",
   "The authors identify membership, subevent relations, and spatiotemporal continuity as recurring forms of partial event identity, with spatiotemporal continuity capturing events that evolve across time or space.",
   "Partial event identity can violate transitivity, so the dataset preserves pairwise judgments rather than imposing transitive closure over all coreference links.",
   "Crowd agreement is substantially more difficult for partial identity than for clear full identity: perfect three-annotator agreement is reported for 31% of full-coreference links versus 13% of partial-coreference links."
  ]
 },
 {
  "paper_id": "2206.10009",
  "title": "Event-Case Correlation for Process Mining using Probabilistic Optimization",
  "research_question": "How can events lacking explicit case identifiers be assigned to process instances by combining control-flow, temporal, and data-attribute evidence?",
  "key_findings": [
   "Data attributes and domain constraints can materially improve reconstruction of concrete process-instance identity when explicit case identifiers are absent.",
   "Across the reported datasets, adding data constraints improves the average trace-, n-gram-, and especially case-level similarity measures, with the paper reporting average gains of roughly 6%, 15%, and 28% respectively.",
   "On the large BPIC17 experiment, the reported improvement in case-level similarity from using data constraints reaches approximately 46%.",
   "Increasing the number of correct constraints generally improves reconstruction quality, while inaccurate constraints degrade the inferred correlations.",
   "The method can operate with process models containing cyclic and parallel behavior, relaxing restrictions present in some earlier event-correlation approaches."
  ]
 },
 {
  "paper_id": "2211.07342",
  "title": "MAVEN-ERE: A Unified Large-scale Dataset for Event Coreference, Temporal, Causal, and Subevent Relation Extraction",
  "research_question": "Can a unified large-scale annotation of event coreference, temporal, causal, and subevent relations provide a stronger benchmark for event-relation extraction and exploit interactions among these relation types?",
  "key_findings": [
   "MAVEN-ERE explicitly separates same-event identity from temporal, causal, and subevent relations, containing 103,193 event coreference chains, 1,216,217 temporal relations, 57,992 causal relations, and 15,841 subevent relations.",
   "Event coreference is defined by whether mentions refer to the same real-world event, making coreference the dataset's explicit representation of event identity.",
   "Subevent links are distinct from identity: a subevent is treated as a component of a larger event that is spatiotemporally contained by that larger event.",
   "The annotation scheme permits temporal ambiguity through sub-timelines and allows an event to occur on multiple timelines, so the representation is richer than a single total temporal order.",
   "The framework makes substantial use of transitivity: the authors report that 88.8% of temporal relations and 23.9% of causal relations can be inferred from other annotated relations using their transitivity rules."
  ]
 },
 {
  "paper_id": "2405.05160",
  "title": "Selective Classification Under Distribution Shifts",
  "research_question": "How can selective classifiers reliably reject uncertain predictions and maintain low risk when test data contain in-distribution examples together with label, covariate, and out-of-distribution shifts?",
  "key_findings": [
   "Common confidence and out-of-distribution scores do not consistently provide reliable selective-classification rankings when multiple forms of distribution shift coexist.",
   "The proposed logit-margin scores produce competitive or better risk-coverage behavior than strong softmax-response and OOD-oriented alternatives across the evaluated image and text benchmarks.",
   "On mixed ImageNet distribution shifts, the proposed margin scores are among the methods that maintain decreasing risk as coverage is reduced and perform strongly when several shift types coexist.",
   "The methods require no additional training and can rank predictions from an already trained classifier using its output logits.",
   "The paper does not determine how an operational calibration set should be constructed or how the abstention threshold should be selected in deployment."
  ]
 },
 {
  "paper_id": "2406.15990",
  "title": "Enhancing Cross-Document Event Coreference Resolution by Discourse Structure and Semantic Information",
  "research_question": "Can document-level discourse structure and cross-document semantic information improve the identification and clustering of mentions that refer to the same event across documents?",
  "key_findings": [
   "Combining discourse structure and lexical-chain semantics improves cross-document event-coreference performance over the evaluated baselines on both English and Chinese datasets.",
   "On WEC-Zh, DIE-EC reports a CoNLL F1 of 66.9 compared with 62.1 for the cited WEC baseline, with improvements also reported for B3 and CEAF metrics.",
   "Ablation experiments show that removing lexical chains causes a larger performance reduction than removing RST structure, indicating that cross-document semantic coherence contributes strongly to event identity decisions.",
   "Lexical chains are especially useful when event mentions have little direct lexical overlap, with substantially larger F1 degradation when the lexical-chain component is removed in the low-overlap subset.",
   "RST-based discourse information becomes more useful for long documents, where removing the RST component produces larger performance losses."
  ]
 },
 {
  "paper_id": "2407.11988",
  "title": "Generating Harder Cross-document Event Coreference Resolution Datasets using Metaphoric Paraphrasing",
  "research_question": "Can constrained metaphoric paraphrasing create a lexically more diverse cross-document event-coreference benchmark that exposes models' dependence on surface trigger similarity while preserving the underlying event identities?",
  "key_findings": [
   "Human quality checking estimated that approximately 99% of single-word ECB+META transformations and 95% of multi-word transformations could reasonably refer to the same original events.",
   "A lemma-based filtering heuristic suffered a large recall decline under lexical transformation, while KNN retrieval was substantially more robust, especially for single-word metaphors.",
   "The strongest tested cross-encoder dropped from about 78 CoNLL F1 on ECB+ to 71.4 on the single-word metaphor set and 54.8 on the multi-word metaphor set.",
   "Trigger lexical diversity increased strongly from ECB+ to the metaphoric variants, with reported MLTD values of 7.33, 11.92, and 26.48 for ECB+, ECB+META1, and ECB+METAm respectively.",
   "Increasing lexical diversity and metaphor complexity were associated with lower CDEC performance."
  ]
 },
 {
  "paper_id": "2607.26384",
  "title": "An ER-Model-Based Framework for Case Notion Selection in Object-Centric Processes",
  "research_question": "How can an ER-schema-grounded case notion identify coherent enterprise process executions in object-centric event logs without losing coordination among business objects or spuriously merging executions through shared resource objects?",
  "key_findings": [
   "The framework grounds case identity in concrete business entities: a domain-selected primary entity acts as the semantic anchor, while selected secondary entities connect primary-entity instances participating in a joint execution.",
   "Filtering out resource-like and parent objects is intended to prevent unrelated executions from being merged merely because they share employees, equipment, customers, or other broadly connected objects.",
   "On the evaluated 1,000-event log, the framework reports 40 cases derived from 114 orders and 50 packages, with zero omitted primary entities and zero overlap between cases.",
   "The largest reported case contains 11 orders connected transitively through four packages even though no single package directly connects all 11 orders, demonstrating that case identity can arise from a chain of coordination events rather than a single shared event.",
   "The evaluation identifies 21 complete and 19 incomplete cases; incomplete cases remain legitimate cases even when the expected package event has not yet appeared, which provides concrete evidence for partially observed and potentially evolving work executions."
  ]
 },
 {
  "paper_id": "doi-10-1002-asi-21264",
  "title": "New event detection and topic tracking in Turkish",
  "research_question": "How effectively can new-event detection and topic tracking be performed on Turkish news streams, and how do representation, similarity, temporal-window, stemming, stopword, and adaptive-tracking choices affect performance?",
  "key_findings": [
   "The paper operationalizes continuity across documents as a TDT topic consisting of a seminal event or activity plus directly related subsequent events and activities, so document membership can persist even when later stories describe consequences or related developments rather than merely repeat the original event.",
   "Adaptive topic tracking, which updates the topic representation with newly accepted stories, was consistently more effective than corresponding static tracking approaches, providing evidence that an evolving representation can preserve continuity as a topic develops.",
   "Combining cover-coefficient and cosine decisions with an OR rule reduced new-event miss rate and produced the lowest test CDet among the evaluated NED variants, although its advantage over the individual similarity measures was not statistically significant on the test set.",
   "A broad stoplist significantly improved Turkish NED relative to using no stopwords, showing that feature-selection choices materially affect judgments of whether a document continues an existing event.",
   "Topic tracking was substantially easier than first-story detection, and the authors judged Turkish tracking performance suitable for operational use while stating that NED still had considerable room for improvement."
  ]
 },
 {
  "paper_id": "doi-10-1002-sim-4780140510",
  "title": "Probabilistic linkage of large public health data files",
  "research_question": "How can large public-health files be linked probabilistically when identifiers are uncertain or erroneous while making linkage computationally feasible and statistically defensible?",
  "key_findings": [
   "The method models linkage uncertainty using match-agreement probabilities and chance-agreement probabilities for comparison fields rather than treating field agreement as deterministic identity.",
   "Expectation-maximization is used to estimate linkage parameters iteratively rather than requiring all agreement probabilities to be fixed before matching.",
   "The approach incorporates linear-sum assignment optimization to make globally consistent linkage assignments between two files.",
   "The abstract states that modeling match and nonmatch probabilities across individual field values provides greater precision when field-value frequencies are non-uniform, but the accessible abstract does not expose quantitative evidence for the gain.",
   "The abstract describes iterative parameter estimation as more robust than estimating parameters before matching, although the underlying comparative results are not available in the accessible text."
  ]
 },
 {
  "paper_id": "doi-10-1007-978-3-030-33223-5-12",
  "title": "A Probabilistic Approach to Event-Case Correlation for Process Mining",
  "research_question": "Can missing case identifiers in timestamped business-process events be reconstructed automatically, without requiring acyclic processes or external execution-time heuristics, by optimizing process-model conformance and activity-duration consistency?",
  "key_findings": [
   "EC-SA can reconstruct a complete case assignment from an event stream without case identifiers, assigning every input event to exactly one case even when an event cannot be replayed as enabled by the process model.",
   "With effectively perfect process knowledge, EC-SA achieved an average L2Lsim of 0.901 across the twelve evaluated real-life logs, corresponding to an average accuracy loss of about 10 percent, while average L2LSMAPE was 17.6 percent.",
   "Replacing perfect process knowledge with mined process models reduced L2Lsim by 4.42 percent on average and increased L2LSMAPE by 16.67 percent on average relative to the first experiment.",
   "Correlation quality depends materially on the quality of the process model: low precision creates more alternative replay possibilities, while poor fitness can prevent stricter correlation methods from assigning deviating events.",
   "Against DCI using Split Miner models, EC-SA had better L2Lsim on most evaluated logs, although DCI achieved higher L2Lsim on three logs and lower L2LSMAPE on one log."
  ]
 },
 {
  "paper_id": "doi-10-1007-978-3-030-49461-2-23",
  "title": "Incremental Multi-source Entity Resolution for Knowledge Graph Completion",
  "research_question": "How can multi-source entity resolution incorporate newly arriving entities efficiently while preserving clustering quality and correcting earlier identity decisions without repeatedly resolving all previously processed data?",
  "key_findings": [
   "Incremental resolution can achieve clustering quality comparable to batch resolution while avoiding repeated linking and clustering of all historical entities.",
   "Simple max-both incremental assignment can become sensitive to the order in which sources arrive, whereas one-depth reclustering substantially reduces this dependency.",
   "One-depth reclustering reaches approximately the same clustering quality as batch processing in the reported source-wise experiments while allowing previous cluster decisions to be repaired locally.",
   "Linking newly arriving entities to one another as well as to historical entities improves results in entity-wise incremental scenarios.",
   "All evaluated incremental approaches are faster than repeatedly executing the batch procedure on the growing data, with max-both variants being faster than the more repair-oriented n-depth method."
  ]
 },
 {
  "paper_id": "doi-10-1007-978-3-540-27868-9-84",
  "title": "A Two-Stage Classifier with Reject Option for Text Categorisation",
  "research_question": "Can a text classifier improve overall classification reliability by rejecting uncertain category decisions at a first stage and automatically resolving those rejected decisions with a specialized second-stage classifier?",
  "key_findings": [
   "With an MLP first-stage classifier, the two-stage reject architecture raises micro-F1 from 0.846 to 0.854 and macro-F1 from 0.447 to 0.481 in the reported configurations.",
   "With Naive Bayes at the first stage, reported micro-F1 rises from 0.700 to 0.825 and macro-F1 from 0.214 to 0.456 under the strongest shown reject configuration.",
   "For a fixed first-stage reject rate, larger second-stage training sets generally produce larger improvements.",
   "When the second-stage training and validation sets are too small, F1 can fall below the corresponding no-reject result.",
   "In some configurations the tailored two-stage architecture outperforms a conventional k-NN classifier without rejection."
  ]
 },
 {
  "paper_id": "doi-10-1007-s00778-010-0203-9",
  "title": "Event correlation for process discovery from Web service interaction logs",
  "research_question": "How can events scattered across Web-service interaction logs be correlated, partly automatically and with user guidance, so that useful business-process executions and process views can be discovered?",
  "key_findings": [
   "A single collection of enterprise service-interaction events can admit multiple plausible correlations and therefore multiple process views rather than one uniquely determined process reconstruction.",
   "The paper represents alternative event-correlation interpretations explicitly through the concepts of process views and process space.",
   "Exhaustively exploring possible event correlations is computationally expensive, motivating heuristics that concentrate on correlated event sets likely to yield interesting process views.",
   "Because event correlation can be subjective, the proposed discovery workflow incorporates interactive user guidance instead of relying entirely on automatic inference.",
   "Experiments on both synthetic and real-world data are reported as showing the viability and efficiency of the proposed approach."
  ]
 },
 {
  "paper_id": "doi-10-1007-s10115-019-01430-6",
  "title": "Case notion discovery and recommendation: automated event log building on databases",
  "research_question": "Can candidate case notions for process mining be automatically discovered from complex databases and ranked by predicted event-log interestingness before the expensive event logs themselves are constructed?",
  "key_findings": [
   "The framework can systematically generate alternative database case notions and construct corresponding event logs, allowing multiple process perspectives to be explored from the same underlying data.",
   "The authors' unsupervised predictors were substantially less accurate for individual log-property values than stronger supervised regressors such as quantile regression and neural-network regression.",
   "Despite weak absolute prediction accuracy, the custom unsupervised predictor preserved relative interestingness well enough to provide useful rankings and outperformed the evaluated regressors on average for ranking quality.",
   "Among the compared supervised ranking approaches, MART and Random Forest were the only algorithms whose median NDCG@10 exceeded the custom predictor's median in the reported comparison.",
   "When labeled training data are available, supervised regressors are preferable for accurate property prediction and learning-to-rank methods such as Random Forest and MART provide stronger rankings; the proposed predictor is intended for settings without such training data."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-ipm-2025-104085",
  "title": "Improving cross-document event coreference resolution by discourse coherence and structure",
  "research_question": "Can cross-document event coreference resolution be improved by constructing coherent discourse between mentions in different documents and exploiting the resulting rhetorical discourse structure for pairwise coreference decisions?",
  "key_findings": [
   "ECD-CoE explicitly constructs a textual bridge between event mentions from separate documents so that cross-document pairs can be processed more like document-level coherent discourse.",
   "The model represents the constructed discourse as a rhetorical tree and derives global pair information from the closest common ancestor and the shortest rhetorical path between event mentions.",
   "The reported CoNLL F1 scores are 88.1 on ECB+ and 87.3 on GVC.",
   "The proposed approach is reported to outperform several state-of-the-art comparison systems on both ECB+ and GVC.",
   "The evaluation uses gold event mentions rather than evaluating an end-to-end event-detection and coreference pipeline."
  ]
 },
 {
  "paper_id": "doi-10-1038-s41598-025-32765-6",
  "title": "Argument centric causal intervention for cross document event coreference resolution",
  "research_question": "Can cross-document event coreference be improved by explicitly suppressing spurious trigger-word correlations and shifting model decisions toward event arguments and contextual semantics through causal and counterfactual intervention?",
  "key_findings": [
   "ACCI achieves a reported CoNLL F1 of 88.4 on ECB+, outperforming the compared systems on aggregate CoNLL F1 in the reported table.",
   "ACCI reports a CoNLL F1 of 85.2 on GVC; it is competitive but is not the highest result in that table, where Chen2025 reports 85.8.",
   "Removing both trigger-bias mitigation and context-argument enhancement reduces CoNLL F1 from 88.4 to 87.2 on ECB+ and from 79.0 to 77.6 in the corresponding GVC ablation setting.",
   "The cross-dataset experiments report that ACCI consistently exceeds its corresponding baselines when training on ECB+ and testing on GVC or reversing the domains.",
   "Qualitative cases demonstrate both relevant identity patterns: semantically different events can share the same trigger, and the same event can be expressed with different triggers."
  ]
 },
 {
  "paper_id": "doi-10-1038-s41598-026-40637-w",
  "title": "Conformal selective prediction with cost aware deferral for safe clinical triage under distribution shift",
  "research_question": "Can calibrated prediction, conformal uncertainty sets, and cost-aware deferral be combined to make early-sepsis triage safer under both in-distribution and shifted clinical data?",
  "key_findings": [
   "At 80% prediction coverage, selective prediction is reported to reduce error on retained cases by 49.6% in-distribution and 46.7% out-of-distribution.",
   "Nominal 90% conformal coverage remains close to target in-distribution but degrades under distribution shift, with the importance-weighted variant reported as the most robust of the tested conformal strategies.",
   "Gender-stratified Mondrian conformal prediction reduces the reported subgroup coverage gap to 1.4 percentage points.",
   "The reported expected clinical cost is 0.5640 in-distribution and 0.7053 out-of-distribution under the evaluated decision setup.",
   "The calibrated model reports expected calibration error of 0.016 in-distribution and 0.030 out-of-distribution, indicating deterioration but still relatively small measured calibration error after temporal shift."
  ]
 },
 {
  "paper_id": "doi-10-1080-01621459-1969-10501049",
  "title": "A Theory for Record Linkage",
  "research_question": "How can a record-linkage system optimally decide whether records from two files represent the same underlying person, object, or event while controlling false-link and false-nonlink errors?",
  "key_findings": [
   "Record linkage can be formulated as a three-way statistical decision problem with link, possible-link, and non-link outcomes.",
   "For fixed false-link and false-nonlink error levels, the optimal linkage rule minimizes the probability of leaving a comparison unresolved as a possible link.",
   "The optimal ordering of comparison patterns is determined by the likelihood ratio m(gamma)/u(gamma), with upper and lower thresholds defining link, review, and non-link regions.",
   "The derived linkage rule is equivalent to a likelihood-ratio hypothesis-testing procedure.",
   "Under conditional independence of groups of comparison variables, the logarithm of the likelihood ratio decomposes into additive field-level weights."
  ]
 },
 {
  "paper_id": "doi-10-1109-access-2023-3284053",
  "title": "Step-by-Step Case ID Identification Based on Activity Connection for Cross-Organizational Process Mining",
  "research_question": "Can corresponding case identifiers across independently identified organizational event logs be recovered accurately by iteratively discovering temporal connections between activities, including in cyclic business processes?",
  "key_findings": [
   "The step-by-step procedure can recover cross-organizational case relationships without using a globally shared case identifier during mining.",
   "Iteratively using already identified case mappings to discover new activity connections expands the set of cases that can subsequently be matched.",
   "On the two evaluated datasets, the resulting integrated process models achieved precision above 98.4% and recall above 94.2% in the reported headline evaluation.",
   "The proposed approach outperformed the compared previous method for reconstructing process models in the evaluated settings.",
   "Removing integration-order bias produces a more robust three-organization process model on the BPI Challenge 2017 experiment."
  ]
 },
 {
  "paper_id": "doi-10-1109-icpm57379-2022-9980684",
  "title": "Improving Accuracy and Explainability in Event-Case Correlation via Rule Mining",
  "research_question": "Can event-case correlation be made more accurate and explainable when reliable prior domain rules are unavailable by iteratively learning association rules during the correlation process?",
  "key_findings": [
   "When no prior data rules were supplied, EC-SA-RM produced more accurate event-case correlations than the baseline simulated-annealing method across the evaluated logs.",
   "In the no-prior-rule experiment, average structural similarity improved by about 14% for the 2-gram measure and about 20% for the case-similarity measure.",
   "In the same experiment, elapsed-time and cycle-time deviations decreased by about 13% and 19%, respectively.",
   "When partial prior rules were available, iterative rule mining still improved structural and temporal correlation quality over the comparison method using only the supplied rules.",
   "The mined association rules provide human-readable conditions that can be used to explain why events are assigned to particular cases."
  ]
 },
 {
  "paper_id": "doi-10-1109-tbdata-2022-3204207",
  "title": "Tracking the Evolution of Clusters in Social Media Streams",
  "research_question": "Can a density-peak stream-clustering method efficiently track the evolving identity and structure of clusters and outliers when only a local, partial view of a high-speed social-media stream is available?",
  "key_findings": [
   "The paper treats cluster continuity as an evolving relation with explicit adjustment, emergence, disappearance, split, and merge actions rather than assuming that a cluster has a fixed identity through time.",
   "The streaming setting is explicitly characterized by a local or partial view of the data rather than access to the complete global history.",
   "Temporal decay decreases the influence of older textual documents, while micro-clusters compactly summarize the evolving stream in memory.",
   "The shared dependency tree maintains dynamic dependency relationships and is intended to improve the efficiency of tracking changing clusters.",
   "Across five reported real datasets, TStream improves cluster mapping measure over MStream, MStreamF, EDMStream, OSGM, and EStream by up to 17.8%, 18.6%, 6.9%, 16.4%, and 20.1%, respectively, and is reported as more efficient than several of those baselines in response time and throughput."
  ]
 },
 {
  "paper_id": "doi-10-1145-1111449-1111471",
  "title": "Automatically classifying emails into activities",
  "research_question": "Can incoming email be incrementally associated with the user's evolving work activities more accurately than by relying on conventional email threads alone?",
  "key_findings": [
   "Email-thread membership alone is insufficient to recover work-activity identity because an activity can span messages that are not in one reply thread.",
   "Content-based retrieval provides substantially stronger activity recommendations than the threading baseline, with the best reported top-three recommendation accuracy around 94% versus about 58% for threading.",
   "Combining threading, people, and content evidence by voting achieves approximately 93% recognition accuracy and an F-measure of 0.81, compared with an F-measure around 0.60 for threading alone.",
   "The study directly demonstrates longitudinal cross-thread email-to-work-activity linking in an online setting where the set of activities evolves over time.",
   "Participant identity alone is unreliable for work-item linking because the same people may participate in several simultaneous activities and the participant set of one activity can change over time."
  ]
 },
 {
  "paper_id": "doi-10-1145-1111449-1111472",
  "title": "Linking messages and form requests",
  "research_question": "Can an intelligent interface infer the form and field values implied by free-text email or instant-message requests and support task completion more efficiently than routing those requests through a human form expert?",
  "key_findings": [
   "The prototype operationalizes a concrete work request by mapping a free-text message to a particular form and extracted field values, while keeping the requester in the loop to repair incorrect mappings.",
   "The form classifier had a 20.8% error rate in the experiment, so the initially selected form was correct roughly four-fifths of the time, with the interface designed to let users repair the remaining errors.",
   "Average task time was 22.6 minutes in the VIO condition versus 33.0 minutes in the human-webmaster condition, but the authors explicitly state that the sample was too small for reliable statistical claims.",
   "The human-webmaster condition contained 14 non-optimal interactions among 108 task transactions, including incomplete requests, ambiguity, corrections, and one case in which two concurrently outstanding tasks were confused and required multiple email exchanges to disentangle.",
   "The observed inter-task confusion provides direct evidence that multiple outstanding email-mediated work requests can lose task identity across exchanges, although the paper does not propose a persistent cross-thread work-item identity model to solve that problem."
  ]
 },
 {
  "paper_id": "doi-10-1145-1111449-1111473",
  "title": "A hybrid learning system for recognizing user tasks from desktop activities and email messages",
  "research_question": "Can machine-learning models automatically infer a user's current task from desktop activity or an incoming email with sufficiently high precision to reduce the need for manual task selection?",
  "key_findings": [
   "Incoming email can be classified into a user's predefined work tasks using sender, recipient, and subject information with high precision at useful but incomplete coverage.",
   "The email predictor reached about 92% precision at roughly 66% coverage with the hybrid classifier in the reported evaluation.",
   "The hybrid Naive-Bayes/SVM design generally matched or exceeded the best individual classifier's precision at comparable coverage.",
   "Using approximately 200 mutual-information-selected features was sufficient for the evaluated email and desktop predictors and avoided unnecessary feature growth.",
   "Words from the email body did not provide additional predictive benefit in the authors' experiments beyond sender, recipient, and subject features."
  ]
 },
 {
  "paper_id": "doi-10-1145-290941-290953",
  "title": "A Study of Retrospective and On-Line Event Detection",
  "research_question": "How effectively can text retrieval and document-clustering techniques, using content and temporal information, detect previously unknown events retrospectively and identify new events as news stories arrive?",
  "key_findings": [
   "Hierarchical document clusters were reported to be informative for retrospective discovery of previously unidentified events.",
   "The resulting cluster structure supported both query-free and query-driven retrospective retrieval.",
   "Temporal distribution patterns of document clusters were reported to improve both retrospective and online event detection.",
   "Retrospective event detection achieved an F1 measure of 82%.",
   "Online event detection achieved an F1 measure of 42%, substantially below the retrospective result."
  ]
 },
 {
  "paper_id": "doi-10-1145-290941-290954",
  "title": "On-Line New Event Detection and Tracking",
  "research_question": "How can a system operating strictly online detect previously unseen real-world news events and continue tracking those events as their reporting and descriptive features evolve over time?",
  "key_findings": [
   "The paper treats concrete event identity, rather than broad topical similarity, as the central relation for detection: a story is old if it describes an event identical to one already represented, and otherwise it is a new event.",
   "The authors find that event identity is intrinsically difficult to delimit by time and place; their own examples show that an intuitively single event can extend across long periods and multiple locations.",
   "Adding a temporal penalty to detection thresholds generally improved performance, supporting the idea that stories close together in the stream are more likely to concern the same event than stories far apart.",
   "Failure analysis shows a granularity problem: representations of a specific event can drift toward a broad event class, causing a system to confuse distinct plane crashes, bombing-related stories, or other events that share class-level vocabulary.",
   "Event tracking benefits substantially from incremental adaptation because important event-specific entities and facts may emerge only well after the initial stories; adaptive query rebuilding can capture such later features and reduce the amount of initial training material required."
  ]
 },
 {
  "paper_id": "doi-10-1145-354756-354843",
  "title": "First Story Detection In TDT Is Hard",
  "research_question": "Can first-story detection performance be explained and bounded by tracking performance, and what does that relationship imply about the practical difficulty of detecting genuinely new topics in a news stream?",
  "key_findings": [
   "Observed first-story detection performance falls close to and substantially overlaps the range predicted from the corresponding tracking system, supporting the proposed reduction from first-story detection to tracking.",
   "The tracking error rates achievable by the evaluated similarity-based systems imply poor first-story detection performance across practical operating thresholds.",
   "For the one-training-story tracking case, reaching the authors' illustrative first-story target would require roughly a twenty-fold improvement in tracking effectiveness.",
   "Historical tracking results available to the authors gave little reason to expect an improvement of that magnitude from conventional tracking or filtering technology.",
   "The authors conclude that substantially better first-story detection probably requires approaches that exploit information about event or topic structure rather than simply treating the problem as repeated full-text tracking."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2020-coling-main-275",
  "title": "Event Coreference Resolution with their Paraphrases and Argument-aware Embeddings",
  "research_question": "Can event-coreference resolution be improved by jointly modeling event-centered paraphrase evidence and argument-aware semantic representations instead of relying mainly on lexical matching or fixed argument slots?",
  "key_findings": [
   "EPASE reaches a reported CoNLL F1 of 84.3 on the combined within-document and cross-document ECB+ evaluation.",
   "The paper reports a 4.3-point CoNLL F1 improvement over the compared Joint+Chirps system on the combined evaluation.",
   "For within-document coreference, EPASE reports a CoNLL F1 of 88.3, 4.2 points above the compared Joint model result reported in the paper.",
   "Ablation of the argument-aware semantic component lowers combined CoNLL F1 from 84.3 to 82.1, indicating that the semantic representation supplies substantial predictive value.",
   "Ablation of the event-specific paraphrase component lowers combined CoNLL F1 from 84.3 to 82.7, supporting the usefulness of paraphrase information beyond the other model components."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2022-emnlp-main-58",
  "title": "Cross-document Event Coreference Search: Task, Dataset and Modeling",
  "research_question": "Can cross-document event coreference be reformulated as large-scale semantic search from a single query event mention, and can retrieval-plus-reading models effectively find and extract its coreferring mentions across a large document collection?",
  "key_findings": [
   "CoreSearch establishes a query-oriented alternative to exhaustive cross-document event clustering, in which a marked event mention is used to retrieve and extract all coreferring mentions from a large passage collection.",
   "The dense SpanBERT-based retriever outperformed the BM25 baseline across the reported retrieval metrics.",
   "On the test set, the integrated end-to-end model achieved MRR@10 of 90.06, mAP@10 of 63.26, mAP@50 of 72.91, exact match of 71.44, and span F1 of 84.16.",
   "Explicit mention-boundary markers provide a strong signal, improving retriever performance and particularly helping mention-span detection in the reader.",
   "Replacing the generic DPR passage-selection score with an explicit coreference-scoring component improved both passage reranking and mention detection."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2023-emnlp-main-294",
  "title": "Cross-Document Event Coreference Resolution on Discourse Structure",
  "research_question": "Does representing global discourse structure and long-distance discourse paths improve clustering of event mentions across documents that refer to the same real-world event?",
  "key_findings": [
   "The task explicitly defines cross-document event identity as grouping event mentions from different documents that refer to the same real-world event.",
   "Adding within-document discourse lowest-common-parent information raised CoNLL from 81.1 to 82.3, adding cross-document LCP information raised it further to 83.9, and adding discourse-tree shortest-path information raised it to 85.7.",
   "The ablation results provide direct evidence that cross-document global discourse information contributes beyond local event-sentence representations when deciding event identity.",
   "With Longformer as encoder, the proposed model reached a CoNLL score of 86.4 and significantly exceeded the strongest reported comparison by 0.7 points.",
   "The best cross-document discourse construction strategy retained the event sentences while compressing other context; using only event sentences lost useful contextual links, while concatenating full documents introduced excessive noise."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2024-findings-emnlp-725",
  "title": "Distance-aware Calibration for Pre-trained Language Models",
  "research_question": "Can a post-hoc calibration method that reduces confidence as a sample moves farther from the training distribution improve language-model calibration under distribution shift and improve out-of-distribution detection?",
  "key_findings": [
   "DAC consistently improves out-of-distribution calibration over the evaluated baselines under random-character and keyboard-typo perturbations, with the largest gains at higher noise levels.",
   "Under non-synthetic content shifts, DAC remains strong for OOD calibration but temperature scaling is a substantially stronger competitor and beats DAC in at least the RoBERTa natural-language-inference case.",
   "For in-domain calibration, DAC improves on the uncalibrated model, but temperature scaling is generally more effective.",
   "Using DAC confidence for OOD detection improves the underlying language model and achieves the best reported result among the compared methods in all but one evaluated model/task case.",
   "The ablation finds KNN distance more effective than Mahalanobis distance or a Gaussian-mixture-model score for DAC in the evaluated noisy-text settings."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2025-acl-long-1134",
  "title": "Employing Discourse Coherence Enhancement to Improve Cross-Document Event and Entity Coreference Resolution",
  "research_question": "Can explicitly adding coherent bridging discourse between mentions from different documents improve cross-document event and entity coreference resolution?",
  "key_findings": [
   "Adding selected coherent bridging text improves cross-document coreference performance relative to the same coreference approach without discourse-coherence enhancement.",
   "Reported CoNLL-score gains over the corresponding no-enhancement model include 1.6 points for ECB+ event coreference, 1.0 point for ECB+ entity coreference, 5.7 points on WEC, 3.6 points on ECB+META1, and 5.7 points on ECB+METAm.",
   "Random or deliberately suboptimal inserted text performs worse than coherently selected text across the reported datasets, supporting the authors' claim that discourse coherence rather than merely extra context drives the benefit.",
   "Event identity is represented as ordinary coreference: mention pairs judged to refer to the same event are clustered into shared coreference chains.",
   "The resulting identity relation is equivalence-style clustering rather than a representation of partial, subevent, evolving, or explicitly non-transitive continuity."
  ]
 },
 {
  "paper_id": "doi-10-2139-ssrn-7284343",
  "title": "Multimodal Cross-Document Event Coreference Resolution via Contrastive Evidence Reasoning",
  "research_question": "Can a training-free, zero-shot multimodal framework resolve cross-document event coreference competitively by contrasting explanations for same-event and different-event hypotheses while also supporting streaming updates?",
  "key_findings": [
   "MM-CDECR reports CoNLL F1 scores of 88.1% on ECB+, 73.3% on AIDA Phase 1, and 72.2% on WEC-Eng.",
   "On ECB+, the training-free framework reportedly matches the strongest supervised text-only system in aggregate CoNLL F1 and obtains the best B3 and CEAFe scores among non-oracle baselines.",
   "On AIDA Phase 1, MM-CDECR reportedly exceeds the best prior multimodal-benchmark baseline by 6.6 points.",
   "On WEC-Eng, MM-CDECR reportedly exceeds the best supervised baseline by 6.3 points.",
   "The framework performs coreference inference without task-specific training data and produces abductive explanations for individual decisions."
  ]
 },
 {
  "paper_id": "doi-10-3115-1220575-1220591",
  "title": "Using Names and Topics for New Event Detection",
  "research_question": "Can separate similarity evidence from named entities, topical terms, and full text improve automatic discrimination between stories that continue known events and stories that introduce new events?",
  "key_findings": [
   "The central identity hypothesis is that stories about the same topic should usually overlap in both event-characterizing names and topical terms, whereas different but superficially similar events may overlap strongly in only one of those dimensions.",
   "SVM classifiers using full-text, named-entity, and topic-term similarities significantly improved NED performance over the baseline vector-space system on the tested TDT collections.",
   "The main observed benefit was better separation of previously seen stories from genuinely new stories, especially by moving many old-story scores toward the old end of the confidence scale and thereby reducing false alarms.",
   "Names alone are insufficient for event identity because two distinct events may share high-IDF people, places, or organizations while differing in topical content.",
   "The method becomes unreliable for loosely connected evolving topics in which later stories share only a tenuous cue such as the disaster name or location with the original story."
  ]
 },
 {
  "paper_id": "doi-10-3115-v1-w14-2910",
  "title": "Evaluation for Partial Event Coreference",
  "research_question": "How should systems that predict partial, hierarchical relationships among event mentions be evaluated when ordinary event-coreference metrics assume flat equivalence clusters?",
  "key_findings": [
   "Grouping fully coreferential mentions into conceptual event nodes provides a representation in which partial coreference can be evaluated as hierarchical relations between events rather than only as flat mention clusters.",
   "Extensions of MUC and BLANC satisfy the paper's evaluation desiderata more adequately than the normalized Simple Tree Matching approach examined by the authors.",
   "The normalized Simple Tree Matching metric fails some monotonicity or linearity requirements in the tested response configurations.",
   "The partial-coreference extension of MUC is described as flexible but retains known MUC weaknesses, including preferences associated with larger coreference groups and poor treatment of singleton recall.",
   "The partial-coreference extension of BLANC is presented as an attractive alternative when true event mentions are supplied, while mention-detection mismatches complicate its use."
  ]
 },
 {
  "paper_id": "doi-10-3390-industries1010003",
  "title": "StableID: An Iterative Graph-Based Framework for Persistent Entity Identification in Evolving Industrial Data Systems",
  "research_question": "How can graph-based entity-resolution systems preserve stable, auditable identifiers for real-world entities as identifying evidence and connected components evolve over repeated executions?",
  "key_findings": [
   "Feeding prior entity-group assignments into later graph executions and retaining a dominant historical identifier substantially reduces identifier churn across repeated runs.",
   "StableID maintains roughly 95% or better identifier retention through most iterative runs, while the naive independently recomputed connected-component baseline exhibits about 40% identifier churn on otherwise stable data.",
   "The graph converges as new identifying evidence is absorbed: reported merge counts fall from 12,847 in iteration 8 to 847 in iteration 9 and 12 in iteration 10 while the total identifier count stabilizes near 7.63 million.",
   "The deterministic dominance rule preserves the identifier carrying the greatest historical support when previously separate components merge, making identifier evolution auditable rather than arbitrary.",
   "The evaluation does not establish precision or recall against definitive real-world identity ground truth because such ground truth was unavailable for the protected voter-identity setting."
  ]
 },
 {
  "paper_id": "manual-03d6dfa532",
  "title": "Post-Hoc Uncertainty Calibration for Domain Drift Scenarios",
  "research_question": "Can post-hoc confidence calibration remain reliable under domain drift by fitting calibrators to deliberately perturbed validation data rather than only to in-domain validation examples?",
  "key_findings": [
   "Post-hoc calibrators fitted only on in-domain validation data become increasingly overconfident as domain shift grows.",
   "Fitting calibrators on perturbed validation samples reduces overall calibration error across the evaluated drift scenarios and architectures.",
   "The benefit of perturbation-aware calibration also appears on ObjectNet, providing evidence beyond the synthetic perturbation experiments.",
   "Perturbation-aware temperature-scaling variants can trade better shifted-domain calibration for worse calibration on unshifted or mildly shifted data.",
   "Perturbation-aware isotonic regression provides a comparatively favorable balance, improving shifted-domain calibration without the same pronounced in-domain deterioration observed for some temperature-scaling variants."
  ]
 },
 {
  "paper_id": "manual-35bac66e3c",
  "title": "Detecting Subevent Structure for Event Coreference Resolution",
  "research_question": "Can event coreference resolution explicitly distinguish full event identity from partial identity expressed through hierarchical subevent parent-child and sister relations, and can structural reasoning improve those classifications?",
  "key_findings": [
   "The paper directly distinguishes full event identity from partial event identity, treating subevent parent-child relations as a form of partial coreference rather than collapsing them into either identity or non-identity.",
   "Event structure is not purely pairwise: several subevents can share a parent and form a subevent cluster, while subevents under the same parent can have sister relations.",
   "The first-stage multiclass model jointly predicts full coreference, directed subevent parent-child relations, subevent sister relations, and no coreference.",
   "Using sister-cluster structure to vote for a parent improved subevent-parent BLANC F1 from 56.19 in the first-stage model to 59.45 with the stronger second-stage option, a gain of about 3.2 points.",
   "The results support the value of enforcing structure beyond independent pairwise judgments, but the authors identify structural consistency as unfinished work rather than a solved problem."
  ]
 },
 {
  "paper_id": "manual-5c20fb0229",
  "title": "Topic Detection and Tracking Evaluation Overview",
  "research_question": "How can topic detection and tracking technologies for multilingual news streams be defined and evaluated consistently under controlled conditions?",
  "key_findings": [
   "Topic continuity in a document stream can be decomposed into five distinct evaluation tasks: tracking, link detection, topic detection, first-story detection, and story segmentation.",
   "TDT uses controlled laboratory simulations so competing technologies can be compared under standardized conditions.",
   "Shared corpora and evaluation metrics are central components of the TDT methodology.",
   "The evaluation framework is designed for multilingual, news-oriented textual material originating from multiple broadcast-news sources."
  ]
 },
 {
  "paper_id": "manual-61a7e10e5f",
  "title": "Semantic Relations between Events and their Time, Locations and Participants for Event Coreference Resolution",
  "research_question": "How much do event participants, times, locations, and semantic relations such as hyponymy and granularity contribute to cross-document event coreference resolution beyond matching event actions alone?",
  "key_findings": [
   "Using semantic similarity for actions rather than strict lemma matching increases recall by as much as about six percentage points on most metrics but reduces precision by roughly two to seventeen points.",
   "Adding participant compatibility to action similarity performs slightly better than adding time or location information, with approximately one percentage point higher precision in the reported comparison.",
   "For participant matching, the semantic similarity heuristic produces about one point higher F-scores and roughly two to four points higher precision than the granularity heuristic on most metrics.",
   "Both participant-based variants improve F-scores over the action-similarity-only heuristic on most metrics, by roughly one to four points for granularity and one to six points for participant similarity.",
   "The best action-plus-participant configuration reports F-scores of 70.7 MUC, 74.1 B3, 64.9 CEAFm, 70.4 BLANC, and 69.8 CoNLL."
  ]
 },
 {
  "paper_id": "manual-c43ffe3135",
  "title": "Cross-document Event Identity via Dense Annotation",
  "research_question": "How can cross-document event identity be densely annotated so that both full event identity and important forms of partial or quasi-identity are represented?",
  "key_findings": [
   "CDEC-WN contains 7,220 event mentions and 4,282 cross-document event links across 198 document pairs drawn from 55 subtopics.",
   "About 32 percent of the annotated cross-document links were identified as candidates for partial rather than full event identity.",
   "The analysis identifies membership, subevent relations, and a newly proposed spatiotemporal-continuity category as important forms of quasi-identity.",
   "Partial event identity can violate transitivity, making conventional event clustering an imperfect representation for these links.",
   "The neural cross-encoder reaches 57.6 test F1 compared with 48.2 for the lemma-matching baseline, but performance remains limited, particularly on partial identity."
  ]
 },
 {
  "paper_id": "manual-e988e24127",
  "title": "Revisiting Joint Modeling of Cross-document Entity and Event Coreference Resolution",
  "research_question": "Can cross-document entity and event coreference be improved by jointly and iteratively modeling the dependencies between event mentions and their entity arguments rather than resolving the two tasks independently?",
  "key_findings": [
   "The joint model achieved 79.5 CoNLL F1 for event coreference, 10.5 points above the previously published KCP result and 1.0 point above the authors' disjoint model.",
   "For entity coreference, the joint system obtained 71.2 CoNLL F1, compared with 70.0 for the disjoint variant and 67.4 for the Cluster+Lemma baseline.",
   "Joint modeling improved both entity and event coreference over the disjoint architecture, with the reported differences significant under bootstrap and permutation testing at p<0.001.",
   "Document topic pre-clustering was itself highly consequential: adding the authors' clustering stage to KCP improved its event-coreference CoNLL F1 by 4.6 points.",
   "Ablation experiments showed that representations of semantically dependent mentions contributed more than the simple pairwise binary joint features, while removing both joint components reduced event CoNLL F1 from 79.5 to 78.5."
  ]
 },
 {
  "paper_id": "manual-f56d02b8f9",
  "title": "Using a sledgehammer to crack a nut? Lexical diversity and event coreference resolution",
  "research_question": "Is EventCorefBank representative of the lexical and event diversity found in large news streams, and can its coverage be improved by adding distinct instances of the same event types?",
  "key_findings": [
   "EventCorefBank generally covers only one seminal event within a domain, substantially simplifying the diversity encountered in real news streams.",
   "Introducing different instances of already represented event types increases the corpus's lexical and event diversity.",
   "The augmentation adds 502 texts spanning alternative instances associated with the 43 existing ECB topics.",
   "The resulting ECB+ corpus is intended to provide a more representative resource for event-coreference research on web news."
  ]
 }
]

JSON schema for the verdict:
{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "title": "ReviewerResult",
 "description": "Schema for reviewer gate results (synthesis reviewer, rank reviewer).",
 "type": "object",
 "required": [
  "reviewer_task_id",
  "target_artifact",
  "status"
 ],
 "properties": {
  "reviewer_task_id": {
   "type": "string"
  },
  "target_artifact": {
   "type": "string"
  },
  "status": {
   "type": "string",
   "enum": [
    "accepted",
    "rejected",
    "accepted_with_issues"
   ]
  },
  "issues": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "unsupported_claims": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "required_fixes": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "confidence": {
   "type": "number",
   "minimum": 0.0,
   "maximum": 1.0
  },
  "notes": {
   "type": "string"
  }
 }
}

Reply with one block containing one JSON object:
`reviewer_task_id` = "review-synthesis-web", `target_artifact` =
"/home/grammy-jiang/Projects/msgloom/research/03-cross-thread-topic-tracking/runs/2be7131314a5/analysis/synthesis.json", `status` = accepted | accepted_with_issues | rejected,
`issues` (each naming the finding or paper it is about), `required_fixes`
(required when rejected), `unsupported_claims`, `confidence`, and `scores`
with faithfulness, coherence, gap_completeness (0-1) and citation_integrity
(true/false).
===BEGIN synthesis_review.json===
<content>
===END synthesis_review.json===

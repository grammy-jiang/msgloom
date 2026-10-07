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

Research topic: **Direct empirical NLP methods for longitudinal work-item revision in workplace or operational communication, especially relation labeling for supersession/correction/supplementation/reopening/conflict and evidence models separating claimed completion from independently corroborated completion.**

You did not write this synthesis and you are not reviewing your own work.
Your verdict decides whether the report may be written. Rejecting is a normal
outcome: reject when the evidence does not support the synthesis. Do not
soften a real problem into a note so that the work can pass.

Check five things against the analyses below, not against how well the
synthesis reads:

1. Faithfulness — every finding is traceable to at least one analysis, and no
   finding states more than its cited analyses support.
2. Citation integrity — every cited paper_id is one of: `1804.06020`, `1805.06975`, `1909.00429`, `1909.05360`, `2007.14864`, `2011.03088`, `2103.08541`, `2104.01146`, `2110.08222`, `2210.15067`, `2406.00197`, `2406.19764`, `2606.18037`, `2608.20116`, `doi-10-1007-3-540-44503-x-20`, `doi-10-1007-s10458-012-9202-0`, `doi-10-1007-s10579-009-9089-9`, `doi-10-1007-s11390-024-2655-1`, `doi-10-1016-0004-3702-86-90080-9`, `doi-10-1016-0020-0255-94-90059-0`, `doi-10-1016-j-artint-2003-08-003`, `doi-10-1016-j-ipm-2021-102836`, `doi-10-1016-j-ipm-2026-104709`, `doi-10-1016-j-knosys-2016-07-032`, `doi-10-1017-cbo9780511526664-007`, `doi-10-1023-a-1010318403544`, `doi-10-1093-jos-ffn013`, `doi-10-1145-1082473-1082754`, `doi-10-1162-tacl-a-00182`, `doi-10-18653-v1-2021-acl-long-122`, `doi-10-18653-v1-2021-emnlp-main-815`, `doi-10-18653-v1-2023-findings-acl-44`, `doi-10-18653-v1-d18-1155`, `doi-10-18653-v1-p19-1412`, `manual-2362cbe877`, `manual-b3703967d3`, `manual-d574dff39d`, `manual-eef7a0219f`.
3. Coherence — contradictions between papers are named, not averaged away.
4. Gap completeness — a gap this corpus cannot close is reported as open. A
   gap presented as closed without evidence is a rejection.
5. Overreach — transfer-domain or synthetic evidence is not presented as
   direct-domain evidence, and no production claim rests on it.

Synthesis under review:
{
 "topic": "Direct empirical NLP methods for longitudinal work-item revision in workplace or operational communication, especially relation labeling for supersession/correction/supplementation/reopening/conflict and evidence models separating claimed completion from independently corroborated completion.",
 "paper_count": 38,
 "executive_summary": "The 38-paper corpus provides strong component-level evidence for source-relative factuality, temporal ordering, longitudinal state tracking, revision alignment, provenance, contradiction handling, and evidence-based verification, but it does not directly validate the target task as an integrated workplace-communication problem. Empirical NLP results show that broader context and structured reasoning can improve temporal and state predictions, while revision datasets demonstrate recoverable alignments between successive document versions. Formal commitment, dialogue, belief-revision, and provenance work supplies precise distinctions among cancellation, correction, conflict, reopening, support, and historical persistence. However, workplace-domain evidence is narrow, no admitted study jointly labels the required revision relations across successive operational messages, and no study directly separates a completion claim from independently corroborated completion within such a longitudinal state model. All eight carried gaps therefore remain open.",
 "themes": [
  "Source-relative factuality and speaker commitment are distinct from objective or independently verified truth.",
  "Longitudinal state and temporal interpretation often benefit from document-level context, global constraints, or propagated relational information.",
  "Revision can be represented through explicit alignment, edit intention, correction, retraction, and reopening rather than by overwriting prior content.",
  "Provenance research preserves source responsibility, alternative derivations, and historical support as evidence changes.",
  "Evidence retrieval and source attribution are major bottlenecks for verification under multiple or changing sources.",
  "Formal belief-update and dialogue models preserve distinctions that current empirical NLP models do not jointly implement.",
  "Direct workplace-email evidence exists for task and message-relation learning, but not for the complete longitudinal state-revision problem studied here.",
  "Transfer evidence dominates the corpus, so performance on news, scientific documents, procedural text, synthetic reasoning, and formal dialogue does not establish workplace production accuracy."
 ],
 "findings": [
  {
   "statement": "Event factuality is explicitly modeled in the admitted factuality literature as a source-relative judgment involving polarity and certainty or commitment, rather than as direct determination of objective real-world truth.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1007-s10579-009-9089-9"
    },
    {
     "paper_id": "doi-10-18653-v1-2023-findings-acl-44"
    },
    {
     "paper_id": "doi-10-18653-v1-2021-acl-long-122"
    }
   ]
  },
  {
   "statement": "Speaker-commitment models generalize imperfectly to naturally occurring discourse, with especially weak results for no-commitment cases and systematic difficulty on constructions including conditionals, questions, modality, and neg-raising.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-18653-v1-p19-1412"
    }
   ]
  },
  {
   "statement": "Across several temporal-relation benchmarks, contextual information, temporal commonsense priors, global inference, or propagated relative-time information improve temporal-relation prediction, although the size and source of the gain vary across systems and datasets.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "1804.06020"
    },
    {
     "paper_id": "1909.00429"
    },
    {
     "paper_id": "doi-10-1162-tacl-a-00182"
    },
    {
     "paper_id": "doi-10-18653-v1-2021-emnlp-main-815"
    },
    {
     "paper_id": "manual-b3703967d3"
    }
   ]
  },
  {
   "statement": "In procedural text, document-level state modeling substantially outperforms sentence-local modeling for several state-tracking measures, and referent ambiguity and incomplete transition annotation are themselves substantial sources of error.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "1805.06975"
    },
    {
     "paper_id": "manual-2362cbe877"
    }
   ]
  },
  {
   "statement": "Formal commitment and dialogue models distinguish lifecycle states such as active, satisfied, canceled, and violated, and separately model correction, retraction, persistent undisputed content, and reopening of earlier commitments.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1007-s10458-012-9202-0"
    },
    {
     "paper_id": "doi-10-1093-jos-ffn013"
    },
    {
     "paper_id": "doi-10-1023-a-1010318403544"
    },
    {
     "paper_id": "doi-10-1145-1082473-1082754"
    }
   ]
  },
  {
   "statement": "Scientific-document revision datasets demonstrate that successive versions can be aligned at sentence or finer granularity and that revision intent can be classified; they also show that one explicit revision request may correspond to multiple realized edits.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2210.15067"
    },
    {
     "paper_id": "2406.00197"
    }
   ]
  },
  {
   "statement": "Provenance mechanisms can retain multiple supporting derivations or source locations as data changes, while source-aware verification models can explicitly evaluate whether a claim is supported by the correct source rather than merely by some semantically related evidence.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1007-3-540-44503-x-20"
    },
    {
     "paper_id": "2007.14864"
    },
    {
     "paper_id": "2606.18037"
    },
    {
     "paper_id": "doi-10-1016-j-ipm-2026-104709"
    }
   ]
  },
  {
   "statement": "Fact-verification accuracy is strongly constrained by evidence retrieval: verification degrades substantially when required evidence is not available, and retrieval becomes markedly harder as evidence chains span more documents or dialogue context.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2011.03088"
    },
    {
     "paper_id": "2110.08222"
    }
   ]
  },
  {
   "statement": "Current language models show substantial difficulty with belief revision and conflicting-evidence arbitration, including update-versus-maintain trade-offs, presentation-order effects, modality preferences, and strong use of temporal recency as an arbitration cue.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2406.19764"
    },
    {
     "paper_id": "2608.20116"
    }
   ]
  },
  {
   "statement": "A direct email study shows that relational information between messages and speech acts can improve task identification and message-relation prediction, while free-text work email exhibits fuzzy task boundaries that can be difficult even for human annotation.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "manual-d574dff39d"
    }
   ]
  },
  {
   "statement": "Formal temporal and belief-change work distinguishes multiple kinds of change: event time, valid time, and transaction time are used to represent retroactive, proactive, corrected, and delayed information, while belief-update theory distinguishes changes in the represented world from revisions to beliefs about a static world.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1016-0020-0255-94-90059-0"
    },
    {
     "paper_id": "doi-10-1017-cbo9780511526664-007"
    }
   ]
  }
 ],
 "contradictions": [
  {
   "topic": "Value of explicit transitivity constraints in temporal reasoning",
   "papers": [
    "doi-10-1162-tacl-a-00182",
    "1909.05360"
   ],
   "note": "CAEVO reports a large improvement when transitive inference is added in dense temporal ordering, whereas the structured joint model reports no gain from its transitivity constraint on TB-Dense and only 0.1 F1 on MATRES. The results come from different architectures and inference setups, so the corpus does not support a universal claim that explicit transitivity constraints will help."
  },
  {
   "topic": "Joint versus pipeline learning",
   "papers": [
    "1909.05360",
    "doi-10-1016-j-ipm-2021-102836",
    "doi-10-18653-v1-2021-acl-long-122"
   ],
   "note": "Joint or multi-task learning improves end-to-end temporal extraction in 1909.05360 and degrades when removed from DLGRN in doi-10-1016-j-ipm-2021-102836, but modal dependency parsing reports virtually identical event-extraction F1 for joint and pipeline models and slightly better gold-mention attachment for the pipeline, while joint learning helps when mentions are automatic. The benefit is therefore task- and error-regime-dependent."
  },
  {
   "topic": "Direct timeline prediction versus relation-based temporal representations",
   "papers": [
    "doi-10-18653-v1-d18-1155",
    "manual-eef7a0219f"
   ],
   "note": "Direct contextual timeline prediction outperforms indirect conversion on the TE3 split in doi-10-18653-v1-d18-1155, but loses to indirect TL2RTL on its TimeBank-Dense-derived split. Separately, manual-eef7a0219f reports gains from a logical endpoint decomposition over direct relation classification on TB-Dense and MATRES. These results do not identify one temporal representation as uniformly superior."
  },
  {
   "topic": "Benefit of explicit source-aware modeling for verification",
   "papers": [
    "2606.18037",
    "doi-10-1016-j-ipm-2026-104709"
   ],
   "note": "HeterMV reports multi-source verification gains from heterogeneous source-aware modeling, while ProvenanceGuard finds a source-blind MiniCheck baseline statistically competitive on binary rejection and identifies explicit source attribution, rather than binary rejection alone, as its distinctive advantage. The results use different tasks and metrics and should not be averaged into a single source-awareness accuracy claim."
  },
  {
   "topic": "Temporal recency versus semantic correction structure",
   "papers": [
    "2608.20116",
    "doi-10-1093-jos-ffn013"
   ],
   "note": "The evidence-arbitration experiments show that models often give strong weight to temporal recency, whereas the dialogue semantics formalization treats correction as selectively removing disavowed commitments while retaining undisputed material and can restore earlier material when a correction is itself corrected. This is a tension between observed model behavior and a formal account of revision semantics, not a head-to-head empirical comparison."
  }
 ],
 "gaps": [
  {
   "id": "gap-1",
   "description": "No admitted paper directly evaluates longitudinal state tracking across workplace messages in which one work item moves among requested, proposed, planned, approved, completed, revoked, superseded, disputed, conditional, and unresolved states while retaining historical assessments.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "workplace email enterprise chat longitudinal work item lifecycle state tracking requested planned approved completed revoked superseded disputed unresolved",
   "evidence": [
    "1805.06975",
    "doi-10-1007-s10458-012-9202-0",
    "manual-d574dff39d"
   ]
  },
  {
   "id": "gap-2",
   "description": "The corpus provides formal treatments of correction, retraction, persistence, and reopening and empirical work on document revision, but does not establish a natural-language method evaluated across successive operational communications for distinguishing supersession, correction, supplementation, contradiction, reopening, and unresolved conflict.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "natural language dialogue revision relation classification supersession correction supplementation contradiction reopening unresolved conflict longitudinal",
   "evidence": [
    "doi-10-1093-jos-ffn013",
    "doi-10-1023-a-1010318403544",
    "2210.15067",
    "2406.00197",
    "2103.08541"
   ]
  },
  {
   "id": "gap-3",
   "description": "No admitted paper jointly evaluates source-relative factuality, temporal ordering, lifecycle state, contradiction, and provenance as one longitudinal model; the admitted studies validate separate components and their combination remains untested.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"event factuality\" temporal relation contradiction provenance lifecycle longitudinal joint model",
   "evidence": [
    "doi-10-1007-s10579-009-9089-9",
    "1909.00429",
    "doi-10-1007-s10458-012-9202-0",
    "2606.18037",
    "2608.20116"
   ]
  },
  {
   "id": "gap-4",
   "description": "Direct target-task evidence for workplace email, Teams-like dialogue, or comparable operational communication remains absent. One admitted workplace-email study evaluates task and message-relation learning, but not longitudinal factuality, lifecycle revision, supersession, or evidence-backed current-state resolution.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "workplace email enterprise chat operational communication task state tracking revision factuality temporal commitment",
   "evidence": [
    "manual-d574dff39d",
    "2110.08222"
   ]
  },
  {
   "id": "gap-5",
   "description": "The admitted factuality literature models what a source presents or commits to, and the fact-verification literature evaluates corroborating evidence, but no admitted paper establishes how to distinguish an author's assertion that work is complete from independent confirmation or stronger evidential verification of completion in longitudinal operational communication.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "dialogue event factuality evidentiality source attribution claimed completion independent confirmation corroboration longitudinal",
   "evidence": [
    "doi-10-1007-s10579-009-9089-9",
    "doi-10-18653-v1-2023-findings-acl-44",
    "2011.03088",
    "2110.08222",
    "2606.18037",
    "doi-10-1016-j-ipm-2026-104709"
   ]
  },
  {
   "id": "gap-6",
   "description": "Evaluation is still needed on adversarial longitudinal sequences such as plan-to-cancel, approve-to-revoke, deadline changes, contradictory same-time updates, out-of-order ingestion, stale messages arriving late, and completion claims later corrected.",
   "classification": "ENGINEERING",
   "priority": "HIGH",
   "evidence": [
    "2103.08541",
    "2406.19764",
    "2608.20116",
    "doi-10-1093-jos-ffn013"
   ]
  },
  {
   "id": "gap-7",
   "description": "The combined representation of message time, event or effective time, deadline or constraint time, and observed collection or version time has not been benchmarked for the target state-resolution task; the corpus contains related temporal formalisms and temporal NLP evaluations rather than such a combined benchmark.",
   "classification": "ENGINEERING",
   "priority": "HIGH",
   "evidence": [
    "doi-10-1016-0020-0255-94-90059-0",
    "doi-10-18653-v1-d18-1155",
    "doi-10-18653-v1-2021-emnlp-main-815"
   ]
  },
  {
   "id": "gap-8",
   "description": "The corpus does not evaluate a provenance-preserving implementation for this target state-resolution task that stores immutable source observations and successive assessments while exposing a separately derived current-state view.",
   "classification": "ENGINEERING",
   "priority": "HIGH",
   "evidence": [
    "2007.14864",
    "doi-10-1007-3-540-44503-x-20",
    "2104.01146",
    "2606.18037"
   ]
  }
 ],
 "actionable_insights": [
  "Synthesis-derived recommendation: represent source observations, interpreted assessments, and any derived current-state view as separate layers so that later reinterpretation does not overwrite historical evidence.",
  "Synthesis-derived recommendation: represent longitudinal revision as explicit relation edges such as supersedes, corrects, supplements, reopens, conflicts-with, and unresolved, with an abstention or unknown state rather than inferring revision from message recency alone.",
  "Synthesis-derived recommendation: keep source-relative claimed factuality separate from an evidence-strength or corroboration dimension, so that a statement of completion and independent confirmation of completion are not encoded as the same property.",
  "Synthesis-derived recommendation: preserve distinct message time, event or effective time, deadline or constraint time, and collection or version time when those values are available, rather than collapsing them into one timestamp.",
  "Synthesis-derived recommendation: evaluate the state model with adversarial longitudinal sequences, including late ingestion, changed deadlines, cancellation after planning, revocation after approval, contradictory same-time evidence, and corrected completion claims.",
  "Synthesis-derived recommendation: permit incompatible assessments to coexist with explicit provenance until the available evidence justifies a resolved current assessment, rather than deleting a conflicting historical record.",
  "Synthesis-derived recommendation: treat global consistency, transitivity, and joint inference as candidate mechanisms to benchmark rather than assumptions, because the admitted empirical results show architecture- and dataset-dependent gains.",
  "Synthesis-derived recommendation: require target-domain evaluation on workplace or operational communication before making production-accuracy claims, because most component evidence in this corpus comes from news, procedural text, scientific revision, formal dialogue, synthetic reasoning, or general fact verification."
 ],
 "confidence_summary": "Confidence is high in the component-level findings because multiple distinct literatures independently establish source-relative factuality, temporal-relation modeling, longitudinal state tracking, revision alignment, provenance, and evidence-retrieval effects. Confidence is medium for transferring those mechanisms to operational communication because only one admitted study directly uses workplace email and it addresses task/message relations rather than longitudinal state revision. Confidence is low for the integrated target problem: no admitted paper evaluates the full combination of revision-relation labeling, state lifecycle, factuality, time, conflict, provenance, and independent corroboration in successive workplace messages. The corpus therefore supports well-supported design principles and candidate mechanisms, not a validated combined production model.",
 "limitations": [
  "The synthesis is based on the supplied reduced per-paper analyses rather than fresh inspection of the full papers, so details not retained in those analyses cannot be recovered here.",
  "Most empirical NLP evidence comes from news, procedural narratives, scientific-document revision, fact verification, or synthetic reasoning; those results are transfer evidence rather than direct workplace-state-tracking evidence.",
  "Formal dialogue, commitment, truth-maintenance, temporal-database, and belief-revision papers establish semantic distinctions or algorithms but do not by themselves demonstrate NLP classification accuracy on operational communication.",
  "The workplace-email study directly supports message/task relational learning but does not evaluate the longitudinal lifecycle and revision labels required by this topic.",
  "Several apparent contradictions compare different corpora, architectures, annotation schemes, or metrics; they establish that effects are not universal, not that one paper invalidates another.",
  "The component papers do not jointly validate a combined scheme. Factuality, temporal relations, state tracking, provenance, verification, and revision alignment have largely been evaluated separately.",
  "The inherited Topic 05 handoff and project context were treated only as scoping conditions and were not used as evidence for any finding or for closing any gap.",
  "No duplicate titles are apparent among the 38 supplied analyses, but the reduced records do not provide enough bibliographic metadata to independently rule out differently titled or differently identified duplicate publications."
 ],
 "gap_status": [
  {
   "id": "gap-1",
   "status": "open",
   "note": "Procedural state tracking, formal commitment lifecycles, and email task-relation learning cover separate portions of the problem, but no admitted paper evaluates the specified multi-state work-item lifecycle across successive workplace messages while retaining historical assessments.",
   "evidence": [
    "1805.06975",
    "doi-10-1007-s10458-012-9202-0",
    "manual-d574dff39d"
   ]
  },
  {
   "id": "gap-2",
   "status": "open",
   "note": "Formal dialogue work distinguishes correction, retraction, persistence, and reopening, while scientific revision datasets align and classify document edits, but no admitted empirical NLP study classifies the complete operational relation set across successive communications.",
   "evidence": [
    "doi-10-1093-jos-ffn013",
    "doi-10-1023-a-1010318403544",
    "2210.15067",
    "2406.00197",
    "2103.08541"
   ]
  },
  {
   "id": "gap-3",
   "status": "open",
   "note": "Separate admitted studies evaluate factuality, temporal relations, lifecycle or commitment state, conflicting evidence, and provenance, but none evaluates all of these jointly as one longitudinal model.",
   "evidence": [
    "doi-10-1007-s10579-009-9089-9",
    "1909.00429",
    "doi-10-1007-s10458-012-9202-0",
    "2606.18037",
    "2608.20116"
   ]
  },
  {
   "id": "gap-4",
   "status": "open",
   "note": "manual-d574dff39d supplies direct workplace-email evidence for task and message-relation learning, so workplace email is not wholly absent from the corpus; however, it does not evaluate the target longitudinal state, factuality, supersession, correction, or corroboration task. Direct target-task operational evidence therefore remains open.",
   "evidence": [
    "manual-d574dff39d",
    "2110.08222"
   ]
  },
  {
   "id": "gap-5",
   "status": "open",
   "note": "Source-relative factuality and evidence-based verification are both represented in the corpus, but no admitted paper evaluates the specific distinction between a longitudinal work-item completion assertion and independent corroboration of that completion in operational communication.",
   "evidence": [
    "doi-10-1007-s10579-009-9089-9",
    "doi-10-18653-v1-2023-findings-acl-44",
    "2011.03088",
    "2110.08222",
    "2606.18037",
    "doi-10-1016-j-ipm-2026-104709"
   ]
  },
  {
   "id": "gap-6",
   "status": "open",
   "note": "Revision-aware fact verification, belief revision, conflict arbitration, and formal correction semantics each cover selected adversarial changes, but no admitted study evaluates the specified end-to-end longitudinal adversarial suite.",
   "evidence": [
    "2103.08541",
    "2406.19764",
    "2608.20116",
    "doi-10-1093-jos-ffn013"
   ]
  },
  {
   "id": "gap-7",
   "status": "open",
   "note": "The temporal-database literature supplies a related event/valid/transaction-time formalization and temporal NLP studies evaluate event ordering, but no admitted benchmark combines message, effective, deadline, and collection/version time for the target state-resolution task.",
   "evidence": [
    "doi-10-1016-0020-0255-94-90059-0",
    "doi-10-18653-v1-d18-1155",
    "doi-10-18653-v1-2021-emnlp-main-815"
   ]
  },
  {
   "id": "gap-8",
   "status": "open",
   "note": "Provenance and event-sourcing studies demonstrate relevant storage and update mechanisms, but they do not evaluate a provenance-preserving implementation of this specific NLP state-resolution task with immutable observations, successive assessments, and a derived current-state view.",
   "evidence": [
    "2007.14864",
    "doi-10-1007-3-540-44503-x-20",
    "2104.01146",
    "2606.18037"
   ]
  }
 ]
}

Per-paper analyses (reduced to questions and top findings to fit the size cap):
[
 {
  "paper_id": "1804.06020",
  "title": "Improving Temporal Relation Extraction with a Globally Acquired Statistical Resource",
  "research_question": "Can large-scale corpus-derived prior knowledge about the temporal ordering of event types improve local and globally constrained temporal-relation extraction?",
  "key_findings": [
   "TemProb contains approximately 51,000 distinct verb semantic frames, 9.2 million verb-pair-relation entries, and up to about 80 million extracted temporal relations from the NYT corpus.",
   "TemProb's before/after probabilities behave as meaningful confidence estimates on TimeBank-Dense: increasing the probability threshold raises precision while reducing recall.",
   "On the converted EventCausality evaluation, using TemProb priors achieved 66.2% accuracy, an 11.5-point improvement over the majority T-Before baseline.",
   "Adding the full TemProb prior distribution as local classifier features improved F1 by 2.7 points for same-sentence relations and 6.5 points for adjacent-sentence relations relative to the original local features.",
   "Combining TemProb features and ILP regularization increased global TimeBank-Dense F1 from 46.2 to 52.1 and temporal-awareness F-score from 42.5 to 49.6, with the reported comparison significant at p<0.0005."
  ]
 },
 {
  "paper_id": "1805.06975",
  "title": "Tracking State Changes in Procedural Text: A Challenge Dataset and Models for Process Paragraph Comprehension",
  "research_question": "Can models reliably infer when entities are created, destroyed, or moved and where they are located across natural procedural paragraphs, and does global process modeling outperform approaches developed for shorter or synthetic reasoning tasks?",
  "key_findings": [
   "ProPara provides dense longitudinal annotations of entity existence and location over natural process descriptions, enabling evaluation of complete state trajectories rather than isolated sentence classification.",
   "ProGlobal substantially outperforms ProLocal and the earlier baselines on the aggregate state-tracking metrics, with reported macro scores of 45.08 for ProGlobal and 34.50 for ProLocal.",
   "The largest gap between global and local modeling appears on locating entities after changes: ProGlobal scores 35.9 on the location category versus 10.35 for ProLocal.",
   "About 30% of final locations are not explicitly stated in the sentence where the state change occurs, providing a structural reason that sentence-local extraction is insufficient for many examples.",
   "Human performance remains far above the evaluated models, with a reported macro score of 80.76 compared with 45.08 for ProGlobal, showing substantial remaining difficulty."
  ]
 },
 {
  "paper_id": "1909.00429",
  "title": "An Improved Neural Baseline for Temporal Relation Extraction",
  "research_question": "Can a comparatively standard neural architecture become a substantially stronger temporal-relation baseline when paired with higher-quality temporal annotations, contextual embeddings, temporal commonsense knowledge, and global consistency inference?",
  "key_findings": [
   "The best Concat+CSE variants improve over CogCompTime on MATRES by roughly ten absolute points in accuracy and F1, about five points in temporal-awareness score, and about eight points in the average of the three metrics.",
   "Adding the TemProb-based Common Sense Encoder improves the Concat model under every reported metric for both ELMo and BERT, with the paper reporting statistical significance for the CSE improvement.",
   "Direct concatenation of the two event-position hidden states is significantly better overall than the position-indicator approach across the embedding and metric comparisons.",
   "Contextualized ELMo and BERT representations significantly outperform conventional embeddings, while the difference between ELMo and BERT is not statistically significant in these experiments.",
   "The advantage generalizes to the separate TCR test set: Concat+CSE reaches a three-metric average of 76.4 with ELMo and 74.9 with BERT versus 66.8 for CogCompTime."
  ]
 },
 {
  "paper_id": "1909.05360",
  "title": "Joint Event and Temporal Relation Extraction with Shared Representations and Structured Prediction",
  "research_question": "Can event identification and temporal-relation extraction be learned jointly with shared representations and global structural constraints to reduce pipeline error propagation?",
  "key_findings": [
   "The structured joint model improves end-to-end temporal-relation F1 over the reported baselines by 10.0 points on TB-Dense and 6.8 points on MATRES, reaching 49.4 and 59.6 F1 respectively.",
   "The same structured model improves event-extraction F1 over the baselines by 3.5 points on TB-Dense and 2.6 points on MATRES.",
   "Sharing representations between event and relation tasks provides more benefit on heterogeneous TB-Dense events than on MATRES, where all annotated events are verbs and multi-task gains are smaller.",
   "The event-relation consistency constraint accounts for most of the measured structural-inference gain, adding 0.9 F1 on TB-Dense and 1.0 on MATRES, while the added transitivity constraint contributes no gain on TB-Dense and only 0.1 on MATRES.",
   "Severe class imbalance remains problematic: the neural model concentrates on dominant relations and fails to make any correct SIMULTANEOUS predictions in the class-weight experiment even when that class is weighted up to ten times."
  ]
 },
 {
  "paper_id": "2007.14864",
  "title": "How and Why is An Answer (Still) Correct? Maintaining Provenance in Dynamic Knowledge Graphs",
  "research_question": "Can the validity and derivational provenance of standing-query answers over large knowledge graphs be maintained efficiently as underlying facts are inserted or deleted, rather than recomputed from scratch?",
  "key_findings": [
   "Provenance polynomials retain the individual graph facts and alternative derivations responsible for each query answer, allowing the system to explain both why an answer exists and how it was derived.",
   "After a fact deletion, an answer can remain valid when at least one provenance monomial still evaluates nonzero, so alternative derivations act as explicit independently surviving evidence paths.",
   "Average update time was 0.119 seconds on YAGO2 and 1.252 seconds on DBpedia, and the authors report HUKA as roughly 4 to 48 times faster than the nearest compared baselines for update processing.",
   "Combining common subquery work into a global execution plan reduced the number of intermediate expressions by close to 70%.",
   "HUKA supports both insertion and deletion of graph facts and treats a factual update as a deletion followed by an insertion, enabling provenance to evolve with the underlying knowledge graph."
  ]
 },
 {
  "paper_id": "2011.03088",
  "title": "HoVer: A Dataset for Many-Hop Fact Extraction And Claim Verification",
  "research_question": "Can a large-scale fact-verification benchmark require models to retrieve evidence across as many as four documents and thereby expose weaknesses in shallow single-hop retrieval and verification methods?",
  "key_findings": [
   "HoVer contains 26,171 claims whose evidence may span as many as four English Wikipedia articles, creating a substantially longer evidence chain than common earlier fact-verification benchmarks.",
   "Five-worker claim labeling yielded Fleiss' kappa of 0.63, and 2,222 claims with a 2-2-1 vote split were discarded.",
   "The intended three-way distinction between Refuted and NotEnoughInfo proved ambiguous: an independent 100-claim validation matched the majority three-way label only 63% of the time, while the merged Supported versus Not-Supported labeling matched 90%.",
   "TF-IDF retrieval of the top 100 documents recovered all required supporting documents for about 80.02% of 2-hop claims, 39.18% of 3-hop claims, and 15.59% of 4-hop claims, demonstrating sharply increasing retrieval difficulty.",
   "With complete oracle evidence the BERT verifier reaches 81.2% accuracy, whereas a claim-only model reaches 63.7%, showing both a meaningful benefit from evidence and residual exploitable claim artifacts."
  ]
 },
 {
  "paper_id": "2103.08541",
  "title": "Get Your Vitamin C! Robust Fact Verification with Contrastive Evidence",
  "research_question": "Can fact-verification models be made more sensitive and robust to factual changes in evolving evidence by training on contrastive revisions where small textual edits alter a claim's truth status?",
  "key_findings": [
   "An ALBERT model using the full before-and-after sentences achieved 83.18 F1 and 91.97 AUC for factual-revision flagging, outperforming edit-distance, bag-of-words, and edited-span-only baselines.",
   "Contrastive training substantially increased sensitivity to changed evidence: the ALBERT-base FEVER-only model flipped its verdict on 55.53% of contrastive cases, whereas VitaminC plus FEVER training reached 85.89%, and the corresponding ALBERT-xlarge model reached 90.94%.",
   "Adding VitaminC training improved performance on adversarial evaluations while largely preserving in-domain FEVER or MNLI accuracy, indicating that revision-aware examples reduced reliance on static or lexical shortcuts.",
   "Distant token-level supervision derived from revision edits raised word-level rationale F1 from 37.33 to 47.36 and edit-prediction F1 from 31.23 to 59.11.",
   "For factually consistent generation, the BART claim generator received an 85.83 verifier score and the BART revision generator received 76.26, with manual evaluation additionally checking grammaticality and support."
  ]
 },
 {
  "paper_id": "2104.01146",
  "title": "An Empirical Characterization of Event Sourced Systems and Their Schema Evolution - Lessons from Industry",
  "research_question": "How are event-sourced systems used and defined in industry, how do practitioners evolve their event data structures, and what recurring engineering challenges arise?",
  "key_findings": [
   "Practitioners reported five major challenges: evolving event systems, a steep learning curve, insufficient technology support, rebuilding projections, and data privacy.",
   "The study identifies five event-schema evolution techniques used in practice: versioned events, weak schema, upcasting, in-place transformation, and copy-and-transform.",
   "No single schema-evolution technique is appropriate in every context; versioned events and weak schema are presented as comparatively simple starting points, upcasting as a way to retain event-store immutability, and copy-and-transform as an option when performance or maintainability motivates a more expensive transformation.",
   "Copy-and-transform preserves the original source events while creating new transformed event streams, allowing historical source events to remain immutable.",
   "Immutability was not universal in the 19 studied systems: eight never changed events, three permitted controlled cut-off changes backed by retained backups, and eight allowed event changes without indefinitely retained backups; the last group therefore did not preserve a complete audit trail."
  ]
 },
 {
  "paper_id": "2110.08222",
  "title": "DialFact: A Benchmark for Fact-Checking in Dialogue",
  "research_question": "Can dialogue fact-checking be benchmarked as a pipeline of verifiable-claim detection, evidence retrieval, and evidence-grounded claim verification, and can dialogue-adapted training improve over models developed for non-dialogue fact-checking?",
  "key_findings": [
   "Dialogue context materially improves evidence-document retrieval: test-set recall rises from 60.8 to 75.0 for the WikiAPI method and from 44.7 to 58.8 for the WoW-fine-tuned DPR method when context is added to the claim.",
   "The Aug-WoW verification model outperforms the evaluated baselines across oracle, Wiki-retrieved, and DPR-retrieved evidence settings; on the test set it reaches 69.2% accuracy and 69.0 macro F1 with oracle evidence.",
   "Evidence retrieval is a major bottleneck: Aug-WoW falls from 69.2% accuracy with oracle evidence to 51.6% with Wiki evidence and 51.5% with DPR evidence, with analogous degradation for other models.",
   "Verifiable-claim detection remains especially difficult for non-verifiable conversational content: the best reported Lexical+DNLI baseline has 82.8% overall accuracy but only 39.1 F1 for the Non-Verifiable class.",
   "Models frequently confuse Refuted and NEI claims and can be misled by lexical overlap instead of correctly reasoning over the semantics of claims and evidence."
  ]
 },
 {
  "paper_id": "2210.15067",
  "title": "arXivEdits: Understanding the Human Revision Process in Scientific Writing",
  "research_question": "How can revisions across successive versions of full scientific papers be aligned, decomposed into fine-grained edits, and automatically classified by the authors' revision intentions?",
  "key_findings": [
   "The corpus provides longitudinal full-document revision data for 751 papers and 1,790 versions, with manually annotated sentence alignment covering 13,008 sentence pairs.",
   "The neural sentence-alignment model trained on arXivEdits achieved 93.8 F1, supporting automated linkage of corresponding sentences across document versions.",
   "Span-alignment methods extracted finer-grained edits than latexdiff; QA-align with parse-based heuristics achieved 88.1 F1 on all revisions compared with 75.3 for latexdiff.",
   "A T5-large intention classifier achieved 79.3 accuracy and 78.9 weighted F1 in the fine-grained eight-class experimental setup, while the collapsed four-class setup reached 84.4 accuracy and 84.6 weighted F1 when trained directly on four classes.",
   "The annotated document-level alignments explicitly capture insertions, deletions, rephrasings, splits, merges, fusions, and unchanged copying across successive versions."
  ]
 },
 {
  "paper_id": "2406.00197",
  "title": "Re3: A Holistic Framework and Dataset for Modeling Collaborative Document Revision",
  "research_question": "How can document revisions, peer-review requests, and revision summaries be represented and annotated jointly so that collaborative revision behavior and NLP systems can be studied across edit granularity, action, intent, and cross-document relationships?",
  "key_findings": [
   "Re3 explicitly links a review request to the concrete edits that address it and allows one request to correspond to multiple edits, providing a direct representation of requested versus realized revision.",
   "The dataset contains 314 document-revision pairs and annotations at section, paragraph, sentence, and subsentence granularity, allowing revision history to be analyzed hierarchically rather than as a flat diff.",
   "Modify and Add are the dominant edit operations, and Fact/Evidence is the most common edit intent, showing that many revisions change substantive content rather than only surface form.",
   "More than half of explicit review suggestions are implemented, while 18.47% of implemented review requests are realized through multiple sentence edits, demonstrating that request-to-revision alignment is frequently one-to-many.",
   "Automatic intent classification remains imperfect: the best reported joint classification result reaches 0.70 accuracy and 0.69 macro F1, with Claim and Fact/Evidence among the difficult distinctions."
  ]
 },
 {
  "paper_id": "2406.19764",
  "title": "Belief Revision: The Adaptability of Large Language Models Reasoning",
  "research_question": "How reliably can language models decide whether a previously inferred conclusion should be updated or maintained when a new premise changes the conditions governing that conclusion?",
  "key_findings": [
   "Belief-R contains 1,912 basic two-premise cases and 1,744 three-premise revision cases, comprising 1,074 Belief Update and 670 Belief Maintain examples.",
   "Models that perform well on the initial basic inference still perform poorly on belief revision; most non-API models have near-zero Belief Update accuracy, and the larger open and commercial models reach only about 50% at best on the balanced BREU measure.",
   "The experiments reveal a trade-off between updating and maintaining prior conclusions, with models that improve on Belief Update often performing worse on Belief Maintain.",
   "Belief revision is harder in the modus-tollens subset, where the models show lower balanced revision performance and a stronger imbalance between updating and maintaining.",
   "Chain-of-thought prompting does not significantly improve average belief revision, and plan-and-solve prompting yields only about a one-percentage-point improvement in BREU overall."
  ]
 },
 {
  "paper_id": "2606.18037",
  "title": "ProvenanceGuard: Source-Aware Factuality Verification for MCP-Based LLM Agents",
  "research_question": "Can factuality verification for multi-source MCP agents explicitly preserve source ownership so that unsupported claims, contradictions, and claims supported by the wrong source are reliably blocked?",
  "key_findings": [
   "On the held-out set of 40 traces and 361 claims, ProvenanceGuard achieved 0.802 reject/block F1, 0.993 reject recall, and 0.858 source accuracy over source-eligible claims.",
   "Source-blind support baselines remained competitive on binary rejection, with MiniCheck reaching 0.783 F1, and the 0.019 F1 gap to ProvenanceGuard was not statistically significant; the distinctive measured capability was explicit claim-to-source attribution.",
   "On the harder multi-source benchmark, reject/block F1 remained 0.846 while source accuracy fell to 0.503 and source-plus-relation accuracy to 0.229, showing that exact provenance attribution becomes much harder among semantically similar candidate sources.",
   "All 50 deliberately injected source-attribution swaps in the controlled conflation probes were blocked and labeled as conflations, and no repaired output retained the deliberately wrong attribution.",
   "The repair loop made all 173 initially blocked full-trace answers pass reverification, but 144 resolutions used terminal fallback text, so verifier passage did not usually imply successful recovery of a rich substantive answer."
  ]
 },
 {
  "paper_id": "2608.20116",
  "title": "When Text and Numbers Disagree: Evidence Arbitration in Large Language Models",
  "research_question": "How do instruction-tuned language models arbitrate between conflicting textual, numerical, temporally recent, reliability-marked, and tool-generated evidence when exactly one source is correct?",
  "key_findings": [
   "Models exhibit model-specific modality priors even when textual and numerical evidence are designed to be equally reliable: Qwen models tend toward numerical evidence, while Llama and Mistral show stronger textual preferences and Gemma is more balanced.",
   "Evidence presentation order materially affects arbitration, with later evidence frequently exerting greater influence and textual evidence benefiting especially from being placed last.",
   "Temporal recency is a stronger and more consistently used arbitration cue than an explicit indication that one source is unreliable.",
   "Conflicting tool forecasts produce the strongest degradation among the tested conflict types, and some model configurations follow the tool despite the observed context being perfectly informative.",
   "Increasing model size does not monotonically improve conflict arbitration in the principal experiments; larger Qwen variants can still make systematic source-selection errors under conflict."
  ]
 },
 {
  "paper_id": "doi-10-1007-3-540-44503-x-20",
  "title": "Why and Where: A Characterization of Data Provenance",
  "research_question": "How can the provenance of query-produced data be formally characterized and computed in terms of both why an output exists and where its values originated, while remaining meaningful under query rewriting and view composition?",
  "key_findings": [
   "The paper distinguishes why-provenance, which identifies source data responsible for an output's existence, from where-provenance, which identifies source locations from which particular output values were obtained.",
   "Every well-formed query in the defined language has an equivalent normal form reachable through a strongly normalizing rewrite system.",
   "For a normal-form query and singular output value, the proposed Why procedure computes the same witness basis as the formal provenance definition.",
   "Although a query-dependent witness basis is not invariant under all equivalent formulations, its minimal witness basis is invariant for equivalent well-formed queries restricted to equality conditions, with stated extensions to some inequality subclasses.",
   "Why-provenance can be propagated through materialized views so that recursively tracing witnesses through views agrees with composing the views out of the query."
  ]
 },
 {
  "paper_id": "doi-10-1007-s10458-012-9202-0",
  "title": "Representing and monitoring social commitments using the event calculus",
  "research_question": "How can social commitments, their temporal conditions, and their changing lifecycle states be represented declaratively and monitored online as events occur?",
  "key_findings": [
   "The Event Calculus formalization gives an explicit lifecycle in which conditional commitments can be active and base-level commitments can be active, satisfied, canceled, or violated, with event-triggered operations moving commitments between states.",
   "Cancellation and violation are semantically distinct: cancellation results from an action, whereas violation results from failure to bring about or maintain a required temporal property.",
   "Reactive Event Calculus provides an executable semantics for updating commitment state incrementally as an event narrative grows, supporting online monitoring rather than only static verification.",
   "In the reported car-rental experiment with 15 contract clauses and 6000 events, total processing time was below five minutes and the longest single-event processing time was 294 ms.",
   "Increasing the number of contract clauses by factors of 5, 10, and 50 while holding 6000 events and 200 customers fixed did not produce a statistically significant change in total processing time in the reported experiment."
  ]
 },
 {
  "paper_id": "doi-10-1007-s10579-009-9089-9",
  "title": "FactBank: a corpus annotated with event factuality",
  "research_question": "How can event factuality be represented and reliably annotated as source-relative combinations of polarity and epistemic certainty in text?",
  "key_findings": [
   "FactBank contains 208 documents and 9,488 manually annotated events drawn from TimeBank and a subset of the AQUAINT TimeML corpus.",
   "The factuality representation combines positive, negative, or underspecified polarity with certain, probable, possible, or underspecified modality, thereby distinguishing facts, counterfacts, uncertainty, and non-commitment.",
   "Inter-annotator agreement was high for the annotation decomposition: Cohen's kappa was 0.88 for source-introducing predicates, 0.95 for source identification, and 0.81 for factuality-value assignment.",
   "The corpus explicitly represents factuality relative to relevant sources rather than treating factuality as a single source-independent truth value.",
   "The annotation deliberately excludes factuality changes that require multiple sentences, even though the authors note that an initially uncommitted event may later be presented as a fact."
  ]
 },
 {
  "paper_id": "doi-10-1007-s11390-024-2655-1",
  "title": "Document-Level Event Factuality Identification via Reinforced Semantic Learning Network",
  "research_question": "Can document-level event factuality be identified end to end by jointly encoding event and document semantics while learning to select the sentences and tokens most relevant to the target event?",
  "key_findings": [
   "The paper explicitly observes that sentence-level factualities concerning an event may differ within a document while defining the document-level factuality as a single value.",
   "On ExDLEF, RSLN reports macro/micro F1 of 67.42/77.48 for English and 75.74/78.29 for Chinese, outperforming the reported comparison systems.",
   "Ablation results identify the event encoder and topic-context encoder as two of the most important components: removing them produces substantial macro- and micro-F1 losses in both languages.",
   "Sentence selection has a larger measured effect than token selection: removing SPNet reduces macro-F1 by 4.07 points in English and 4.64 in Chinese, compared with 1.35 and 0.85 points when TPNet is removed.",
   "ExDLEF contains 5,030 English instances and 5,150 Chinese instances across Uu, CT-, PS-, PS+, and CT+ factuality categories."
  ]
 },
 {
  "paper_id": "doi-10-1016-0004-3702-86-90080-9",
  "title": "An assumption-based TMS",
  "research_question": "How can a truth-maintenance system represent and reason over many mutually incompatible assumption contexts simultaneously while preserving derivational support and avoiding repeated backtracking, context switching, and retraction?",
  "key_findings": [
   "An ATMS label records minimal consistent assumption environments supporting a datum, thereby preserving explicit provenance for which combinations of assumptions make each conclusion valid.",
   "Contradictory assumption combinations are stored as nogoods, and conclusions depending on those combinations are invalidated without forcing unrelated conclusions or alternative contexts to disappear.",
   "Mutually contradictory candidate solutions can coexist in separate consistent environments, allowing reasoning to continue without selecting a single global current belief state.",
   "Context membership can be determined from assumption-set inclusion, making repeated context switching unnecessary for applications that need to explore multiple alternatives.",
   "Directly retracting justifications is described as correct but very inefficient because it can trigger recursive recomputation of labels and previously recorded nogoods; representing defeasibility through assumptions is preferred."
  ]
 },
 {
  "paper_id": "doi-10-1016-0020-0255-94-90059-0",
  "title": "Resolution of time concepts in temporal databases",
  "research_question": "Which temporal dimensions and validity concepts are necessary to preserve database history precisely and losslessly when information may be entered retroactively, proactively, corrected, or recorded after a delay?",
  "key_findings": [
   "Three distinct temporal concepts are required for the paper's account of precise and lossless preservation of temporal database information.",
   "Valid time and transaction time alone cannot correctly represent retroactive and proactive updates; event time is additionally required.",
   "The combination of event time, valid time, and transaction time is presented as adequate for preserving past states generated by retroactive updates, proactive updates, error corrections, and delayed updates.",
   "Temporal validity and interpretation-based validity are introduced to clarify the semantics of different time concepts and to define an object's evolution along the valid-time dimension.",
   "The paper sketches a relational-data-model implementation for retaining object history rather than treating the formal distinctions only as abstract semantics."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-artint-2003-08-003",
  "title": "Weakening conflicting information for iterated revision and knowledge integration",
  "research_question": "Can conflicts in prioritized knowledge bases be resolved with less information loss by weakening conflicting formulas rather than deleting them, while retaining practical computational behavior and desirable revision semantics?",
  "key_findings": [
   "DMA resolves inconsistency by weakening formulas involved in conflicts through disjunction rather than simply discarding all conflicting formulas at the affected priority level.",
   "DMA can preserve strictly more information than Maxi-Adjustment because information lost by removal can survive in weaker disjunctive form.",
   "DMA inference is shown to be equivalent to lexicographical inference, providing a compiled consistent base without explicitly enumerating the potentially exponential set of lexicographically preferred subbases.",
   "In the eight reported DIMACS examples, standard Adjustment retained no clauses from the inconsistent second stratum, while DMA retained or generated at least as much information as Maxi-Adjustment and substantially more on several instances.",
   "Whole-DMA was dramatically faster than kernel-computing MA, DMA, and IDMA on the eight reported examples, taking about 0.1 seconds per instance while some kernel-based runs required hundreds of seconds."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-ipm-2021-102836",
  "title": "End-to-end event factuality prediction using directional labeled graph recurrent network",
  "research_question": "Can event anchors and their factuality scores be predicted jointly from plain sentences while improving factuality estimation through directional and labeled syntactic graph information?",
  "key_findings": [
   "Across the four benchmarks, DLGRN is reported to reduce MAE by an average of 17.12% and increase Pearson correlation by 5.40% relative to the strongest baseline.",
   "DLGRN achieved the best factuality-induction values in the reported comparison on all four datasets, including MAE/correlation pairs of 0.240/0.912 on FactBank, 0.279/0.516 on Meantime, 0.346/0.863 on UW, and 0.722/0.912 on UDS-IH2.",
   "The UW ablation shows labeled syntactic information as the most consequential tested graph component: removing it changes F1 from 0.91 to 0.89, MCC from 0.883 to 0.745, MAE from 0.346 to 0.422, and correlation from 0.863 to 0.788.",
   "Removing multi-task learning and reverting toward a pipeline setup degrades both event-anchor detection and factuality induction, supporting shared learning between the two subtasks.",
   "DLGRN outperforms the compared GCN and GAT-LSTM systems across sentence-length buckets, with larger correlation gaps in the longest buckets."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-ipm-2026-104709",
  "title": "HeterMV: Multi-view reasoning over source-aware heterogeneous evidence graph for multi-source fact verification",
  "research_question": "Can explicit source-aware heterogeneous graph modeling and multi-view evidence reasoning improve multi-source fact verification while suppressing irrelevant, redundant, or inconsistent auxiliary evidence?",
  "key_findings": [
   "The framework explicitly preserves source roles by representing core evidence, context, and reference documents as different node types and by using source-specific directed relations rather than homogenizing all evidence.",
   "Four decoupled reasoning views are used to separate evidence perspectives, while view-conditioned prompt tuning aligns each perspective with the claim and cross-view contrastive learning is intended to reinforce supportive signals and suppress noisy ones.",
   "On Check-COVID with 1,504 claims, HeterMV reports Micro-F1 improvements of 3.06 percentage points in the gold setting and 3.27 percentage points under BM25 retrieval over the compared state-of-the-art baselines.",
   "On FEVEROUS-S with 29,890 claims, HeterMV reports Micro-F1 improvements of 1.72 percentage points in the gold setting and 1.41 percentage points in the corresponding BM25-retrieval setting.",
   "The accessible article preview reports that ablation studies validate contributions from the framework's major components and that the evaluation also includes hyperparameter-sensitivity and case analyses."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-knosys-2016-07-032",
  "title": "Cross-document event ordering through temporal, lexical and distributional knowledge",
  "research_question": "Can temporal compatibility, lexical-semantic knowledge, and distributional-semantic knowledge be combined to improve cross-document event coreference and chronological timeline construction from multiple texts?",
  "key_findings": [
   "Combining temporal, lexical-semantic, and distributional-semantic knowledge improved the cross-document event-ordering results over previously evaluated systems, with gains reported as high as eight F1 points.",
   "The best configuration continued to be the combination of temporal, lexical, and distributional semantics when manual entity-coreference annotations were substituted for automatic entity coreference.",
   "With manual MEANTIME entity coreference, the combined configuration reached micro-F1 30.09, precision 25.37, and recall 36.98; relative to the best automatic-entity-coreference setup, the paper reports gains of 3.5 F1 points, 1.7 precision points, and 6.61 recall points.",
   "Entity-coreference quality is an important upstream bottleneck because correcting it manually particularly increases event recall in the resulting timelines.",
   "Nominal event mentions such as deverbal nouns remain difficult to match with verbal mentions, creating cross-document event-coreference errors."
  ]
 },
 {
  "paper_id": "doi-10-1017-cbo9780511526664-007",
  "title": "On the difference between updating a knowledge base and revising it",
  "research_question": "How should knowledge-base update for a changing world be distinguished from revision prompted by new information about a static world, and what does that distinction imply for rationality postulates governing belief change?",
  "key_findings": [
   "Knowledge-base update and revision are fundamentally different operations: update concerns a world that has changed, whereas revision concerns new information about a world treated as static.",
   "A single set of rationality postulates is not adequate for every knowledge-base modification application.",
   "The AGM postulates developed for belief revision require substantial modification when the intended operation is update.",
   "Ordinary database changes and state changes caused by a robot's actions are examples of update because they alter the represented world rather than merely correcting beliefs about an unchanged world."
  ]
 },
 {
  "paper_id": "doi-10-1023-a-1010318403544",
  "title": "The Problem of Retraction in Critical Discussion",
  "research_question": "What kind of dialogue model can permit retractions when they are reasonable or required while constraining or sanctioning retractions that would disrupt an orderly critical discussion?",
  "key_findings": [
   "Retraction changes a participant's current commitments rather than erasing the historical fact that an earlier utterance occurred, so adequate scorekeeping alone does not remove the problem caused by changing commitments on which another participant relied.",
   "A successful elementary critical discussion necessarily ends with at least one participant retracting a commitment, either the proponent's thesis or the opponent's doubt.",
   "Retraction rules should specify both which retractions are permissible in a given dialogical state and what consequences follow, including possible secondary retractions.",
   "Appropriate retraction rules depend on both the type of dialogue and the type of commitment, rather than being uniform across all conversations.",
   "Assertions and concessions carry different obligations, and a statement can in principle be retracted as an assertion while remaining available as a concession."
  ]
 },
 {
  "paper_id": "doi-10-1093-jos-ffn013",
  "title": "Agreement, Disputes and Commitments in Dialogue",
  "research_question": "How can dialogue semantics represent agreement, disagreement, correction, and changing commitments in a logically consistent way while accounting for implicit agreement and preservation of undisputed prior content?",
  "key_findings": [
   "Agreement can be defined as shared entailments of the dialogue participants' public commitments, including commitments introduced by rhetorical relations, which permits logically explicit treatment of implicit agreement.",
   "Keeping each participant's commitments in a separate information structure allows participants to hold mutually inconsistent positions while the dialogue representation itself remains interpretable rather than collapsing into inconsistency.",
   "When a speaker accepts a correction, the update should remove commitments that are disavowed while preserving parts of earlier contributions that were not denied.",
   "A correction can target a rhetorical relation rather than all of the underlying propositional content, so disagreement does not imply that every proposition in the corrected contribution is rejected.",
   "When a correction is itself corrected, the Denying Corrections principle normally restores the relevant earlier, undenied commitment structure and makes prior material available again, providing a formal account of reopening a previously disputed commitment."
  ]
 },
 {
  "paper_id": "doi-10-1145-1082473-1082754",
  "title": "Layered message semantics using social commitments",
  "research_question": "How can message semantics in open multiagent systems be grounded in publicly observable social commitments and conversational context rather than relying primarily on unverifiable private mental states?",
  "key_findings": [
   "The proposed semantics decomposes message interpretation into four cumulative levels: compositional structure, conversational use, commitment state, and joint activity.",
   "Social commitments provide publicly represented states including inactive, accepted or active, fulfilled, violated, and cancelled states, with adoption, fulfillment, violation, and discharge as relevant transitions.",
   "Conversational meaning depends on the temporal and sequential context of shared utterances, including whether a proposal remains available for a reply.",
   "At the commitment-state level, the same structural message can receive a more specific interpretation according to the current state of the referenced commitment, such as an offer withdrawal when an active commitment is proposed for discharge by the original offering agent.",
   "At the joint-activity level, message meaning is related to role-specific actions and their dependencies, as illustrated by bid production, bid evaluation, and contract performance in a contract-net activity."
  ]
 },
 {
  "paper_id": "doi-10-1162-tacl-a-00182",
  "title": "Dense Event Ordering with a Multi-Pass Architecture",
  "research_question": "How should temporal-ordering systems and evaluation change when they must label densely connected event graphs rather than only a sparse set of preselected event pairs?",
  "key_findings": [
   "TimeBank-Dense contains 12,715 labeled temporal relations over 36 TimeBank newspaper articles and produces strongly connected local event-time graphs by requiring annotation of all relevant pairs within the same or neighboring sentences plus document-time links.",
   "CAEVO achieves 50.7 F1 on the dense test setting, a 14% relative improvement over the retrained top TempEval-3 systems used for comparison.",
   "Global transitive inference is a major contributor: adding transitivity raises the ablated CAEVO configuration from 32.1 to 39.8 F1, and the authors estimate that transitive inference alone contributes about ten percent performance improvement.",
   "Edges produced through transitive inference have higher precision than edges directly classified by sieves, approximately 54.4-54.5% versus 49.8%.",
   "Time-time relations constitute only 2.6% of the evaluated edges, yet removing the time-time sieve reduces overall performance by almost five percent because those relations affect other decisions through transitive closure."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2021-acl-long-122",
  "title": "Factuality Assessment as Modal Dependency Parsing",
  "research_question": "Can factuality assessment be formulated as modal dependency parsing that jointly identifies events and information sources, links them hierarchically, and predicts the degree of certainty each source asserts toward each event?",
  "key_findings": [
   "The resulting corpus contains 353 documents, 24,016 events, and 2,938 conceivers; crowd-worker versus expert agreement is 78.6% for unlabeled attachment and 72.1% for labeled attachment.",
   "Joint learning does not materially improve event extraction: test F1 is 90.8 for the joint model versus 90.9 for the pipeline.",
   "Joint learning significantly improves test conceiver extraction from 67.5 F1 to 70.4 F1.",
   "With gold mentions, the pipeline has slightly higher test labeled attachment performance, 80.6 versus 80.1 for the joint model.",
   "With automatically extracted mentions, the joint model significantly improves test labeled attachment from 67.5 to 69.0, indicating reduced pipeline error propagation."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2021-emnlp-main-815",
  "title": "Utilizing Relative Event Time to Enhance Event-Event Temporal Relation Extraction",
  "research_question": "Can latent relative event times learned from temporal-relation supervision improve event-event temporal relation extraction when explicit event-time expressions are sparse?",
  "key_findings": [
   "The Stack-Propagation model reaches precision 78.4, recall 85.2, and F1 81.7 on MATRES, compared with F1 80.2 for the vanilla RoBERTa classifier; the paper reports p<0.05 for the comparison.",
   "The proposed model slightly exceeds the reported 81.6 F1 of the self-training baseline while not using that baseline's additional annotated and raw training resources.",
   "Relative-time prediction alone in the multi-task configuration improves F1 from 80.2 to 80.6, while explicitly propagating predicted times into classification raises F1 further to 81.7.",
   "Deriving relations by directly comparing predicted timestamps yields the highest recall, 86.8, but only F1 80.7 because this strategy cannot adequately handle VAGUE relations.",
   "Predicted relative-time differences correlate with BEFORE and AFTER decisions, while VAGUE and EQUAL pairs tend to have relative-time differences near zero."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2023-findings-acl-44",
  "title": "Towards Generative Event Factuality Prediction",
  "research_question": "Can an end-to-end generative model predict source-relative event factuality, including factuality holders, target events, and factuality values, and can output design and multi-task learning improve that prediction?",
  "key_findings": [
   "Event factuality is modeled as the factuality presentation or judgment attributed to an author or other source, rather than as direct determination of objective real-world truth.",
   "Text normalization increased the source-and-target FactBank baseline exact-match triplet F1 from 0.472 to 0.512, with much of the improvement attributed to morphology and orthography corrections.",
   "Multi-task learning with the author-only FactBank projection substantially improved source-and-target prediction, with the FBST plus FBAO* configuration reaching an exact-match triplet F1 of 0.684 compared with 0.535 for the reported Table 4 baseline.",
   "For author-only FactBank prediction, the multi-task FBAO* plus FBST configuration achieved exact-match F1 of 0.897, compared with 0.866 for the basic FBAO configuration.",
   "The structure of generated output materially affects results; in the author-only exact-match evaluation, inline annotation generation performed worse than tuple or triplet generation."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-d18-1155",
  "title": "Temporal Information Extraction by Predicting Relative Time-lines",
  "research_question": "Can temporal information be extracted more efficiently and consistently by directly predicting relative event time-lines instead of first predicting pairwise temporal relations?",
  "key_findings": [
   "Direct relative time-line prediction can avoid pairwise temporal-relation extraction while producing temporally consistent outputs with linear prediction complexity in the number of entities.",
   "On the TE3 evaluation split, contextual C-TLM with the regular time-line loss achieved F=56.1, exceeding all reported TL2RTL variants, whose best F-score was 52.8.",
   "On the smaller TimeBank-Dense-derived split, indirect TL2RTL performed better than C-TLM, with the best TL2RTL result reaching F=62.3 while the best C-TLM result was F=58.4.",
   "The regular time-line loss was the most robust of the tested losses and was also cheaper and more directly interpretable than losses requiring scores for every relation type.",
   "The contextual direct model appears better than TL2RTL at correctly positioning temporally related entities that are farther apart in the text, consistent with reduced dependence on locally pruned pairwise TLink extraction."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-p19-1412",
  "title": "Do You Know That Florence Is Packed with Visitors? Evaluating State-of-the-art Models of Speaker Commitment",
  "research_question": "How well do state-of-the-art speaker-commitment models generalize to naturally occurring discourse, and which linguistic constructions systematically explain their errors?",
  "key_findings": [
   "The linguistically informed rule-based model outperforms the evaluated biLSTM models on the full CommitmentBank, but all systems perform substantially worse there than on their original reference datasets.",
   "Pearson correlation on the full set is 0.41 for the rule-based model versus 0.24, 0.09, and 0.23 for the linear, tree, and hybrid biLSTMs; on the restricted set the corresponding values are 0.50, 0.31, 0.13, and 0.33.",
   "The rule-based model captures negation relatively well with r=0.45 but performs poorly on modal and question environments, while the hybrid model is more consistent across negation, modality, and questions; both fail on conditionals.",
   "Both models have essentially no useful correlation on neg-raising examples, with r=0.04 for the rule-based model and -0.07 for the hybrid model.",
   "In the three-way classification analysis, neither system reliably recognizes the no-commitment class: its F1 is 0 for the rule-based model and 0.11 for the hybrid model."
  ]
 },
 {
  "paper_id": "manual-2362cbe877",
  "title": "ProPara-CRTS: Canonical Referent Tracking for Reliable Evaluation of Entity State Tracking in Process Narratives",
  "research_question": "Can a canonical referent-tracking representation and targeted reannotation make ProPara a more reliable benchmark for longitudinal entity-state tracking while improving model training and evaluation without changing model architectures?",
  "key_findings": [
   "The CRTS representation separates surface mentions from immutable underlying referents and requires an explicit state for each referent at each process step, directly reducing ambiguity in longitudinal state chains.",
   "The reannotation identified 789 errors, with incomplete state accounting accounting for 357 cases and referent-uniqueness problems for 311, showing that missing transitions and referential ambiguity were major sources of label noise.",
   "On a 100-paragraph dual-annotation sample, state-label agreement reached Cohen's kappa of 0.72 and location agreement reached pairwise F1 of 0.56, indicating meaningful but nontrivial residual annotation difficulty.",
   "Across the main model comparisons, CRTS generally increased sentence-level or document-level F1, including improvements for fine-tuned Llama 3.1, MeeT, and CGLI.",
   "The paper's broad statement that CRTS improves F1 in all settings except GPT-4o-mini sentence-level evaluation is not fully consistent with Table 2, where GPT-4o direct prompting has document-level F1 of 58.8 on CRTS versus 59.6 on original ProPara."
  ]
 },
 {
  "paper_id": "manual-b3703967d3",
  "title": "Joint Inference for Event Timeline Construction",
  "research_question": "Can an interval-based globally constrained model that jointly reasons over event-time associations, event-event temporal relations, and event coreference construct more accurate and coherent event timelines than independent local classifiers?",
  "key_findings": [
   "Global inference achieved overall F1 46.01 versus 42.13 for the local classifiers, a 9.2% relative improvement that was significant at p<0.01.",
   "Using gold event coreference with global inference raised overall F1 to 52.47, about 14% relatively above global inference without coreference and significantly above the compared systems.",
   "Automatically learned event coreference produced overall F1 46.42, but its improvement over global inference without coreference was not statistically significant, showing that the benefit depends strongly on coreference quality.",
   "The interval-based ILP averaged about 21 seconds per article, whereas the corresponding time-point formulation did not finish within five hours before being terminated.",
   "The evaluation corpus contains 232 intervals and 324 event mentions; after logical saturation it contains 324 event-time associations and 5,940 annotated or inferred event-event temporal relations."
  ]
 },
 {
  "paper_id": "manual-d574dff39d",
  "title": "Email Task Management: An Iterative Relational Learning Approach",
  "research_question": "Can email task management be improved by jointly and iteratively learning semantic parent-child relations between messages and message-level speech acts so that each prediction supplies relational evidence for the other?",
  "key_findings": [
   "Structured email information and clustering refinements substantially improve task identification in the e-commerce corpus, where reported F1 rises from 0.15 for plain cosine clustering to 0.82 for the strongest reported configuration.",
   "Free-text work email is harder and less cleanly partitioned into tasks than transaction email; the authors note that task boundaries in free text are fuzzy and may be disputed even by human annotators.",
   "Adding neighboring-message speech acts as relational features yields statistically significant Kappa improvements for the Request and Commit speech acts and overall improvements for several speech-act classifiers.",
   "Using speech-act information to identify message links achieves precision 0.91, recall 0.80, and F1 0.85 in the authors' potential-improvement experiment, improving precision relative to similarity-only relation identification.",
   "In the final cross-user iterative experiment, relation identification starts at precision, recall, and F1 of 0.95 and after the first iteration reaches precision 1.0, recall 0.95, and F1 0.98; speech-act performance also improves for most acts except Amend."
  ]
 },
 {
  "paper_id": "manual-eef7a0219f",
  "title": "More than Classification: A Unified Framework for Event Temporal Relation Extraction",
  "research_question": "Can event temporal relation extraction be improved and made more transferable by representing relation labels as logical constraints over event start and end points rather than as independent one-hot classes?",
  "key_findings": [
   "The unified endpoint framework consistently improves over the enhanced direct-classification baseline and reaches 68.1 micro-F1 on TB-Dense and 82.6 on MATRES with RoBERTa-Large, reported as 0.3 F1 above the previous state of the art on both benchmarks.",
   "Explicit logical treatment of the Vague relation substantially reduces confusion with Vague: the number of Vague-associated errors falls by 95 on TB-Dense and 22 on MATRES, although non-Vague errors increase slightly.",
   "The unified representation is more data-efficient in low-resource TB-Dense experiments, averaging gains of 2.9 micro-F1 and 1.8 macro-F1 over the baseline across training subsets from 1% to 30%.",
   "When trained on TB-Dense and evaluated under MATRES relation definitions, the unified model obtains 70.4 micro-F1 versus 63.1 and 64.3 for two baseline label-mapping strategies.",
   "Gains occur with both BERT-Base and RoBERTa-Large, suggesting that the endpoint decomposition contributes beyond the choice of text encoder."
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
"/home/grammy-jiang/Projects/msgloom/research/06-item-state-and-temporal-reasoning/runs/0ecdd7e4a549/analysis/synthesis.json", `status` = accepted | accepted_with_issues | rejected,
`issues` (each naming the finding or paper it is about), `required_fixes`
(required when rejected), `unsupported_claims`, `confidence`, and `scores`
with faithfulness, coherence, gap_completeness (0-1) and citation_integrity
(true/false).
===BEGIN synthesis_review.json===
<content>
===END synthesis_review.json===

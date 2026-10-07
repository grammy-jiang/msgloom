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

Research topic: **authentic workplace email and enterprise-chat benchmarks for structured action/decision extraction, focusing specifically on implicit and group assignees, action-to-deadline binding, condition/negation/modality scope, and exact argument evidence spans**

You did not write this synthesis and you are not reviewing your own work.
Your verdict decides whether the report may be written. Rejecting is a normal
outcome: reject when the evidence does not support the synthesis. Do not
soften a real problem into a note so that the work can pass.

Check five things against the analyses below, not against how well the
synthesis reads:

1. Faithfulness — every finding is traceable to at least one analysis, and no
   finding states more than its cited analyses support.
2. Citation integrity — every cited paper_id is one of: `1410.4868`, `1606.07849`, `1606.07965`, `1909.03546`, `1909.10094`, `1911.03766`, `2005.13084`, `2104.05919`, `2106.08037`, `2109.09393`, `2202.12109`, `2303.16763`, `2305.13469`, `2312.05471`, `2409.18602`, `2410.03594`, `doi-10-1007-11965152-18`, `doi-10-1109-hicss-2006-528`, `doi-10-1109-scc-2013-62`, `doi-10-1145-1076034-1076094`, `doi-10-1145-1076034-1076140`, `doi-10-1145-3289600-3290984`, `doi-10-1145-3331184-3331260`, `doi-10-1145-3594536-3595162`, `doi-10-1162-coli-a-00110`, `doi-10-1162-tacl-a-00006`, `doi-10-1186-1471-2105-9-s11-s9`, `doi-10-18653-v1-2007-sigdial-1-4`, `doi-10-18653-v1-2020-acl-main-667`, `doi-10-18653-v1-2020-coling-main-164`, `doi-10-18653-v1-2023-findings-acl-378`, `doi-10-18653-v1-d16-1078`, `doi-10-18653-v1-n18-1076`, `doi-10-18653-v1-w18-6104`, `doi-10-26615-978-954-452-092-2-076`, `doi-10-3115-1564535-1564540`, `doi-10-3115-1708376-1708410`, `manual-01c535c108`, `manual-0839b98ee7`, `manual-1e8332286e`, `manual-20b8cd2fdd`, `manual-69bc2555ab`, `manual-90280d2776`, `manual-cd3fa58e4c`, `manual-d19b0f6f1e`, `manual-e6bb5aee88`, `manual-ee40d588e3`, `manual-fde6beef40`.
3. Coherence — contradictions between papers are named, not averaged away.
4. Gap completeness — a gap this corpus cannot close is reported as open. A
   gap presented as closed without evidence is a rejection.
5. Overreach — transfer-domain or synthetic evidence is not presented as
   direct-domain evidence, and no production claim rests on it.

Synthesis under review:
{
 "topic": "authentic workplace email and enterprise-chat benchmarks for structured action/decision extraction, focusing specifically on implicit and group assignees, action-to-deadline binding, condition/negation/modality scope, and exact argument evidence spans",
 "paper_count": 48,
 "executive_summary": "Across 48 papers, the evidence supports structured treatment of workplace actions beyond message-level intent labels. Authentic email and Slack studies show that requests, commitments, assignments, proposals, and decisions are context-sensitive, often coexist within one message, and can depend on preceding turns, participant roles, or recipient metadata. Owner extraction is particularly difficult because responsibility may be implicit, plural, or absent from listed recipients. Explicit argument spans are feasible for stated arguments, but adjacent-domain event research shows that implicit and scattered arguments cannot always be represented by one contiguous evidence span. Temporal, modality, negation, and conditionality research provides useful transfer evidence for relation and scope modeling, but direct workplace evaluation remains sparse. No paper in the corpus jointly evaluates act type, owner, object, deadline, conditions, and exact provenance in authentic workplace communication.",
 "themes": [
  "Context-sensitive extraction in authentic workplace communication",
  "Structured action items as multi-argument and sometimes multi-utterance objects",
  "Implicit, plural, and context-dependent responsibility assignment",
  "Action-to-time relations rather than date detection alone",
  "Condition, negation, and modality scope over actions and commitments",
  "Exact evidence spans versus implicit and scattered arguments",
  "Multiple acts and multiple actions within one message or sentence",
  "Proposal, decision, commitment, and request distinctions",
  "Domain variation and error propagation in end-to-end extraction"
 ],
 "findings": [
  {
   "statement": "Authentic workplace email and Slack studies show that surrounding message or conversation context can materially improve classification or extraction of actionable intents, event arguments, and dialogue acts compared with isolated-sentence or isolated-message processing.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1145-3331184-3331260",
     "section": "Key findings"
    },
    {
     "paper_id": "2305.13469",
     "section": "Key findings"
    },
    {
     "paper_id": "2312.05471",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "Context is not uniformly beneficial across tasks: collective thread modeling degraded the Deliver act in one email experiment, different context configurations were optimal on different meeting corpora, and predicted upstream contextual structure can propagate errors into downstream extraction.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1145-1076034-1076094",
     "section": "Key findings"
    },
    {
     "paper_id": "2303.16763",
     "section": "Key findings"
    },
    {
     "paper_id": "2106.08037",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "Responsibility assignment is empirically difficult: meeting action-item studies report owner as one of the hardest components, while the EPA email benchmark shows that a task owner may be implicit, plural, or not among candidate recipients at all.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1007-11965152-18",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-3115-1564535-1564540",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-18653-v1-w18-6104",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "Workplace communication can contain several actionable intents or actions in the same message or sentence: one enterprise-email study found substantial multi-intent messages, a task extractor explicitly handles coordinated task verbs, and a Slack annotation scheme permits multiple acts at clause or fragment granularity.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1145-3331184-3331260",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-18653-v1-2020-coling-main-164",
     "section": "Key findings"
    },
    {
     "paper_id": "2312.05471",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "For explicitly stated event arguments, span-based extraction and offset-based evaluation are well established, but complex-argument research shows that implicit arguments may have no direct source span and scattered arguments may require several discontinuous pieces of discourse evidence.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "1909.03546",
     "section": "Key findings"
    },
    {
     "paper_id": "2202.12109",
     "section": "Key findings"
    },
    {
     "paper_id": "2410.03594",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "Conditionality, negation, and modality can be represented as relations between cues and the events or propositions they modify, but the strongest scope evaluations in this corpus come largely from biomedical or general event-processing domains; workplace-email studies additionally report conditional commitments and offers as recurrent annotation ambiguities.",
   "confidence": "MEDIUM",
   "evidence": [
    {
     "paper_id": "1410.4868",
     "section": "Key findings"
    },
    {
     "paper_id": "2109.09393",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-1186-1471-2105-9-s11-s9",
     "section": "Key findings"
    },
    {
     "paper_id": "manual-0839b98ee7",
     "section": "Key findings"
    },
    {
     "paper_id": "manual-d19b0f6f1e",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "Action-item and temporal-relation studies treat time as something linked to an action or event rather than as an isolated expression: meeting work annotates timeframe as an action-item component, and event-time work finds that relation text and document-wide temporal evidence materially affect correct anchoring.",
   "confidence": "MEDIUM",
   "evidence": [
    {
     "paper_id": "doi-10-18653-v1-2007-sigdial-1-4",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-1162-tacl-a-00006",
     "section": "Key findings"
    },
    {
     "paper_id": "manual-1e8332286e",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "Authentic organizational email evidence distinguishes proposed actions from stated decisions, while meeting research represents decisions as multi-utterance processes containing issues, proposals, restatements, and agreement rather than as a single binary utterance label.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-18653-v1-2023-findings-acl-378",
     "section": "Key findings"
    },
    {
     "paper_id": "manual-90280d2776",
     "section": "Key findings"
    },
    {
     "paper_id": "1606.07965",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "End-to-end event-argument extraction remains substantially harder than extraction with gold triggers or candidate spans: MAILEX reports low workplace-email argument F1 and strong gains from gold triggers, while RAMS results show a large drop when argument spans must be discovered rather than supplied.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "2305.13469",
     "section": "Key findings"
    },
    {
     "paper_id": "1911.03766",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "Commitment detection exhibits measurable corpus dependence across authentic email collections: within-corpus performance exceeds unadapted cross-corpus transfer, although adaptation and weak-supervision methods recover some of the lost performance.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1145-3289600-3290984",
     "section": "Key findings"
    },
    {
     "paper_id": "2005.13084",
     "section": "Key findings"
    }
   ]
  }
 ],
 "contradictions": [
  {
   "topic": "Whether more conversational context consistently improves extraction",
   "papers": [
    "doi-10-1145-3331184-3331260",
    "2305.13469",
    "2312.05471",
    "doi-10-1145-1076034-1076094",
    "2303.16763",
    "2106.08037"
   ],
   "note": "Several studies report gains from fuller message or conversation context, but collective email context degraded the Deliver class, optimal context configurations differed between meeting corpora, and noisy predicted contextual structure sometimes reduced downstream performance. These are task- and corpus-specific results rather than a single universal effect."
  },
  {
   "topic": "Sentence-level versus message-level annotation granularity",
   "papers": [
    "doi-10-1145-1076034-1076140",
    "manual-20b8cd2fdd",
    "manual-d19b0f6f1e"
   ],
   "note": "Sentence-level action-item annotation improved automatic document detection in one study, whereas workplace request/commitment annotation achieved higher human agreement at message level and attributed part of the improvement to avoiding sentence-locus ambiguity. The experiments optimize different outcomes and therefore do not establish one universally superior granularity."
  },
  {
   "topic": "Exact argument spans versus semantically recoverable implicit arguments",
   "papers": [
    "1909.03546",
    "2202.12109",
    "2410.03594",
    "doi-10-18653-v1-2020-acl-main-667"
   ],
   "note": "Span-based event extraction treats explicit argument offsets as the target representation, while complex-argument research demonstrates cases in which the semantic argument is implicit or distributed and therefore has no single contiguous gold span. The two lines of work support different subsets of argument realization."
  },
  {
   "topic": "Surface or recipient-based owner inference versus contextual ownership",
   "papers": [
    "doi-10-18653-v1-2020-coling-main-164",
    "manual-e6bb5aee88",
    "doi-10-18653-v1-w18-6104",
    "2312.05471"
   ],
   "note": "Some task extractors use grammatical person, dependency structure, or recipient identity as owner cues, whereas the EPA email benchmark and workplace Slack analysis show owners that are implicit, plural, absent from candidate recipients, or dependent on participant role and project responsibility. Surface cues therefore cover only part of the observed ownership problem."
  },
  {
   "topic": "Operational simplicity of commitments versus observed conditional ambiguity",
   "papers": [
    "doi-10-1109-scc-2013-62",
    "manual-0839b98ee7",
    "manual-d19b0f6f1e",
    "manual-20b8cd2fdd"
   ],
   "note": "The service-engagement commitment model formally permits conditional commitments but operationally treats most examined interactions as unconditional, whereas workplace-email annotation studies identify conditional offers and commitments as major sources of disagreement and explicitly model optional conditions. The corpus therefore contains differing empirical emphasis on conditionality."
  }
 ],
 "gaps": [
  {
   "id": "gap-1",
   "description": "There is no direct modern workplace email/chat benchmark in this corpus that jointly annotates speech-act type, owner/assignee, action object, deadline, conditions/exceptions, and exact evidence spans.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"action item extraction\" (email OR Slack OR \"workplace chat\" OR \"enterprise chat\") assignee deadline condition \"evidence span\" corpus"
  },
  {
   "id": "gap-2",
   "description": "Direct empirical evidence for extracting decisions, approvals, rejections, and proposals with structured arguments from authentic workplace email or chat is still missing from this corpus.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "(\"decision extraction\" OR \"decision detection\" OR \"proposal extraction\") (\"workplace email\" OR \"enterprise chat\" OR Slack) approval rejection proposal \"argument extraction\""
  },
  {
   "id": "gap-3",
   "description": "Owner/assignee extraction remains weakly evidenced, especially for implicit owners, group ownership, multiple actions with different owners, and owners recoverable only from organizational or conversation context.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "(\"assignee prediction\" OR \"assignee extraction\" OR \"responsibility extraction\" OR \"action owner\") (email OR Slack OR \"workplace chat\") implicit owner group owner context"
  },
  {
   "id": "gap-4",
   "description": "The corpus does not establish reliable deadline binding in workplace communication: distinguishing a deadline for a particular action from a merely mentioned date, shared date, scheduling expression, or conditional future time remains open.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "(\"deadline extraction\" OR \"due date extraction\" OR \"deadline detection\") (email OR \"workplace communication\" OR Slack) \"action item\" temporal relation event argument"
  },
  {
   "id": "gap-5",
   "description": "Direct workplace evidence is insufficient for attaching conditions, exceptions, negation, and modality to the correct action when several actions or clauses occur together.",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "(\"conditional commitment\" OR \"deontic modality\" OR \"negation scope\" OR \"condition extraction\") (email OR \"workplace communication\" OR Slack) action attachment obligation"
  },
  {
   "id": "gap-6",
   "description": "Build an independent argument-level benchmark and adversarial fixture suite covering implicit owners, multiple actions in one sentence, shared deadlines, conditional and negated actions, overlapping request/commitment labels, quoted-history contamination, and attachment references; score false positives, false negatives, and each argument separately.",
   "classification": "ENGINEERING",
   "priority": "HIGH"
  },
  {
   "id": "gap-7",
   "description": "Compare sentence-local, message-level, and selectively expanded thread-context extraction with controlled ablations, because the literature shows both context gains and context-induced degradation.",
   "classification": "ENGINEERING",
   "priority": "HIGH"
  },
  {
   "id": "gap-8",
   "description": "Test author/quoted/forwarded content zoning while preserving provenance, and measure whether zoning improves act and argument extraction without losing obligations whose interpretation depends on prior-message context.",
   "classification": "ENGINEERING",
   "priority": "HIGH"
  },
  {
   "id": "gap-9",
   "description": "Evaluate an uncertainty-preserving structured output in which owner, deadline, condition, or act subtype can remain unresolved, and measure whether this reduces false obligations and wrong argument assignments without unacceptable recall loss.",
   "classification": "ENGINEERING",
   "priority": "HIGH"
  },
  {
   "id": "boundary-1",
   "description": "Exact proposition-level scope for approvals, rejections, agreements, answers, and commitments remains an inherited Topic 04 problem; this synthesis does not establish that an extracted Topic 05 act label has the correct antecedent scope.",
   "classification": "OUT_OF_SCOPE",
   "priority": "HIGH"
  }
 ],
 "actionable_insights": [
  "Synthesis-derived recommendation: represent each extracted work-relevant act with separately nullable fields for act type, actor or owner, object, recipient or beneficiary, deadline wording and normalized time, conditions or exceptions, source evidence, and uncertainty rather than forcing every field to be populated.",
  "Synthesis-derived recommendation: distinguish explicitly stated owners from contextually inferred owners, support multiple or group assignees, and permit a no-owner or unresolved-owner outcome.",
  "Synthesis-derived recommendation: model deadlines and conditions as relations attached to particular actions rather than as message-level attributes; a shared expression may link to several actions, while proximity alone should not establish that relation.",
  "Synthesis-derived recommendation: preserve exact source spans for explicit arguments, but represent implicit arguments as inferred values with separate supporting-context provenance instead of fabricating a nonexistent exact span.",
  "Synthesis-derived recommendation: evaluate speech-act classification and every structured argument independently, including false-positive and false-negative counts for owner, object, deadline, condition, and evidence support.",
  "Synthesis-derived recommendation: compare sentence-local, full-message, and selectively expanded thread context under controlled ablations rather than assuming that more context always improves extraction.",
  "Synthesis-derived recommendation: evaluate quoted-message and forwarded-content zoning separately from contextual expansion so that contamination reduction and loss of necessary historical evidence are measured independently.",
  "Synthesis-derived recommendation: keep proposal, intention, request, commitment, decision, approval, and rejection distinctions explicit instead of treating all actionable language as a single action-item class.",
  "Synthesis-derived recommendation: keep Topic 04 antecedent-scope resolution separate from Topic 05 act classification, and keep later commitment or decision state changes separate for Topic 06."
 ],
 "confidence_summary": "The corpus provides well-supported design principles around context sensitivity, multi-intent communication, structured argument representations, owner ambiguity, end-to-end error propagation, and the distinction between explicit-span extraction and implicit argument recovery. Confidence is highest where authentic Enron, Avocado, organizational email, or Slack data directly support the claim. Evidence for deadline binding and condition/negation/modality attachment is weaker for the target domain because much of the strongest empirical work comes from meetings, news, biomedical text, contracts, or general event extraction. The individual components have substantial empirical support, but no admitted paper validates the complete combined scheme in authentic workplace email or enterprise chat.",
 "limitations": [
  "The corpus mixes authentic workplace email and Slack with scenario-driven meetings, telephone dialogue, news, biomedical text, contracts, industry requirements, and other transfer domains; results from those domains do not establish production workplace accuracy.",
  "No admitted benchmark jointly evaluates all target fields, so evidence for individual components cannot be interpreted as validation of their combination.",
  "Several older email studies use relatively small datasets, hand-engineered features, or annotation schemes that differ from modern structured extraction tasks.",
  "Owner, request, commitment, and action-item annotations show nontrivial annotator disagreement, so some apparent model errors may reflect genuine task ambiguity.",
  "Exact-span metrics favor explicitly realized arguments and cannot by themselves evaluate implicit arguments that have no literal source span.",
  "Meeting decision studies demonstrate multi-utterance decision structure but do not establish equivalent behavior in authentic enterprise email or chat.",
  "The synthesis relies on the supplied per-paper analyses rather than re-reading the original papers, so it cannot resolve omissions or interpretation errors in those analyses.",
  "The inherited Topic 04 uncertainty about exact proposition-level approval, rejection, agreement, and answer scope remains outside this synthesis and must not be inferred from Topic 05 act labels."
 ],
 "gap_status": [
  {
   "id": "gap-1",
   "status": "open",
   "note": "MAILEX supplies authentic workplace-email event and argument extraction, EPA supplies email assignees, and several email studies supply speech-act labels, but no paper jointly annotates and evaluates act type, owner, object, deadline, conditions or exceptions, and exact argument provenance.",
   "evidence": [
    "2305.13469",
    "doi-10-18653-v1-w18-6104",
    "manual-d19b0f6f1e",
    "doi-10-1145-3331184-3331260"
   ]
  },
  {
   "id": "gap-2",
   "status": "open",
   "note": "LEDA directly distinguishes proposals and decisions in organizational email, while several meeting papers model decision structure, but the corpus still lacks structured argument extraction for decisions, approvals, rejections, and proposals in authentic workplace email or enterprise chat.",
   "evidence": [
    "doi-10-18653-v1-2023-findings-acl-378",
    "manual-90280d2776",
    "doi-10-3115-1708376-1708410",
    "1606.07965"
   ]
  },
  {
   "id": "gap-3",
   "status": "open",
   "note": "EPA directly establishes implicit, plural, and no-one assignees in email, and Slack and meeting studies show contextual responsibility cues and owner difficulty, but reliable extraction for implicit owners, groups, several actions with different owners, and organization-dependent ownership remains unestablished.",
   "evidence": [
    "doi-10-18653-v1-w18-6104",
    "2312.05471",
    "doi-10-1007-11965152-18",
    "doi-10-3115-1564535-1564540"
   ]
  },
  {
   "id": "gap-4",
   "status": "open",
   "note": "Meeting action-item and general temporal-relation studies provide evidence for timeframe extraction and event-time linking, but no admitted workplace email/chat benchmark directly measures whether a particular date is the deadline of the correct action under multiple, shared, scheduling, or conditional temporal expressions.",
   "evidence": [
    "doi-10-18653-v1-2007-sigdial-1-4",
    "doi-10-1162-tacl-a-00006",
    "doi-10-1109-scc-2013-62",
    "manual-1e8332286e"
   ]
  },
  {
   "id": "gap-5",
   "status": "open",
   "note": "The corpus contains direct workplace evidence that conditional commitments are difficult and substantial transfer evidence for negation and modality scope, but it does not directly validate correct attachment of conditions, exceptions, negation, and modality to several co-occurring workplace actions.",
   "evidence": [
    "manual-0839b98ee7",
    "manual-d19b0f6f1e",
    "1410.4868",
    "2109.09393",
    "doi-10-18653-v1-d16-1078"
   ]
  },
  {
   "id": "gap-6",
   "status": "open",
   "note": "The literature identifies the component failure modes, but it does not perform the project-specific independent argument-level and adversarial evaluation described by this engineering gap.",
   "evidence": [
    "doi-10-18653-v1-w18-6104",
    "doi-10-18653-v1-2020-coling-main-164",
    "manual-0839b98ee7",
    "manual-cd3fa58e4c",
    "2410.03594"
   ]
  },
  {
   "id": "gap-7",
   "status": "open",
   "note": "Published results establish that context can help and can also hurt depending on task and corpus, but the required controlled comparison of sentence-local, message-level, and selectively expanded thread context has not been carried out for the project.",
   "evidence": [
    "doi-10-1145-3331184-3331260",
    "doi-10-1145-1076034-1076094",
    "2303.16763",
    "2305.13469"
   ]
  },
  {
   "id": "gap-8",
   "status": "open",
   "note": "Email zoning improves request detection, while conversational history improves event extraction, but the corpus does not jointly evaluate provenance-preserving zoning against loss of obligations that depend on quoted or earlier-message context.",
   "evidence": [
    "manual-cd3fa58e4c",
    "2305.13469",
    "manual-20b8cd2fdd"
   ]
  },
  {
   "id": "gap-9",
   "status": "open",
   "note": "Several papers expose unresolved owners, difficult implicit arguments, annotator ambiguity, and systems insufficient for unattended annotation, but none evaluates the project-specific effect of nullable structured fields on false obligations, wrong assignments, and recall.",
   "evidence": [
    "doi-10-18653-v1-w18-6104",
    "manual-fde6beef40",
    "2410.03594",
    "manual-0839b98ee7"
   ]
  }
 ]
}

Per-paper analyses (reduced to questions and top findings to fit the size cap):
[
 {
  "paper_id": "1410.4868",
  "title": "A Modality Lexicon and its use in Automatic Tagging",
  "research_question": "Can a practical modality annotation scheme and lexicon support automatic identification of modality triggers and their semantic targets with useful precision for downstream language processing?",
  "key_findings": [
   "The representation explicitly distinguishes a modality trigger from the target proposition or event over which that modality operates, providing a form of trigger-to-evidence binding.",
   "The annotation design represents several interactions between modality and negation through thirteen operational choices plus target polarity, but it deliberately simplifies some semantically distinct negation readings.",
   "Although holder is one of the three theoretical modality components, holders were not annotated and automatic holder identification was left outside the project scope.",
   "The semi-automatically expanded modality lexicon began from about 150 trigger lemmas and was made publicly available.",
   "Sentence-level agreement between the string-based and structure-based taggers was kappa 0.82 for triggers and 0.76 for targets."
  ]
 },
 {
  "paper_id": "1606.07849",
  "title": "Focused Meeting Summarization via Unsupervised Relation Extraction",
  "research_question": "Can unsupervised relation extraction identify the salient content phrases associated with individual meeting decisions well enough to support focused, potentially abstractive decision summaries?",
  "key_findings": [
   "The paper distinguishes a Decision Cue from the Decision Content and argues that only the content phrase, rather than the entire decision-related utterance, should normally enter a focused decision summary.",
   "The relation representation extracts phrase-level indicator-argument structures, providing finer evidence than whole-utterance decision detection and preserving identifiable source phrases.",
   "Under gold decision clusterings, configurations of the unsupervised method outperform the reported utterance-level and generic relation-extraction baselines on ROUGE-1 F1 and ROUGE-SU4 F1, while remaining competitive rather than superior to the strongest supervised SVM.",
   "With true clusterings, the 10-relation model reports ROUGE-1 F1 of 37.47, ROUGE-2 F1 of 12.20, and ROUGE-SU4 F1 of 14.59; the supervised SVM reports 40.87, 12.91, and 16.29 respectively.",
   "Performance falls substantially when automatically produced decision clusterings replace gold clusterings, showing strong dependence on accurate upstream association of dialogue acts with decisions."
  ]
 },
 {
  "paper_id": "1606.07965",
  "title": "Summarizing Decisions in Spoken Meetings",
  "research_question": "How effectively can decision-related utterances in multi-party meetings be clustered by decision and summarized using dialogue-act-level or token-level supervised and unsupervised methods?",
  "key_findings": [
   "Decision-related dialogue acts can be distributed and interleaved across a meeting, motivating an explicit clustering stage before decision summarization.",
   "Supervised clustering performs better than the reported unsupervised LDA clustering on B-cubed F1, although the LDA method remains competitive for downstream summary quality.",
   "With automatically produced clusters, an unsupervised LDA-based clustering pipeline can yield decision-summary quality comparable to the supervised clustering alternative.",
   "When true decision clusters are supplied, supervised token-level summarization with discourse context achieves the strongest reported supervised configuration and approaches the paper's extractive upper bound more closely than automatic-cluster conditions.",
   "The AMI data are scenario-driven four-person design-team meetings rather than authentic enterprise email or chat logs."
  ]
 },
 {
  "paper_id": "1909.03546",
  "title": "Entity, Relation, and Event Extraction with Contextualized Span Representations",
  "research_question": "Can a unified span-based information-extraction architecture combine contextualized language representations and dynamically propagated span graphs to improve entity, relation, and event extraction across domains?",
  "key_findings": [
   "The framework achieves reported state-of-the-art results on the three high-level extraction tasks and on all listed subtasks except event argument identification, although event-argument gains are not statistically supported.",
   "Coreference propagation improves named-entity recognition across the evaluated domains and improves relation extraction on SciERC, demonstrating that non-local mention links can improve span representations.",
   "Event-specific graph propagation does not improve the best ACE event-extraction results; the authors hypothesize that asymmetric trigger-argument structure may require better higher-order modeling.",
   "Increasing BERT's sentence context can help some entity, relation, trigger, and argument tasks, but the effects are task-dependent rather than uniformly positive.",
   "Evaluation explicitly requires matching gold offsets, making this paper directly relevant to exact evidence-span extraction methodology."
  ]
 },
 {
  "paper_id": "1909.10094",
  "title": "Deep Structured Neural Network for Event Temporal Relation Extraction",
  "research_question": "Can a jointly trained neural and structured-prediction model improve event-event temporal relation extraction by combining contextual representations with global consistency constraints?",
  "key_findings": [
   "The global structured model improved over its local neural counterpart across all three temporal-relation datasets, and the TCR improvement of more than 1.2 F1 points was reported as statistically significant.",
   "With BERT representations, reported global-model F1 values were 63.2 on TB-Dense, 81.7 on MATRES, and 80.9 on TCR, exceeding the cited previous state of the art.",
   "Ablations show that transitivity constraints consistently improve results, while symmetry-related augmentation and constraints improve robustness when relation direction is reversed.",
   "BERT representations account for a substantial part of the gain, although the structured architecture using GloVe remained competitive or superior to previous systems on several datasets.",
   "Negation remained a significant failure mode: 20% of a manually analyzed sample of common errors was categorized as negation-related, and the authors explicitly identify better handling of negation and hypothetical language as future work."
  ]
 },
 {
  "paper_id": "1911.03766",
  "title": "Multi-Sentence Argument Linking",
  "research_question": "Can a document-level model reliably link event roles to argument spans across sentence boundaries, and can a new large-scale benchmark support progress on this task?",
  "key_findings": [
   "RAMS contains 9,124 annotated event instances from 3,993 news documents, with 139 event types, 65 role types, and 21,237 annotated argument links.",
   "Although most RAMS arguments occur in the trigger sentence, arguments in neighboring sentences remain common enough to motivate document-level linking, with 82% of annotated arguments reported as sentence-local.",
   "With gold trigger and gold argument spans supplied, the main model obtains 68.3 test F1, and type-constrained decoding using gold event types raises test F1 to 73.3.",
   "When the system must consider all possible spans instead of being given gold argument spans, performance drops to about 6 F1, showing that candidate-span identification is a major unresolved end-to-end difficulty.",
   "Performance on arguments one or two sentences from the trigger is comparable to performance on local arguments in the reported development-set analysis."
  ]
 },
 {
  "paper_id": "2005.13084",
  "title": "Learning with Weak Supervision for Email Intent Detection",
  "research_question": "Can noisy supervision derived from users' post-email interactions be combined with a small quantity of clean annotations to improve enterprise email intent detection?",
  "key_findings": [
   "Behavioral weak-labeling functions are informative but substantially noisy: manual checks reported accuracies of about 0.675 for Request Information, 0.71 for Schedule Meeting, and 0.63 for Promise Action.",
   "Hydra consistently outperformed comparison methods that had access to both clean and weak examples, with the advantage especially useful when clean labels were scarce.",
   "Both self-paced learning and explicit weak-label correction contributed measurably: at a 10% clean ratio aggregate accuracy fell from 0.716 to 0.690 without self-paced learning and to 0.688 without label correction.",
   "For the Request Information task with a fixed clean set, increasing weakly labeled data improved reported accuracy from 0.688 with no weak examples to 0.804 when the full weak set was used.",
   "Weak supervision learned from Avocado transferred to Enron; the reported zero-shot experiment using an Avocado-trained Hydra model achieved 0.738 accuracy on Enron."
  ]
 },
 {
  "paper_id": "2104.05919",
  "title": "Document-Level Event Argument Extraction by Conditional Generation",
  "research_question": "Can document-level event arguments be extracted more accurately by generating filled event templates conditioned on the entire document rather than classifying candidate argument spans independently?",
  "key_findings": [
   "Template-conditioned BART generation outperforms the compared extraction baselines on both RAMS and WikiEvents for document-level event argument extraction.",
   "The paper reports gains of 7.6 F1 on RAMS and 5.7 F1 on WikiEvents over the next-best compared systems, with a 9.3 F1 improvement for informative argument extraction.",
   "WikiEvents evaluates argument heads by matching annotated offsets, while an alternative coreference-aware score gives credit when the predicted mention is coreferential with the reference argument.",
   "Informative argument extraction deliberately prefers more informative mentions, such as names over nominal mentions and pronouns, which often requires selecting arguments farther from the trigger.",
   "The authors identify remaining errors in which mutually exclusive semantic roles are both predicted and note that commonsense reasoning is needed for some implicit arguments."
  ]
 },
 {
  "paper_id": "2106.08037",
  "title": "The Possible, the Plausible, and the Desirable: Event-Based Modality Detection for Language Processing",
  "research_question": "Can modality be modeled and automatically detected at the event level by identifying open-class modal triggers, assigning them a linguistically grounded fine-grained sense, and linking each trigger to the event it modifies?",
  "key_findings": [
   "Restricting modality to a small closed set of modal auxiliary verbs makes detection much easier than allowing modal triggers from arbitrary syntactic classes; for example, RoBERTa modal-versus-nonmodal F1 drops from 99.9 on the six modal verbs to 73.2 on all trigger types.",
   "When a modal trigger is already known, contextual information improves sense classification, especially for fine-grained senses: the full-context RoBERTa condition reaches 76.4 F1 versus 72.0 for majority voting, while masking the trigger reduces F1 to 58.3.",
   "For unrestricted trigger detection and classification, RoBERTa consistently improves over the majority-vote baseline; fine-grained labeled F1 is 58.14 compared with 51.29 for the baseline.",
   "Gold event-head information substantially helps modal-trigger tagging, but using predicted event heads can reduce performance because event-prediction errors propagate into trigger classification.",
   "Modal-trigger information improves detection of the event being modified: modal/nonmodal event-span F1 rises from 51.1 without trigger information to 71.13 with a gold trigger, although predicted-trigger information gives only 53.55."
  ]
 },
 {
  "paper_id": "2109.09393",
  "title": "Modality and Negation in Event Extraction",
  "research_question": "Can an open-domain event extractor distinguish events that happened, did not happen, or remain uncertain by modeling negation, modality, conditionality, counterfactuality, and propositional attitudes with syntactic scope?",
  "key_findings": [
   "MoNTEE represents several kinds of event uncertainty rather than treating all extracted events as factual, including explicit and lexical negation, modal operators, conditionality, counterfactuality, and propositional attitudes.",
   "The system uses dependency paths from modality triggers to events as a mechanism for approximating syntactic scope.",
   "On the 100-relation intrinsic evaluation, the three-way happened/uncertain/did-not-happen classification achieves micro-F1 of 0.81 and macro-F1 of 0.76.",
   "The paper explicitly excludes implicit negation from its treatment of negation, limiting coverage of pragmatically implied negative meaning.",
   "The authors identify missing discourse context as an important limitation because modality can depend on surrounding text rather than only the local sentence."
  ]
 },
 {
  "paper_id": "2202.12109",
  "title": "Prompt for Extraction? PAIE: Prompting Argument Interaction for Event Argument Extraction",
  "research_question": "Can prompt-based joint span extraction improve sentence- and document-level event argument extraction while handling long-range dependencies, multiple same-role arguments, limited supervision, and inference efficiency?",
  "key_findings": [
   "PAIE performs direct evidence-span extraction: an argument is represented by its start and end offsets and associated with an event role.",
   "PAIE achieved the strongest reported results in the paper on all three evaluated benchmarks, including base-model Arg-C scores of 69.8 on ACE05, 49.5 on RAMS, and 63.4 on WIKIEVENTS.",
   "Joint multi-role prompts consistently improved performance over single-role prompting, supporting the value of modeling interactions among argument roles.",
   "Bipartite matching contributed an average Arg-C improvement of about 0.7 percentage points across the three benchmarks.",
   "On WIKIEVENTS roles containing three or at least four arguments, PAIE exceeded EEQA-BART by 9.5 and 26.4 Arg-C F1 points respectively."
  ]
 },
 {
  "paper_id": "2303.16763",
  "title": "Meeting Action Item Detection with Regularized Context Modeling",
  "research_question": "Can regularized modeling of both nearby and non-contiguous meeting context, together with lightweight reuse of different pretrained models, improve sentence-level action-item detection across Chinese and English meetings?",
  "key_findings": [
   "AMC-A substantially expands publicly described action-item resources in the study, containing 424 meetings, 306,846 utterances, and 1,506 labeled actions, with train/dev/test splits of 295, 65, and 64 meetings.",
   "Action-item annotation remained subjective despite detailed guidelines: average pairwise kappa among AMC-A annotators was 0.47, followed by expert review of disagreements.",
   "Adding ordinary local and global context already improved AMC-A StructBERT positive F1 from 67.84 for the focus sentence alone to 69.09 for local plus global context.",
   "On AMC-A, dynamic Context-Drop with local and global context achieved 70.82 positive F1, an absolute gain of 2.98 over the sentence-only baseline and 2.10 over the corresponding R-Drop configuration.",
   "On AMI, the strongest reported Context-Drop configuration was fixed Context-Drop with local context at F1 43.12, compared with 38.67 for sentence-only StructBERT and 42.72 for local-context R-Drop; the configuration that was best on AMC-A was therefore not universally best."
  ]
 },
 {
  "paper_id": "2305.13469",
  "title": "MAILEX: Email Event and Argument Extraction",
  "research_question": "Can event triggers and their structured arguments be extracted reliably from conversational workplace email threads despite shared triggers, long non-entity arguments, and dependencies on preceding messages?",
  "key_findings": [
   "MAILEX provides an authentic workplace-email event extraction benchmark derived from Enron, with event roles that include people or members, dates, times, and action-related information.",
   "End-to-end argument extraction remains difficult: the reported argument-classification F1 is 0.368 for the BERT sequence-labeling system and 0.363 for the BART generation system.",
   "Providing gold triggers substantially improves argument extraction, showing that trigger errors propagate strongly into downstream argument prediction.",
   "Conversation history is useful: removing preceding emails lowers trigger and argument scores, and manual inspection found that 11 of 50 sampled emails required information from an earlier turn.",
   "Shared or discontinuous trigger realizations and long non-named-entity arguments are recurring failure modes for the evaluated models."
  ]
 },
 {
  "paper_id": "2312.05471",
  "title": "Fine-Grained Analysis of Team Collaborative Dialogue",
  "research_question": "Can fine-grained hierarchical dialogue-act annotation and context-aware sequence classification provide explainable measures of team communication and collaboration in long-running workplace Slack conversations?",
  "key_findings": [
   "The taxonomy explicitly distinguishes task assignment, voluntary task ownership, acceptance, requests, proposals, rejection, and counter-assignment, making it directly relevant to extracting action ownership and changes of responsibility from workplace chat. citeturn731643view2",
   "Participant role and project responsibility can change the interpretation of an utterance from a request to an assignment, showing that owner assignment cannot always be inferred from surface wording alone. citeturn246367view0turn731643view4",
   "The annotation scheme can separate multiple acts inside one sentence at clause or fragment granularity, but it also permits annotators to label larger multi-sentence blocks that are subsequently split automatically, so it is not a strict token-level evidence-span annotation scheme. citeturn246367view0turn731643view4",
   "Longer conversational context improves dialogue-act classification relative to classifying isolated messages, with the best reported configuration using a ten-line window plus a one-hour temporal boundary and reaching 0.61 test accuracy versus 0.58 for the one-line setting. citeturn731643view5",
   "Temporal proximity was a better contextual segmentation cue than restricting context to two speakers for this team, while the authors caution that the optimal segmentation strategy is probably team-dependent. citeturn731643view5turn731643view0"
  ]
 },
 {
  "paper_id": "2409.18602",
  "title": "Do LLMs suffer from Multi-Party Hangover? A Diagnostic Approach to Addressee Recognition and Response Selection in Conversations",
  "research_question": "How do textual content, interaction structure, prompt formulation, and structural conversation complexity affect zero-shot LLM performance on response selection and addressee recognition in multi-party conversations?",
  "key_findings": [
   "Addressee recognition benefits strongly from explicit interaction structure: combinations containing the speaker-addressee interaction transcript consistently outperform the text-only conversation baseline.",
   "Response selection depends more strongly on linguistic content: the raw conversation transcript, alone or combined with structure, consistently gives the strongest results across the diagnostic subsets.",
   "Generated conversation summaries preserve substantially more useful information than speaker-description-only representations and can approach the strongest configurations in some higher-participant settings.",
   "Addressee recognition is more sensitive to prompt formulation than response selection, with verbose prompts frequently giving the best addressee results while no consistent verbosity benefit appears for response selection.",
   "As the next speaker's degree centrality increases, addressee-recognition performance generally falls across input combinations, revealing weaknesses that are obscured by aggregate macro accuracy."
  ]
 },
 {
  "paper_id": "2410.03594",
  "title": "Explicit, Implicit, and Scattered: Revisiting Event Extraction to Capture Complex Arguments",
  "research_question": "How should event argument extraction be reformulated and benchmarked when important event arguments may be implicit in context or distributed across multiple discontinuous parts of a discourse rather than appearing as one explicit span?",
  "key_findings": [
   "A majority of annotated event arguments require more than ordinary contiguous-span extraction: 51.2% are implicit and 17.4% are scattered, so 68.6% are either inferred or distributed across the discourse. citeturn326926view0turn568280view2",
   "The paper demonstrates a fundamental limitation of exact evidence-span assumptions: implicit arguments have no directly stated source span, while scattered arguments are assembled from discontinuous information distributed through the document. citeturn568280view1turn945402view3",
   "Because the dataset stores generated natural-text argument values rather than start/end text spans, it supports semantic event reconstruction but does not itself provide strict provenance spans for every extracted argument. citeturn945402view0turn945402view2",
   "Traditional extractive QA performs substantially worse on complex arguments, with mean relaxed-match F1 of 17.13 and recall of only 9.40% for implicit and 13.44% for scattered arguments. citeturn568280view2turn326926view3",
   "Even the strongest evaluated generative system remains far from solving the task: GPT-4 with question-guided prompting reaches mean relaxed-match F1 of 41.98, while its best reported recall for implicit arguments is 36.53% and for scattered arguments is 54.12%. citeturn326926view3turn945402view3"
  ]
 },
 {
  "paper_id": "doi-10-1007-11965152-18",
  "title": "Detecting Action Items in Multi-party Meetings: Annotation and Initial Experiments",
  "research_question": "How should action items in multi-party meetings be annotated and detected so that systems can identify both the relevant dialogue region and properties such as task description, owner, timeframe, and commitment?",
  "key_findings": [
   "The initial flat utterance-level formulation performs poorly, with precision, recall, and F1 below 0.25 on the earlier meeting data and relatively low inter-annotator agreement.",
   "The revised annotation scheme decomposes an action item into task Description, Owner, Timeframe, and Agreement components, explicitly modeling both responsibility and commitment.",
   "Among the component classifiers, Agreement is easiest in the reported experiment with F1 0.40, while Owner is hardest with F1 0.17.",
   "Combining evidence from several nearby utterances can locate action-item regions, but results vary greatly between meetings, with reported per-meeting F1 ranging from 0.00 to 1.00.",
   "The results motivate treating action-item creation as a multi-utterance discourse process rather than as an isolated sentence-classification problem."
  ]
 },
 {
  "paper_id": "doi-10-1109-hicss-2006-528",
  "title": "Using Speech Acts to Categorize Email and Identify Email Genres",
  "research_question": "Can email-specific speech-act and genre categories be reliably annotated and automatically identified from verb-class and email-specific features?",
  "key_findings": [
   "The 30-subcategory annotation scheme achieved Cohen's kappa of 0.89 on 100 emails, indicating high agreement between the two annotators.",
   "The taxonomy explicitly distinguishes information requests, directives that ask another person to act, and commitments or offers to perform an action, but the experimental data merged information requests with directives and did not retain commitments as a standalone classifier class.",
   "Email-specific features alone produced 0.57 precision with Random Forests, outperforming either verb lexicon alone in the overall five-class task.",
   "Combining the 24-class Ballmer-Brennenstuhl verb representation with the email-specific feature set gave the best reported Random Forest result, with precision of 0.63.",
   "Part-of-speech filtering did not improve the best combination: BB plus email features fell from 0.63 without TnT tagging to 0.52 with it."
  ]
 },
 {
  "paper_id": "doi-10-1109-scc-2013-62",
  "title": "Monitoring Commitments in People-Driven Service Engagements",
  "research_question": "Can commitments and their lifecycle operations be automatically identified and tracked from real-world email and chat conversations in people-driven service engagements?",
  "key_findings": [
   "The representation explicitly separates a commitment's debtor, creditor, antecedent, and consequent, making this paper directly relevant to structured responsibility assignment rather than only action-intent classification.",
   "Although the formal model supports conditional commitments, the operational extraction treatment states that most examined email and chat interactions are taken to indicate unconditional commitments, so empirical conditional-antecedent extraction is limited.",
   "The approach derives owner-like roles explicitly: task performer maps to commitment debtor and beneficiary maps to creditor, while conversation roles and parsed linguistic structure help identify those parameters.",
   "Deadline expressions are included as a feature indicating commitment creation or delegation, but the evaluated representation does not separately extract and score an explicit deadline span bound to a particular consequent.",
   "Negation is operationalized primarily as evidence of cancellation: an existing commitment whose matching action appears with a negative dependency such as 'not' can be classified as canceled."
  ]
 },
 {
  "paper_id": "doi-10-1145-1076034-1076094",
  "title": "On the collective classification of email \"speech acts\"",
  "research_question": "Does exploiting the sequential relationship among messages in an email thread improve classification of email acts such as requests and commitments beyond content-only classifiers?",
  "key_findings": [
   "Email acts show exploitable sequential regularities: requests are often followed by delivery-related acts, while commitments are particularly associated with proposals or preceding commitments.",
   "In the preliminary 3F2-to-1F3 experiment, iterative collective classification improved Commit from F1 36.66 and kappa 23.16 to F1 44.06 and kappa 32.42.",
   "The broader Commissive class improved in the same preliminary experiment from F1 77.47 and kappa 35.19 to F1 82.96 and kappa 47.83.",
   "Thread context was not universally beneficial: Deliver degraded in the preliminary experiment from F1 77.08 and kappa 47.47 to F1 71.27 and kappa 35.78.",
   "Across the four test teams, average kappa improvement was statistically significant for the non-delivery-related email acts at p=0.01, but the improvement across all eight acts was not significant at p=0.18."
  ]
 },
 {
  "paper_id": "doi-10-1145-1076034-1076140",
  "title": "Detecting Action-Items in E-mail",
  "research_question": "Does using fine-grained sentence-level action-item annotation improve automatic detection of action-item e-mails compared with document-level annotation, and which text representations work best for the task?",
  "key_findings": [
   "Sentence-level classifiers generally produced better document-level action-item detection than classifiers trained directly on whole e-mails; the advantage was significant for the reported comparisons except SVM F1.",
   "N-gram features improved document-level performance for k-NN and SVM and yielded the strongest document-level representations, while multinomial naive Bayes was hurt by n-gram double-counting.",
   "The best reported document-detection F1 was 0.7790 for the sentence-level n-gram k-NN system, while the best reported document accuracy was 0.8173 for the sentence-level n-gram SVM system.",
   "At sentence granularity, unigrams approached n-gram performance because the short sentence window already captured much of the local lexical-pattern information supplied explicitly by n-grams.",
   "Direct sentence detection achieved accuracy around 0.94-0.96 but substantially lower F1 around 0.62-0.67, indicating that the positive action-item class remained considerably harder than overall accuracy alone suggests."
  ]
 },
 {
  "paper_id": "doi-10-1145-3289600-3290984",
  "title": "Domain Adaptation for Commitment Detection in Email",
  "research_question": "How strongly does email-domain variation degrade sentence-level commitment detection, and can domain-adaptation methods learn commitment models that transfer more reliably between email corpora?",
  "key_findings": [
   "Commitments can be detected reasonably well when training and testing within the same corpus, with word-ngram LR F1 of 0.81 on Avocado and 0.78 on Enron.",
   "Cross-domain transfer without adaptation degraded performance: Avocado-to-Enron F1 fell to 0.73 and Enron-to-Avocado F1 to 0.76, with particularly large AUC deterioration.",
   "A classifier could distinguish Avocado from Enron sentences with F1 of 0.85, empirically demonstrating substantial corpus-specific lexical structure.",
   "Sample-level importance weighting significantly improved transfer in both directions, and the tested feature-level adaptation methods also produced improvements in at least some transfer settings.",
   "The proposed autoencoder benefited from its multiple loss components, and the variant using all available objectives achieved the strongest reported autoencoder performance."
  ]
 },
 {
  "paper_id": "doi-10-1145-3331184-3331260",
  "title": "Context-Aware Intent Identification in Email Conversations",
  "research_question": "Does incorporating the surrounding email-message context improve sentence-level identification of actionable workplace email intents?",
  "key_findings": [
   "Enterprise messages frequently contain multiple intents: 55.2% of the analyzed messages had one intent, 35.8% had two, and 9.0% had three or more.",
   "Providing annotators with the full email body substantially improved Request Information recall, from 52.86 without context to 76.61 with context, while precision changed from 91.51 to 93.45.",
   "The context-sensitive DCRNN significantly outperformed the compared models on all three evaluated intents, reporting F1 values of 73.48 for Schedule Meeting, 80.42 for Promise Action, and 78.37 for Request Information.",
   "Simply concatenating conventional target-sentence and message-context features did not reliably help LR or SVM; the gains came from modeling interactions between the target sentence and relevant parts of context.",
   "Performance generally increased as more surrounding context was supplied, and the full email body produced the best DCRNN results among the tested context windows."
  ]
 },
 {
  "paper_id": "doi-10-1145-3594536-3595162",
  "title": "Computable Contracts by Extracting Obligation Logic Graphs",
  "research_question": "Can contractual obligations and their semantic dependencies be extracted from natural-language contracts into a structured graph representation suitable for downstream conversion into executable code?",
  "key_findings": [
   "The work introduces a structured graph representation intended to preserve contractual obligations and dependencies between obligations rather than extracting isolated entities alone.",
   "Contract-OLG is reported to contain 1,876 contract provisions, 18,597 entities, and 18,170 relationships.",
   "The extraction problem is formulated jointly over entities and relations, which is relevant to tasks that must bind an action or obligation to its associated participants and qualifiers.",
   "The abstract reports a substantial gap between machine systems and human experts, particularly for relation extraction.",
   "The accessible abstract does not establish that the benchmark specifically distinguishes implicit assignees from explicit assignees or evaluates group assignee resolution."
  ]
 },
 {
  "paper_id": "doi-10-1162-coli-a-00110",
  "title": "Semantic Role Labeling of Implicit Arguments for Nominal Predicates",
  "research_question": "Can implicit semantic arguments of nominal predicates be identified and linked to discourse constituents using supervised features derived from lexical, syntactic, semantic, and discourse resources?",
  "key_findings": [
   "Adding manually identified implicit arguments increases semantic-role coverage for the ten studied nominal predicates by roughly 20 absolute percentage points, corresponding to a reported 71% relative increase over NomBank's explicit-role coverage.",
   "The discriminative system achieves 57.9 precision, 44.5 recall, and 50.3 F1 on filled implicit arguments, compared with 28.9 F1 for the baseline.",
   "The oracle reaches 87.6 F1, indicating that a substantial portion of remaining error comes from candidate generation and search-window restrictions rather than only candidate ranking.",
   "Approximately 31% of analyzed system errors arise because the true filler is either absent from the candidate set despite being in the window or lies outside the two-sentence window.",
   "Semantic-role compatibility is among the strongest predictive feature classes, while sentence distance also contributes strongly to filler selection."
  ]
 },
 {
  "paper_id": "doi-10-1162-tacl-a-00006",
  "title": "Event Time Extraction with a Decision Tree of Neural Classifiers",
  "research_question": "Can a hierarchical decision tree of neural classifiers use document-wide temporal evidence to anchor events to precise single-day or multi-day time intervals more accurately than local temporal-relation systems?",
  "key_findings": [
   "Document-wide temporal reasoning is empirically important because the paper reports that a substantial fraction of events require temporal evidence outside the same or adjacent sentence to recover their occurrence time.",
   "The full system achieves 42.0% strict overall accuracy against 56.7% inter-annotator agreement, while relaxed overall accuracy is 84.6%.",
   "For single-day events the model reaches 74.6% exact-match accuracy, a reported 33.1 percentage-point improvement over CAEVO in the paper's conclusion.",
   "Multi-day anchoring remains much harder, with 24.5% strict accuracy and particularly low 28.5% strict accuracy for begin-point extraction.",
   "Removing the text between an event and its temporal expression reduces overall strict accuracy by 9.7 percentage points, supporting explicit modeling of the linguistic relation connecting a time expression to an event."
  ]
 },
 {
  "paper_id": "doi-10-1186-1471-2105-9-s11-s9",
  "title": "The BioScope corpus: biomedical texts annotated for uncertainty, negation and their scopes",
  "research_question": "Can a manually annotated biomedical corpus reliably capture lexical cues and linguistic scopes of negation and uncertainty across heterogeneous clinical and scientific text?",
  "key_findings": [
   "BioScope contains more than 20,000 annotated sentences, and more than 10% of sentences contain at least one negation or uncertainty modifier.",
   "The annotation scheme explicitly links minimal negation or speculation cues to maximal linguistic scope spans, making the resource directly useful for span-level scope-resolution research.",
   "Two independent annotations were reconciled by an expert, and agreement evaluation required exact scope-boundary correspondence for full-scope agreement.",
   "Negation and hedge interpretation cannot be determined from apparent cue words alone because context and syntactic structure can change whether a candidate is genuinely negative or speculative.",
   "Scientific text presents greater cue ambiguity and scope difficulty than the clinical subcorpus; for example, the candidate 'or' was annotated as speculative far less often in scientific abstracts than in clinical text."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2007-sigdial-1-4",
  "title": "Detecting and Summarizing Action Items in Multi-Party Dialogue",
  "research_question": "Can action items in natural multi-party meetings be detected as structured multi-utterance commitments and summarized into useful task and timeframe information under both manual-transcript and speech-recognition conditions?",
  "key_findings": [
   "The structured detector outperforms the flat detector on manual transcripts, reaching overlap-based F1 of 0.45 versus 0.35 for the flat approach.",
   "Automatic speech recognition reduces action-item detection performance substantially; the structured overlap F1 falls from 0.45 on manual transcripts to 0.36 on 1-best ASR, with word confusion networks recovering only a small amount to 0.37.",
   "Timeframe summarization benefits from semantic and temporal features, with the best reported automatic configuration reaching F1 0.51 compared with 0.31 for a TIMEX-only baseline and 0.39 for an entire-utterance baseline.",
   "Task-description summarization remains difficult: semantic features can raise precision, but the evaluated candidate-ranking systems do not exceed the entire-utterance description baseline in F1.",
   "The action-item annotations are sparse and moderately to substantially reproducible, with only about 1.4% of utterances receiving any action-item class and pairwise kappa values ranging from 0.64 to 0.78."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2020-acl-main-667",
  "title": "A Two-Step Approach for Implicit Event Argument Detection",
  "research_question": "Can document-level implicit event argument detection be made more tractable and accurate by first detecting argument head words and then expanding those heads to full evidence spans?",
  "key_findings": [
   "When gold argument spans are supplied as candidates, head-word representations produce performance comparable to the earlier span-based RAMS model, supporting the hypothesis that contextualized argument heads can represent much of the useful span information.",
   "For full argument detection with gold event-type constrained decoding, the head-based model reaches 41.8 Span-F1 and 49.7 Head-F1 on the test set, significantly exceeding the corresponding sequence-labeling results of 40.5 and 48.0.",
   "Without type-constrained decoding, the head-based model is also slightly better on average than the sequence-labeling baseline, although the reported significance claim is attached to the type-constrained comparison.",
   "Fine-tuned BERT and explicit indicators marking the trigger/center-sentence context materially improve performance over frozen BERT or an LSTM encoder.",
   "Non-local arguments are much harder than same-sentence arguments; only about 18% of RAMS arguments are non-local, creating a substantial data imbalance in addition to weaker syntactic signals."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2020-coling-main-164",
  "title": "Lin: Unsupervised Extraction of Tasks from Textual Communication",
  "research_question": "Can specific task actions be extracted from email and chat without supervised task labels by combining dependency syntax with VerbNet semantic information?",
  "key_findings": [
   "Lin achieved 80.42% F1 on the Enron email dataset and 90.45% F1 on the chat dataset.",
   "The combined syntactic-semantic system outperformed its syntax-only and semantics-only variants, showing complementary value from the two information sources.",
   "Lin explicitly filters negated imperatives such as a prohibition from being treated as positive tasks.",
   "The method uses first-person and second-person grammatical information plus dependency relations as a limited representation of the task performer.",
   "Coordination is handled so that multiple distinct task verbs can be extracted from one sentence."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2023-findings-acl-378",
  "title": "LEDA: a Large-Organization Email-Based Decision-Dialogue-Act Analysis Dataset",
  "research_question": "What dialogue-act taxonomy and empirical patterns can characterize decision-making communication in a large, distributed organization, and how predictable are those acts from email text and conversational context?",
  "key_findings": [
   "The calibrated taxonomy contains explicit decision-relevant categories including ProposeAction and StateDecision while retaining broader information-seeking, information-providing, response, and social categories.",
   "ProposeAction is much more frequent than StateDecision in the annotated corpus, with 2,225 versus 359 labeled instances, indicating substantially more discussion of possible actions than explicit decision statements.",
   "The frequency of ProposeAction remains comparatively stable over the draft life cycle, whereas questions and answers are more common earlier in discussions.",
   "Draft authors and participants with high interaction-graph centrality make more StateDecision acts than their comparison groups; influential participants also propose slightly more actions.",
   "Approximately two thirds of annotated questions appear to remain unanswered, and answer rates vary substantially by participant role, with chairs receiving answers more often than authors."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-d16-1078",
  "title": "Speculation and Negation Scope Detection via Convolutional Neural Networks",
  "research_question": "Can convolutional neural networks using syntactic-path and positional features accurately identify the token-level scope of speculation and negation cues and generalize across biomedical text genres?",
  "key_findings": [
   "On BioScope Abstracts, the strongest reported configuration reaches 85.75% exact-scope accuracy for speculation and 77.14% for negation, outperforming the cited prior result for speculation and ranking second among the compared systems for negation.",
   "Constituency-path features perform better for speculation on Abstracts, whereas dependency-path features perform better for negation, indicating that the two phenomena benefit from different syntactic representations.",
   "The CNN models improve negation right-boundary detection markedly relative to the feature-based baseline, which accounts for an important part of the overall gain.",
   "Models trained on Abstracts transfer comparatively well to Clinical Records, obtaining exact-scope scores of 73.92% for speculation and 89.66% for negation with the best reported configurations.",
   "Cross-domain performance is substantially worse on Full Papers, where the best reported exact-scope scores are 59.82% for speculation and 55.32% for negation."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-n18-1076",
  "title": "Implicit Argument Prediction with Event Knowledge",
  "research_question": "Can distributed event knowledge and entity-salience information improve prediction of implicit arguments whose fillers occur elsewhere in a document?",
  "key_findings": [
   "Combining learned event knowledge with entity-salience features substantially improves argument-cloze accuracy over frequency and simpler event-embedding baselines.",
   "On the shorter OntoNotes setting, the 40-million-example EventComp model with salience reaches 47.75% accuracy, compared with 41.89% without salience and 22.76% for the most-frequent-entity baseline.",
   "On the longer and more entity-dense OntoNotes setting, the 40-million-example EventComp model with salience reaches 27.87% accuracy, outperforming the corresponding model without salience at 21.79%.",
   "For the Gerber-Chai natural implicit-argument task, successive adaptations for deciding whether a role is filled, handling multiple roles, and adding salience raise the 40-million-example EventComp system to 49.6 F1.",
   "The final adapted system approaches the original Gerber-Chai result while exceeding the authors' automatically reproducible Gerber-Chai baseline, suggesting that broad event knowledge can substitute for some manually engineered resources."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-w18-6104",
  "title": "Assigning people to tasks identified in email: The EPA dataset for addressee tagging for detected task intent",
  "research_question": "Given a task already detected in an email thread, how can the people responsible for carrying it out be annotated and predicted from the sender, recipient, and conversational context?",
  "key_findings": [
   "Task ownership in email can be implicit, plural, or absent from the candidate recipients, so recipient metadata and thread context are necessary parts of the assignment problem.",
   "EPA supports multiple responsible people and an explicit no-one outcome rather than assuming every detected task must belong to one recipient.",
   "The released Enron annotations contain 15,649 email-task-recipient tuples covering 5,998 unique emails and 6,300 tasks.",
   "Owner labeling was substantially noisy: recipient-level perfect agreement was 71.07% and Krippendorff's alpha was 0.6123.",
   "The comparable Avocado annotations had higher agreement than Enron, and the authors associate much of the difference with cleaner and more consistent formatting and sentence segmentation."
  ]
 },
 {
  "paper_id": "doi-10-26615-978-954-452-092-2-076",
  "title": "Reading between the Lines: Information Extraction from Industry Requirements",
  "research_question": "Can scope, applicability conditions, and demanded behavior be extracted from authentic industrial requirement sentences when some of that information is implicit in document context?",
  "key_findings": [
   "The final annotated training collection contains 2,147 requirement sentences from 23 authentic DNV industry documents, and contextual annotation yields substantially more scope spans than sentence-only annotation because scope is frequently implicit outside the requirement sentence.",
   "Adding document context produces the largest improvement for scope extraction with RoBERTa, whose average scope scores on the held-out test rise from 0.45 to 0.70 ROUGE-L, 0.43 to 0.62 BLEU-1, and 0.55 to 0.77 embedding similarity.",
   "Condition and demand extraction change comparatively little when context is added to the RoBERTa input, consistent with these components being more often explicit in the requirement sentence itself.",
   "Without contextual input, GPT-3 performs better than RoBERTa on the reported scope and demand text-similarity measures, whereas contextual RoBERTa becomes stronger on scope.",
   "The authors' contextual representation does not produce a comparable scope gain for the GPT-3 few-shot system, suggesting that its prompting setup does not exploit the supplied context as effectively as the supervised sequence-labeling model."
  ]
 },
 {
  "paper_id": "doi-10-3115-1564535-1564540",
  "title": "Shallow Discourse Structure for Action Item Detection",
  "research_question": "Can action items in multi-party meeting transcripts be detected more effectively, while also exposing their task, owner, timeframe, and agreement information, by modeling shallow discourse structure instead of treating all action-item-related utterances as one flat class?",
  "key_findings": [
   "Flat binary action-item classification was weak: the five CALO meetings produced F1 scores between 0.30 and 0.38, and neither higher-order n-grams nor alternative discriminative classifiers improved the reported baseline.",
   "The proposed discourse representation decomposes an action item into task description, timeframe, owner, and agreement, while allowing one utterance to realize multiple components and multiple utterances to realize the same component.",
   "Initial annotation reliability on one relatively complex ISL meeting was substantially higher than the earlier flat action-item agreement cited by the paper, with kappa 0.86 for timeframe, about 0.77 for owner, and 0.73 for agreement and task description.",
   "Subclass detection performance varied greatly: agreement was the strongest subclass at F1 0.40, while owner was weakest at F1 0.17; description and timeframe reached F1 0.29 and 0.26 respectively.",
   "The authors attribute some owner-class difficulty to overlap with other component classes, because owner utterances were especially likely to receive multiple labels."
  ]
 },
 {
  "paper_id": "doi-10-3115-1708376-1708410",
  "title": "Extracting Decisions from Multi-Party Dialogue Using Directed Graphical Models and Semantic Similarity",
  "research_question": "Can directed graphical models improve structured detection of decision-making dialogue, and can semantic similarity improve extraction of concise issue-and-resolution summaries from both manual and ASR meeting transcripts?",
  "key_findings": [
   "The best directed graphical models outperformed the earlier hierarchical SVM for all four decision-dialogue-act classes on both evaluation metrics, with class-level F1 gains reported between 0.04 and 0.19 and p < 0.005.",
   "Using DGM outputs plus simple structural rules improved decision-discussion-region F1 from 0.50 for the hierarchical SVM system to 0.55, with precision 0.39 and recall 0.93 for the DGM-based system.",
   "Explicitly adding dependencies among the DDA classes did not improve Issue, Resolution Proposal, or Resolution Restatement detection; Agreement gained 0.03 under the 40-second metric, but that gain was not statistically significant.",
   "Removing manually annotated dialogue-act features reduced the strongest Issue, Resolution Proposal, and Agreement F1 scores by roughly 0.07 to 0.09, indicating that dialogue-act information was materially useful.",
   "The DGM approach remained usable on one-best ASR output; for some Issue and Resolution Proposal configurations the reported ASR F1 was even higher than on manual transcripts, although the authors partly attribute this to different sparsity caused by segmentation."
  ]
 },
 {
  "paper_id": "manual-01c535c108",
  "title": "Dialogue Act Modeling for Automatic Tagging and Recognition of Conversational Speech",
  "research_question": "Can dialogue acts in spontaneous conversation be automatically recognized by probabilistically combining lexical, prosodic, and dialogue-sequence evidence, while also using dialogue-act information to improve speech recognition?",
  "key_findings": [
   "Using transcribed words, dialogue-act classification reached 71.0% accuracy with a trigram discourse grammar, compared with a 35% chance baseline and approximately 84% human labeling agreement.",
   "Dialogue-sequence context was highly informative: with true words, accuracy rose from 54.3% without a discourse grammar to 71.0% with a trigram model, and with recognized words it rose from 42.8% to 64.8%.",
   "Combining recognized-word evidence with prosody and a bigram discourse grammar yielded 65.0% dialogue-act accuracy, slightly above the 64.3% recognizer-only result.",
   "In balanced focused classifications, adding prosody consistently improved word-only classification for question-versus-statement and agreement-versus-backchannel distinctions, with larger relative value when words came from speech recognition.",
   "The 42-class inventory contains an Action-directive category and an Offers, Options & Commits category, but they account for only about 0.4% and 0.1% of utterances respectively."
  ]
 },
 {
  "paper_id": "manual-0839b98ee7",
  "title": "Can Requests-for-Action and Commitments-to-Act be Reliably Identified in Email Messages?",
  "research_question": "Can human annotators reliably and repeatedly identify the presence and strength of requests for action and commitments to act in workplace email at sentence level well enough to support later automated classification?",
  "key_findings": [
   "Annotators agreed relatively well on whether a sentence contained a Request-for-Action, with three-way kappa 0.78, but agreement on request strength was lower at 0.60.",
   "Commitments-to-Act were substantially harder to annotate: presence achieved three-way kappa 0.54 and strength only 0.37.",
   "Agreement varied with audience type and was highest for single-recipient messages and lowest for closed-group messages, with the effect particularly pronounced for commitments.",
   "Conditional offers were a major systematic ambiguity: sentences containing offers accounted for almost 40% of disagreements about whether a Commitment-to-Act was present.",
   "Implicit requests, especially meeting-related statements, produced recurring disagreement because identifying the obligation can require information from other parts of the message."
  ]
 },
 {
  "paper_id": "manual-1e8332286e",
  "title": "TimeML: Robust Specification of Event and Temporal Expressions in Text",
  "research_question": "How can a general markup language represent events, temporal expressions, temporal ordering, modality, and underspecified temporal information in natural-language text?",
  "key_findings": [
   "TimeML separates event and temporal mentions from the relations among them through four principal structures: EVENT, TIMEX3, SIGNAL, and LINK.",
   "TIMEX3 represents explicit dates, times, durations, and underspecified expressions and supports delayed computation of normalized time values through temporal functions.",
   "TLINK encodes temporal relationships between events or between an event and a time, including before, after, inclusion, simultaneity, beginnings, and endings, making it suitable as a temporal layer for actions associated with dates or deadline-like constraints.",
   "SLINK represents subordination relations such as modality, factuality, counterfactuality, evidentiality, and negation, allowing a temporal-event representation to distinguish asserted events from possible or subordinated ones.",
   "The EVENT taxonomy contains an I_ACTION class whose examples include promise and offer, so commitment-related predicates can be represented as event mentions even though TimeML does not itself define workplace commitment speech acts."
  ]
 },
 {
  "paper_id": "manual-20b8cd2fdd",
  "title": "Requests and Commitments in Email are More Complex Than You Think: Eight Reasons to be Cautious",
  "research_question": "Which recurring phenomena make requests and commitments in real workplace email difficult to annotate or extract reliably, and what annotation principles are needed to handle those phenomena consistently?",
  "key_findings": [
   "More explicit guidance for conditional and indirect phenomena coincided with a large improvement in commitment agreement: three-way commitment kappa increased from 0.54 in the first sentence experiment to 0.74 in the second, while request kappa changed from 0.78 to 0.80.",
   "Message-level annotation yielded still higher agreement, with kappa 0.84 for requests and 0.78 for commitments; the paper links part of this gain to avoiding sentence-level locus ambiguity.",
   "The authors identify eight systematic edge-case categories: locus ambiguity, meetings, pleasantries, requests for inaction, process instructions, attachment-review requests, reported requests and commitments, and third-party commitments that also function as requests.",
   "Several categories cannot be classified reliably from surface wording alone and instead require message context, intended recipient information, or knowledge about whether an obligation is actually imposed.",
   "The same underlying obligation may have multiple direct or indirect sentence realizations, so the authors' high-recall scheme marks every sentence that realizes a request or commitment rather than forcing a single textual locus."
  ]
 },
 {
  "paper_id": "manual-69bc2555ab",
  "title": "Predicate-specific Annotations for Implicit Role Binding: Corpus Annotation, Data Analysis and Evaluation Experiments",
  "research_question": "Can higher-volume, predicate-specific annotation of omitted semantic roles improve the empirical analysis and automatic linking of implicit arguments to discourse antecedents?",
  "key_findings": [
   "The annotation effort yields 630 null-instantiated roles for genuine target-frame readings across 438 verb occurrences, providing substantially denser predicate-specific implicit-role evidence than the sparse SemEval resource motivating the work.",
   "Non-resolvable implicit roles are more common than discourse-resolvable ones in the new annotations, at 61.6% versus 38.4%.",
   "Seventy-eight percent of resolvable implicit roles have their antecedent within a three-sentence window, although the rate differs from previously reported corpora and therefore appears genre- and target-dependent.",
   "For a given predicate, null instantiation tends to concentrate in one or two semantic roles rather than being distributed uniformly across all roles.",
   "Annotation calibration achieves high agreement for resolvability classification and reasonably high agreement for the selected antecedent, including kappa 0.94 and 85.7% antecedent agreement in the two-annotator give calibration."
  ]
 },
 {
  "paper_id": "manual-90280d2776",
  "title": "Decision Detection Using Hierarchical Graphical Models",
  "research_question": "Can hierarchical graphical models improve automatic detection of decision-discussion regions in multi-party meetings by jointly modeling observable utterance features, decision dialogue acts, and higher-level decision regions?",
  "key_findings": [
   "The hierarchical graphical model reports precision 0.69, recall 0.96, and F1 0.80 for decision-region detection, compared with F1 0.55 for the DGM method and 0.50 for the hierarchical SVM in the paper's controlled comparison.",
   "The improvement is attributed to jointly modeling dependencies between high-level decision regions, mid-level decision dialogue acts, and observable utterance features rather than detecting decision-related utterances independently.",
   "The annotation scheme distinguishes issue, resolution proposal, resolution restatement, and agreement utterances, thereby representing stages of collective decision formation rather than only a binary decision/non-decision label.",
   "An utterance can belong to more than one decision-dialogue-act class, and multiple utterances of the same class can contribute to one decision discussion.",
   "The experiment relies on manual transcripts and manually annotated dialogue-act information; it therefore does not establish equivalent performance on raw enterprise chat or automatically transcribed meetings."
  ]
 },
 {
  "paper_id": "manual-cd3fa58e4c",
  "title": "Detecting Emails Containing Requests for Action",
  "research_question": "Can emails containing requests for action be detected accurately at message level, and does removing quoted and other non-author message zones improve classification?",
  "key_findings": [
   "Message zoning substantially improves request detection, raising accuracy from 72.28% without zoning to 83.76% with zoning.",
   "With zoning, request-class F1 reaches 0.843 and weighted overall F1 reaches 0.838.",
   "The improvement from zoning is statistically significant across the reported classification metrics and corresponds to more than a 41% reduction in classification error.",
   "Lexical n-gram features provide most of the predictive power, while zoning makes even small lexical feature sets substantially more effective.",
   "Important remaining errors include implicit requests, request-like spam or marketing text, requests embedded in ignored zones, zoning mistakes, pleasantries, and requests associated with attachments."
  ]
 },
 {
  "paper_id": "manual-d19b0f6f1e",
  "title": "The nature of requests and commitments in email messages",
  "research_question": "How can requests and commitments in workplace email be defined at the utterance level robustly enough to support consistent annotation and subsequent automated detection?",
  "key_findings": [
   "More explicit annotation guidance substantially improved agreement for commitments: three-way kappa rose from 0.54 in the first experiment to 0.74 in the second, while request agreement rose from 0.78 to 0.80.",
   "Conditional commitments and implicit requests were major sources of disagreement in the initial annotation experiment, and better treatment of conditional commitments accounted for much of the later agreement improvement.",
   "The final representation separates the underlying act from its linguistic realization: a request is represented by an action, requestor, requestee, and optional condition, while a commitment contains an action, committor, committee, and optional condition.",
   "Requests are treated broadly as actionable obligations for the recipient, including requests for physical action as well as questions that require an informational response.",
   "Conditionality is modeled explicitly because execution or scheduling of an action may depend on a stated condition that can occur in the same utterance or elsewhere in the email."
  ]
 },
 {
  "paper_id": "manual-e6bb5aee88",
  "title": "Extraction de tâches dans les e-mails : une approche fondée sur les rôles sémantiques",
  "research_question": "Can a semantic-role-based symbolic system detect and structure action and information requests in professional French emails so that the action predicate and participants such as agent, theme, recipient, and temporal context are explicitly represented?",
  "key_findings": [
   "The proposed representation structures a task around a predicate and semantic arguments such as Agent, Theme/Patient, Recipient, Time, Location, Purpose, Manner, Instrument, Cause, and Consequence, making it substantially closer to structured action-argument extraction than simple email classification.",
   "On the uncorrected test emails, the system reports F1 scores of 0.91 for detecting messages containing requests, 0.83 for action requests, 0.93 for information requests, and 0.84 for semantic-role extraction.",
   "After manual spelling correction, reported F1 rises to 0.94 for request-containing messages, 0.88 for action requests, 0.94 for information requests, and 0.89 for semantic roles, indicating notable sensitivity to noisy email text.",
   "The action-request filter requires an Agent corresponding to the email recipient and uses imperative, semi-auxiliary, or complement-clause constructions while excluding predicates governed by conjectural verbs such as think, presume, hope, or believe.",
   "The task definition explicitly allows negative requested actions and includes a Time semantic role, but the evaluation does not separately measure negation attachment or deadline-to-action attachment accuracy."
  ]
 },
 {
  "paper_id": "manual-ee40d588e3",
  "title": "*SEM 2012 Shared Task: Resolving the Scope and Focus of Negation",
  "research_question": "How accurately can computational systems identify negation cues, their scope, negated events or properties, and the focus of negation under standardized shared-task conditions?",
  "key_findings": [
   "Negation cue detection is substantially easier than complete resolution of cue, scope, and negated event together.",
   "The best closed-track official global score for complete negation resolution was 57.63 F1, while individual cue identification reached above 92 F1.",
   "Machine-learning systems generally outperformed the rule-based system on the complete Task 1 evaluation.",
   "Only one team participated in focus detection, and its best reported focus score was 58.40 F1.",
   "Scope scores are sensitive to how partial matches are counted, although the alternative evaluation reported by the organizers did not change the system ranking."
  ]
 },
 {
  "paper_id": "manual-fde6beef40",
  "title": "Classifying Action Items for Semantic Email",
  "research_question": "Can action items in email be automatically classified into useful semantic categories using a computationally tractable speech-act model and linguistic rules?",
  "key_findings": [
   "The proposed model represents action items through action, object, and subject dimensions and yields 22 basic action-item combinations.",
   "The implemented classifier uses modality, verb category, tense, negation, and semantic-role information, with additional rules for phenomena such as conditional constructions.",
   "An earlier human annotation exercise over the 22-category scheme achieved inter-annotator agreement of 0.811, indicating substantial but imperfect agreement on the task.",
   "In the reported evaluation, the rule-based classifier achieved precision 0.56, recall 0.60, and F1 0.58.",
   "The authors conclude that the classifier is not reliable enough for unattended automatic annotation and is better used to suggest candidate annotations for user review and correction."
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
"/home/grammy-jiang/Projects/msgloom/research/05-action-items-and-commitments/runs/5060d000e7b4/analysis/synthesis.json", `status` = accepted | accepted_with_issues | rejected,
`issues` (each naming the finding or paper it is about), `required_fixes`
(required when rejected), `unsupported_claims`, `confidence`, and `scores`
with faithfulness, coherence, gap_completeness (0-1) and citation_integrity
(true/false).
===BEGIN synthesis_review.json===
<content>
===END synthesis_review.json===

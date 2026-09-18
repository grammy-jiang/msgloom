# Executive Summary

Across 17 papers, the strongest direct workplace-email evidence supports distinguishing requests from commitments, representing conditional and indirect acts explicitly, allowing overlapping speech acts, and using message context when sentence-local wording is insufficient. Meeting and dialogue studies provide transfer evidence that action items often require structured, multi-utterance representations containing description, owner, timeframe, and agreement, but owner extraction remains difficult and context does not help every class or dataset. Decision-dialogue work similarly supports structured Issue/Resolution/Agreement modeling. Temporal, modality, and negation papers contribute component-level representations and difficulty evidence rather than independent validation of a complete workplace-action schema. No paper in this corpus jointly validates extraction of act, owner, object, deadline, condition, and evidence spans on authentic workplace email or chat. The resulting design principles are therefore well motivated, but several product-critical argument-level questions remain open.

# Themes

**Finding 1 — Speech-act distinctions matter. HIGH confidence.** Requests, commitments, proposals, deliveries, and related communicative acts should not be collapsed into one undifferentiated action label. Email taxonomies distinguish these functions, message-level models can use multiple labels, and real email contains cases where a commitment simultaneously imposes a request on a recipient. [doi-10-1109-hicss-2006-528] [doi-10-1145-1076034-1076094] [manual-20b8cd2fdd]

**Finding 2 — Structured action-item representations are better motivated than flat labels, especially in meeting transfer evidence. HIGH confidence.** Several meeting studies decompose action items into task description, owner, timeframe, and agreement/commitment and combine evidence across nearby utterances. The same experiments repeatedly identify owner recognition as particularly difficult. [doi-10-1007-11965152-18] [doi-10-3115-1564535-1564540] [doi-10-18653-v1-2007-sigdial-1-4]

**Finding 3 — Context helps often, but not reliably enough to be unconditional. HIGH confidence.** Local/global context improves action-item detection on meeting data, and dialogue-sequence information strongly improves general dialogue-act classification. However, collective email classification makes some acts worse, and the context configuration performing best on AMC-A is not best on AMI. [2303.16763] [doi-10-1145-1076034-1076094] [manual-01c535c108]

**Finding 4 — Localization and reliable judgment occur at different useful granularities. HIGH confidence.** Sentence-level action-item classification improved document-level detection in one email experiment, but later Enron work found higher agreement for message-level request/commitment judgments and documented cases where the same obligation has multiple sentence realizations or no unambiguous single locus. [doi-10-1145-1076034-1076140] [manual-20b8cd2fdd]

**Finding 5 — Conditions and indirectness are first-class difficulties. HIGH confidence.** Conditional offers account for substantial commitment disagreement, implicit requests can require message context, and a condition governing a request or commitment may occur outside the same sentence as the governed act. [manual-0839b98ee7] [manual-20b8cd2fdd] [manual-d19b0f6f1e]

**Finding 6 — Message zoning is directly useful for email request detection. HIGH confidence.** Removing quoted, forwarded, signature, and similar non-author zones substantially improves message-level request detection, although implicit requests, attachment-related requests, and zoning mistakes remain error sources. [manual-cd3fa58e4c]

**Finding 7 — Temporal modeling supplies useful components, not a validated deadline extractor. MEDIUM confidence.** TimeML supplies explicit temporal mentions, normalization machinery, and event-time relations; meeting work demonstrates gains from semantic and temporal features in timeframe extraction; direct email work explicitly leaves deadline representation for future work. These results do not establish that a system can reliably distinguish a deadline for an action from any other date mention in workplace communication. [manual-1e8332286e] [doi-10-18653-v1-2007-sigdial-1-4] [manual-d19b0f6f1e]

**Finding 8 — Modality and negation provide component-level evidence only. HIGH confidence.** Open-class modal-trigger detection is substantially harder than detection restricted to conventional auxiliaries, while complete negation cue/scope/event resolution is substantially harder than cue identification. These papers motivate scoped modality and negation handling but do not independently validate a complete workplace-action schema. [2106.08037] [manual-ee40d588e3]

**Finding 9 — Structured decision-dialogue modeling improves the compared detection task. HIGH confidence.** Structured modeling of Issue, Resolution Proposal, Resolution Restatement, and Agreement improved decision-dialogue-act detection relative to the compared hierarchical SVM. The representation does not extract workplace owners, deadlines, or conditions. [doi-10-3115-1708376-1708410]

**Finding 10 — The complete target schema remains unvalidated as a joint extraction task. HIGH confidence.** No paper in this corpus jointly demonstrates end-to-end extraction of speech-act type, action owner, detailed action object, deadline, conditions, and supporting evidence spans on authentic workplace email or chat. Direct email work typically detects requests/commitments or action-containing messages; meeting work supplies only subsets of the desired structure; temporal work lacks task roles; decision work lacks owners, deadlines, and conditions. [manual-d19b0f6f1e] [manual-cd3fa58e4c] [2303.16763] [doi-10-3115-1708376-1708410] [manual-1e8332286e]

**Finding 11 — Gold-label uncertainty is itself significant. HIGH confidence.** Request presence can be annotated relatively reliably, but commitments and strength judgments are harder. AMC-A action-item annotation has only moderate pairwise agreement, and modality error analysis finds that some apparent model errors are actually missed or incorrect annotations. [manual-0839b98ee7] [2303.16763] [2106.08037]

Recurring themes across these findings are therefore: speech-act type and action arguments are related but distinct; structured representations are more informative than flat action labels; context is necessary in many hard cases but must be used selectively; owner assignment remains a weak point; conditions, modality, negation, and temporal relations require scoped linkage; and direct workplace-email evidence is substantially narrower than the transfer evidence from meetings and dialogue.

# Contradictions

**Context benefit.** [2303.16763] and [manual-01c535c108] show material gains from contextual or sequential evidence, whereas [doi-10-1145-1076034-1076094] shows that thread context can degrade particular email-act classes such as Deliver. Even within [2303.16763], the best AMC-A context configuration is not the best AMI configuration. This is best interpreted as a task- and dataset-dependent tension, not evidence that context is generically beneficial or harmful.

**Sentence versus message granularity.** [doi-10-1145-1076034-1076140] finds that sentence-level classifiers improve email-level action-item detection, while [manual-20b8cd2fdd] reports higher human agreement at message level and attributes part of the difference to sentence-level locus ambiguity. These findings measure different objectives: localizing actionable material and deciding whether the message contains an obligation should not be assumed to require the same granularity.

**ASR robustness.** [doi-10-18653-v1-2007-sigdial-1-4] reports substantial degradation in structured action-item detection when moving from manual transcripts to ASR. In contrast, [doi-10-3115-1708376-1708410] reports some decision-dialogue configurations with ASR results comparable to or above manual-transcript scores, while explicitly noting that segmentation and sparsity differences may contribute. The corpus therefore does not support a single general claim about ASR robustness.

# Open Gaps

**G1 — ACADEMIC, HIGH.** There is no direct modern workplace email/chat benchmark in this corpus jointly annotating speech-act type, owner/assignee, action object, deadline, conditions/exceptions, and exact evidence spans. Relevant limitations appear across [manual-d19b0f6f1e], [manual-cd3fa58e4c], and [2303.16763].  
Suggested query: `"action item extraction" workplace email chat owner assignee deadline condition span corpus`

**G2 — ACADEMIC, HIGH.** Direct empirical evidence for extracting decisions, approvals, rejections, and proposals with structured arguments from authentic workplace email or chat remains absent. The decision evidence here is meeting transfer evidence [doi-10-3115-1708376-1708410], while email speech-act work does not provide the desired structured decision extraction [doi-10-1109-hicss-2006-528].  
Suggested query: `"decision extraction" email workplace approval rejection proposal dialogue act`

**G3 — ACADEMIC, HIGH.** Owner/assignee extraction remains weakly evidenced, particularly for implicit owners, group ownership, multiple actions with different owners, and owners recoverable only from relationship or conversation context. [doi-10-1007-11965152-18] [doi-10-3115-1564535-1564540] [manual-0839b98ee7]  
Suggested query: `"assignee extraction" OR "owner extraction" action item email implicit argument responsibility`

**G4 — ACADEMIC, HIGH.** Reliable deadline binding remains open: the corpus does not establish how accurately a system can distinguish a deadline for a specific action from a merely mentioned date, shared date, scheduling expression, or conditional future time in workplace communication. [manual-1e8332286e] [doi-10-18653-v1-2007-sigdial-1-4] [manual-d19b0f6f1e]  
Suggested query: `"deadline extraction" email temporal relation action item due date event argument`

**G5 — ACADEMIC, HIGH.** Direct workplace evidence is insufficient for attaching conditions, exceptions, negation, and modality to the correct action where multiple clauses or actions coexist. The email papers identify the phenomenon, while the modality and negation papers provide transfer/component evidence rather than workplace validation. [manual-d19b0f6f1e] [manual-20b8cd2fdd] [2106.08037] [manual-ee40d588e3]  
Suggested query: `"conditional commitment" workplace email negation scope deontic modality action extraction`

**G6 — ENGINEERING, HIGH.** Build an independent argument-level benchmark and adversarial fixture suite covering implicit owners, multiple actions in one sentence, shared deadlines, conditional and negated actions, overlapping request/commitment labels, quoted-history contamination, and attachment references. Score false positives, false negatives, act labels, and each argument separately. This recommendation is synthesis-derived from recurring failure modes in [manual-20b8cd2fdd], [manual-0839b98ee7], [doi-10-3115-1564535-1564540], and [manual-cd3fa58e4c].

**G7 — ENGINEERING, HIGH.** Compare sentence-local, message-level, and selectively expanded thread-context extraction with controlled ablations. This is a synthesis-derived experiment motivated by the mixed context evidence in [2303.16763], [doi-10-1145-1076034-1076094], and [manual-20b8cd2fdd].

**G8 — ENGINEERING, HIGH.** Test author/quoted/forwarded zoning while preserving provenance, measuring whether zoning improves extraction without losing obligations whose interpretation requires prior-message context. Zoning benefit is directly supported by [manual-cd3fa58e4c]; preservation of lineage is a synthesis-derived engineering recommendation motivated by the context dependence documented in [manual-20b8cd2fdd].

**G9 — ENGINEERING, HIGH.** Evaluate an uncertainty-preserving structured output where owner, deadline, condition, or act subtype may remain unresolved, and measure whether this reduces false obligations and wrong assignments without unacceptable recall loss. This is a synthesis-derived recommendation motivated by owner weakness and annotation ambiguity in [manual-0839b98ee7], [doi-10-1007-11965152-18], and [2303.16763].

**Prior-gap status.** Attempt 1 was rejected, but the supplied material does not contain the complete prior synthesis gap list or its identifiers. Assigning one `resolved`/`open` record per prior gap would therefore require inventing prior history. No such statuses are asserted; `gap_status` is intentionally empty.

# Actionable Insights

1. Keep request, commitment, proposal/decision-related, and action-item concepts distinguishable, and allow overlapping act labels where the same text legitimately performs more than one function. This is directly supported by [doi-10-1109-hicss-2006-528], [manual-20b8cd2fdd], and [doi-10-1145-1076034-1076094].

2. **Synthesis-derived recommendation:** represent an extracted work event with separately assessable act type, owner, action/object, timeframe/deadline candidate, condition, and evidence rather than filling every field by inference. Owner difficulty and human disagreement make silent completion of missing values particularly risky. [doi-10-1007-11965152-18] [doi-10-3115-1564535-1564540] [manual-0839b98ee7]

3. **Synthesis-derived recommendation:** use context gating instead of unconditional thread expansion. Begin with the local candidate and expand to message or thread context when indirectness, conditionality, ownership, or act disambiguation requires it. Benchmark each level because added context is not uniformly beneficial. [2303.16763] [doi-10-1145-1076034-1076094] [manual-20b8cd2fdd]

4. Model conditionality as belonging to the governed request or commitment and allow its supporting text to occur outside the act sentence. This is directly supported by [manual-d19b0f6f1e] and [manual-0839b98ee7].

5. **Synthesis-derived recommendation:** separate temporal-expression detection, normalization, action-time linking, and the final judgment that the linked time is actually a deadline. The literature supports the component mechanisms more directly than deadline classification itself. [manual-1e8332286e] [doi-10-18653-v1-2007-sigdial-1-4] [manual-d19b0f6f1e]

6. **Synthesis-derived recommendation:** preserve source lineage while performing message zoning. Zoning can improve classification, but quoted/history material should remain recoverable when interpretation requires it rather than being irreversibly discarded. [manual-cd3fa58e4c] [manual-20b8cd2fdd]

7. At the component level, attach modality and negation to the event or scope they govern rather than treating the presence of a modal or negation cue as sufficient semantic evidence. [2106.08037] [manual-ee40d588e3]

8. **Synthesis-derived recommendation:** evaluate exact act and argument correctness, missed obligations, false obligations, wrong owners, wrong deadlines, and lost conditions independently. Overall accuracy can obscure poor positive-class or argument performance. [doi-10-1145-1076034-1076140] [2303.16763] [doi-10-3115-1564535-1564540]

9. **Project-scope boundary, not a literature-derived conclusion:** this synthesis concerns semantic extraction at the utterance/message time described in the supplied Topic context. It should not be used as evidence for how later lifecycle-state processing is routed or implemented.

# Confidence Summary

The corpus provides **HIGH-confidence support for several well-supported design principles**, not proof that every element is a necessary production requirement. In particular, the evidence strongly supports distinguishing requests from commitments and related acts, explicitly representing conditionality and indirectness, allowing contextual and multi-utterance evidence, and evaluating structured arguments rather than only a flat action label.

The distinction between evidence domains is important. **Direct workplace-email evidence** is strongest for request/commitment annotation, message zoning, locus ambiguity, indirect requests, conditional commitments, and contextual edge cases, but it is concentrated largely in Enron-era and small university datasets. [manual-0839b98ee7] [manual-20b8cd2fdd] [manual-d19b0f6f1e] [manual-cd3fa58e4c] [doi-10-1145-1076034-1076140]

**Meeting and general dialogue evidence is transfer evidence.** It supports structured action-item decomposition, decision-dialogue structure, contextual modeling, and owner/timeframe components, but it does not establish production accuracy on workplace email or chat. [2303.16763] [doi-10-1007-11965152-18] [doi-10-18653-v1-2007-sigdial-1-4] [doi-10-3115-1708376-1708410] [manual-01c535c108]

Similarly, **TimeML, event-modality, and negation research supplies component-level representations or difficulty evidence**, not independent validation of the complete workplace-action schema. [manual-1e8332286e] [2106.08037] [manual-ee40d588e3]

Confidence is therefore **MEDIUM for the complete proposed structured workplace-action representation** and **LOW-to-MEDIUM for claims about current production accuracy on Outlook or Teams** until direct domain evaluation is performed.

# Limitations

- The corpus mixes authentic email, simulated-company email, natural and simulated meetings, telephone dialogue, news/literary temporal or negation corpora, and general modality data. Their results are not directly interchangeable.
- Direct workplace-email evidence is concentrated in Enron and small older email datasets. Modern enterprise chat such as Microsoft Teams or Slack is minimally represented.
- Several meeting studies use small samples, scenario-driven meetings, indirect action labels, manually tuned rules, or human transcripts.
- No included study jointly evaluates the target combination of act type, owner, object, deadline, conditions, and exact supporting evidence.
- Attachments and other multimodal workplace evidence are largely absent from the direct email corpora even though attachment-related requests are identified as an important error source. [manual-20b8cd2fdd] [manual-cd3fa58e4c]
- Some annotation studies use their authors as annotators, discard disagreement cases, or report substantial ambiguity, so difficult cases may not admit a single uncontested gold interpretation. [manual-0839b98ee7] [manual-cd3fa58e4c] [2303.16763]
- The synthesis uses only the supplied per-paper analyses and does not independently re-read the source papers.
- The complete gap list and IDs from the rejected first synthesis were not supplied. To avoid inventing prior-gap history, no one-to-one prior-gap resolution status is claimed.

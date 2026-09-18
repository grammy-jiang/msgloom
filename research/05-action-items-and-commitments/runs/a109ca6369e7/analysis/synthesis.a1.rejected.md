# Executive Summary

Across 17 papers, the strongest recurring conclusion is that workplace action understanding should be modeled as structured, contextual extraction rather than binary action-item detection. Requests, commitments, decisions, owners, timeframes, conditions, modality, negation, and evidence loci are partially separable phenomena, and several can span multiple utterances. Context usually helps, but thread or neighboring-context features can also degrade particular classes, so contextual reasoning should be selective rather than unconditional. Owner extraction is repeatedly difficult, while conditions, implicit requests, conditional offers, and commitment interpretation create substantial human disagreement. Temporal work supports explicit event-time relations and underspecified dates, but direct evidence for correctly linking workplace actions to deadlines remains weak. The corpus provides useful design principles, but direct end-to-end evidence for extracting msgloom's complete schema from modern workplace email and chat remains missing.

# Themes

- **Structured action records are preferable to undifferentiated action labels.** Meeting work independently converges on decompositions such as Description, Owner, Timeframe, and Agreement [doi-10-1007-11965152-18] [doi-10-3115-1564535-1564540]. Email work represents requests and commitments through actors, counterparties, actions, and optional conditions [manual-d19b0f6f1e], while another email taxonomy separates action, object, and subject dimensions [manual-fde6beef40].

- **Speech-act detection is not argument extraction.** A classifier can decide that an email contains a request or commitment without recovering who owns the work, what exactly must be done, when it is due, or under what conditions. This limitation is explicit across email-act and action-item studies [doi-10-1109-hicss-2006-528] [doi-10-1145-1076034-1076140] [doi-10-1145-1076034-1076094].

- **Owner extraction is especially risky.** Owner was the weakest reported structured action-item subclass in two closely related meeting studies, reaching F1 0.17 in their preliminary experiments [doi-10-1007-11965152-18] [doi-10-3115-1564535-1564540]. Later meeting work still excluded owner identity from its summarization evaluation [doi-10-18653-v1-2007-sigdial-1-4]. This directly supports msgloom's requirement to preserve an unknown owner instead of inventing one.

- **Conditionality, modality, and negation are scoped semantics, not simple flags.** Conditional offers account for a major proportion of commitment-annotation disagreements [manual-0839b98ee7], and conditions may occur outside the sentence containing the request or commitment [manual-d19b0f6f1e]. Open-class modal detection is markedly harder than recognizing a few modal auxiliaries [2106.08037], while negation cue recognition is much easier than resolving the complete cue, scope, and negated event [manual-ee40d588e3].

- **Context helps, but not uniformly.** Local and global meeting context improves action-item detection on AMC-A, yet the best configuration changes on AMI [2303.16763]. Dialogue-act sequence context produces large classification gains in Switchboard [manual-01c535c108]. Thread-level collective classification improves several email acts, especially Commissive, but degrades Deliver and does not significantly improve every act [doi-10-1145-1076034-1076094]. Context should therefore be treated as evidence subject to validation, not as an unconditional performance improvement.

- **Localization is useful, but one action need not equal one sentence.** Sentence-level email classifiers improve document-level action-item detection [doi-10-1145-1076034-1076140]. At the same time, the same obligation may be realized by several sentences [manual-20b8cd2fdd], and meeting action descriptions, owners, timeframes, or agreement evidence can be spread across utterances [doi-10-3115-1564535-1564540] [doi-10-18653-v1-2007-sigdial-1-4]. msgloom therefore needs multi-span evidence rather than a forced single-sentence locus.

- **Request and commitment should remain distinct but need not be exclusive.** Email taxonomies distinguish information requests, directives, commitments, and related categories [doi-10-1109-hicss-2006-528]. CSpace explicitly supports multiple email-act labels [doi-10-1145-1076034-1076094], and Enron annotation work documents cases where a third-party commitment simultaneously imposes a request on a recipient [manual-20b8cd2fdd]. This argues for multi-label act representation.

- **Deadlines require event-time binding.** TimeML provides explicit event-time relations, temporal anchors, and underspecified temporal expressions [manual-1e8332286e]. Meeting research shows that semantic and temporal features can materially improve timeframe extraction [doi-10-18653-v1-2007-sigdial-1-4]. However, direct email request/commitment work explicitly leaves deadline representation for future work [manual-d19b0f6f1e]. A detected date therefore cannot safely be assumed to be the deadline of the nearby action.

- **Input preparation materially affects results.** Removing quoted and other non-author zones increases Enron request-detection accuracy from 72.28% to 83.76% [manual-cd3fa58e4c]. A workplace-email annotation study reports at least a 10% sentence-segmentation error rate in its pilot material [manual-0839b98ee7]. Structured meeting action detection also degrades from manual transcripts to ASR [doi-10-18653-v1-2007-sigdial-1-4].

- **Decision extraction has its own internal structure.** Decision dialogue is usefully separated into Issue, Resolution Proposal, Resolution Restatement, and Agreement, and structured graphical models outperform a previous hierarchical SVM on those components [doi-10-3115-1708376-1708410]. This supports distinguishing proposals from final decisions rather than mapping all future-oriented language into one action label.

- **Human disagreement is part of the semantic problem.** Request presence is annotated more consistently than commitment presence, and commitment strength is particularly unstable [manual-0839b98ee7]. Better instructions for conditional and indirect cases substantially improve agreement [manual-d19b0f6f1e] [manual-20b8cd2fdd]. AMC-A still reports only moderate pairwise agreement despite detailed guidelines and expert adjudication [2303.16763]. Uncertainty should therefore remain visible in system output.

# Contradictions

### Context: useful versus universally beneficial

Several studies show substantial gains from discourse or neighboring context. Local/global meeting context improves action-item detection [2303.16763], dialogue-act sequence models strongly improve conversational act classification [manual-01c535c108], and collective email-thread classification improves several commissive categories [doi-10-1145-1076034-1076094].

The qualification is important: AMC-A's strongest context configuration is not the strongest AMI configuration [2303.16763], while adding relational context makes Deliver worse in the email study [doi-10-1145-1076034-1076094]. The cross-paper conclusion is therefore not "more context is better"; it is that context is useful evidence whose relevance must be learned or gated.

### Sentence-level versus message-level granularity

Automatic action-item detection benefits from sentence-level modeling compared with direct whole-email classification [doi-10-1145-1076034-1076140]. Conversely, human request/commitment annotation obtains higher agreement at message level, partly because message-level judgments avoid deciding which exact sentence carries an obligation [manual-20b8cd2fdd].

These results address different objectives. msgloom needs sentence/span-level evidence for traceability, but its semantic event representation should permit several spans to instantiate one action.

### Single-label versus overlapping acts

The HICSS email-act experiment merges several theoretically distinct categories because of data sparsity and focuses on a primary communicative intent [doi-10-1109-hicss-2006-528]. Other evidence directly supports overlap: CSpace allows several email-act labels per message [doi-10-1145-1076034-1076094], and Enron annotation documents cases where one commitment simultaneously functions as a request [manual-20b8cd2fdd].

For msgloom, a mutually exclusive speech-act field would therefore discard supported distinctions.

### ASR degradation versus apparent ASR robustness

Structured action-item detection falls from overlap F1 0.45 on manual transcripts to 0.36 on one-best ASR [doi-10-18653-v1-2007-sigdial-1-4]. In decision-dialogue experiments, some Issue and Resolution Proposal configurations perform as well as or better on ASR than on manual transcripts [doi-10-3115-1708376-1708410]. The decision paper cautions that segmentation and sparsity differences partly explain this result. The evidence therefore does not support a general claim that structured extraction is ASR-robust.

### Strict action item versus unaccepted request

Meeting action-item studies use a comparatively strict construct: a concrete future action, identifiable responsible person, timeframe, and agreement or public commitment [doi-10-1007-11965152-18] [doi-10-18653-v1-2007-sigdial-1-4]. Workplace-email request studies classify an obligation imposed on a recipient as a request even when no acceptance or explicit timeframe exists [manual-d19b0f6f1e] [manual-cd3fa58e4c].

These are not interchangeable labels. A request may exist without a commitment, and an action-item detector trained on the stricter meeting definition would risk missing unaccepted work requests that matter to msgloom.

# Open Gaps

### G1 — ACADEMIC — HIGH

No paper in this corpus evaluates end-to-end extraction of the complete msgloom record from modern workplace email or chat: speech-act type, actor/owner, recipient, action object, deadline, conditions/exceptions, and exact evidence spans with unresolved fields preserved. Existing email studies generally stop at request/action detection or partial semantic structure [manual-d19b0f6f1e] [manual-20b8cd2fdd] [doi-10-1145-1076034-1076140], while the strongest structured extraction evidence is meeting-based [2303.16763].

Suggested query: `"workplace email" OR "business email" OR "enterprise chat" structured action extraction owner assignee deadline condition evidence span request commitment decision`

### G2 — ACADEMIC — HIGH

Modern workplace chat and cross-channel generalization are not established. Direct email evidence is dominated by Enron, small personal/university collections, or simulated-company email [manual-0839b98ee7] [manual-20b8cd2fdd] [manual-cd3fa58e4c] [doi-10-1145-1076034-1076094], while newer structured work focuses on meetings [2303.16763].

Suggested query: `"Microsoft Teams" OR Slack OR "enterprise chat" request detection commitment detection action item extraction workplace`

### G3 — ACADEMIC — HIGH

Reliable owner/assignee resolution remains unresolved, particularly when ownership is implicit or must be reconstructed from participants, discourse, or organizational relationships. Owner is the weakest structured meeting component in two experiments [doi-10-1007-11965152-18] [doi-10-3115-1564535-1564540], and email annotators report that organizational relationships materially affect interpretation [manual-0839b98ee7].

Suggested query: `"assignee extraction" OR "owner extraction" OR "responsibility extraction" implicit argument workplace email task action item`

### G4 — ACADEMIC — HIGH

The literature here does not directly solve joint workplace extraction of action plus governing condition, exception, modality, or negation scope. Conditional commitments are empirically important in email [manual-d19b0f6f1e] [manual-0839b98ee7], while modality and negation papers show that event linkage and semantic scope are themselves difficult [2106.08037] [manual-ee40d588e3].

Suggested query: `"conditional commitment" request negation modality scope email dialogue obligation NLP`

### G5 — ACADEMIC — MEDIUM

Direct workplace email/chat evidence remains limited for jointly distinguishing proposal, intention, commitment, assignment, approval, rejection, and final decision when several acts coexist. Existing evidence comes from relatively coarse email-act taxonomies or meeting decision structure [doi-10-1109-hicss-2006-528] [doi-10-1145-1076034-1076094] [doi-10-3115-1708376-1708410].

Suggested query: `"decision extraction" approval proposal commitment "workplace email" OR "enterprise chat" speech act`

### G6 — ENGINEERING — HIGH

Build an independent msgloom benchmark and adversarial fixture set for the complete event schema. It should contain implicit owners, multiple actions in one sentence, shared deadlines, multi-span evidence, conditional and negated obligations, simultaneous request/commitment cases, reported speech, and intentionally unknown arguments. These failure modes are directly motivated by the corpus [manual-20b8cd2fdd] [manual-d19b0f6f1e] [doi-10-3115-1564535-1564540] [manual-ee40d588e3].

### G7 — ENGINEERING — HIGH

Test deadline binding separately from temporal recognition. Preserve original wording, normalize only when an appropriate anchor exists, and evaluate whether each temporal expression is attached to the correct action [manual-1e8332286e] [doi-10-18653-v1-2007-sigdial-1-4] [manual-d19b0f6f1e].

### G8 — ENGINEERING — HIGH

Benchmark robustness to message zoning, quoted history, segmentation errors, attachment references, and chat-style boundaries. Existing results show large zoning effects and meaningful segmentation errors, while several dialogue benchmarks assume cleaner boundaries than production systems will receive [manual-cd3fa58e4c] [manual-0839b98ee7] [manual-20b8cd2fdd] [manual-01c535c108].

### G9 — ENGINEERING — MEDIUM

Use disagreement-aware evaluation. Score act label and each argument/evidence relation independently, retain difficult examples rather than restricting evaluation to unanimous cases, and expose uncertainty when human interpretation is unstable [manual-0839b98ee7] [manual-20b8cd2fdd] [2303.16763] [2106.08037].

### G10 — OUT_OF_SCOPE — HIGH

Whether an extracted action or commitment is later completed, cancelled, revoked, superseded, contradicted, or still pending is lifecycle-state tracking rather than Topic 05 semantic extraction. Structured action-item studies establish the event at creation time but do not solve its later state [doi-10-1007-11965152-18]. This belongs to Topic 06.

### G11 — OUT_OF_SCOPE — HIGH

Correctly determining which antecedent proposition or request an approval, rejection, agreement, or commitment applies to must remain a Topic 04 concern. Decision and email-act work demonstrates the importance of surrounding discourse [doi-10-3115-1708376-1708410] [doi-10-1145-1076034-1076094], but a Topic 05 act label must not be treated as proof that antecedent scope was resolved correctly.

### G12 — OUT_OF_SCOPE — MEDIUM

Executing actions, invoking tools, sending messages, or treating a generated draft as approval is outside semantic extraction. Even an action-item classifier judged insufficiently reliable for unattended annotation was proposed as a candidate-generation aid rather than an autonomous executor [manual-fde6beef40].

No prior-round gap list was supplied with this synthesis task, so `gap_status` is empty rather than inventing prior gap identifiers or resolution states.

# Actionable Insights

1. Adopt a first-class event record containing act type or types, actor/owner, recipient or beneficiary, action/object, modality or utterance-time status, original deadline wording, normalized time only when justified, conditions/exceptions, source spans, confidence, and unresolved fields.

2. Never fabricate missing owner, deadline, object, or condition. Record `unknown`, and distinguish explicitly stated ownership from contextually inferred ownership.

3. Permit multi-label speech acts. Request and commitment are semantically different, but one passage can legitimately instantiate both [manual-20b8cd2fdd] [doi-10-1145-1076034-1076094].

4. Allow one event to cite multiple source spans and allow different arguments to come from different utterances. The literature does not support forcing every work item into one sentence [manual-20b8cd2fdd] [doi-10-18653-v1-2007-sigdial-1-4].

5. Use context selectively. Compare sentence-only, local-message, thread, and wider Topic context, and require empirical evidence that each additional context layer helps rather than assuming it will [2303.16763] [doi-10-1145-1076034-1076094].

6. Represent condition, modality, and negation as scoped relations to an event rather than message-level Boolean properties [manual-d19b0f6f1e] [2106.08037] [manual-ee40d588e3].

7. Split deadline processing into temporal interpretation and action-time attachment. Keep the original phrase even when a normalized value is available [manual-1e8332286e].

8. Evaluate detection and extraction separately. First measure whether an actionable act was found; then independently measure speech-act label, owner, action/object, deadline, conditions, and evidence support.

9. Use zoning to control irrelevant quoted or boilerplate content, but preserve source bytes and lineage rather than permanently discarding excluded zones. Zoning materially changes request-classification quality [manual-cd3fa58e4c].

10. Include ambiguous examples in gold evaluation. Removing disagreement cases creates an artificially easier test set and disproportionately removes the examples most relevant to missed-obligation risk [manual-cd3fa58e4c] [manual-0839b98ee7].

11. Route low-confidence or semantically incomplete records to explicit uncertainty/review rather than silently turning suggestions, capabilities, conditional offers, or vague future language into assigned work [manual-fde6beef40] [manual-0839b98ee7].

12. Keep Topic 05 strictly at utterance-time semantics. Later completion, revocation, contradiction, and supersession belong to Topic 06.

# Confidence Summary

Confidence is **HIGH** that msgloom should use structured argument-level extraction, contextual interpretation, explicit conditionality/modality handling, multi-span evidence, multi-label speech acts, and unknown-field preservation. These conclusions recur across independent workplace-email, meeting, dialogue-act, temporal, modality, and negation research [manual-d19b0f6f1e] [manual-20b8cd2fdd] [doi-10-1007-11965152-18] [2106.08037] [manual-ee40d588e3].

Confidence is also **HIGH** that owner extraction and implicit or conditional cases are particularly difficult [doi-10-3115-1564535-1564540] [manual-0839b98ee7].

Confidence is only **MEDIUM** regarding achievable production accuracy for msgloom. No paper here evaluates the complete target schema end-to-end on modern Outlook/Teams-like communication, and much of the structured evidence comes from meetings, simulated settings, or older email corpora [2303.16763] [doi-10-1145-1076034-1076094] [manual-20b8cd2fdd].

# Limitations

- No included paper evaluates msgloom's entire proposed record over modern workplace email and chat. Most solve detection, classification, or selected arguments only [manual-d19b0f6f1e] [2303.16763].

- Direct email evidence is heavily concentrated in Enron, small personal collections, university email, or simulated-company communication, limiting organizational and temporal representativeness [manual-20b8cd2fdd] [doi-10-1109-hicss-2006-528] [doi-10-1145-1076034-1076094].

- The strongest structured action and decision work is meeting-based, so transfer to asynchronous email and Teams-like chat is plausible but not empirically established [doi-10-18653-v1-2007-sigdial-1-4] [doi-10-3115-1708376-1708410].

- Reported metrics are not directly comparable. The papers evaluate message classification, sentence detection, dialogue-region overlap, individual action components, annotation agreement, temporal parsing, modality, and negation with different denominators and task definitions.

- Several experiments use very small datasets, manually weighted combinations, indirect labels, gold segmentation, or manually supplied dialogue-act annotations [doi-10-1007-11965152-18] [doi-10-3115-1564535-1564540] [doi-10-3115-1708376-1708410] [manual-01c535c108].

- Some classifier evaluations remove disagreement cases, making the evaluated data cleaner than the real semantic boundary msgloom must handle [manual-cd3fa58e4c].

- Important email corpora lack attachments even though attachment-review requests are identified as a meaningful workplace phenomenon [manual-20b8cd2fdd] [manual-cd3fa58e4c].

- The supplied papers provide little direct evidence about modern foundation-model or LLM-based structured extraction. The synthesis therefore supports representation, failure-mode, and evaluation requirements more strongly than any particular current model architecture.

- This synthesis is restricted to the 17 supplied analyses and does not claim that the broader literature is exhausted.

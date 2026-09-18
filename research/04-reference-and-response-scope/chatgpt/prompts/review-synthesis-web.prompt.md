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

Research topic: **direct empirical studies of proposition-level partial reply scope in workplace email or enterprise dialogue, especially multi-question messages, unanswered subquestions, scoped approval/rejection, and responses linked jointly to multiple antecedent propositions**

You did not write this synthesis and you are not reviewing your own work.
Your verdict decides whether the report may be written. Rejecting is a normal
outcome: reject when the evidence does not support the synthesis. Do not
soften a real problem into a note so that the work can pass.

Check five things against the analyses below, not against how well the
synthesis reads:

1. Faithfulness — every finding is traceable to at least one analysis, and no
   finding states more than its cited analyses support.
2. Citation integrity — every cited paper_id is one of: `1706.02256`, `2306.15103`, `2403.16609`, `doi-10-1007-bf00351935`, `doi-10-1007-bf00983299`, `doi-10-1007-s10489-013-0481-1`, `doi-10-1016-j-pragma-2007-07-011`, `doi-10-1016-j-pragma-2010-04-002`, `doi-10-1016-j-pragma-2018-03-015`, `doi-10-1093-jos-17-1-51`, `doi-10-1109-icaicta63815-2024-10762999`, `doi-10-1145-3209978-3210046`, `doi-10-1162-coli-a-00327`, `doi-10-1177-002383099603900306`, `doi-10-1515-ling-2018-0008`, `doi-10-1515-text-2003-021`, `doi-10-15398-jlm-v4i2-173`, `doi-10-15760-mcnair-2019-13-1-2`, `doi-10-1609-aaai-v33i01-3301134`, `doi-10-18653-v1-2021-codi-sharedtask-1`, `doi-10-18653-v1-2021-naacl-main-329`, `doi-10-18653-v1-2022-emnlp-main-778`, `doi-10-18653-v1-2023-eacl-main-247`, `doi-10-18653-v1-2023-findings-acl-710`, `doi-10-18653-v1-d15-1109`, `doi-10-18653-v1-p17-1009`, `doi-10-18653-v1-s15-1035`, `doi-10-3115-1220355-1220483`, `doi-10-3115-1708376-1708429`, `doi-10-3115-v1-d14-1056`, `doi-10-3233-aic-2012-0516`, `doi-10-3765-sp-5-6`, `doi-10-5087-dad-2020-104`, `doi-10-5210-dad-2022-203`, `doi-10-5210-dad-2023-201`, `manual-555fa5b6e8`, `manual-5a32708675`, `manual-5c0971730d`, `manual-7743c50805`, `manual-849c5f1c6d`, `manual-8b8a394daa`, `manual-a6314f615a`, `manual-ad98de9372`, `manual-b0133009f6`, `manual-be69c3aa17`, `manual-e1981ecd9a`, `manual-e4d6ad7ca1`.
3. Coherence — contradictions between papers are named, not averaged away.
4. Gap completeness — a gap this corpus cannot close is reported as open. A
   gap presented as closed without evidence is a rejection.
5. Overreach — transfer-domain or synthetic evidence is not presented as
   direct-domain evidence, and no production claim rests on it.

Synthesis under review:
{
 "topic": "direct empirical studies of proposition-level partial reply scope in workplace email or enterprise dialogue, especially multi-question messages, unanswered subquestions, scoped approval/rejection, and responses linked jointly to multiple antecedent propositions",
 "paper_count": 47,
 "executive_summary": "Across 47 papers, the strongest cross-paper result is that reply semantics cannot safely be represented as one message-to-message edge. Natural dialogue, email, and customer-service data contain partial answers, unanswered questions, non-adjacent replies, one-to-many answer links, multi-parent discourse attachments, and abstract references to composite proposition sets. Multiple interrogatives also need structural interpretation because they may be reformulations or narrowing moves rather than independent obligations. Annotation studies further show that exact antecedent boundaries and answer scope are genuinely ambiguous, while explicit no-link and alternative antecedent representations are empirically justified. However, direct workplace evidence remains concentrated on question-answer alignment, not proposition-level approval, rejection, agreement, or clarification scope. Therefore the literature supports msgloom's representational requirements, but not production thresholds or domain-accuracy claims. The remaining high-value work is workplace-oriented annotation/evaluation plus calibrated, asymmetric abstention and scope-error testing.",
 "themes": [
  "Partial response coverage is a real discourse property: a response may address only one component of a multi-question message while leaving other components unresolved [doi-10-1016-j-pragma-2010-04-002] [manual-849c5f1c6d].",
  "Unanswered questions and explicit no-link outcomes must be represented rather than silently attached to the nearest plausible response [doi-10-3115-1220355-1220483] [doi-10-3115-1708376-1708429] [doi-10-15398-jlm-v4i2-173].",
  "Message adjacency and email reply structure are insufficient proxies for semantic response scope because replies can target older material and concurrent threads [doi-10-3115-1220355-1220483] [2403.16609] [doi-10-18653-v1-d15-1109].",
  "One response can legitimately target several antecedents, and several propositions can jointly form a composite antecedent [doi-10-1609-aaai-v33i01-3301134] [doi-10-18653-v1-2023-eacl-main-247] [doi-10-5087-dad-2020-104] [doi-10-1515-ling-2018-0008].",
  "Exact non-nominal antecedent boundaries are difficult and sometimes intrinsically ambiguous, motivating clause-level constraints, alternative antecedent sets, and partial-credit evaluation [doi-10-1162-coli-a-00327] [manual-7743c50805] [manual-e4d6ad7ca1] [doi-10-5210-dad-2023-201].",
  "Multiple interrogatives do not automatically create multiple independent obligations because later questions can reformulate, particularize, repair, or replace an earlier question [doi-10-1016-j-pragma-2007-07-011] [doi-10-1515-text-2003-021] [doi-10-1016-j-pragma-2018-03-015].",
  "Agreement and rejection are proposition-sensitive rather than simple utterance-level polar labels: a response can accept a weaker subproposition while rejecting stronger content [doi-10-1177-002383099603900306].",
  "Response attachment and relation labeling are interdependent, while speaker, turn, and dialogue-structure signals materially improve discourse-link prediction [2306.15103] [doi-10-18653-v1-2023-eacl-main-247].",
  "Recency is useful but domain dependent: some dialogue phenomena are highly local, whereas asynchronous email and multi-thread dialogue contain important non-local links [doi-10-18653-v1-2022-emnlp-main-778] [manual-e1981ecd9a] [doi-10-3115-1220355-1220483]."
 ],
 "findings": [
  {
   "statement": "Multi-question messages frequently receive selective rather than exhaustive responses, so response coverage must be evaluated per component question instead of assuming that a reply resolves the whole message.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1016-j-pragma-2010-04-002",
     "section": "Key findings"
    },
    {
     "paper_id": "manual-849c5f1c6d",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-1016-j-pragma-2018-03-015",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "Question-level unresolved status is an empirically necessary output: questions, requests, and clarification attempts can remain unanswered even when later discourse is locally coherent.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-3115-1220355-1220483",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-3115-1708376-1708429",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-15398-jlm-v4i2-173",
     "section": "Key findings"
    },
    {
     "paper_id": "manual-e1981ecd9a",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "Semantic reply scope cannot be inferred reliably from adjacency, Reply/Reply-All structure, or nearest-turn heuristics because email and dialogue contain non-adjacent answers, concurrent threads, and replies to older contributions.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-3115-1220355-1220483",
     "section": "Key findings"
    },
    {
     "paper_id": "2403.16609",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-18653-v1-d15-1109",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "Non-bijective alignment is a core requirement: one answer may respond to multiple prior questions, one question may receive multiple answer links, and one conversational move may have multiple discourse parents.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1609-aaai-v33i01-3301134",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-3233-aic-2012-0516",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-18653-v1-2023-eacl-main-247",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-18653-v1-d15-1109",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "Composite proposition-level antecedents are linguistically and discourse-structurally supported: coherent sets of propositions or discourse units can jointly function as the target of a later reference or response.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1515-ling-2018-0008",
     "section": "Key findings"
    },
    {
     "paper_id": "manual-8b8a394daa",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-5087-dad-2020-104",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-18653-v1-d15-1109",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "Exact proposition or discourse-segment boundaries are often substantially harder to agree on than the general antecedent region, so exact-span evaluation should coexist with partial-overlap credit and explicit ambiguity representation.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1162-coli-a-00327",
     "section": "Key findings"
    },
    {
     "paper_id": "manual-7743c50805",
     "section": "Key findings"
    },
    {
     "paper_id": "manual-e4d6ad7ca1",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-5210-dad-2023-201",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "A sequence containing several questions must first be interpreted structurally because apparent component questions may be reformulations, particularizations, repairs, or collateral independent questions; simply counting interrogatives can overstate unresolved obligations.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-1016-j-pragma-2007-07-011",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-1515-text-2003-021",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-1016-j-pragma-2018-03-015",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "Acceptance and rejection can have narrower semantic scope than the preceding utterance as a whole: a response may accept an entailed or weaker proposition while rejecting stronger or omitted content.",
   "confidence": "MEDIUM",
   "evidence": [
    {
     "paper_id": "doi-10-1177-002383099603900306",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "Recency should be treated as a strong prior rather than a hard candidate cutoff: discourse deixis and clarification answers are often highly local, but asynchronous email and multi-thread conversation show materially important long-range response links.",
   "confidence": "HIGH",
   "evidence": [
    {
     "paper_id": "doi-10-18653-v1-2022-emnlp-main-778",
     "section": "Key findings"
    },
    {
     "paper_id": "manual-e1981ecd9a",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-3115-1220355-1220483",
     "section": "Key findings"
    },
    {
     "paper_id": "manual-555fa5b6e8",
     "section": "Key findings"
    }
   ]
  },
  {
   "statement": "The literature supports separating response/anaphor detection, antecedent selection, attachment, and relation labeling while allowing information to flow between them, because errors arise at each stage and joint modeling can improve structurally coupled decisions.",
   "confidence": "MEDIUM",
   "evidence": [
    {
     "paper_id": "manual-b0133009f6",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-18653-v1-s15-1035",
     "section": "Key findings"
    },
    {
     "paper_id": "2306.15103",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-18653-v1-2023-eacl-main-247",
     "section": "Key findings"
    },
    {
     "paper_id": "doi-10-18653-v1-p17-1009",
     "section": "Key findings"
    }
   ]
  }
 ],
 "contradictions": [
  {
   "topic": "Locality of antecedents and answers",
   "papers": [
    "doi-10-18653-v1-2022-emnlp-main-778",
    "manual-e1981ecd9a",
    "doi-10-3115-1220355-1220483",
    "2403.16609",
    "doi-10-18653-v1-d15-1109"
   ],
   "note": "Dialogue discourse-deixis and clarification studies report very strong locality, whereas email and multi-thread dialogue document semantically valid links to older material. This is best interpreted as genre and relation dependence rather than a factual contradiction; it argues against a universal hard recency window."
  },
  {
   "topic": "Stack-shaped versus partially ordered issue structure",
   "papers": [
    "doi-10-3765-sp-5-6",
    "doi-10-15398-jlm-v4i2-173"
   ],
   "note": "The QUD framework models unresolved questions with a stack, while the query-response analysis argues that some response classes require multiple simultaneously accessible issues organized as a partial order. For msgloom, the latter warns against assuming strict last-in-first-out resolution when several work questions remain active."
  },
  {
   "topic": "Tree-constrained discourse attachment versus genuine multi-parent structure",
   "papers": [
    "2306.15103",
    "doi-10-18653-v1-2023-eacl-main-247",
    "doi-10-18653-v1-d15-1109",
    "doi-10-5087-dad-2020-104"
   ],
   "note": "A globally structured spanning-tree parser achieves strong benchmark results, but several STAC-based studies explicitly document multi-parent and non-tree relations. The conflict is between useful modeling constraint and representational completeness, not between the empirical observations themselves."
  },
  {
   "topic": "One-to-one alignment assumptions versus observed one-to-many response scope",
   "papers": [
    "doi-10-1109-icaicta63815-2024-10762999",
    "doi-10-1609-aaai-v33i01-3301134",
    "doi-10-3233-aic-2012-0516"
   ],
   "note": "The assembly-minutes work uses a one-to-one alignment algorithm and still shows substantial residual alignment error with gold segmentation, whereas customer-service and email studies explicitly observe one answer aligned to multiple questions. The evidence cautions against imposing one-to-one matching unless the domain annotation contract guarantees it."
  },
  {
   "topic": "Usefulness of syntactic constraints",
   "papers": [
    "1706.02256",
    "doi-10-3115-v1-d14-1056",
    "manual-555fa5b6e8"
   ],
   "note": "Syntactic information helps some shell-noun configurations but hurts broader unrestricted abstract-anaphora transfer, and more elaborate event-antecedent syntactic expansions can add noise. The consistent interpretation is that syntax is useful as a selective feature, not a universally reliable hard constraint."
  }
 ],
 "gaps": [
  {
   "id": "gap-1",
   "description": "Direct empirical evidence is still missing for proposition-level agreement, rejection, approval, clarification, and answer scope in authentic workplace email or enterprise chat, especially short responses applying to only part of a preceding message. Existing workplace-email studies primarily cover question-answer linkage, while proposition-sensitive acceptance/rejection evidence comes from broader dialogue work [doi-10-1145-3209978-3210046] [doi-10-3115-1220355-1220483] [doi-10-1177-002383099603900306].",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"partial reply\" OR \"response scope\" email workplace dialogue proposition agreement rejection approval"
  },
  {
   "id": "gap-2",
   "description": "A validated combined msgloom annotation and evaluation scheme is still missing for exact proposition/span targets with exact, partial, ambiguous, unsupported, discontinuous, multiple-antecedent, composite, and explicit no-link outcomes. The literature validates many ingredients separately but not the combined workplace contract [manual-e4d6ad7ca1] [manual-be69c3aa17] [doi-10-5210-dad-2023-201] [2403.16609].",
   "classification": "ENGINEERING",
   "priority": "HIGH"
  },
  {
   "id": "gap-3",
   "description": "Direct evidence for multi-question partial replies is now materially stronger, including email cases where only a subset of questions is answered and answer sentences can map to several questions, but the corpus still does not fully validate proposition-level handling of mixed workplace questions, requests, and alternatives together or a complete unresolved-subquestion detector [manual-849c5f1c6d] [doi-10-3233-aic-2012-0516] [doi-10-3115-1220355-1220483].",
   "classification": "ACADEMIC",
   "priority": "HIGH",
   "suggested_query": "\"multiple questions\" \"partial answer\" dialogue email question answer alignment unanswered subquestions"
  },
  {
   "id": "gap-4",
   "description": "It remains open how authentic workplace systems should distinguish one response independently targeting several antecedent propositions from one response targeting a single composite multi-proposition discourse object. Both structures are supported in dialogue and abstract-reference research, but direct workplace evaluation of this distinction is missing [doi-10-1609-aaai-v33i01-3301134] [doi-10-5087-dad-2020-104] [doi-10-1515-ling-2018-0008] [doi-10-18653-v1-d15-1109].",
   "classification": "ACADEMIC",
   "priority": "MEDIUM",
   "suggested_query": "\"multi-antecedent\" dialogue response \"composite antecedent\" proposition discourse email"
  },
  {
   "id": "gap-5",
   "description": "The msgloom policy for abstention, ambiguity, missing antecedents, and asymmetric error costs remains unvalidated. Explicit no-link, ambiguous alternatives, future-context dependence, and partial-credit scoring are supported, but no paper establishes thresholds appropriate to the product cost of inventing an approval or commitment versus leaving a link unresolved [2403.16609] [manual-e4d6ad7ca1] [doi-10-3115-1708376-1708429] [doi-10-5210-dad-2023-201].",
   "classification": "ENGINEERING",
   "priority": "HIGH"
  }
 ],
 "actionable_insights": [
  "Represent semantic response structure below the message level: segment candidate questions, propositions, requests, conditions, and decisions, then allow each response span to link to zero, one, or multiple antecedent spans [manual-849c5f1c6d] [doi-10-1609-aaai-v33i01-3301134] [doi-10-18653-v1-d15-1109].",
  "Make unresolved/no-link a first-class outcome. Never force every response onto an antecedent or mark every earlier question closed merely because a later message exists [doi-10-3115-1220355-1220483] [doi-10-3115-1708376-1708429] [doi-10-15398-jlm-v4i2-173].",
  "For a multi-question turn, first classify the internal relationship among components—independent/collateral, reformulation, particularization, repair, or replacement—before creating separate open obligations [doi-10-1016-j-pragma-2007-07-011] [doi-10-1515-text-2003-021] [doi-10-1016-j-pragma-2018-03-015].",
  "Support both multiple independent antecedent edges and a composite-antecedent object; do not collapse the two representations because the literature provides evidence for each [doi-10-5087-dad-2020-104] [doi-10-1515-ling-2018-0008] [doi-10-18653-v1-2023-eacl-main-247].",
  "Store ambiguity explicitly as candidate antecedent sets or alternative analyses rather than selecting a single target when annotators or context cannot distinguish them [2403.16609] [manual-be69c3aa17] [manual-e4d6ad7ca1].",
  "Use recency and thread structure as ranking features, not hard semantic constraints; asynchronous email can answer material several messages back and dialogue can contain crossing thread dependencies [doi-10-3115-1220355-1220483] [doi-10-18653-v1-d15-1109].",
  "Evaluate at proposition/link level with exact-match and partial-overlap measures, explicit zero-link scoring, multi-antecedent partial credit, and separate false-positive and false-negative counts [doi-10-5210-dad-2023-201] [manual-7743c50805] [manual-e4d6ad7ca1].",
  "Weight over-broad positive links separately from unresolved links in engineering evaluation, because the academic literature establishes ambiguity and no-link cases but does not determine msgloom's asymmetric business cost function [2403.16609] [doi-10-3115-1708376-1708429].",
  "Keep missing-context failures distinct from semantic-resolution failures: when the antecedent is absent from supplied evidence, preserve the unresolved reference for Topic 07 rather than hallucinating a target; discourse studies explicitly contain cases with no identifiable linguistic antecedent or interpretation dependent on later context [doi-10-1093-jos-17-1-51] [2403.16609].",
  "Use component-level error analysis for response detection, antecedent selection, attachment, relation labeling, and scope classification even if the implementation later trains some components jointly [manual-b0133009f6] [doi-10-18653-v1-s15-1035] [2306.15103]."
 ],
 "confidence_summary": "Confidence is HIGH that msgloom needs proposition-level, zero-or-many, non-adjacent, ambiguity-preserving response links and explicit unresolved-question state because these requirements recur across email, customer-service, dialogue-discourse, question-response, and abstract-anaphora studies [doi-10-3115-1220355-1220483] [doi-10-1609-aaai-v33i01-3301134] [2403.16609] [doi-10-1162-coli-a-00327]. Confidence is MEDIUM for transferring specific parsing architectures or locality assumptions across domains [2306.15103] [doi-10-18653-v1-2022-emnlp-main-778]. Confidence is LOW-to-MEDIUM for claims about real workplace proposition-level approval/rejection scope because that exact target remains sparsely studied; the strongest direct workplace evidence concerns QA alignment rather than approval or commitment semantics [doi-10-1145-3209978-3210046] [doi-10-3115-1708376-1708429].",
 "limitations": [
  "The corpus contains much stronger direct evidence for question-answer alignment than for workplace approval, rejection, agreement, condition, or clarification scope; transferring the latter from general dialogue remains indirect [doi-10-1177-002383099603900306] [doi-10-1145-3209978-3210046].",
  "Several strong structural results come from task-oriented, game, interview, parliamentary, forum, or customer-service dialogue rather than authentic enterprise email or Teams-style communication [2306.15103] [doi-10-5087-dad-2020-104] [doi-10-1109-icaicta63815-2024-10762999].",
  "The supplied per-paper material is reduced to research questions and top findings, so this synthesis cannot independently inspect annotation manuals, error categories, dataset sampling, or detailed experimental sections beyond those summaries.",
  "Some papers address discourse deixis or abstract anaphora rather than replies themselves; they support antecedent representation, ambiguity, and span evaluation but do not establish workplace reply-scope accuracy [doi-10-1162-coli-a-00327] [manual-e4d6ad7ca1].",
  "Reported metrics are not directly comparable because tasks range from answer alignment and discourse attachment to anaphora resolution and thread-level unresolved-discussion classification [doi-10-1609-aaai-v33i01-3301134] [2306.15103] [doi-10-1007-s10489-013-0481-1].",
  "The literature does not quantify msgloom's asymmetric downstream harm from a false broad approval/commitment link versus an unresolved link, so production decision thresholds cannot be derived from these papers [2403.16609] [doi-10-5210-dad-2023-201]."
 ],
 "gap_status": [
  {
   "id": "gap-1",
   "status": "open",
   "note": "The corpus adds useful direct workplace-email QA evidence and strong general-dialogue evidence for proposition-sensitive acceptance/rejection, but no included study directly validates exact partial agreement, rejection, approval, clarification, and answer scope together in authentic workplace email or enterprise chat.",
   "evidence": [
    "doi-10-1145-3209978-3210046",
    "doi-10-3115-1220355-1220483",
    "doi-10-3115-1708376-1708429",
    "doi-10-1177-002383099603900306"
   ]
  },
  {
   "id": "gap-2",
   "status": "open",
   "note": "The corpus supports nearly every required representational ingredient separately, including exact spans, ambiguity, alternative antecedents, multi-antecedents, no-link outcomes, and partial-credit scoring, but does not validate the combined msgloom annotation/evaluation contract.",
   "evidence": [
    "manual-e4d6ad7ca1",
    "manual-be69c3aa17",
    "doi-10-5210-dad-2023-201",
    "2403.16609",
    "doi-10-3115-1708376-1708429"
   ]
  },
  {
   "id": "gap-3",
   "status": "open",
   "note": "The new corpus materially narrows this gap: direct email evidence shows multi-question messages, incomplete first replies, unanswered questions, and one answer linked to multiple questions. It still does not fully close the broader workplace requirement covering mixed questions, requests, alternatives, and complete proposition-level unresolved-subquestion detection.",
   "evidence": [
    "manual-849c5f1c6d",
    "doi-10-3233-aic-2012-0516",
    "doi-10-3115-1220355-1220483",
    "doi-10-1016-j-pragma-2010-04-002"
   ]
  },
  {
   "id": "gap-4",
   "status": "open",
   "note": "The corpus now strongly establishes both multi-parent response links and composite abstract antecedents, including one-to-many QA alignment, but does not directly evaluate the semantic distinction between independent multiple targets and one composite multi-proposition target in authentic workplace communication.",
   "evidence": [
    "doi-10-1609-aaai-v33i01-3301134",
    "doi-10-5087-dad-2020-104",
    "doi-10-1515-ling-2018-0008",
    "doi-10-18653-v1-d15-1109",
    "doi-10-18653-v1-2023-eacl-main-247"
   ]
  },
  {
   "id": "gap-5",
   "status": "open",
   "note": "Explicit ambiguity, no-link states, later-context dependence, and partial-credit evaluation are empirically supported, but the literature does not establish msgloom-specific confidence thresholds, abstention rules, or asymmetric costs for over-broad commitments versus unresolved links.",
   "evidence": [
    "2403.16609",
    "manual-e4d6ad7ca1",
    "doi-10-3115-1708376-1708429",
    "doi-10-5210-dad-2023-201"
   ]
  }
 ]
}

Per-paper analyses (reduced to questions and top findings to fit the size cap):
[
 {
  "paper_id": "1706.02256",
  "title": "A Mention-Ranking Model for Abstract Anaphora Resolution",
  "research_question": "Can a neural mention-ranking model trained largely on automatically generated data learn to rank clause-like antecedents for abstract anaphors and transfer to shell-noun and unrestricted abstract-anaphora benchmarks?",
  "key_findings": [
   "The mention-ranking LSTM reaches substantially higher success-at-1 results than the compared earlier shell-noun method for the evaluated shell nouns, although the amount of gain varies by noun and tuning condition.",
   "On ARRAU-AA, model variants perform strongly for nominal anaphors, with a reported success-at-1 of 51.89 for the best listed nominal configuration compared with 40.10 for the syntactic-tag baseline.",
   "Pronominal abstract anaphora remains markedly harder: the neural configurations reach at most about 28.57 success-at-1 in the reported table, below the syntactic-tag baseline's 35.17.",
   "Explicit syntactic information helps on the shell-noun task but can hurt on the broader ARRAU-AA task; removing or disrupting syntactic information yields substantially better ARRAU-AA ranking results.",
   "Automatically generated training instances can transfer to naturally occurring abstract-anaphora cases despite a substantial mismatch between the artificial training distribution and the unrestricted evaluation data."
  ]
 },
 {
  "paper_id": "2306.15103",
  "title": "Structured Dialogue Discourse Parsing",
  "research_question": "Can dialogue discourse parsing be improved by globally and jointly learning discourse links and relation labels as a structured labeled multi-root non-projective spanning tree rather than making independent local decisions?",
  "key_findings": [
   "The proposed parser reaches LAS 59.6 on STAC and 59.9 on Molweni, improving over the previous best results by 2.3 and 1.5 points respectively.",
   "In cross-domain evaluation, the method obtains LAS 38.0 for STAC-to-Molweni and 31.6 for Molweni-to-STAC, beating the best compared baselines by 5.1 and 4.8 points respectively, although it is not best on cross-domain UAS.",
   "The structured parser's performance degrades less than baseline parsers as dialogues become longer.",
   "The structured method improves correct predictions for relations including QA_pair and Comment on STAC and QA_pair and Clarification Question on Molweni, while low-resource relations remain difficult.",
   "Removing speaker and turn information reduces STAC LAS from 59.6 to 54.4 for the proposed parser, compared with 57.3 to 47.8 for the Struct-Aware baseline."
  ]
 },
 {
  "paper_id": "2403.16609",
  "title": "Conversational Grounding: Annotation and Analysis of Grounding Acts and Grounding Units",
  "research_question": "How can natural task-oriented dialogues be annotated in terms of grounding acts, common grounding units, and degrees of grounding, and how effectively can a baseline transformer model predict those structures?",
  "key_findings": [
   "A single utterance can participate in multiple Common Grounding Units, so the annotation explicitly permits one response to have distinct relations to several simultaneously active discourse units.",
   "The paper documents a direct multi-question scope ambiguity: after three successive questions, a negative response could not be reliably assigned to any one question, so the associated grounding was labeled ambiguous even though the interaction moved on.",
   "Grounding is not irrevocable: an already grounded CGU may be reopened by repair or acknowledgment requests, and a proposer can also revoke information from the grounded set.",
   "Written chat contained non-linear and multi-threaded response behavior in which a later utterance answered an older contribution rather than the immediately preceding material, demonstrating that simple nearest-turn linkage is insufficient.",
   "The annotations sometimes require future context: annotators revised 23 Meetup cases after seeing later utterances, and 171 Spot the Difference cases were marked as requiring subsequent utterances for correct interpretation."
  ]
 },
 {
  "paper_id": "doi-10-1007-bf00351935",
  "title": "Syntax and Semantics of Questions",
  "research_question": "How can a Montague-style grammar provide a compositional and substantially unified account of the syntax and semantics of yes-no, alternative, single-wh, and multiple-wh questions and their behavior under question-embedding predicates?",
  "key_findings": [
   "The paper analyzes the denotation of a question as a set of propositions that together constitute its true and complete answer rather than as an undifferentiated set of all possible answers.",
   "Alternative questions and wh-questions can be assigned the same broad semantic type, with yes-no questions treated as a limiting form of alternative question.",
   "Wh expressions can retain semantic types closely related to corresponding existential noun phrases while special syntactic rules derive their interrogative scope.",
   "The compositional rules extend from single-wh to multiple-wh questions and provide representations for differences in quantifier scope.",
   "Question-embedding predicates motivate a semantics in which their complements supply answer propositions rather than simply ordinary propositional objects."
  ]
 },
 {
  "paper_id": "doi-10-1007-bf00983299",
  "title": "Resolving questions, II",
  "research_question": "How should a formal semantics distinguish questions, propositions, and facts while explaining the shared semantic relations that allow facts to resolve questions and prove propositions?",
  "key_findings": [
   "The paper argues for an ontology that distinguishes propositions, questions, and facts instead of reducing these categories to a single type of semantic object.",
   "Despite this ontological distinction, the analysis identifies a common role for facts: facts can prove propositions and resolve questions.",
   "The proposed relation between facts and propositions/questions is used to explain why predicates such as know carry factive presuppositions.",
   "The framework is also applied to the behavior of adverbially modified predicates when their arguments are interrogatives, declaratives, or fact-denoting nominals.",
   "In the broader two-part theory summarized by the abstract, a question is not reductively identified with its answers, allowing question resolution to depend on contextual parameters such as conversational goals and inferential capabilities."
  ]
 },
 {
  "paper_id": "doi-10-1007-s10489-013-0481-1",
  "title": "Towards identifying unresolved discussions in student online forums",
  "research_question": "Can message-level forum speech acts and the resulting thread-level discourse structures be used to identify student discussions containing unanswered questions, confusion, or unresolved issues?",
  "key_findings": [
   "The proposed representation explicitly records whether a question in a discussion thread was followed by an answer, making unanswered-question status a modeled discourse property rather than merely a lexical property of individual messages.",
   "Forum speech acts distinguish communicative roles such as questions, issue raising, and answers before thread-level classification is performed.",
   "The approach uses combinations of message-level speech acts to represent larger discourse structures and then uses those structures to identify discussions with unresolved issues or unanswered questions.",
   "The reported discussion-thread classifiers achieved accuracies ranging from 0.79 to 0.87 across several classification problems.",
   "The accessible abstract does not establish that the method distinguishes a fully answered question from a partially answered multi-proposition question."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-pragma-2007-07-011",
  "title": "Multiple questions in oral proficiency interviews",
  "research_question": "What interactional circumstances motivate interviewers in oral proficiency interviews to produce repeated or multiple questions, and how do reactive and proactive multiple-question sequences function in managing candidate comprehension?",
  "key_findings": [
   "Interviewers frequently use multiple questions on the same topic both to prevent potential comprehension problems and to react to problems that have already become visible.",
   "Reactive or vertical multiple questions are sequentially tied to immediate problems in the candidate's uptake of the preceding question.",
   "The reactive environments identified include repair sequences, missing rejoinders, and problematic answers.",
   "Proactive or horizontal multiple questions occur in interactional environments judged fragile, where the probability of mishearing is comparatively high.",
   "Because multiple questions may be repetitions or reformulations serving comprehension management, the presence of several interrogatives does not by itself imply several independent answer obligations."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-pragma-2010-04-002",
  "title": "A coding scheme for question–response sequences in conversation",
  "research_question": "How can naturally occurring question-response sequences be operationalized with a coding scheme that permits systematic cross-linguistic comparison?",
  "key_findings": [
   "The scheme explicitly marks a 'through-produced' multi-question when two or more questions are delivered as one query in a single turn.",
   "The authors state that through-produced multi-questions require separate treatment because they can mix polar and content questions and the response often answers only one component question.",
   "Question responses are coded separately as no response, a non-answer response, an answer, or indeterminate, allowing unanswered questions to be distinguished from indirect or evasive responses.",
   "For polar questions that receive an answer, the scheme codes whether the answer confirms or disconfirms the questioned proposition rather than equating confirmation mechanically with the words yes or no.",
   "Polar-answer form distinguishes repetitions from interjections and marked interjections, and the repetition category includes partial as well as full repeats of the antecedent question."
  ]
 },
 {
  "paper_id": "doi-10-1016-j-pragma-2018-03-015",
  "title": "‘But what is the reason why you know such things?’: Question and response patterns in the LADO interview",
  "research_question": "What recurrent question-response and repair patterns create interactional problems in LADO interviews, and how might those problems be avoided or resolved?",
  "key_findings": [
   "When an interviewer bundled a broad directive with more specific questions, interviewees generally answered the most specific and/or most recent question rather than carrying out the broader directive.",
   "Sequential analysis shows that an apparently unanswered broad question can result from the interviewer immediately narrowing it to a yes/no or otherwise specific question, leaving no interactional opportunity to answer the original request.",
   "Directives intended to elicit language samples worked more effectively when the interviewer supplied a concrete topic for extended talk rather than issuing an underspecified request to speak.",
   "Echo questions were predominantly treated as confirmation requests and could therefore fail when interviewers intended them as prompts for elaboration or repair initiators.",
   "Questions framed as challenges, including negative questions, source-of-knowledge challenges, turn-initial but, and hostile reformulations, contributed to confrontational interaction while producing little apparent information-gathering benefit."
  ]
 },
 {
  "paper_id": "doi-10-1093-jos-17-1-51",
  "title": "Dialogue Acts, Synchronizing Units, and Anaphora Resolution",
  "research_question": "How can pronouns and demonstratives in spontaneous spoken dialogue be classified and resolved when their antecedents may be noun phrases, sentential discourse material, or not linguistically identifiable?",
  "key_findings": [
   "Fewer than half of the analyzed pronouns and demonstratives have noun-phrase antecedents in the preceding discourse.",
   "Approximately 22% of the analyzed pronouns and demonstratives have sentential antecedents, showing that proposition-like discourse material is an empirically important antecedent class.",
   "The remaining analyzed pronouns and demonstratives include cases with no identifiable linguistic antecedent.",
   "Inter-annotator agreement experiments for anaphor typing, antecedent identification, and dialogue-act segmentation were reported to support the reliability of the annotation method.",
   "The proposed resolver handles both noun-phrase and sentential antecedents rather than restricting antecedent search to nominal expressions."
  ]
 },
 {
  "paper_id": "doi-10-1109-icaicta63815-2024-10762999",
  "title": "Automatic Question-Answer Alignment for Japanese Diverse Local Assembly Minutes",
  "research_question": "Can a two-stage segmentation-and-alignment pipeline trained largely on Tokyo assembly minutes robustly recover question-answer correspondences in local assemblies with different linguistic and discourse conventions?",
  "key_findings": [
   "On Anjo question segmentation, supervised BERT improved F1 from 0.55 for the Tokyo-specific regular expressions to 0.69.",
   "On Anjo answer segmentation, supervised BERT improved over the regular-expression baseline from F1 0.38 to 0.48, although LCseg performed better at F1 0.57.",
   "For complete QA alignment on the Anjo minutes, the supervised-BERT segmentation pipeline achieved precision 0.60, recall 0.41, and F1 0.48, compared with 0.30, 0.32, and 0.31 for regular-expression segmentation.",
   "The authors report that supervised segmentation raised Anjo QA-alignment F1 by 0.17, recall by 0.09, and precision by 0.30 relative to the regular-expression pipeline.",
   "Even when gold segmentation was supplied on Anjo, the one-to-one alignment algorithm reached only recall 0.55 and F1 0.68, showing that segmentation errors were not the only bottleneck."
  ]
 },
 {
  "paper_id": "doi-10-1145-3209978-3210046",
  "title": "Characterizing and Supporting Question Answering in Human-to-Human Communication",
  "research_question": "How do information workers exchange and later retrieve question-answer information in enterprise email, and can corresponding answers in email threads be automatically identified?",
  "key_findings": [
   "Question-answer information is a frequent workplace-email retrieval need: 98.7% of surveyed respondents reported needing to locate an answer from their mailbox at least once in the preceding month.",
   "The constructed QA dataset contains 1,695 unique question sentences, each paired with ten candidate answer paragraphs, with one or more candidates allowed to be relevant.",
   "Selecting the paragraph or paragraphs that answer a question was substantially more subjective than recognizing questionhood: reported inter-annotator agreement was 0.48 for answer selection versus 0.91 for question validity.",
   "The operational QA unit is an individual extracted question sentence matched to answer paragraphs independently, rather than a joint representation of all propositions or subquestions in an email.",
   "The proposed neural matching model outperformed TF-IDF, BiMPM, and decomposable attention on Avocado QA, reaching MAP 48.95 and average recall 82.34 before external pretraining."
  ]
 },
 {
  "paper_id": "doi-10-1162-coli-a-00327",
  "title": "Anaphora With Non-nominal Antecedents in Computational Linguistics: a Survey",
  "research_question": "What linguistic properties, annotation practices, computational approaches, resources, and unresolved problems characterize anaphora whose antecedents are non-nominal and denote abstract entities such as events, facts, situations, or propositions?",
  "key_findings": [
   "Non-nominal anaphora is computationally difficult because potential antecedents have diverse syntactic forms, the candidate space is large, antecedent boundaries can be unclear, and ordinary nominal-coreference features such as gender and number are generally unavailable.",
   "The referent evoked from the same linguistic antecedent can be interpreted at different semantic types, such as an event, proposition, or fact, and the predication context of the anaphor provides important constraints on that interpretation.",
   "Precisely delimiting non-nominal antecedent spans is a central annotation problem and is associated with low or only moderate inter-annotator agreement in several annotation efforts.",
   "Only a limited number of annotated corpora reviewed by the survey are reusable, and many available corpora are small for supervised machine-learning purposes.",
   "Older rule-based resolution approaches often remain competitive with statistical approaches, motivating combinations of explicit linguistic knowledge with modern data-driven representations."
  ]
 },
 {
  "paper_id": "doi-10-1177-002383099603900306",
  "title": "Inferring Acceptance and Rejection in Dialogue by Default Rules of Inference",
  "research_question": "How can conversational participants infer acceptance or rejection of assertions and proposals when responses are indirect, logically consistent with what they reject, or only partially accept the preceding propositional content?",
  "key_findings": [
   "Logical consistency is necessary but not sufficient for interpreting a response as acceptance, while logical inconsistency is sufficient but not necessary for interpreting a response as rejection.",
   "A reply can accept an entailed subproposition of a preceding assertion while rejecting the stronger assertion, so acceptance and rejection scope can differ within the same antecedent proposition.",
   "The corpus analysis motivates three rejection classes beyond straightforward denial, contradiction, and refusal: implicature rejections, epistemic rejections, and deliberation rejections.",
   "A less informative reply can reject only the omitted or replaced portion of a stronger antecedent through scalar implicature rather than rejecting every proposition entailed by the antecedent.",
   "Information structure and prosody help distinguish a partial repetition functioning as acceptance from a superficially similar logically consistent utterance functioning as rejection; acceptances tend to re-realize focal material as old information, whereas implicature rejections substitute a scalarly related focal item."
  ]
 },
 {
  "paper_id": "doi-10-1515-ling-2018-0008",
  "title": "Resolving abstract anaphors in Spanish discourse: Underspecification and mereological structures",
  "research_question": "How can hearers resolve an abstract anaphor when several individual propositions, events, or a merged multi-proposition discourse segment are all plausible antecedents?",
  "key_findings": [
   "Abstract anaphors can be underspecified among multiple higher-order antecedents, including individual propositions, events, and larger multi-sentence discourse segments.",
   "The candidate set for an abstract anaphor can be represented mereologically so that atomic propositions and one or more merged complex abstract referents remain simultaneously available as possible interpretations.",
   "The paper proposes a three-step resolution process: construct a mereological set of possible antecedents, infer rhetorical relations among its propositions, and select the preferred antecedent for the anaphor.",
   "When several thematically connected propositions can be integrated into a coherent rhetorical unit, their merged interpretation is proposed to be preferred over its individual component propositions.",
   "Rhetorical structure can determine proposition-level antecedent scope: a sequence connected by Continuation can form the merged referent of an anaphor while a nearby proposition connected by a different relation can remain outside that referent."
  ]
 },
 {
  "paper_id": "doi-10-1515-text-2003-021",
  "title": "Multi-unit questions in institutional interactions: Sequential organizations and communicative functions",
  "research_question": "What recurrent internal organizations, sequential conditions, and communicative functions characterize multi-unit questioning turns in institutional interaction?",
  "key_findings": [
   "The combined corpora contain 374 multi-unit questioning turns, representing about 16% of all questioning turns, and about 90% of questioning turns are produced by the institutional professional.",
   "Multi-unit questions frequently narrow an initially broader inquiry through particularizing follow-up components; in Hofvendahl's coded component questions, 81% (101 of 124) had a particularizing relation to the preceding head question, compared with 11% generalizing and 7% metacommunicative.",
   "The paper identifies collateral questions as distinct questions delivered together without a particularizing, generalizing, or paraphrasing relation, usually linked by an explicit or implicit common super-topic.",
   "Component questions can remain unanswered during construction of a multi-unit turn: in one analyzed case the initial broad question receives no response and is subsequently replaced or pursued with more specific component questions.",
   "A negative response to one component can occasion production of another collateral component, showing that the evolving scope and content of the question package can depend on the recipient's partial response."
  ]
 },
 {
  "paper_id": "doi-10-15398-jlm-v4i2-173",
  "title": "Query responses",
  "research_question": "What functional kinds of query-as-response occur in dialogue, how common are they, and what contextual or information-state structures are needed to characterize them?",
  "key_findings": [
   "Query-to-query responses are common in the spoken BNC: the authors report 9,279 query-query cross-turn sequences against 41,041 query-declarative sequences, corresponding to their reported 22.61% ratio.",
   "The corpus yielded seven functional response classes; clarification requests dominated the sample, while dependent questions were the largest non-clarification class, accounting for 49.31% after clarification requests were excluded.",
   "Whether the original query was eventually answered depended strongly on response class: the original query was answered in only 11.54% of NO ANSW cases and 16.67% of IGNORE cases, compared with 81.25% of FORM cases and 100% of IND cases.",
   "The NO ANSW and IGNORE classes provide direct empirical evidence that a locally coherent response can leave the preceding question unresolved rather than answering it.",
   "The formal treatment of MOTIV and NO ANSW requires multiple issues to remain simultaneously accessible, motivating a partially ordered QUD rather than a simple stack, while clarification and IGNORE additionally require participant-specific dialogue gameboards and a buffer for ungrounded utterances."
  ]
 },
 {
  "paper_id": "doi-10-15760-mcnair-2019-13-1-2",
  "title": "Abstract Pronominal Anaphora in Three Registers of English",
  "research_question": "How do the distribution, referential functions, pronoun choices, and non-nominal antecedent properties of abstract pronominal anaphora vary across newswire, spontaneous dialogue, and planned speech?",
  "key_findings": [
   "The frequencies of different referential functions vary across the three registers.",
   "Pronoun choice and the referential function served by a pronoun vary by register.",
   "The grammatical structures of non-nominal antecedents vary across the text types.",
   "The difficulty of annotating the relevant anaphoric phenomena varies across the material studied.",
   "The authors conclude that spoken discourse exhibits a range of pronominal reference and non-nominal antecedent patterns that may not be recoverable from even very large newswire collections."
  ]
 },
 {
  "paper_id": "doi-10-1609-aaai-v33i01-3301134",
  "title": "Learning to Align Question and Answer Utterances in Customer Service Conversation with Recurrent Pointer Networks",
  "research_question": "Can recurrent pointer-network models align each customer-service answer utterance with zero, one, or multiple preceding customer question utterances while exploiting conversational context and dependencies among alignments?",
  "key_findings": [
   "The empirical data contain substantial non-bijective structure: None alignments account for 57% of answer utterances and One-to-Many alignments account for 12%, while an answered server utterance aligns to 1.38 customer questions on average when None cases are excluded.",
   "The strongest reported RPN configuration, Model-II with regression loss, obtained overall precision 84.22%, recall 85.51%, and F1 84.86%, compared with F1 79.5% for the SHCNN+CISIR comparison system.",
   "Model-II with regression loss achieved F1 94.07% on Empty alignments, exceeding the 91.1% F1 of the discriminative comparison system highlighted by the authors.",
   "For One-to-Many cases, Model-II with regression loss achieved precision 91.51%, recall 71.67%, and F1 80.39%, compared with F1 76.27% for SHCNN+CISIR.",
   "Regression loss handled One-to-Many alignment better than the classification formulation in Model-II, with F1 80.39% versus 76.38%, which the authors attribute to avoiding a difficult conversation-dependent threshold."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2021-codi-sharedtask-1",
  "title": "The CODI-CRAC 2021 Shared Task on Anaphora, Bridging, and Discourse Deixis in Dialogue",
  "research_question": "How can identity anaphora, bridging reference, and discourse deixis in conversational dialogue be benchmarked across multiple dialogue genres, and what performance do contemporary systems achieve under common evaluation conditions?",
  "key_findings": [
   "The shared task establishes a multi-genre benchmark for three distinct kinds of dialogue anaphora: identity, bridging, and discourse deixis.",
   "The newly annotated portion of the CODI-CRAC 2021 corpus contains 147,725 tokens, 41,807 markables, and 1,097 discourse-deixis instances across four dialogue datasets.",
   "For predicted-mention discourse deixis, UTD_NLP obtains CoNLL average F1 scores between roughly 35 and 42 across the four sub-corpora, substantially ahead of the second submitted system.",
   "In the discourse-deixis track, every submitted system reported in the evaluation outperforms the simple baseline on every sub-corpus.",
   "Providing gold markables does not substantially improve the leading discourse-deixis system on LIGHT, AMI, or SWITCHBOARD, but raises its PERSUASION score by more than 12 CoNLL average F1 points."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2021-naacl-main-329",
  "title": "Stay Together: A System for Single and Split-antecedent Anaphora Resolution",
  "research_question": "Can split-antecedent anaphora be resolved jointly with ordinary single-antecedent anaphora, singleton detection, and non-referring mention recognition in an end-to-end system that uses predicted rather than gold mentions?",
  "key_findings": [
   "Both proposed end-to-end variants substantially outperform prior naive or pipeline-style baselines on split-antecedent recognition and resolution when mentions are predicted.",
   "The pre-trained variant achieves a split-anaphor recognition F1 of 55.1 and a strict split-resolution F1 of 20.4, while the joint variant obtains 50.9 and 15.3 respectively.",
   "Joint optimization does not improve the ordinary single-antecedent and non-referring parts of the system; the pre-trained configuration gives slightly better overall performance on those aspects.",
   "With gold mentions and gold split anaphors, the proposed resolver reaches 68.1 lenient F1 and 45.0 strict accuracy, exceeding the compared earlier system's best reported 66.4 lenient F1 and 35.0 strict accuracy.",
   "A major end-to-end bottleneck is candidate and anaphor identification: predicted mentions cover 98.33 percent of gold split anaphors, but only 65 percent survive the discourse-new candidate restriction, and the pre-trained system recognizes 45 percent of the gold split anaphors."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2022-emnlp-main-778",
  "title": "End-to-End Neural Discourse Deixis Resolution in Dialogue",
  "research_question": "Can an end-to-end neural coreference architecture be adapted with dialogue- and discourse-deixis-specific modeling to improve resolution of anaphors whose antecedents denote utterance-level events, propositions, descriptions, or speech acts?",
  "key_findings": [
   "The proposed dd-utt system achieved a substantially higher average discourse-deixis resolution score than the shared-task system and the two coreference baselines across the four evaluation datasets.",
   "dd-utt obtained an average CoNLL resolution score of 48.5, compared with 41.2 for coref-hoi-utt, 39.6 for coref-hoi, and 38.3 for the UTD_NLP shared-task system.",
   "The resolution improvement was attributed primarily to better antecedent selection rather than better anaphor recognition, because recognition performance was statistically indistinguishable among the compared systems while resolution improved significantly.",
   "Discourse-deictic antecedents were strongly local in the evaluated dialogue data: more than 90 percent occurred within four utterances of the anaphor, and the immediately preceding utterance was the most common distance.",
   "Among the ten proposed extensions, restricting antecedent candidates using a recency window was the only ablation whose removal produced a statistically significant degradation under the reported test, although several other removals also reduced the numerical score."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2023-eacl-main-247",
  "title": "A simple but effective model for attachment in discourse parsing with multi-task learning for relation labeling",
  "research_question": "Can a relatively simple BERT-based local discourse parser jointly exploit attachment and relation-label information while supporting the multiple-parent structures required by multiparty conversation?",
  "key_findings": [
   "The STAC discourse formalism directly permits a single discourse unit to attach to multiple earlier units, reflecting cases in which one conversational move responds to several prior moves at once.",
   "BERTLine can predict multiple parents rather than forcing a tree, but it recovered only about 20% of the 77 multi-parent structures in the reported test set, including a small number with more than three parents.",
   "Question–Answer-Pair is one of the 16 relation labels represented in the STAC graphs, so question/answer linkage is modeled as one discourse-relation type inside a more general attachment graph.",
   "On standard STAC, BERTLine obtained about 73.1 attachment F1 and 56.25 relation-label F1 and was competitive with or better than the reimplemented neural alternatives, particularly for relation labeling.",
   "Joint multi-task training of attachment and relation labeling improved relation F1 by about one point relative to the authors' pipeline formulation, supporting interdependence between deciding whether units connect and deciding how they connect."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-2023-findings-acl-710",
  "title": "Discourse Analysis via Questions and Answers: Parsing Dependency Structures of Questions Under Discussion",
  "research_question": "Can document-level discourse structure be parsed as dependency links labeled by free-form Questions Under Discussion, using crowdsourced question-answer annotations instead of a fixed discourse-relation taxonomy?",
  "key_findings": [
   "The parser represents each non-root sentence as answering a generated question anchored in exactly one earlier sentence, thereby providing explicit response-to-antecedent dependency links over long document context.",
   "Human judges rated 71.5% of full-system generated questions as fully plausible at the predicted anchor, and among the high-quality-question subset they rated the targeted sentence as a clear answer 78.8% of the time.",
   "The answer-scope evaluation distinguishes a clear at-issue answer from a response whose answer content is not the sentence's main point and from a borderline response that is relevant but may not actually address the question.",
   "For the full model's evaluated high-quality questions, 3.1% of judgments were in the not-main-point category and 10.5% were in the sort-of category, demonstrating measurable ambiguity in whether a sentence fully addresses a QUD.",
   "Reranking and named-entity masking improved question quality; removing reranking reduced fully acceptable Q1 judgments, and removing entity masking produced a much larger decline."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-d15-1109",
  "title": "Discourse parsing for multi-party chat dialogues",
  "research_question": "How can full discourse attachment and relation structure be parsed in multi-party chat when dialogues contain concurrent threads, crossing dependencies, multiple antecedents, and other non-tree structures?",
  "key_findings": [
   "The corpus contains genuine many-to-many discourse alignment: one question can receive several answer attachments, and a later acknowledgment can itself attach to several preceding answers.",
   "Non-tree discourse structures account for at least 9% of links in the corpus, so a representation forcing exactly one tree parent cannot faithfully represent all observed reply and antecedent relations.",
   "Complex Discourse Units can combine several EDUs into a single discourse antecedent; the paper gives an example where two utterances jointly form the antecedent of a conditional relation and notes that some CDUs encompass an entire question-answering session.",
   "Concurrent conversation threads create crossing dependencies, including replies or comments directed to material from another active thread, which makes simple adjacency-based reply alignment inadequate.",
   "The best global parser achieved directed attachment F1 of 0.671, undirected attachment F1 of 0.680, and fully labeled structure F1 of 0.516 on the held-out test corpus."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-p17-1009",
  "title": "Joint Learning for Event Coreference Resolution",
  "research_question": "Can event coreference resolution be improved by jointly learning trigger detection, event anaphoricity, and antecedent selection instead of treating these interdependent tasks as a pipeline?",
  "key_findings": [
   "Joint learning improves event coreference over the independently trained model by 1.80 AVG-F points on English and 1.95 AVG-F points on Chinese.",
   "Joint learning yields particularly large improvements in event anaphoricity determination, increasing F-score by 4.59 points on English and 4.02 points on Chinese relative to independent models.",
   "On English, the joint model exceeds the strongest KBP 2016 system by 3.00 points in average event-coreference F-score and by 2.31 points in trigger-detection F-score.",
   "On Chinese, the joint model exceeds the strongest KBP 2016 system by 1.36 points in average event-coreference F-score and by 0.52 points in trigger-detection F-score.",
   "Coreference-trigger interaction factors make the largest contribution to event-coreference performance among the three modeled interaction types and are also the most effective for improving trigger detection."
  ]
 },
 {
  "paper_id": "doi-10-18653-v1-s15-1035",
  "title": "Resolving Discourse-Deictic Pronouns: A Two-Stage Approach to Do It",
  "research_question": "Can discourse-deictic uses of 'it', 'this', and 'that' first be identified and then resolved to verbal or clausal antecedents well enough to improve general-purpose coreference resolution?",
  "key_findings": [
   "The test data contain 252 discourse-deictic instances among 2,075 occurrences of 'it', 'that', and 'this', with large differences in prevalence by pronoun and especially strong class imbalance for 'it'.",
   "The discourse-deixis classifier achieved 35.2 precision, 42.9 recall, and 38.6 F1 overall, versus 34.8 F1 for the stronger naive classification baseline, although performance remained low because of class imbalance and limited discourse-level features.",
   "With gold discourse-deixis classification, the resolver achieved 48.2 overall F1, compared with 39.3 for the nearest-verb baseline and 41.0 for the Müller-style model.",
   "Using predicted rather than oracle classifications greatly reduced resolution performance to 22.2 overall F1, but the two-stage resolver still outperformed both comparison resolvers under the same condition.",
   "Adding the two-stage predictions to Berkeley and HOTCoref produced small increases in their overall CoNLL scores, from 61.71 to 61.73 and from 61.64 to 61.69 respectively; most tested differences were statistically significant, though the attainable improvement with oracle discourse-deixis information was much larger."
  ]
 },
 {
  "paper_id": "doi-10-3115-1220355-1220483",
  "title": "Detection of Question-Answer Pairs in Email Conversations",
  "research_question": "Can questions and their corresponding answer segments be detected automatically in asynchronous email threads, and do email-thread structural features improve pairing beyond lexical similarity alone?",
  "key_findings": [
   "About 20% of the email threads in the corpus primarily involved question-answer exchanges, including both one-question/multiple-response and multiple-question/multiple-response configurations.",
   "Email reply structure is not a reliable proxy for response scope because a message sent using Reply or Reply-All can semantically answer an issue raised several messages earlier, and multiple topics can proceed in parallel.",
   "The annotation explicitly permits questions with no corresponding answer, so unanswered questions remain present rather than being removed from the annotated question set.",
   "Question-segment identification and question-to-answer linking showed kappa values of 0.68 and 0.81 respectively between the two annotators.",
   "The modified interrogative-question detector achieved precision 0.96, recall 0.72, and F1 0.82 after adding handling for questions preceded by declarative material."
  ]
 },
 {
  "paper_id": "doi-10-3115-1708376-1708429",
  "title": "Contrasting the Interaction Structure of an Email and a Telephone Corpus: A Machine Learning Approach to Annotation of Dialogue Function Units",
  "research_question": "Can a common Dialogue Function Unit annotation scheme represent initiation-response structure in workplace email and telephone dialogue, and how accurately can dialogue acts and response links be predicted in the two modalities?",
  "key_findings": [
   "The annotation scheme permits response relations that are non-adjacent and that originate either from explicit requests or from preceding non-request discourse units, making it more general than a strict adjacent question-answer model.",
   "An explicit request with no matching response is represented as a dangling forward link, providing a direct annotation mechanism for unanswered questions or requests.",
   "Dangling links were proportionally more common in Enron email than in Loqui telephone dialogue, at 7% versus 2% in the reported link statistics.",
   "Only 28% of Enron DFUs participated as first or second parts of links, compared with 63% in Loqui, and Enron links more often involved secondary forward links than overt request-response pairs.",
   "Dialogue-act tagging was substantially easier than response-link prediction: structured-SVM dialogue-act accuracy was 88.71% on Enron and 70.26% on Loqui, while paired-link F1 was 34.88% and 49.38% respectively."
  ]
 },
 {
  "paper_id": "doi-10-3115-v1-d14-1056",
  "title": "Resolving Shell Nouns",
  "research_question": "Can linguistically motivated lexico-syntactic knowledge be used to identify the clauses that supply the semantic content of shell nouns such as fact, idea, reason, and problem?",
  "key_findings": [
   "The resolver without strict shell-noun-family constraints outperformed the lexico-syntactic baseline for every one of the twelve evaluated nouns.",
   "Across all evaluated nouns, the permissive resolver achieved 69 percent accuracy, compared with 57 percent for the baseline and 64 percent for the resolver that enforced Schmid-family constraints.",
   "Family-specific syntactic cues were especially useful for nouns with relatively strict syntactic expectations, including reason and fact.",
   "Strict family-specific cues harmed performance for several syntactically versatile nouns because valid shell-content constructions could fall outside the prototypical patterns.",
   "Individual-noun accuracies varied substantially, ranging from approximately the low sixties to the low eighties for the better system on different nouns, indicating that shell-noun behavior is strongly noun dependent."
  ]
 },
 {
  "paper_id": "doi-10-3233-aic-2012-0516",
  "title": "Detection of imperative and declarative question–answer pairs in email conversations",
  "research_question": "Can interrogative and non-interrogative questions in email be detected and linked to their answers accurately and efficiently at sentence level by exploiting textual, contextual, and thread-structural information?",
  "key_findings": [
   "Non-interrogative questions form a substantial minority of email questions: about 11% of the annotated questions were imperative, 5% declarative, and 4% other, so punctuation-only question detection misses meaningful requests.",
   "The hand-crafted Regex detector achieved 0.959 precision, 0.860 recall, and 0.907 F1 when interrogative and non-interrogative questions were evaluated together, outperforming the tested Naive and S&M methods on F1.",
   "The sentence-level heuristic pairing variants substantially outperformed the S&M and Naive baselines; on the union annotation set, Heuristic-LR obtained 0.5935 LCS F1 compared with 0.5108 for the strongest S&M variant and 0.1544 for Naive.",
   "Human agreement was imperfect but reasonably strong: Fleiss kappa was 0.69 for identifying question paragraphs and 0.77 for linking answers to questions, while the two most prolific annotators reached 0.74 and 0.83 respectively.",
   "A single answer sentence can correspond to several preceding questions; varying the maximum number of questions assigned to an answer modestly improved F1, with three questions per answer performing best on the authors' data."
  ]
 },
 {
  "paper_id": "doi-10-3765-sp-5-6",
  "title": "Information structure in discourse: Towards an integrated formal theory of pragmatics",
  "research_question": "How can discourse information structure be formally represented around questions under discussion so that answerhood, relevance, discourse strategy, and the interpretation of English prosodic focus receive an integrated pragmatic account?",
  "key_findings": [
   "A discourse context can be represented with an explicit QUD stack in addition to the common ground, allowing accepted unresolved questions to constrain subsequent moves.",
   "An assertion is relevant to the current QUD when it contributes at least a partial answer, while a subordinate question is relevant when answering it forms part of a strategy for answering the current QUD.",
   "Discourse strategies are hierarchically organized through questions and subquestions, so a reply can contribute indirectly to a larger conversational goal by resolving a strategically subordinate question.",
   "Accepted assertions update the common ground whereas accepted unresolved questions update the QUD structure, providing different contextual roles for declarative and interrogative moves.",
   "English prosodic focus is analyzed as presupposing congruence between the utterance's focus alternatives and the current QUD, which can also help hearers accommodate an implicit question."
  ]
 },
 {
  "paper_id": "doi-10-5087-dad-2020-104",
  "title": "Modelling Structures for Situated Discourse",
  "research_question": "How should discourse structure be modeled when multiparty linguistic moves interact with nonlinguistic events in a situated environment, including structures that cannot be represented as a simple tree?",
  "key_findings": [
   "Responses can have multiple distinct antecedents: in one analyzed exchange, a single acknowledgement is interpreted as responding jointly to three preceding negative replies.",
   "Such multi-antecedent links are not rare in this corpus: 928 of 12,588 discourse units in the chat-only annotations, about 7%, are classified as truly non-treelike because they receive incoming links from different source units.",
   "The corpus contains simultaneously developing dialogue threads, and even an individual speaker can participate in several independent threads at once.",
   "Offers and their acceptances or refusals are modeled propositionally through Question-Answer Pair relations: a completed trade can function as a yes to an offer, while a trade-panel refusal or rejection functions as a no.",
   "Complex discourse units allow several antecedent events or replies to be treated jointly as the argument of a later relation; for example, an action can be annotated as the result of an entire sequence of failed offers and refusals rather than of one immediately preceding unit."
  ]
 },
 {
  "paper_id": "doi-10-5210-dad-2022-203",
  "title": "Characterizing the Response Space of Questions: data and theory",
  "research_question": "Can a broad empirically grounded taxonomy and formal theory characterize the range of responses that natural-language questions receive across different dialogue genres and languages?",
  "key_findings": [
   "The proposed response taxonomy achieved greater than 99.5% coverage in each of the four English corpora because fewer than 0.5% of responses required the OTHER category.",
   "Direct answers were the largest response category in every corpus, ranging from 54.67% to 88.93% across the English corpora and accounting for 64.27% of Polish Spokes responses.",
   "Task-oriented BEE and MapTask dialogues had higher direct-answer rates than free-conversation BNC and Spokes data, indicating substantial genre dependence in response behavior.",
   "The direct-answer category theoretically allows partial polar answers and partial wh-answers, but these subcategories were not distinguished in the empirical annotation.",
   "Annotation disagreements reveal that partiality can affect response classification: the authors note that some partial responses may have been labeled difficult-to-provide-answer because partial answers were not explicitly highlighted in the guidelines."
  ]
 },
 {
  "paper_id": "doi-10-5210-dad-2023-201",
  "title": "Scoring Coreference Chains with Split-Antecedent Anaphors",
  "research_question": "How can standard coreference evaluation metrics be generalized so that systems receive appropriate partial credit when resolving split-antecedent anaphors and related multi-antecedent discourse deixis?",
  "key_findings": [
   "Partial-credit evaluation is empirically important because only 16% of split antecedents in the ARRAU evaluation were fully resolved by the tested Yu et al. model, while many others were only partially recovered.",
   "Split-antecedent phenomena can be almost invisible in aggregate coreference scores when they are rare: only 0.8% of ARRAU clusters contained split antecedents, whereas split-only evaluation exposed differences of up to 20 CoNLL-score percentage points.",
   "After normalizing the FRIENDS annotation so later references to an already accommodated group became ordinary coreference, 4.1% of mentions remained genuine split-antecedent anaphors, providing a larger test bed than ARRAU.",
   "The Zhou and Choi scoring method substantially overweights missing split-antecedent links in the authors' diagnostic experiment: a system otherwise perfect on singular clusters loses 10 to 18 percentage points, whereas the proposed extensions give scores between 95% and 97%, close to the roughly 96% expected from the proportion of split mentions.",
   "The same machinery can score split-antecedent discourse deixis, where the antecedents are utterances or clauses rather than noun phrases, and the authors report that this approach was used in CODI/CRAC shared tasks."
  ]
 },
 {
  "paper_id": "manual-555fa5b6e8",
  "title": "Resolving Event Noun Phrases to Their Verbal Mentions",
  "research_question": "Can event-denoting noun phrases be linked to their corresponding verbal event mentions across potentially long discourse distances using lexical, positional, syntactic, and pairwise-ranking information?",
  "key_findings": [
   "Event noun phrases can refer to verbal mentions across substantially longer distances than the local windows commonly used for pronoun resolution, producing a much larger candidate set.",
   "The flat-feature model obtained an F-score of 43.35, while combining the same features with the minimum-expansion tree kernel raised F-score to 59.01.",
   "All reported composite-kernel configurations improved F-score by more than ten percentage points over the flat-feature baseline.",
   "The minimum-expansion structural representation performed better than the more elaborate simple and full expansions, which the authors interpret as evidence that additional syntactic structure can introduce harmful noise.",
   "Twin-candidate ranking improved the best composite model from 59.01 to 61.36 F-score, with precision of 66.41 and recall of 57.93."
  ]
 },
 {
  "paper_id": "manual-5a32708675",
  "title": "Overview of the NTCIR-16 QA Lab-PoliInfo-3 Task",
  "research_question": "How should real-world Japanese political-information tasks, including the alignment of batched assembly questions with their corresponding answers, be operationalized, benchmarked, and evaluated in the NTCIR-16 QA Lab-PoliInfo-3 shared task?",
  "key_findings": [
   "The task is explicitly motivated by assembly sessions in which one member asks several questions together and officials subsequently answer them, leaving the original transcript without direct adjacency between each question and its answer.",
   "The gold representation groups potentially multiple question sentences and multiple answer sentences under a common correspondence identifier, and evaluation expands each group into all cross-product question-answer sentence pairs.",
   "Formal-run submission 314 from ditlab obtained F-measure 0.8329, precision 0.8703, and recall 0.8037, whereas the organizer baseline obtained F-measure 0.6166, precision 0.5991, and recall 0.6437.",
   "The formal run received 54 on-time QA Alignment submissions plus one late submission from three participating teams, providing substantial system-level comparison on the same benchmark.",
   "Participating systems used materially different alignment strategies: AKBL combined semantic segmentation with BM25 similarity and Hungarian matching, ditlab used heuristic paragraph construction and matching features, and Forst used clue-expression segmentation followed by similarity-based mapping."
  ]
 },
 {
  "paper_id": "manual-5c0971730d",
  "title": "A Twin-Candidate Based Approach for Event Pronoun Resolution using Composite Kernel",
  "research_question": "Can event pronouns be resolved more accurately by combining lexical and positional features with syntactic tree kernels and by learning pairwise preferences between competing antecedent candidates?",
  "key_findings": [
   "Combining syntactic tree information with the flat lexical, positional, and syntactic features produced markedly better event-pronoun resolution than the flat-feature baseline.",
   "The best composite-kernel configuration using the simple expansion tree reached an F-score of 0.561 before twin-candidate ranking, whereas the flat-feature baseline obtained 0.406.",
   "Training with negative examples drawn from non-event pronouns improved precision and overall F-score relative to training without those negative instances.",
   "Balancing negative examples and tuning the event/non-event hyperplane on development data further improved the reported resolution performance.",
   "Twin-candidate preference learning increased recall from 0.492 to 0.540 and F-score from 0.561 to 0.579, with a modest decrease in precision from 0.652 to 0.626."
  ]
 },
 {
  "paper_id": "manual-7743c50805",
  "title": "Identifying reference to abstract objects in dialogue",
  "research_question": "Can linguistically naive annotators reliably identify unconstrained stretches of prior dialogue that serve as antecedents for discourse-deictic references to abstract objects?",
  "key_findings": [
   "Using a criterion of at least three annotators, 35 of 181 phrase markables in the first dialogue, or 19.3%, had a plausible discourse-segment antecedent; a similar 20 of 102, or 19.6%, was obtained in the second experiment after removal of an outlying annotator.",
   "Annotators showed meaningful but far from perfect convergence on antecedent spans: for the 16 most readily identified anaphors, Krippendorff alpha was 0.45 with Jaccard distance and 0.55 with both Dice and Passonneau distances.",
   "Antecedent endings were more consistently localized than antecedent beginnings; among the 16 clearest cases, annotators chose the most popular beginning 42% of the time and the most popular ending 64% of the time.",
   "Demonstrative pronouns, especially 'that', were much more readily associated with discourse-segment antecedents than personal 'it' or suggestive definite descriptions.",
   "A simple model based on selecting an antecedent at a fixed distance from the anaphor explained much of the annotators' span behavior, suggesting that approximate antecedent vicinity may be easier to identify than exact boundaries."
  ]
 },
 {
  "paper_id": "manual-849c5f1c6d",
  "title": "Automatically Selecting Answer Templates to Respond to Customer Emails",
  "research_question": "Can historical customer-email question-answer associations be learned well enough to select and combine response templates for new emails that may contain multiple questions?",
  "key_findings": [
   "The system explicitly decomposes an email containing multiple questions and attempts to associate each individual question with an answer and ultimately a response template.",
   "The Pine-Info sample directly demonstrates incomplete first replies: 30 initiating emails contained 43 annotated questions but only 36 question-answer mappings in the first responses, and the paper's worked example has two questions but only one marked answer.",
   "In the 30 Pine-Info pairs, an initiating email averaged 1.43 questions, its first response averaged 1.3 answers, and there were 1.2 mapped question-answer pairs per pair of messages.",
   "The authors operationalize partial reply coverage explicitly: if a two-question message receives a system response matching the human response for only one question, that response receives 50% partial credit.",
   "On Pine-Info, the automatic mapping recovered 28 of the 36 manually identified question-answer mappings, reported as 77.78% correct."
  ]
 },
 {
  "paper_id": "manual-8b8a394daa",
  "title": "Resolving abstract anaphors in Spanish discourse: Underspecification and mereological structures",
  "research_question": "How can Spanish abstract anaphors be resolved when several preceding propositions or events are plausible antecedents, and what roles do mereological grouping and rhetorical coherence play in selecting their discourse referent?",
  "key_findings": [
   "The paper proposes a three-stage resolution process in which hearers construct possible atomic and complex abstract referents, infer rhetorical connections among their components, and then resolve the abstract anaphor.",
   "Mereological structure alone is insufficient to select among all logically possible sums of preceding propositions because some structurally available combinations do not form coherent discourse units.",
   "A summed or merged propositional referent is predicted to become salient when its components participate in a meaningful rhetorical organization that advances a common discourse purpose.",
   "Coordinating relations such as Narration and Continuation are particularly compatible with constructing merged abstract referents, often under a broader Elaboration relation.",
   "A complex abstract referent can function as a discourse topic summarizing several propositions and can be incrementally enlarged as further coherent material is added."
  ]
 },
 {
  "paper_id": "manual-a6314f615a",
  "title": "Detection of Question-Answer Pairs in Email Conversations",
  "research_question": "Can question-answer pairs in asynchronous email threads be detected for summarization more effectively by combining automatic question detection with thread-structure-aware answer pairing than by relying on lexical similarity alone?",
  "key_findings": [
   "Thread-structure and candidate-context features substantially improved answer-pair detection over lexical similarity alone: on the Union annotation set, F1 increased from 0.503 with cosine similarity to 0.656 with the full feature set.",
   "Alignment became markedly harder as the number of plausible answer segments increased: the full model reached F1 0.899 for questions with at most two candidate answers but 0.625 for questions with more candidates.",
   "Training separate classifiers for low- and high-candidate cases and combining their predictions produced F1 0.730, compared with 0.656 for the unsplit Union data.",
   "A heuristic that split initially missed utterances at commas and re-applied the question rules to the first and last phrases raised interrogative-question recall from 0.56 to 0.72 while precision remained 0.96, increasing F1 from 0.70 to 0.82.",
   "The annotations included highlighted questions for which no corresponding answer was present in the thread, but answer-pair training instances were constructed only for questions that had a marked answer."
  ]
 },
 {
  "paper_id": "manual-ad98de9372",
  "title": "The DAD Parallel Corpora and their Uses",
  "research_question": "How are abstract pronominal anaphors represented and used in Danish and Italian DAD corpora, and how effectively can their pronominal functions be classified computationally?",
  "key_findings": [
   "The DAD scheme explicitly treats predicates, verb phrases, clauses, and discourse segments as possible antecedents of abstract anaphors whose referents can be properties, events, facts, propositions, and speech acts.",
   "The annotation records the antecedent itself, its syntactic type, the semantic type of the referent, anaphoric distance in clauses, and identity or non-identity relation, providing an explicit representation of links to proposition-like discourse material.",
   "Italian abstract pronominal anaphora are relatively uncommon in these data and are frequently realized as zero anaphora when they do occur, while demonstrative abstract pronouns are especially rare.",
   "Supervised classification substantially outperformed ZeroR baselines; for Italian, the best text system reached F1 81.1 versus 25.8 for ZeroR, and the best dialogue system reached F1 69.6 versus 33.7.",
   "Classification of Danish multiparty dialogue was markedly weaker than for the more homogeneous monologue and two-party datasets, and the paper specifically notes the absence of adjacency-pair annotation as an important missing signal for multiparty dialogue processing."
  ]
 },
 {
  "paper_id": "manual-b0133009f6",
  "title": "The CODI-CRAC 2022 Shared Task on Anaphora, Bridging, and Discourse Deixis in Dialogue",
  "research_question": "How effectively can systems identify and resolve identity anaphora, bridging references, and discourse deixis across several dialogue domains under predicted-mention, gold-mention, and gold-anaphor evaluation conditions?",
  "key_findings": [
   "The new dialogue datasets comprise 218 documents and 214,625 tokens across AMI, LIGHT, PERSUASION, and SWITCHBOARD, with 1,583 discourse-deixis instances reported in Table 1.",
   "Participant systems outperform the supplied baselines on virtually all shared-task settings.",
   "For discourse deixis, the best UTD_NLP system obtains macro-average CoNLL F1 of 48.69 with predicted mentions, 49.56 with gold mentions, and 66.66 when gold anaphors and mentions are supplied, while the corresponding baselines score 14.56, 23.15, and 42.28.",
   "The substantial improvement under the gold-anaphor condition indicates that identifying which expressions are discourse-deictic remains a major difficulty, not merely selecting their antecedents.",
   "For bridging, supplying gold anaphors produces a much larger gain than supplying gold mentions alone; the best macro-average rises from 25.94 in Gold M to 46.87 in Gold A."
  ]
 },
 {
  "paper_id": "manual-be69c3aa17",
  "title": "Annotating Abstract Pronominal Anaphora in the DAD Project",
  "research_question": "Can an extension of the MATE/GNOME annotation scheme represent abstract pronominal anaphora with non-nominal and discourse-segment antecedents in Danish and Italian in a way that annotators can apply reliably?",
  "key_findings": [
   "The scheme explicitly represents antecedents larger than noun phrases, including verbal phrases, simple and complex clauses, and discourse segments, making proposition- and multi-proposition reference part of the annotation target.",
   "Semantic referent labels include eventualities, fact-like entities, propositions, questions, and speech acts, allowing abstract reference to be distinguished by discourse-semantic type rather than only by span.",
   "When more than one antecedent or referent interpretation is plausible, annotators choose a preferred interpretation but can record alternatives in a comment field.",
   "Agreement for identifying non-NP antecedents was substantial across the evaluated subsets, with kappa values of 0.81 and 0.79 for Danish texts and dialogues and 0.89 and 0.87 for Italian texts and dialogues.",
   "Agreement on proposition-valued referents was also high in the reported samples, with kappa values from 0.80 to 0.92 across language and modality conditions."
  ]
 },
 {
  "paper_id": "manual-e1981ecd9a",
  "title": "Answering Clarification Questions",
  "research_question": "Which factors affect how clarification questions are interpreted and whether, how, and how quickly interlocutors respond to them?",
  "key_findings": [
   "A large proportion of clarification requests appeared unanswered in the BNC: 39% had no apparent answer under the broad coding, falling to 17% when possible answers transcribed as unclear and cases where the requester immediately continued were discounted.",
   "Clarification form and interpretation constrain answer form: sluices were normally answered with fragments and not polar particles, conventional clarifications tended toward full sentences, while reprise fragments could receive fragments or yes-no responses.",
   "When clarification requests were answered, the linkage was highly local: 94% of the 289 answered cases received their answer in the immediately following BNC sentence, and none in the analyzed set were more than three sentences away.",
   "In the controlled chat experiment, 50% of 215 inserted reprise clarifications received no response, and the authors observed that simultaneous typing could displace some replies until the end of an in-progress turn or a later turn.",
   "Grounding status affected response probability: 58% of reprise clarifications of first mentions received a response compared with 33% of reprises of second mentions."
  ]
 },
 {
  "paper_id": "manual-e4d6ad7ca1",
  "title": "Anaphoric Annotation in the ARRAU Corpus",
  "research_question": "Can an anaphora annotation scheme represent ambiguous interpretations, multiple antecedents, and discourse deixis to abstract clause-level antecedents with useful human agreement across dialogue and written genres?",
  "key_findings": [
   "Agreement on anaphoric chains in the reported annotation experiments was approximately alpha 0.6-0.7.",
   "For discourse deixis, annotators tended to agree on the general antecedent region but disagreed about exact boundaries, yielding agreement around alpha 0.55.",
   "The annotation experiments motivated constraining discourse-deixis antecedent regions to predefined clause-level units and distinguishing plural multi-antecedent cases from genuinely ambiguous alternative interpretations.",
   "The reported corpus contains 110 texts and 94,212 words, including 455 markables pointing to textual regions and 103 explicitly ambiguous markables.",
   "ARRAU can encode several antecedents for a plural anaphoric expression and can encode two alternative sets of antecedent pointers for ambiguity."
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
"/home/grammy-jiang/Projects/msgloom/research/04-reference-and-response-scope/runs/347e4c36d5de/analysis/synthesis.json", `status` = accepted | accepted_with_issues | rejected,
`issues` (each naming the finding or paper it is about), `required_fixes`
(required when rejected), `unsupported_claims`, `confidence`, and `scores`
with faithfulness, coherence, gap_completeness (0-1) and citation_integrity
(true/false).
===BEGIN synthesis_review.json===
<content>
===END synthesis_review.json===

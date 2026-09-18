# Topic 04 current status

## Academic research

- Rounds 1–4: complete. Stopped on `round_cap_reached`, the configured
  four-round cap, on 2026-09-16.
- Corpus: 47 papers admitted and read. Three papers were written off with
  recorded reasons (no retrievable bibliographic identity); they are named in
  `runs/<run>/analysis/skipped.json`.
- New papers per round: 13, 13, 12, 9. Every round contributed evidence, so
  the loop was never stopped by `no_new_papers`.
- Independent review: rounds 1 and 2 were rejected once each and accepted
  after a single repair; rounds 3 and 4 were accepted at the first attempt.
  Final faithfulness 0.91, coherence 0.95, gap completeness 0.97, citation
  integrity passed. Every rejection is preserved under
  `runs/<run>/review/synthesis_review.a<N>.rejected.json`.
- Report: `msgloom-topic-04-reference-and-response-scope-research-report.md`,
  validated PASS. Per-round snapshots are kept as `…-report.r1…r3.md`.

**Reaching the round cap is a stopping condition, not evidence.** All five
gaps remain open and none was downgraded.

## Correction recorded 2026-09-17 — the corpus count is overstated

Found by a duplicate scan written while reviewing Topics 06 and 08, not by
this topic's own review. **The corpus of 47 records is 45 distinct papers.**
Two studies were each admitted twice, once as a bare `manual-` row from the
model's own search and once, in a later round, with a DOI:

| Pair | Study |
| --- | --- |
| `manual-8b8a394daa` + `doi-10-1515-ling-2018-0008` | Resolving abstract anaphors in Spanish discourse |
| `manual-a6314f615a` + `doi-10-3115-1220355-1220483` | Detection of question-answer pairs in email conversations |

**What it affects.** The second pair is never cited twice in one place, so no
finding rests on it. The first is, in three places:

- **Finding 5, labelled HIGH** — "Composite proposition-level antecedents are
  linguistically supported" lists four supporting papers, two of which are the
  same study. It rests on **three** distinct papers, not four.
- The Supporting-papers list for that section names five; four are distinct.
- The coverage table row for composite antecedents shows four ticks; three are
  distinct.

**What it does not affect.** The finding is not unsupported: three distinct
papers remain behind it. Nothing here changes a gap's status, and no gap is
downgraded. The other findings and the gap set are unaffected.

**Why it happened.** The search gate excluded papers earlier rounds had
already reviewed by identifier only, so the same study returning with a second
identifier passed through, and the cross-round merge deduplicated by
identifier as well. Fixed in `25e7efa4`: the search gate now also excludes by
normalised title. The fix post-dates this topic and was not applied to it.

**Not re-run.** Re-running four rounds to correct a count of two would cost
more than the inaccuracy does. The number to quote is **45 distinct papers**,
and Finding 5 rests on three.

## Retained gaps

Academic, and not closable by the four rounds already run:

- **G1 (HIGH)** Direct empirical evidence for exact proposition-level
  agreement, rejection, approval, clarification and answer scope in authentic
  workplace email or enterprise chat.
- **G3 (HIGH)** Mixed multi-question partial replies: workplace messages that
  combine questions, requests, alternatives and conditions, with complete
  unresolved-subquestion detection validated together.
- **G4 (MEDIUM)** Whether a response independently targets several
  propositions or targets one composite multi-proposition object.

Engineering, and deliberately not literature-search targets, because the
required contract and cost function are msgloom-specific:

- **G2 (HIGH)** A combined annotation and evaluation scheme for exact,
  partial, ambiguous, unsupported, discontinuous, multiple-antecedent,
  composite and no-link outcomes.
- **G5 (HIGH)** Abstention, ambiguity, missing-antecedent and asymmetric
  error-cost policy.

## Remaining deferred / handed-off work

- Production-domain representativeness: deferred until suitable authorized
  domain data exists; not a current blocker.
- Speech-act and action classification, given the antecedent scope: Topic 05.
- Missing antecedents turned into targeted evidence needs: Topic 07.
- References to tables, screenshots, attachments, cells, pages and visual
  regions: Topic 08.
- G2 and G5 as evaluation methodology: Topic 10, which owns general
  calibration and attribution while Topic 04 keeps ownership of what the
  outcomes mean.
- No production architecture has been approved by Topic 04 research.

Each handoff is recorded in the receiving topic's `TOPIC_CONTEXT.md` under
"Direct handoffs from earlier Topics". A handoff recorded only here would not
be read when that topic starts.

## Inherited handoffs that Topic 04 answered

Topics 01 and 02 both deferred "semantic response / partial-agreement scope"
to Topic 04. Topic 04 addressed it to the extent the literature allows: the
mechanisms, representations and failure modes are now documented with
evidence, and what is still missing is stated as G1, G3 and G4 rather than
presented as resolved.

## Run record

Driven by the ChatGPT orchestrator (`.github/scripts/chatgpt_research.py` on
`feat/chatgpt-orchestrator`), `chat` profile, 18 active steps per round.
Worker conversations were archived locally and deleted from the account.
Historical round reports, syntheses and gap snapshots remain unchanged; this
file records the outcome rather than rewriting research history.

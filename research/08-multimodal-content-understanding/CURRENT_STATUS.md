# Topic 08 current status

## Academic research

- Rounds 1–4: complete. Stopped on `round_cap_reached`, the configured
  four-round cap, on 2026-09-17.
- Corpus: 53 records admitted and read, none written off. **52 distinct
  papers** — see the correction below.
- New papers per round were 14, 14, 10, 15. Every round contributed and the
  loop was never stopped by `no_new_papers`.
- Independent review: rounds 1 and 3 were accepted at the first attempt;
  rounds 2 and 4 were each rejected once and accepted after a single repair.
  Final faithfulness 0.96, coherence 0.98, gap completeness 0.99.
- Report:
  `msgloom-topic-08-multimodal-content-understanding-research-report.md`.

**Reaching the round cap is a stopping condition, not evidence.** All eight
gaps remain open and none was downgraded.

## Correction — one study is in the corpus twice

`doi-10-1109-tmm-2022-3219642` and `manual-1048d6caf2` are both
**"Scene-Text Oriented Referring Expression Comprehension"**. The first
carries the DOI, authors, year and venue; the second is a bare row with no
authors and a year of 2026, which is its ingestion date. The bare row was
admitted in round 1 from the model's own search, and the DOI record in round
2 when the same study was found again.

**Quote 52 distinct papers, not 53.**

The round-2 review caught it — "do not present the DOI and manual records as
independent corroborating studies" — and the repair separated
`paper_count: 27` from `analysis_count: 28` for that round. The final report
inherits that discipline. No structural check saw it: the identifiers differ,
so the accounting closed cleanly at every gate. Only the reader noticed.

Fixed for future topics in `25e7efa4` (the search gate now excludes an
already-reviewed study by normalised title) and `14ab393b` (a duplicate scan
is now the sixth integrity invariant). Neither fix reached this run: the
orchestrator process had loaded its code at 00:54 and the fixes landed at
03:08.

## Retained gaps

Academic, and not closed by four rounds of searching:

- **gap-1 (HIGH)** No complete method maintains evidence provenance across
  successive workplace attachment versions.
- **gap-2 (HIGH)** Direct grounding of workplace-message referring
  expressions — "this screenshot", "the highlighted row", "numbers below" —
  is not established.
- **gap-3 (HIGH)** Comprehensive spreadsheet understanding remains open for
  formulas, hidden rows and sheets, cross-sheet references and merged cells.
- **gap-4 (HIGH)** No admitted paper validates one end-to-end provenance
  representation jointly identifying attachment version, page, document
  element and region.

Engineering, and deliberately not literature-search targets:

- **gap-5 (HIGH)** End-to-end behaviour when extraction or grounding is
  unsupported, incomplete or wrong.
- **gap-6 (HIGH)** Robustness on heterogeneous workplace-style documents.
- **gap-7 (MEDIUM)** Operational scaling on long documents, large tables and
  realistic workbooks.
- **gap-8 (HIGH)** One evaluation measuring semantic correctness, extraction
  completeness, exact provenance and unsupported-evidence handling together.

## Remaining deferred / handed-off work

- Production-domain representativeness: deferred until suitable authorized
  domain data exists; not a current blocker.
- Interpreting and locating evidence inside a retrieved document or workbook:
  Topic 07. Named directly in Topic 08's report.
- Structured evidence a briefing must preserve rather than flatten: Topic 09.
- gap-5 to gap-8 as evaluation methodology, plus the evidence-counting
  failure mode above: Topic 10.
- No production architecture has been approved by Topic 08 research.

Each handoff is recorded in the receiving topic's `INHERITED_HANDOFFS.md`,
and each entry states what it rests on.

## Inherited handoffs that Topic 08 answered

Topic 04 handed over references to tables, screenshots, attachments, cells,
pages and visual regions, which its own corpus excluded. Topic 05 handed over
action evidence living in attachments and tables. Both are addressed by this
topic's grounding work, and both senders' open gaps still travel with the
extracted object: Topic 08's gap-2 is the direct continuation of Topic 04's
excluded reference types.

**Topic 06's handoff arrived after this topic had finished.** The two ran in
parallel, and Topic 06 closed at 05:17 while Topic 08 was in its final round.
Its text is in `INHERITED_HANDOFFS.md` so the folder is complete, but no
round here was informed by it. If its substance matters — versioned documents
superseding earlier state — the remedy is one more round on this finished
report, not a re-run.

## Run record

Driven by the ChatGPT orchestrator, `chat` profile, 18 active steps per round,
four gate types. Per-step reasoning effort: `max` for admission, per-paper
analysis, synthesis and review; `extended` for terminology, search, report
writing and gap classification.

Round durations, first send to last: 63.9, 88.9, 70.3, 87.5 minutes.

**Topic 08 ran in parallel with Topic 06 throughout.** This was the
programme's first concurrent pair. No send-window contention, no
conversation-id collision and no rate-limit event was recorded in either run.

**Round 4 aborted once and was resumed.** After the round-4 review rejected
the synthesis, the repair — a follow-up turn in a conversation already
holding a 53-paper prompt and a 58.9 kB reply — was truncated at 20 kB on
two successive attempts and the run stopped. Re-dispatching the synthesis
into a *fresh* conversation produced a complete reply in six minutes and the
repair was accepted. The ledger entry for the truncated worker stays at
`failed` for that reason. The misleading error it produced ("no `===BEGIN`
block found", when the block was opened and never closed) is fixed in
`4378aaae`.

Worker conversations were archived locally and deleted from the account.

# Topic 02 gap-review decision before Academic Round 2

## Purpose

This document records the project-value review of the 20 Round 1 gaps. It supersedes neither the historical `gaps.json` nor `TARGETED_FOLLOWUP.md`; those remain Round 1 snapshots. This decision determines what is important enough to do now, what requires engineering validation later, and what belongs to another research topic.

## Decision rule

A gap is prioritized now only if resolving it can materially affect one of the following:

1. whether msgloom can represent a concrete work matter without losing supporting spans;
2. whether segmentation/assignment can silently omit or broaden decision-bearing evidence;
3. whether the chosen representation/evaluation would force incorrect architecture decisions;
4. whether additional academic evidence is likely to change the next engineering experiment.

Automatic gap-classifier priority is advisory only. `HIGH` does not automatically mean “search for more papers now.”

## Academic Round 2 — authorized streams

### R2-A — Set-valued, overlapping, and non-contiguous Topic assignment

Covers **G1-A + G2-A**.

Target evidence:

- one Topic supported by multiple separated spans within one message;
- one span assigned simultaneously to multiple Topics;
- explicit prediction/evaluation of those structures, preferably in email/work communication;
- separation of gold multi-membership from disjoint decoder output, top-K alternatives, or pair/cluster intermediates.

Ordinary contiguous topic-boundary papers and whole-document multi-label classification do not close this stream.

### R2-B — Decision-bearing preservation

Covers **G3-A**.

Target evidence:

- conditions, exceptions, deadlines, evidence, approval constraints, or decision qualifiers preserved or lost by segmentation/assignment;
- semantic/scope preservation measurements or adjudicated omission/broadening rates;
- email/work-message evidence preferred, with qualified transfer evidence where direct evidence is unavailable.

A boundary/cluster F1 score alone does not close this stream.

### R2-C — Modern business/work-email evidence

Covers **G4-A**.

Target evidence:

- modern workplace/business/enterprise email or closely matched work-message benchmarks;
- human gold for Topic segmentation/assignment;
- task-matched prediction and preservation evaluation;
- explicit corpus dates, grouping/split controls, and domain description.

Recent dialogue papers do not count as direct business-email evidence.

## Opportunistic academic acquisition

### G5-A — D05 provenance

Do not open a dedicated search stream. If a clean official/author copy of *A Publicly Available Annotated Corpus for Supervised Email Summarization* is found during Round 2, acquire and verify it for corpus/annotation provenance only. Otherwise retain the gap without blocking Topic 02.

## Handoff to another research topic

### G10-A + G10-E — concrete work-matter identity and count

Transfer to **Topic 03**. Cross-thread/source identity of the same concrete work matter is Topic 03's core question and should not be duplicated in Topic 02.

## Engineering work — important, but not before Academic Round 2 re-review

The following remain candidates for Topic 02 engineering validation after Academic Round 2:

- **G7-E** lossless representation round trip;
- **G9-E** sentence/clause/EDU/arbitrary-span/hybrid unit comparison;
- **G2-E2** set-valued Topic assignment benchmark;
- **G3-E** decision-bearing preservation metrics;
- **G8-E1** incremental/context correction for Topic span assignments, excluding semantic response scope owned by Topic 04;
- **G8-E2** Topic-assignment uncertainty/abstention plumbing, with general calibration methodology owned by Topic 10;
- **G4-E** domain-transfer validation with synthetic/public data now and production-domain validation later.

Supporting artifact audits, not standalone programmes:

- G1-E annotation offsets/recurrence;
- G2-E1 gold-reduction/decoder/scorer behavior;
- G6-E1 metric implementations/denominators;
- G6-E2 dataset/split/duplicate controls.

Conditional/deferred:

- G6-E3 only after selecting a mechanism for faithful reproduction;
- G8-E3 Raspberry Pi performance only after correctness/preservation/candidate selection.

## Required second gap review

Academic Round 2 may close, reduce, merge, or create gaps. Therefore no Topic 02 engineering programme is authorized from this document alone. After Academic Round 2 completes, create a fresh post-Round-2 gap review before engineering implementation begins.

## Production-data boundary

No production email/examples are currently available. Topic 02 must not wait for them. Academic work and synthetic/public engineering validation can proceed. Production representativeness must remain explicitly deferred and may not be inferred from synthetic/public results.

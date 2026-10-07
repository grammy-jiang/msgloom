# Engineering-validation plan

## Evidence status

Academic Round 2 ended with E1-E4 as the high-priority engineering gaps. This programme tests what can be tested now without production data. Synthetic success demonstrates benchmark/harness correctness and exposes controlled failure modes; it does **not** demonstrate production accuracy.

## Sequence

1. **E1 benchmark contract**
   - versioned JSON fixture format;
   - raw RFC 5322 message bytes generated deterministically;
   - message/parent gold;
   - quote occurrence -> source message/span gold;
   - explicit alternative source sets;
   - unique and decision-bearing spans;
   - missing-parent and uncertainty labels.
2. **E2 preservation/alignment**
   - reference body extraction and offset mapping;
   - plain-text quote detection;
   - exact/fuzzy local source matching baseline;
   - span/link/preservation metrics with explicit denominators;
   - adversarial HTML/table/edited/boilerplate cases.
3. **E3 replay/correction**
   - deterministic arrival-order replay;
   - immutable assessment snapshots;
   - final-state comparison across permutations;
   - correction/retraction, relation-transition, removed-relation, parent/ancestry, and occurrence-specific quote metrics.
4. **E4 structural uncertainty**
   - candidate sets and abstention;
   - held-out synthetic template families;
   - accepted-link error, coverage, candidate recall and reliability bins;
   - no claim that heuristic confidence is production-calibrated.

## Gate for calling a gap completed-now

A gap can be marked `COMPLETED_SYNTHETIC` only when:

- the harness has executable tests;
- gold denominators are explicit;
- experiment output is reproducible with a fixed seed;
- results and known limitations are recorded;
- no claim relies on production representativeness.

Anything requiring real mailbox distributions, Topic 04 semantics, external-method adoption, or hardware performance remains `DEFERRED`.

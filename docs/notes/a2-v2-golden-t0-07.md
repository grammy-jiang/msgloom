# A2 v2 golden oracle T0-07: crash, restart, late writes and cancel

This note describes `tests/a2_kedro/golden/t0_07.json`. The oracle covers the
rule "the accepted prefix is preserved, and unfinished work must be
replayable". A person wrote every expected outcome by hand from the A2 Kedro
v2 blueprint. No msgloom code produced any value.

The execution manifest names `tests/a2_kedro/gold/t0_07.json`. The edit
allowlist names `tests/a2_kedro/golden/`. The file lives in `golden/`, as in
decision 5 of `a2-v2-golden-decisions.md`.

## Model

Each case has a frozen workset of N occurrences and a timeline of events.

| Event | Meaning |
| --- | --- |
| `claim` | A process takes the live claim token for a configuration. A new token replaces the old one. |
| `crash` | The process dies. Work that did not reach COMMIT is lost. |
| `cancel` | The bridge-closed flag is set. New saves are refused. |
| `write` | The named token saves the result of one occurrence. |
| `finalize` | The finalizer tries to move the workset from pending to terminal. |

Write outcomes are `accepted`, `reused`, `rejected_stale_claim`,
`rejected_bridge_closed` and `rolled_back`. The live claim is checked first.
Then the bridge flag. Then COMMIT. Then the accepted key.

Each case lists hand-written snapshots. A snapshot gives the accepted
ordinals per configuration, the replayable ordinals, and the workset state.
The replayable set is the frozen set minus the accepted set of the active
configuration.

## Rules used

| Rule | Blueprint section |
| --- | --- |
| Each ordered frozen occurrence needs one accepted terminal. Deduplicated source refs are not enough. | 4.2 |
| Any limitation gives terminal INCOMPLETE. Only full acceptance gives COMPLETE. | 4.2 |
| The finalizer re-checks the claim and every result. A failed step leaves the workset pending. | 4.3 |
| The logical key is deterministic. It holds the configuration version and no attempt or time. Replay returns the stored result. | 5.1 |
| A save checks the live claim first, then reuses an accepted key or inserts one atomic record. | 5.3 |
| Cancel after COMMIT is not a rollback. The next run skips the accepted stage and does not rerun the parser. | 5.3 |
| One owner worker runs a workset. Cancel sets the bridge-closed flag, refuses new saves and drains in-flight work. | 6.1 |
| Claim lost gives FAILED `scheduled-claim-lost`. User cancel gives CANCELLED `scheduled-cancelled`. A trusted partial gives INCOMPLETE `scheduled-preparation-incomplete`. | 8.2 |

## Cases

| Case | Topic |
| --- | --- |
| T0-07-P01 | Crash before the first accept |
| T0-07-P02 | Crash in the middle of a batch |
| T0-07-P03 | Write interrupted before COMMIT |
| T0-07-P04 | Crash after the last accept, before the finalizer |
| T0-07-P05 | Cancel while a write is in flight (decision 1) |
| T0-07-P06 | Cancel after COMMIT |
| T0-07-P07 | Double restart |
| T0-07-P08 | Accepted result with a limitation |
| T0-07-P09 | Two occurrences share one source ref |
| T0-07-P10 | Replay after a configuration change (decision 2) |
| T0-07-N01 | Late writes and late finalize from a lost claim |
| T0-07-N02 | Cancel with an in-flight write that rolls back |
| T0-07-N03 | Finalizer refuses while a prefix is missing |

## Decisions that are not in the blueprint

Each affected case has a `policy_status` field. Nobody has given owner
approval for any item marked PROPOSED.

### 1. T0-07-P05 cancel drains an in-flight write: task-goal decision

- Status: `task_goal_decision`.
- Rationale: Blueprint 6.1 says in-flight work drains. It does not say that a
  draining save must commit. The task goal says cancel drains pending writes
  and leaves no half result. The oracle reads this as: a draining save ends
  its own atomic transaction. P05 shows the commit. N02 shows the rollback.
  Both agree that no half result exists.
- Risk if wrong: A runner may prefer to abort a draining save. Then P05 must
  change to a rollback, and the case needs a new reviewer and a new manifest
  line.

### 2. T0-07-P10 replay under a changed configuration: PROPOSED, owner sign-off needed

- Status: `proposed_owner_signoff_needed`.
- Rationale: Blueprint 5.1 puts the frozen configuration version in the
  logical key. A new configuration therefore gives new keys and new ids.
  Blueprint 4.3 says an operator replay appends and never overwrites. The
  blueprint does not say that a workset frozen under one configuration may be
  replayed under another. It does not say who approves this. It does not say
  how the terminal receipt names the configuration. The oracle proposes that
  the replay runs, the old records stay, and the new records are new.
- Risk if wrong: The owner may require replay under the frozen configuration
  only. Then P10 must change, with a new reviewer and a new manifest line.

## Modeling limits

- The oracle assumes one owner worker that saves occurrences in order
  (blueprint 6.1). The accepted set is then a contiguous prefix. The
  blueprint does not describe out-of-order or parallel saves. The oracle does
  not cover them and does not decide them.
- A takeover (a second `claim` without a `crash`) models a lease that ran
  out. The blueprint says the lease has no automatic renewal. It does not
  describe how a takeover waits for the lease.
- Result ids such as `res-cfg1-0` are hand-chosen placeholders. They stand
  for the deterministic accepted result of one configuration and ordinal.
- The oracle does not cover held occurrences, transition batches or the v1
  and v2 finalizer fence. Other tasks cover them.

## Checks

`tests/a2_kedro/test_gold_t0_07.py` validates the shape and the internal
consistency of the oracle. Its reference checker tests these invariants:

- The accepted set of one configuration is a contiguous prefix.
- A write from a token that is not the live claim leaves no result.
- A save is accepted whole or not at all.
- The replayable set equals the frozen set minus the accepted set.
- Replay returns the same result id.

The test also checks the manifest line against the file bytes. Negative tests
flip outcomes and snapshots and require the checker to report a problem.

## Registration in the shared golden tests

`test_gold_corpus.py` lists T0-07 in `EXPECTED_TASKS`. `test_gold_decisions.py`
lists T0-07-P05 and T0-07-P10 in `EXPECTED_STATUS`. Both decisions are also in
`a2-v2-golden-decisions.md`.

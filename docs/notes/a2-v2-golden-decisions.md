# A2 v2 golden corpus: decisions that are not from A1

Some expected values in `tests/a2_kedro/golden/` do not come from an A1 or
master document. This note lists each one and its status. Nobody has given
owner approval for any item marked PROPOSED.

Each affected case has a `policy_status` field. The field is machine
readable. `tests/a2_kedro/test_gold_decisions.py` checks that the field
exists on exactly the cases listed here, and that this note names them.

## Status values

| `policy_status` value | Meaning |
| --- | --- |
| `proposed_owner_signoff_needed` | PROPOSED. The verdict is a plain secure or safe answer. The owner must sign off before A2 cites it as a requirement. |
| `task_goal_decision` | The task goal fixes the answer. A1 documents are silent or leave it open. A2 authors must not present it as an A1 rule. |

A case without `policy_status` is derived from A1 or master documents or from
a hand derivation. The `provenance` and `rationale` fields give the source.

## Decisions

### 1. T0-10 Dataset path verdicts: PROPOSED, owner sign-off needed

- Cases: T0-10-P01, T0-10-P05, T0-10-N01, T0-10-N02, T0-10-N03, T0-10-N04,
  T0-10-N05, T0-10-N06, T0-10-N07, T0-10-N08, T0-10-N09, T0-10-N10.
- Status: `proposed_owner_signoff_needed`.
- Rationale: No cited A1 or master document defines a Dataset path rule. The
  accept and reject verdicts and the reason words (`traversal`, `absolute`,
  `unc`, `nul`, `symlink_escape`, `empty`) are the plain security answer.
- Risk if wrong: A2 could reject a path the owner wants, or accept one the
  owner wants rejected. The owner must confirm before A2 treats them as
  required.

### 2. T0-09 N08: PROPOSED, owner sign-off needed

- Case: T0-09-N08.
- Status: `proposed_owner_signoff_needed`.
- Rationale: The handoff spec (H6, H18) does not say how A2 reacts when A1
  authority advanced and no release exists. T0-09-N04 fixes only what the
  rules decide: no work, no cursor move, no invented release. N08 adds the
  proposal that A2 reports a visible failure.
- Risk if wrong: The owner may prefer a wait-and-retry state. Then N08 must
  change, with a new reviewer and a new manifest line.

### 3. T0-04 Calendar as a contextual source: task-goal decision

- Cases: T0-04-P04, T0-04-P05, T0-04-N03.
- Status: `task_goal_decision`.
- Rationale: `preparation-semantics.md` names only To Do, OneDrive and
  Contacts as contextual inputs. The handoff spec leaves the final A2 role of
  Calendar open. The task goal says Calendar stays contextual. The cases
  therefore put a Calendar event in a one-member None group.

### 4. T0-02 reply text split and ancestor order: task-goal decision

- Cases: T0-02-P02, T0-02-P03, T0-02-N04.
- Status: `task_goal_decision`.
- Rationale: The split of contributed text and quoted text, and the
  oldest-first order of ancestors, are task-level annotations. The cited A1
  documents do not define them.
- Note: T0-02-P01 is not in this list. It follows A1 only (MIME alternatives
  are extracted independently; equivalence is not inferred).

### 5. Corpus path `golden/` instead of `gold/`: task-goal decision

- Scope: the whole corpus directory. No single case carries a marker.
- Status: task-goal decision. The supervisor set the path.
- Rationale: The execution manifest names `tests/a2_kedro/gold/`. The edit
  allowlist for this work names `tests/a2_kedro/golden/`. The corpus uses
  `golden/` so that all writes stay inside the allowlist. Test files keep the
  `test_gold_*.py` pattern. The owner must decide whether to rename the
  directory or to correct the manifest.
- Check: `test_corpus_directory_is_golden` fails if the directory name
  changes without a decision update.

## T0-07 decisions

The full text is in `a2-v2-golden-t0-07.md`.

- T0-07-P05 cancel drains an in-flight write: `task_goal_decision`. A
  draining save finishes its own atomic transaction.
- T0-07-P10 replay under a changed configuration:
  `proposed_owner_signoff_needed`. The blueprint does not say whether a
  workset frozen under one configuration may replay under another.

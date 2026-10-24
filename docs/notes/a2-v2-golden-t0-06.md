# A2 v2 golden oracle T0-06: no missing item and no overlap

This note describes `tests/a2_kedro/golden/t0_06.json`. The oracle covers the
rule "every item in a held, intake-held, A2-held or transition-only scope has
an accepted prepared@2 result or a held record, never missing and never
both". A person wrote every expected answer by hand from the A2 Kedro v2
blueprint. No msgloom code produced any value.

The execution manifest names `tests/a2_kedro/gold/t0_06.json`. The file lives
in `golden/`, as in decision 5 of `a2-v2-golden-decisions.md`.

## Model

Each case has a frozen workset, a durable store and a receipt claim.

| Part | Meaning |
| --- | --- |
| Scope item | An occurrence, a baseline root, a transition fact or an intake-held entry. |
| Store record | An accepted prepared@2, a2_input_disposition@1 or prepared_transitions@2. A record with `accepted` false was never committed. |
| Receipt row | A claim: this item is covered by this disposition and this ref. |

The expected answer has three parts: a coverage label for each item, the
sorted list of problems, and a finalize ceiling. The ceiling is
`NOT_FINALIZABLE` when any problem exists, else `INCOMPLETE_ONLY` when a held
or partial result exists, else `COMPLETE_ALLOWED`.

## Rules used

| Rule | Blueprint section |
| --- | --- |
| Each ordered frozen occurrence needs one accepted terminal. A shared source ref does not merge two occurrences. | 3.1, 4.2 |
| The terminal is prepared@2 (COMPLETE or limited) or a2_input_disposition@1. | 4.2 |
| A baseline root follows the same rule as an occurrence. | 3.3, 4.2 |
| A non-empty transition list needs exactly one accepted ordered batch. It needs no prepared body. A transition is never A2-held. | 4, 4.2 |
| The frozen intake-held entry is the record. A2 never writes it back. | 4.2 |
| COMPLETE needs no intake-held, no A2-held and no partial result. | 4.2 |
| The finalizer trusts stored accepted results, not the caller claim. | 4.3, 6 |

## Cases

| Case | Topic |
| --- | --- |
| T0-06-P01 | All prepared, COMPLETE allowed |
| T0-06-P02 | Prepared with a limitation |
| T0-06-P03 | One A2-held occurrence |
| T0-06-P04 | A2-held and intake-held origins side by side |
| T0-06-P05 | Intake-held next to complete output |
| T0-06-P06 | Held-only workset |
| T0-06-P07 | Transition-only workset with one batch |
| T0-06-P08 | All four item kinds |
| T0-06-P09 | Historical baseline |
| T0-06-P10 | Two occurrences, one source ref |
| T0-06-P11 | Empty scope |
| T0-06-N01 | Item missing from both sets |
| T0-06-N02 | Overlap listed in the receipt |
| T0-06-N03 | Hidden overlap in the store |
| T0-06-N04 | Duplicate held records |
| T0-06-N05 | Duplicate prepared records |
| T0-06-N06 | Transition-only, no accepted result |
| T0-06-N07 | Transition batch never accepted |
| T0-06-N08 | Transition covered by a body or a disposition |
| T0-06-N09 | Fabricated ref |
| T0-06-N10 | Unaccepted prepared record |
| T0-06-N11 | Ref of the wrong kind |
| T0-06-N12 | Second occurrence reuses the first result |
| T0-06-N13 | A2 disposition with the intake-held origin |
| T0-06-N14 | A2 record over a frozen intake-held entry |
| T0-06-N15 | Origin labels swapped in the receipt |
| T0-06-N16 | Batch in the wrong order |
| T0-06-N17 | Partial batch |
| T0-06-N18 | Two full batches |
| T0-06-N19 | Receipt row for an item that was never frozen |
| T0-06-N20 | A held record does not hide a missing item |

## Decisions that are not in the blueprint

No case carries `policy_status`. Every verdict follows the blueprint text.
The test fails if a case adds the field without an entry in the decisions
note and in `test_gold_decisions.py`.

## Modeling limits

- T0-06-P11 reads the COMPLETE conditions of blueprint 4.2 literally. With no
  item, nothing is missing, nothing is held and nothing is partial. The
  blueprint does not say whether an empty workset can exist. The case fixes
  only that the coverage check finds no problem. A reviewer may drop the
  ceiling for this case if the owner prefers.
- The oracle treats a record that covers the wrong item set as invalid. The
  blueprint does not name this code. The code words are oracle vocabulary.
- The oracle does not model attempts, claims or publication proofs. T0-07
  covers claims and replay. A reused accepted record from an earlier attempt
  would look like any other accepted record here.
- A transition batch has one status for all facts. Per-fact limits are not
  modeled.
- The `status` of an a2_input_disposition@1 record is always INCOMPLETE and
  does not affect the ceiling. Its kind alone forces INCOMPLETE.

## Checks

`tests/a2_kedro/test_gold_t0_06.py` validates the shape of every case and
runs a pure-Python reference checker. The checker has one switch for each of
15 problem codes and 4 ceiling rules. A test per rule switches the rule off
and requires the designated cases to change. Other tests change each answer,
delete each input element and delete each key, and require a failure. The
test also checks the manifest line against the file bytes.

## Registration in the shared golden tests

`test_gold_corpus.py` lists T0-06 in `EXPECTED_TASKS`. No entry is added to
`test_gold_decisions.py` because T0-06 has no decision case. The test in
`test_gold_t0_06.py` enforces that.

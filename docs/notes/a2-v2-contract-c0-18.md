# A2 v2 contract C0-18: read-only scoped status types (PROVISIONAL)

Code: `msgloom/cli/a2_scope_status.py`.
Tests: `tests/a2_kedro/test_c0_18.py`, `tests/a2_kedro/test_c0_18_scope.py`.

This note records the research form of the scoped progress status. The
module is a pure mapping layer. It opens no database, writes nothing, reads
no environment value and imports no persistence module. Nothing calls it
yet. It does not edit `status.py`, `runner.py` or any store.

## Input and output

- `ScopeProgress(scope_id, workset, expected_occurrences, expects_batch,
  expected_intake_held)` names the frozen scope: a workset reference and
  counts. `scope_id` is a lowercase SHA-256 digest, not free text, so an
  address or a path cannot enter a status. A scope with no work is
  rejected.
- `status_from_receipt(progress, receipt)`, `status_from_held(scope_id,
  held)` and `status_from_error(scope_id, error)` return a frozen
  `ScopeStatus`: closed `ScopeState`, scope id, counts and limitation codes.
- `status_line(status)` returns one ASCII line. It holds no scope id, no
  identity, no path and no limitation detail.
- `exit_code(status)` returns the code in the table below.

## States and exit codes

| State | Contract status | Exit |
| --- | --- | --- |
| `complete` | COMPLETE | 0 |
| `claim_lost` | FAILED | 4 |
| `incomplete` | INCOMPLETE | 20 |
| `busy` | INCOMPLETE | 21 |
| `held` | INCOMPLETE | 22 |
| `blocked_source` | BLOCKED | 30 |
| `blocked_reference` | BLOCKED | 31 |
| `blocked_catalog` | BLOCKED | 32 |

Only 0 and 4 are stable. The exit values 20 to 32, the state wire names
and the limitation codes `occurrence_missing`, `batch_missing` and
`intake_held` are PROVISIONAL.

`runner.py` uses 0 (ok), 2 (invalid input), 3 (untrusted authority) and 4
(failed operation). This table reuses 0 and 4 and avoids 2 and 3. The
module entry `python -m msgloom.cli.a2_scope_status STATE` prints the table
line for a state name and exits with its code. A bad command line exits 2.

## Rules

- A receipt binds to the scope by its workset reference. A receipt whose
  `workset` differs from `ScopeProgress.workset` raises `ScopeInputError`
  before any count is read. It never gives COMPLETE and never reaches the
  held check.
- COMPLETE needs every expected occurrence covered, every root and the
  batch COMPLETE, no held root, no intake-held entry and a COMPLETE receipt
  status. The status is recomputed from the roots. The receipt status is
  never trusted alone.
- A receipt with fewer roots than expected is INCOMPLETE with the code
  `occurrence_missing`. More roots, another intake-held count (a
  non-`int` value such as `True` included) or an unexpected batch raise
  `ScopeInputError`.
- An A2-held root is `held` (INCOMPLETE). A held root that claims COMPLETE
  raises `HeldTerminalError`. `status_from_error` maps it to `held`.
- Typed errors share the base `ScopeStatusError`. They take no argument and
  carry a fixed message: blocked source, blocked reference, blocked catalog,
  busy (INCOMPLETE), claim lost (FAILED) and held terminal.
- Limitation detail is never read. A code that is not `[a-z][a-z0-9_]*` (64
  characters at most) becomes `limitation_code_unsafe`. More than 64
  distinct codes end with `limitation_codes_truncated`.

## Open items

- Exit values 20 to 32, state wire names and the limitation codes named
  above are provisional. A later CLI decision must confirm
  them before any operator script depends on them.
- Importing `msgloom.cli.a2_scope_status` imports the `msgloom.cli` package,
  which loads the app and its dependencies. A caller that needs a lighter
  import needs a decision to move the module.
- Nothing yet raises the blocked, busy or claim-lost errors. The caller
  that owns storage must raise them from typed results.

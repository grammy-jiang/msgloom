# A2 v2 async acceptance (C0-12c) and acceptance tests (C0-12d)

Status: PROVISIONAL. Research only. No database is opened except
`tmp_path` SQLite files in tests.

## C0-12c result: BLOCKED_PROTECTED_FILE

`msgloom/persistence/a2_acceptance_async.py` is not delivered. The module
needs one small hook in the protected file
`msgloom/persistence/async_store.py`. The supervisor must approve the hook.
This stage did not edit `async_store.py`.

### Feasibility check

Goal: write an accepted result through the existing semaphore, cancel drain
and close mechanisms of `Phase1Persistence`, with no direct use of the
private `_store` or `asyncio.to_thread`.

Evidence (read only, `async_store.py` at 442 lines):

- All three mechanisms live in one private method, `Phase1Persistence._call`
  (line 376). It takes the semaphore slot, counts the active call for
  `close`, and runs `_drain_thread`, which waits for the worker thread even
  after cancellation.
- Every public method of `Phase1Persistence` forwards to a named
  `Phase1Store` method (`append_result`, `acquire_claim`, `finish_claim`,
  and so on). No public method accepts a caller-supplied operation.
- `accept_result` (`a2_store.py`) needs a `sqlite3.Connection`, not a
  `Phase1Store`. `Phase1Store` has no A2 method and cannot gain one without
  editing the protected `store.py` and `schema_store.py`.
- `_call`, `_drain_thread` and `_await_task_uninterrupted` are private
  names. A subclass that calls `self._call`, or a copy of the drain code
  with its own `asyncio.to_thread`, is the reach-in the task forbids. A
  copy would also run outside the existing semaphore and close accounting.

Conclusion: composing only public API cannot reach the guarded
slot, so the facade is not feasible without a hook.

### Minimal hook for approval

| Item | Proposal |
| --- | --- |
| File | `msgloom/persistence/async_store.py` |
| Class | `Phase1Persistence` |
| Position | After `finalize_preparation_intake_workset`, before `close` (about line 333) |
| Signature | `async def run_bounded[T](self, operation: Callable[[], T]) -> T` |
| Body | `return await self._call(operation)` |
| Imports | None. `Callable` is already imported. |
| Line budget | About 12 lines with a docstring. 442 + 12 = 454 of 500. |
| Tests | Add one test to a new file that checks slot bound, cancel drain and close drain through `run_bounded`. |

Proposed text:

```python
    async def run_bounded[T](self, operation: Callable[[], T]) -> T:
        """
        Run one synchronous operation through the shared bounded worker slot.

        The operation must open and close every resource it uses inside the
        worker thread. It must not touch this facade's store. Cancellation is
        delayed until the thread ends. ``close`` waits for accepted calls and
        rejects later ones.
        """
        return await self._call(operation)
```

Rules the new facade would follow after approval:

1. `AcceptanceAsync(persistence, database_path)` holds the path, not a
   connection. SQLite connections are bound to their creating thread.
2. Each call opens `connect_existing(path)` inside the operation, runs
   `accept_result` or `get_accepted`, and closes the connection in a
   `finally` block. No connection crosses a thread.
3. A cancelled caller waits for the commit or rollback of the worker. The
   caller then reads the row back or replays the same receipt. A replay is
   idempotent (see C0-12d tests), so `on_cancel` cleanup is not needed.
4. `close` stays on `Phase1Persistence`. The facade adds no close of its
   own.

The same hook serves C0-13a (held and receipt async facade).

Rejected alternatives:

- Edit `async_store.py` in this stage: forbidden (protected).
- Subclass and call `_call`: private reach-in.
- New facade with its own semaphore and `asyncio.to_thread`: duplicates the
  mechanism and breaks the shared close boundary.

## C0-12d: `tests/persistence/test_a2_acceptance.py`

The manifest names no test path for C0-12d beyond this file. The tests
call only public functions of `a2_store`, `a2_schema`,
`a2_sqlite_store` and `a2_acceptance_models`. They add no production code.

Coverage:

| Area | Cases |
| --- | --- |
| Replay across attempts | Same key and body by attempts w1 and w2 is idempotent on the schema 5 store and on `A2ResearchStore`. The first writer proof stays. |
| Conflict | A different status, limitation set, payload SHA or metadata SHA (a rule-version change) under the same key is refused. Field names only. Stored row unchanged. |
| Concurrency | Real threads, one connection each, started by a barrier. Two and four legitimate claims, repeated rounds. Never more than one accepted row. |
| Post-commit cancel | An exception raised after `COMMIT` still leaves the committed row. A fresh connection reads it back. A replay returns `replayed`. |
| Rollback and crash | An error before `COMMIT`, a closed connection before `COMMIT` and a failed `COMMIT` leave no row. A second connection never sees uncommitted data. |
| PII | A canary in limitation text, claim data and the injected database error never appears in an error message, a stored attempt row or a stored record. |

### Findings

Recorded while writing the tests. No other module was edited.

1. Metadata SHA change is isolated. A change of only `rule_version` under
   the same key reports exactly `stage_metadata_sha256`. A changed payload
   SHA reports `canonical_sha256` and `stage_metadata_sha256`. A changed
   status reports `status`, `limitations_digest` and
   `stage_metadata_sha256`. Callers must not expect one field per cause.
2. `A2ResearchStore.accept_stage` does not check a live claim or a plan.
   Only `a2_store.accept_result` does. The research store is a decision
   rule test double, not an acceptance writer.
3. A repeat call by the same attempt does not add a second attempt row.
   Both stores deduplicate attempt rows by key, attempt and outcome.
4. Crash-style failure is simulated in process. A hook closes the
   connection right before `COMMIT`. A real process kill is not tested,
   because a portable child process needs importable test helpers. SQLite
   rollback of a killed writer is a SQLite guarantee, not module code.
5. The hook for C0-12c is the only missing behavior. Everything else the
   task named exists as public functions.
6. `tests/persistence/test_a2_acceptance.py` stays under 500 lines (497).
   Tests that need a second Python module would add a file in the
   allowlist.

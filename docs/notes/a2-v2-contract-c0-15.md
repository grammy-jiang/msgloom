# A2 v2 contract C0-15: public prepare surface (PROVISIONAL)

Code: `msgloom/a2_kedro/application_contract.py`.
Tests: `tests/a2_kedro/test_c0_15.py`.

This note records the research form of `async def prepare(...)`. All names
are PROVISIONAL. Nothing is wired into a CLI, Kedro, SQLite or a provider.

## Signature

`prepare(request, *, authority, worker, timeout_seconds) -> PrepareOutcome`

- `request`: `PrepareRequest` with `workset` and the caller-claimed `pin`.
- `authority`: trusted `AuthorityPin` from the Application layer.
- `worker`: injected async callable (`PrepareWorker`). It returns the
  `a2_completion_receipt@2` `ResultRef`.
- `timeout_seconds`: finite, above 0, at most 3600 (provisional).
- `AuthorityPin` fields: `workset`, `workset_sha256`,
  `configuration_version`, `code_version`, `partition_policy_version`.

## Rules

- Pre-flight runs before the worker. Order: request shape, Workset
  identity (`preparation_intake_workset@1`), deadline, missing pin, pin
  mismatch. A failure returns `REJECTED` and the worker never runs.
- Status is closed: `prepared`, `rejected`, `timed_out`, `failed`.
- Reason is closed: `ok`, `invalid_request`, `invalid_workset`,
  `invalid_timeout`, `pin_missing`, `pin_mismatch`, `deadline_exceeded`,
  `contract_violation`, `bad_worker_result`, `unexpected_error`.
- The deadline uses `asyncio.timeout` on the caller's running loop. A
  `TimeoutError` that the scope did not raise is a worker failure.
- `CancelledError` always propagates. It is never swallowed or mapped.
- `prepare` creates no loop. Tests patch `asyncio.run`,
  `asyncio.new_event_loop` and `asyncio.Runner` to fail, and they check the
  worker sees the caller's loop.
- An outcome holds no `str(exc)`. Tests check that a secret in an
  exception message does not reach the outcome.

## Open items

- Async test plugin: `pyproject.toml` configures none. The tests use the
  `anyio` pytest plugin, which is installed as a transitive dependency.
  `anyio` is not a direct dependency. Decide whether to declare it or to
  switch to `asyncio.run` inside sync tests.
- The pin field set is a candidate. C0-10 and C0-21a may add fields such
  as `trusted_scope_digest`.
- The deadline ceiling is provisional. The relation `L > E + 1 s`
  between lease and execution timeout belongs to the Application layer.
- The caller must map `CancelledError` to the bridge-closed protocol of
  the architecture. This module does not do it.

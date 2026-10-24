# A2 v2 semantics P3-07: replay-policy idempotency keys (PROVISIONAL)

Code: `msgloom/a2_kedro/semantics/replay_policy.py`.
Tests: `tests/a2_kedro/test_p3_07.py`.

## Rule

A change to configuration, policy or code version forms a new
idempotency key. The same input and the same policy always form the same
key.

## Records and functions

- `ReplayPolicy`: `policy_id`, `policy_version`, `config_digest`,
  `code_version`, `schema_version`. Strict, frozen, extra fields refused,
  input values hidden in validation errors.
- `config_digest(mapping)`: digest of a configuration mapping in domain
  `a2-replay-config@1`. Canonical JSON sorts mapping keys, so key order
  does not matter. List order stays significant. Floats are refused.
- `derive_replay_key(input_digest, policy)`: pure function. Returns
  `a2-replay:` plus the digest in domain `a2-replay-idempotency-key@1` of
  `{"input_digest": ..., "policy": <policy as JSON>}`.
- `ReplayKey`: frozen record of `key`, `input_digest` and `policy`. The
  validator recomputes the key, so a forged or stale record fails.
- `is_replay_key(text)`: shape check only.

## Reuse

No new hash scheme. Canonical bytes and the NUL-delimited domain prefix
come from `contracts.codec.domain_sha256`. Models extend
`result_base.ResultPart`.

## Decisions

- The key domain differs from `a2-stage-accepted-input@1` and the
  metadata domains. The `a2-replay:` prefix fails `is_accepted_key`, so a
  replay key cannot pass as an accepted stage key.
- The policy goes into the hash as a named JSON object, not a joined
  string, so field boundaries cannot shift.
- Keys are values. The module holds no state. A policy bump gives a new
  key and leaves the old key and record unchanged. Storing, and refusing
  to overwrite a stored key, belong to the caller (the ledger or store).
- `derive_replay_key` re-validates the policy, so a `model_construct`
  bypass cannot reach the hash.
- Errors use fixed text or hidden pydantic input. No digest, version or
  secret appears in an error.

## Known gaps

- Domain names and the prefix are provisional until C0-00.
- The module does not compute the input digest. The caller supplies it
  (for example from `StageIdentity`).
- Nothing yet calls this module. Wiring into a replay ledger is later work.
- `schema_version` is free text. It is not tied to `STAGE_SCHEMAS`.

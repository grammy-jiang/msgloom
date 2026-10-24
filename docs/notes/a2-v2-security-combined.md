# A2 v2 security combined lock candidate

Date: 2026-10-24. Base: master `895fc40`.

This is a candidate. It is not merged and not approved.

## Owner signature status

- The F0-09 and F0-10 owner signature is BLOCKED.
- This candidate is not a risk acceptance.
- The CI audit step stays red. See "Twisted residual".

## Result

- One lock-only change combines two source PRs. No other dependency changes.
- `pyproject.toml`, `.github/workflows/*`, and CI audit ignores are unchanged.
- No `kedro` package is in the lock. No prerelease Twisted is in the lock.
- `pyproject.toml` needs no change. No constraint pins these packages.

## Source PRs

| PR | Branch tip | Change |
| --- | --- | --- |
| PR72 | `55e9643` | `brotli` 1.2.0 to 1.2.1. `brotlicffi` 1.2.0.2 to 1.2.1.0. |
| PR75 | `2d66834` | `filelock` 4.0.3 to 4.2.4. |

Both branches have base `895fc40`. This work did not change either branch.
This work did not use the notes files of the source PRs.

## How the lock was made

Command, from the master lock:

```text
uv lock --upgrade-package brotli --upgrade-package brotlicffi \
  --upgrade-package filelock
```

Environment: `UV_CACHE_DIR=/tmp/uvcache-a2sec`,
`UV_PROJECT_ENVIRONMENT=/tmp/venv-a2-sec`. uv 0.12.24, CPython 3.13.16.

uv printed three updates and nothing else:

- `brotli` v1.2.0 to v1.2.1
- `brotlicffi` v1.2.0.2 to v1.2.1.0
- `filelock` v4.0.3 to v4.2.4

## Lock diff summary

- `git diff --stat 895fc40 -- uv.lock`: 80 insertions, 49 deletions, 1 file.
- A TOML comparison of package records found exactly three changed
  packages: `brotli`, `brotlicffi`, `filelock`.
- The `brotli` and `brotlicffi` records equal the records in PR72.
- The `filelock` record equals the record in PR75.
- Changed lines are only version, sdist URL and hash, and wheel URLs and
  hashes. No dependency edge or marker changed.
- No other package changed. No drift was found.

## Verification

All commands ran in this worktree.

| Command | Exit | Result |
| --- | --- | --- |
| `uv lock --check` | 0 | Lock is current. |
| `uv sync --frozen --group dev` | 0 | Installed. Locked versions are active. |
| `pytest -q -n0 tests/security/test_a2_lock_candidate.py` | 0 | 5 passed |
| `ruff check tests/security` | 0 | All checks passed |
| `ruff format --check tests/security` | 0 | 1 file formatted |
| `pyright tests/security/test_a2_lock_candidate.py` | 0 | 0 errors |
| Focused subset (below), `pytest -q -x -n0` | 0 | 43 passed, 85 s |
| Smoke: Scrapy `br` decode and `filelock` contention | 0 | See below |
| Smoke: `brotlicffi==1.2.1.0` round trip, isolated env | 0 | See below |
| `uv audit` (see "Audit") | 1 | Residual advisories |

Focused subset:

```text
tests/test_onedrive_content_privacy.py
tests/test_onedrive_content_crawl.py
tests/test_evidence_concurrent_blob.py
tests/test_scrapy_settings.py
tests/security
```

Smoke notes:

- Installed versions: `brotli` 1.2.1, `filelock` 4.2.4.
- `HttpCompressionMiddleware` decoded a `br` response. The body matched.
- `filelock` raised `Timeout` on contention and could lock again after release.
- `brotlicffi` is not installed on CPython. Its marker is
  `implementation_name == 'pypy'`. The round trip ran in a temporary isolated
  environment. The repository tests do not exercise it.

Full suite status: NOT COMPLETE.

- Command: `pytest -q -n 4 -m "not exclusive_state and not fastmcp_compat and
  not linux_cgroup_v2"`.
- The run would take more than 15 minutes on this host. Other worktrees used
  the CPU at the same time. I stopped it at about 59 percent.
- Before the stop, the progress lines showed 2808 passed tests and no failure,
  error, or skip. The partial run has no exit code. The exclusive-state group
  did not run.
- Treat the full suite as not run. The manager must run it in CI or a quiet
  host.

## Audit

Command: `uv audit --locked --no-progress --preview-features audit-command
--python-version V`, for V in 3.12, 3.13, 3.14.

| Form | 3.12 | 3.13 | 3.14 |
| --- | --- | --- | --- |
| Raw, no ignore (exit) | 1 | 1 | 1 |
| Raw, vulnerabilities found | 7 | 7 | 7 |
| CI form, with the two existing CI ignores (exit) | 1 | 1 | 1 |
| CI form, vulnerabilities found | 5 | 5 | 5 |

- The "CI form" is the command in `.github/workflows/ci.yml`. It has two
  existing `--ignore-until-fixed` entries. This work added no ignore.
- Master lock, raw, Python 3.13: 14 vulnerabilities. Candidate lock: 7.
  The 7 fewer are all Brotli and filelock findings.
- No `brotli`, `brotlicffi`, or `filelock` finding remains.

### Advisories fixed by this candidate

The table lists what `uv audit` reported on the master lock.

| Package | Advisory | Fixed in | Locked now |
| --- | --- | --- | --- |
| brotli | GHSA-9v8h-qqgm-4m35 | 1.2.1 | 1.2.1 |
| brotli | PYSEC-2026-4322 | 1.2.1 | 1.2.1 |
| brotlicffi | GHSA-9v8h-qqgm-4m35 | 1.2.1.0 | 1.2.1.0 |
| brotlicffi | PYSEC-2026-4323 | 1.2.1.0 | 1.2.1.0 |
| filelock | GHSA-v4x8-3wr5-3wq8 | 4.2.1 | 4.2.4 |
| filelock | GHSA-9vhv-jxww-xfm5 | 4.2.1 | 4.2.4 |
| filelock | GHSA-567q-5qvw-pf92 | 4.2.1 | 4.2.4 |

The PR75 note lists three more filelock advisories from the GitHub database:
GHSA-jqc4-5cvw-7w85, GHSA-2g95-wg33-c5x2, GHSA-crv4-6mhj-j5jh. All are fixed in
4.2.1. `uv audit` did not report them on the master lock.

### Twisted residual

Twisted 26.4.0 stays locked. These advisories remain.

| Advisory | Fixed in | Non-prerelease fix |
| --- | --- | --- |
| GHSA-2qrf-pqgx-qh9v | 26.10.0rc1 | No |
| GHSA-53xc-49m8-p798 | 26.10.0rc1 | No |
| GHSA-cwm5-jh59-mwxr | 26.10.0rc1 | No |
| GHSA-3476-c5c2-fr73 | 26.10.0rc1 | No |
| GHSA-q7qq-6mhp-9rc4 | 26.10.0rc1 | No |
| PYSEC-2026-4304 | none listed | No |

- No non-prerelease fix exists for any Twisted advisory.
- The only fixed version is a release candidate. This work did not lock it.
- PYSEC-2026-4304 is hidden in the CI form. The existing CI ignore
  GHSA-8pqf-f4m5-798g removes it. The raw run shows it.
  This is inferred from the counts (6 raw, 5 in CI form). It is not confirmed
  by an alias lookup.
- PYSEC-2017-83 (Scrapy 2.19.0, no fix versions) is also in the raw run.
  The existing CI ignore hides it.
- **The audit stays red.** `uv audit` exits 1. This candidate does not
  change that. Nothing is hidden or ignored by this work.

## Compatibility notes

- `brotli` 1.2.1 and `brotlicffi` 1.2.1.0 are patch-level releases. Scrapy
  2.19.0 requires both without an upper bound.
- `brotli` applies on CPython. `brotlicffi` applies only on PyPy.
- `filelock` 4.2.4 is a transitive dependency. The runtime path is Scrapy,
  then `tldextract`, then `filelock`. The repository does not import it.
- The tests do not exercise `filelock` directly. The smoke test did.
- `brotli` 1.2.1 and `filelock` 4.2.4 are days old. A reviewer can choose
  `filelock` 4.2.1 with `uv lock --upgrade-package filelock==4.2.1`.
- The lock test checks minimum versions only. It also checks that `kedro`
  and prerelease Twisted are absent.

## Open items

- Owner signature F0-09 and F0-10: BLOCKED.
- Twisted: policy decision needed. No non-prerelease fix exists.
- Merge order of PR72 and PR75 against this candidate: manager decision.

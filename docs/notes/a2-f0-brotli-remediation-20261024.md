# A2 F0 Brotli remediation candidate (2026-10-24)

Status: draft candidate. This is not production dependency admission.
The manager must review, commit, and gate this change.

## Result

A lock-only change fixes the Brotli advisories. `pyproject.toml` is unchanged.

| Package | Before | After | Advisories fixed |
| --- | --- | --- | --- |
| `brotli` | 1.2.0 | 1.2.1 | PYSEC-2026-4322, GHSA-9v8h-qqgm-4m35 |
| `brotlicffi` | 1.2.0.2 | 1.2.1.0 | PYSEC-2026-4323, GHSA-9v8h-qqgm-4m35 |

## Entry path

- Scrapy 2.19.0 declares both packages as direct dependencies.
- `brotli` applies when `implementation_name != 'pypy'`. This covers CPython
  on arm64.
- `brotlicffi` applies when `implementation_name == 'pypy'`. CPython does
  not install it.
- `pyproject.toml` has no Brotli pin or extra.
- Both fixed versions exist on the configured index (pypi.org). `brotli`
  1.2.1 was uploaded on 2026-10-22. The repo has no minimum-release-age
  rule in `renovate.json` or `pyproject.toml`.

## Commands and exit codes

All commands ran in the worktree. uv 0.12.24, CPython 3.13.16, aarch64.

| Step | Command (short form) | Exit |
| --- | --- | --- |
| Venv check | `uv run --frozen python -c 'import sys;print(sys.prefix)'` | 0 |
| Baseline `uv audit` run | CI `uv audit` command, Python 3.12, 3.13, 3.14 | 1, 1, 1 |
| Dry run | `uv lock --upgrade-package brotli --upgrade-package brotlicffi --dry-run` | 0 |
| Lock | `uv lock --upgrade-package brotli --upgrade-package brotlicffi` | 0 |
| Sync | `uv sync --locked --group dev` | 0 |
| Smoke (brotli) | Import, compress/decompress, `HttpCompressionMiddleware` `br` decode | 0 |
| Smoke (brotlicffi) | Isolated env with `brotlicffi==1.2.1.0`, round trip | 0 |
| Tests | `pytest tests/test_onedrive_content_privacy.py tests/test_onedrive_content_crawl.py` | 0 (25 passed) |
| `uv audit` run after | Same CI `uv audit` command, Python 3.12, 3.13, 3.14 | 1, 1, 1 |

- `sys.prefix` was the worktree-local `.venv`. No shared environment changed.
- The `uv audit` command was the one in `.github/workflows/ci.yml`, including its
  two existing `--ignore-until-fixed` entries. This work added no ignore.
- The OneDrive content tests are the only tests that touch content encoding.
- The `brotlicffi` smoke ran in a temporary `uv run --isolated` environment
  because CPython does not install it.
- The `brotli` smoke printed a Scrapy deprecation warning for the `spider`
  argument of `process_response()`. The warning comes from the smoke script.

## Lock diff

`git diff --stat`: `uv.lock | 125 +++++-----` (78 insertions, 47 deletions).
All hunks are inside the `brotli` and `brotlicffi` package blocks. They change
the version, sdist URL and hash, and wheel URLs and hashes. No other package
changed.

## Advisory findings before and after

Before: `brotli`, `brotlicffi`, `filelock`, and `twisted` had findings.
After: `filelock` and `twisted` still have findings. The result is the same
on Python 3.12, 3.13, and 3.14. The `uv audit` step still exits 1.

Remaining findings, recorded as-is, with no ignore added:

- `filelock` 4.0.3 (fixed in 4.2.1): GHSA-v4x8-3wr5-3wq8,
  GHSA-9vhv-jxww-xfm5, GHSA-567q-5qvw-pf92.
- `twisted` 26.4.0 (fixed in 26.10.0rc1): GHSA-2qrf-pqgx-qh9v,
  GHSA-53xc-49m8-p798, GHSA-cwm5-jh59-mwxr, GHSA-3476-c5c2-fr73,
  GHSA-q7qq-6mhp-9rc4.

No Kedro finding appeared in this lock. This work did not change Twisted,
Kedro, or `pypydispatcher`.

## Open issues

- The CI `uv audit` step still fails because of `filelock` and `twisted`. This
  change alone does not turn it green.
- `filelock` 4.2.1 is a fixed release. Check separately whether a lock-only
  upgrade is clean.
- The only Twisted fix is a release candidate (26.10.0rc1). Policy review is
  required before any pin change.
- `brotli` 1.2.1 is two days old. Review its release before admission.

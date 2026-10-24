# A2 F0 filelock repair candidate

This is a candidate. It is not merged and not approved. It needs an
independent exact-SHA review before any merge.

## Result

- `uv.lock` moves `filelock` from 4.0.3 to 4.2.4.
- Only the `filelock` record changes: version, sdist URL and hash, wheel URL
  and hash.
- `uv audit` no longer lists `filelock` on Python 3.12, 3.13, and 3.14.
- `uv audit` still exits 1 on all three versions. `brotli`, `brotlicffi`, and
  `twisted` remain. This change does not address them.

## Advisory facts

Source: GitHub advisory database (`gh api /advisories?affects=filelock`),
read on 2026-10-24. Six advisories were published on 2026-10-23. All six
name 4.2.1 as the first patched version.

| Advisory | Severity | Affected range | Fixed |
| --- | --- | --- | --- |
| GHSA-v4x8-3wr5-3wq8 | high | >= 3.20.4, <= 4.2.0 | 4.2.1 |
| GHSA-jqc4-5cvw-7w85 | medium | >= 4.1.0, <= 4.2.0 | 4.2.1 |
| GHSA-2g95-wg33-c5x2 | medium | >= 4.1.0, <= 4.2.0 | 4.2.1 |
| GHSA-crv4-6mhj-j5jh | medium | >= 4.1.0, <= 4.2.0 | 4.2.1 |
| GHSA-9vhv-jxww-xfm5 | low | >= 3.20.4, <= 4.2.0 | 4.2.1 |
| GHSA-567q-5qvw-pf92 | low | >= 3.22.0, <= 4.2.0 | 4.2.1 |

Earlier advisories (GHSA-qmgc-5h2g-mvrw, GHSA-w853-jp5j-5j7f) are fixed in
3.20.3 and 3.20.1. They do not affect 4.0.3 or later.

The earlier F0 Brotli report listed three of these (GHSA-v4x8-3wr5-3wq8,
GHSA-9vhv-jxww-xfm5, GHSA-567q-5qvw-pf92) for 4.0.3. Three more
(GHSA-jqc4-5cvw-7w85, GHSA-2g95-wg33-c5x2, GHSA-crv4-6mhj-j5jh) are in the
advisory database now. All six are fixed at 4.2.1 or later.

## PyPI releases (from `https://pypi.org/pypi/filelock/json`)

None of the releases below is yanked. The latest release is 4.2.4.

| Version | Upload (UTC) | Wheel sha256 | Sdist sha256 |
| --- | --- | --- | --- |
| 4.0.3 | 2026-09-23 | 30cd166e...bacfab | 87296d60...e87a8aa |
| 4.2.1 | 2026-10-17 | 7be2662e...7905ae44 | c4c937cc...cc1c5d5a3 |
| 4.2.4 | 2026-10-19 | 30124143...db8358e | c6d86635...499d163d |

The hashes in `uv.lock` for 4.2.4 match the PyPI values:

- wheel `301241438c57936ef93f4243a94f2559022268bfcf9b375a9a72eb0f8db8358e`
- sdist `c6d8663535e1650ee430507b4ffbac7b464dd64b7647ea0112a9f406499d163d`

## Why 4.2.4 and not 4.2.1

The native command `uv lock --upgrade-package filelock` selects the newest
release that the constraints allow. No constraint in `pyproject.toml` pins
`filelock`. `filelock` is a transitive dependency. The runtime path is
`scrapy` -> `tldextract` -> `filelock`. The development path is
`virtualenv`, `python-discovery`, `tox`, and `pre-commit`. 4.2.4 is after
the fixed release 4.2.1, so it carries the fixes. I did not review the
4.2.2 to 4.2.4 changelogs. A reviewer can choose 4.2.1 instead with
`uv lock --upgrade-package filelock==4.2.1`. Release age is a factor: 4.2.4
is five days old on 2026-10-24.

## Command log

Base: `895fc40a0ec889bd96f620df8c62491787218217`, uv 0.12.24.

| Command | Exit |
| --- | --- |
| `uv lock --upgrade-package filelock` | 0 |
| `uv lock --check` | 0 |
| `uv venv /tmp/w2-venv --python 3.13` | 0 |
| `UV_PROJECT_ENVIRONMENT=/tmp/w2-venv uv sync --frozen --group dev` | 0 |
| `python -I` smoke test: import, acquire, contention timeout, release | 0 |
| `pytest tests/packaging tests/configuration -q` (55 passed, 4 skipped) | 0 |
| `pre-commit run --files uv.lock docs/notes/a2-f0-filelock-candidate.md` | 0 |
| `uv audit --locked ... --python-version 3.12` | 1 |
| `uv audit --locked ... --python-version 3.13` | 1 |
| `uv audit --locked ... --python-version 3.14` | 1 |

The audit command matches the CI step in `.github/workflows/ci.yml`,
including its two existing scope-restricted `--ignore-until-fixed` entries.
This change adds no ignore.

The repository source and tests do not import `filelock`. The smoke test
and the pytest subset therefore show that the isolated environment installs
and imports the new release. They do not exercise `filelock` through
repository code. The 4 skipped tests come from existing skip conditions
in those directories.

## Full diff summary

`git diff` touches only `uv.lock`: 3 lines added and 3 removed. The changes
are the `filelock` `version`, the `sdist` line, and the single `wheels`
entry. No other package record, dependency edge, or `pyproject.toml` line
changes.

## Remaining findings (same on Python 3.12, 3.13, 3.14)

- `brotli` 1.2.0: GHSA-9v8h-qqgm-4m35, PYSEC-2026-4322 (fixed in 1.2.1).
- `brotlicffi` 1.2.0.2: GHSA-9v8h-qqgm-4m35, PYSEC-2026-4323 (fixed in
  1.2.1.0).
- `twisted` 26.4.0: GHSA-2qrf-pqgx-qh9v, GHSA-53xc-49m8-p798,
  GHSA-cwm5-jh59-mwxr, GHSA-3476-c5c2-fr73, GHSA-q7qq-6mhp-9rc4. The only
  fixed release is a release candidate (26.10.0rc1).

## Remaining risks

- The CI audit step stays red until Brotli and Twisted are resolved.
- New `filelock` advisories can appear. The advisory data was read on
  2026-10-24.
- `filelock` is in the runtime closure through `tldextract` (used by
  Scrapy). The repository does not call it directly. A synthetic
  `tldextract.TLDExtract(suffix_list_urls=())` call with a temporary cache
  directory and a `python -I` import of the Scrapy offsite middleware
  worked with 4.2.4 (exit 0).

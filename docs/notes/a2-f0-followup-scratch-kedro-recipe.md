# A2 F0 follow-up: scratch Kedro recipe and controlled runner

Date: 2026-10-24. Base: PR74 SHA `d2adcc9`.

This note is research evidence. It does not admit Kedro. The default
msgloom environment and test run stay free of Kedro. The Twisted pin,
`pyproject.toml`, `uv.lock` and CI are unchanged.

## Result

- `scripts/research/a2_f0_scratch_kedro_env.py` builds a scratch venv with
  Kedro 1.7.0 from a hash-pinned file. It runs the 69 pure-Python controls
  and the 9 Kedro-dependent controls with one command.
- The default `pytest` collection (4769 tests in `tests`) imports no Kedro
  module. The 9 Kedro tests live in a file that does not match `test_*.py`.
  The gate plugin also deselects them unless `A2_F0_KEDRO_OPT_IN=1`.
- With the opt-in and no interpreter, the 9 tests fail with "NOT VERIFIED".
  They do not skip.

## Commands

```text
python scripts/research/a2_f0_scratch_kedro_env.py build /path/outside/repo
python scripts/research/a2_f0_scratch_kedro_env.py run   /path/outside/repo
```

The venv path is required. The recipe refuses a path that is:

- inside this worktree or the main checkout of the same repository;
- inside any `.venv` directory;
- inside the prefix of the running interpreter;
- an existing non-empty directory that the recipe did not create.

`build` uses `uv venv --no-config` and `uv pip install --no-config
--default-index https://pypi.org/simple --require-hashes --only-binary :all:
--no-deps`. The child environment is an allowlist (`PATH`, `HOME`, locale,
temp, uv cache and certificate variables). Tokens in the caller environment
do not reach uv. The recipe limits the index to PyPI. It disables uv Python downloads, so
the build needs a local Python 3.13. It cannot block other traffic at the
packet level.

`run` starts two pytest processes. Both load `a2_f0_pytest_gate`. The second
one sets `A2_F0_KEDRO_OPT_IN=1` and `A2_F0_KEDRO_PYTHON`. `run` exits
non-zero on any failure, any skip, a hash mismatch between the venv marker
and the requirements file, or a test count other than 69 and 9.

## Hash source

`scripts/research/a2_f0_scratch_kedro_requirements.txt` has 40 pinned
entries (39 for Linux, plus `colorama` for Windows). It holds 470 SHA-256
hashes. They come from the PyPI simple index. uv 0.12.24 read it on
2026-10-24:

```text
uv pip compile in.txt --universal --python-version 3.12 --generate-hashes \
    --only-binary :all: --no-header --no-annotate
```

`in.txt` holds `kedro==1.7.0` and `kedro-telemetry==0.9.0`. The package set
matches the earlier `/tmp` scratch venv (39 packages). A test checks that
each entry has a pin and a hash and has no URL or VCS source.

## Open items

- UNKNOWN: whether PyPI hashes equal the hashes of an independent source.
  The file trusts the PyPI index at generation time.
- The venv uses the system CPython 3.13 that uv finds. Other Python
  versions were not tried.
- CI integration is not part of this work. The runner is a manual command.
- Kedro CVE-2026-3840 stays an open risk. The owner has not decided. This
  work does not accept it.

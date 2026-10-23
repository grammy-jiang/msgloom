# A2 Kedro F0-01: version and wheel provenance

Date: 2026-10-24. Host: Raspberry Pi 5, Linux aarch64.
Task: F0-01 (re-verify the Kedro 1.7 wheel). Branch:
`research/a2-kedro-f0-20261024`, base `895fc40`.

## Pending items in this evidence set

PENDING: two cells in the co-install note (`a2-kedro-f0-coinstall.md`).
They are the full pytest run on Python 3.12.14 (`FULL_312`, with
`FULL_312_EXIT` and `FULL_312_RESULT`) and on Python 3.14.7 (`FULL_314`,
with `FULL_314_EXIT` and `FULL_314_RESULT`). Both runs were still running
when this note was committed. No value is recorded and none is guessed.
The 3.13.16 full run is final: 4705 passed, exit 0.

No row in this note depends on those two cells.

## Result

The PyPI wheel `kedro-1.7.0-py3-none-any.whl` matches the expected SHA-256.
The hash check exited with code 0. The candidate version was not changed.

| Item | Value |
| --- | --- |
| Project and version | `kedro` 1.7.0 (PyPI JSON `info.version`) |
| Wheel SHA-256 | `488701a27c7d595b62a611cb23596953a9929fe5cc42a376c28abe26654c2438` |
| Expected SHA-256 | Same value (handoff and Q0 R2 note) |
| Wheel size | 248245 bytes |
| Wheel upload time | 2026-09-28T16:13:26Z |
| sdist SHA-256 (PyPI JSON only) | `50b654c0f6ec79c465bc913c1680ea6ad35fff287160262dce7f9d4c1bdbd493` |
| Requires-Python | `>=3.10` |
| Wheel tag | `py3-none-any` (pure Python, universal) |
| Yanked | No (PyPI JSON `yanked: false`) |
| Wheel generator | setuptools 84.0.0 |

The sdist was listed only for completeness. It was not downloaded and was
not built. Its hash comes from the PyPI JSON only.

## Source URLs

- PyPI JSON API: `https://pypi.org/pypi/kedro/json`
- Project page: `https://pypi.org/project/kedro/1.7.0/`
- Wheel URL (from the JSON `urls` entry):
  `https://files.pythonhosted.org/packages/20/34/0e59b24df34190198129834e1e35a027767f695196e2acc77e6edd77463b/kedro-1.7.0-py3-none-any.whl`

## Commands and exit codes

Scratch root: `/tmp/f0-scratch-20261024/`. The wheel went into a new,
empty directory. Scripts live in a different directory.

| Step | Command (abridged) | Exit code |
| --- | --- | --- |
| Fetch release metadata | `curl -sS -o json/kedro.json https://pypi.org/pypi/kedro/json` | 0 |
| Download wheel | `curl -fsS -O <wheel URL>` in `wheel/dl2/` | 0 |
| Verify hash | `echo "<expected>  kedro-1.7.0-py3-none-any.whl" \| sha256sum -c -` | 0 (`OK`) |
| Print hash | `sha256sum kedro-1.7.0-py3-none-any.whl` | 0 |
| Negative control | same check with an all-zero hash | 1 (`FAILED`) |
| Zip integrity and names | `python -I` with `zipfile.testzip()` and name scan | 0 |

Observations:

- `sha256sum` printed
  `488701a27c7d595b62a611cb23596953a9929fe5cc42a376c28abe26654c2438`.
- `testzip()` returned `None`. The archive has 127 entries. No entry has an
  absolute path or a `..` component.
- A first download attempt used a guessed URL and produced a 0-byte file.
  That file was discarded. The verified download used the URL from the PyPI
  JSON. No result in this note comes from the discarded file.
- The negative control proves that the hash check can fail.

## Source version inside the wheel

- `kedro-1.7.0.dist-info/METADATA`: `Name: kedro`, `Version: 1.7.0`,
  `Requires-Python: >=3.10`.
- `kedro/__init__.py` line 16: `__version__ = "1.7.0"`.
- `kedro-1.7.0.dist-info/entry_points.txt`: one console script,
  `kedro = kedro.framework.cli:main`.
- `Requires-Dist` includes `kedro-telemetry>=0.5.0` with no extra marker.
  Kedro 1.7.0 declares it as a core dependency. F0-04 tests its behavior.
- Core `Requires-Dist` (no extra): `attrs`, `build`, `click>=8.2`,
  `cookiecutter<3.0`, `dynaconf<4.0`, `fsspec`, `gitpython`,
  `kedro-telemetry`, `more_itertools`, `omegaconf`, `parse`, `pluggy`,
  `PyYAML<7.0`, `rich<16.0`, `tomli` (Python below 3.11), `tomli-w`,
  `typing_extensions`.

## Available Python versions on the Pi

Command: `uv python list` (uv 0.12.24). Exit code 0. Installed
interpreters (aarch64, glibc):

| Series | Installed version | Path kind |
| --- | --- | --- |
| 3.12 | 3.12.14 | uv-managed |
| 3.13 | 3.13.16 (uv-managed) and 3.13.5 (system `/usr/bin/python3.13`) | both |
| 3.14 | 3.14.7 | uv-managed |

The list also shows downloadable but not installed builds: 3.12.15, 3.14.8,
3.15.0rc3 and free-threaded builds. The project `requires-python` is
`>=3.12`. The CI audit loop covers 3.12, 3.13 and 3.14.

The local uv is 0.12.24. CI pins uv 0.13.5
(`.github/workflows/ci.yml`, `setup-uv` `version: "0.13.5"`). Results from
the local uv may differ from CI results. See F0-07.

## Q0 matrix summary

Source: the Q0 worktree `a2-kedro-q0-20261023`, files
`docs/notes/a2-kedro-q0-r2-qualification-20261023.md`,
`a2-kedro-q0-r2-matrix-20261023.json` and
`a2-kedro-q0-r2-independent-acceptance-20261023.md`. This worker read the
R2 qualification note. This worker did not re-run the Q0 matrix.

What Q0 R2 reports:

- 6 process runs (CPython 3.12.14, 3.13.16, 3.14.7; normal and `-O` modes).
  Each run reports 20 of 20 named synthetic checks and exit code 0.
- The checks cover a Kedro DAG with a typed source load, a parser dataset,
  a claim-fenced stage dataset, replay idempotence, injected failures,
  cancellation drain, a heartbeat during CPU work, log redaction, an
  explicit telemetry opt-out, an active socket-block control, and the
  exact-wheel version-path validator.
- A scratch lock of the project plus Kedro went from 146 to 166 packages:
  20 added, 0 upgraded, 0 removed.
- The R2 note records that `uv audit --frozen` exited 1 on both the original
  and the candidate scratch locks, with the same two reports
  (PYSEC-2017-83 and GHSA-8pqf-f4m5-798g).

What Q0 did not prove (limits stated by Q0 itself):

- It used synthetic data and a fake in-memory store. It did not use SQLite,
  `Phase1Persistence`, `ClaimToken` or cross-process fencing.
- It was not an OS-level network sandbox. It does not prove that all future
  hooks lack network access.
- It did not run native parser workers (calamine, pdfium, lxml) under load.
- It did not test the installed `msgloom` wheel together with Kedro. That is
  F0-05a.
- It did not settle the Snyk CVE-2026-3840 difference. That is F0-02.
- It is not production dependency approval.

This note adds one fact that Q0 did not record: the wheel hash was
recomputed from a fresh download in this task (exit code 0).

## Status / Open items

- F0-01: DONE for hash, version, upload date and Requires-Python.
- Open: the sdist hash is a PyPI JSON claim. The sdist was not
  downloaded, so this task did not verify it.
- Open: PyPI metadata and hash match only prove that the file is the one
  PyPI serves today. They do not prove that the upstream source repository
  produced it. No provenance attestation was checked.
- Open: the local uv (0.12.24) differs from the CI uv (0.13.5).
- No STOP condition was found.

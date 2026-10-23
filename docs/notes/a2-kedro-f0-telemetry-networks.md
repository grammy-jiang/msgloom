# A2 Kedro F0-04: telemetry plugin and network behavior

Date: 2026-10-24. Task: F0-04. Candidate: `kedro` 1.7.0 (wheel SHA-256
`488701a27c7d595b62a611cb23596953a9929fe5cc42a376c28abe26654c2438`).

## Full-suite results (final)

The full normal pytest set finished on all three Python versions.

| Python | Exit code | Result |
| --- | --- | --- |
| 3.12.14 | 0 | 4705 passed, 42 min 17 s |
| 3.13.16 | 0 | 4705 passed, 24 min 9 s |
| 3.14.7 | 1 | 1 failed, 4704 passed, 43 min 0 s |

The 3.14.7 failure is
`tests/container_deployment/test_container_qualification.py::test_real_local_container_timeout_is_removed_if_image_present`.
The 3.12.14 and 3.14.7 runs ran at the same time. That test uses the fixed
Docker container name `msgloom-qual-pytest-timeout`. A name collision between
the two runs is a likely cause. It is not proven. The same test passed alone
on 3.14.7 in two runs (exit 0 each). This failure is an open item for the
security owner. Logs: `/tmp/f0-scratch-20261024/f05b/logs/`
(`pytest-normal-cand-3.12.out`, `pytest-normal-cand-3.14.out`,
`exitcodes.txt`).

## Result

`kedro-telemetry` is a forced dependency of Kedro 1.7.0. Kedro 1.7.0
declares `Requires-Dist: kedro-telemetry>=0.5.0` with no extra. The scratch
install pulled `kedro-telemetry` 0.9.0, which depends on `requests`.

In a network-less sandbox, plain use of Kedro (import plus an in-memory
pipeline run, no session) made 0 network attempts. A `KedroSession` with
default consent made a DNS lookup for `heapanalytics.com`. With an opt-out,
or with the plugin disabled, it made 0 attempts.

The plugin treats missing consent as consent (opt-out model). Any msgloom
design that uses `KedroSession` or loads `kedro.hooks` entry points needs an
explicit control. This note records observations. It does not approve any
design.

## STOP conditions

- No unexpected network attempt occurred in the planned path (modes A, B).
- STOP for any design that uses `KedroSession`, or registers `kedro.hooks`
  entry points, without an opt-out control. Mode G shows the real plugin
  starts a lookup for `heapanalytics.com` under those conditions. In this
  test the sandbox blocked it, so no data left the host.

## Test method

Each mode ran in a fresh process with the following controls.

- Network: `unshare -rn` (user and network namespace). Only a down
  loopback interface exists. No packet can leave. Checked with
  `unshare -rn sh -c 'ip -brief link'` (exit 0, shows only `lo DOWN`).
- Recording: the probe replaces `socket.socket.connect`, `connect_ex`,
  `socket.getaddrinfo`, `gethostbyname` and `create_connection`. Each
  replacement records the call and raises `OSError`. A recorded
  `getaddrinfo` call means the code tried a DNS lookup.
- Isolation: `env -i`; `HOME` and `XDG_CONFIG_HOME` point to a fresh
  directory per mode. The probe lists new files under `HOME`. Current
  directory is a fresh directory. The consent variables are unset except
  where a mode sets them.
- Interpreter: `python -I` from the scratch venv `venv-kedro` (CPython 3.13,
  kedro 1.7.0 and kedro-telemetry 0.9.0 installed with `--only-binary :all:`).
  The probe script and the runner live outside the work directories.
- This is not a null plugin test. The real `kedro_telemetry.plugin` module
  and its real `requests`-based sender were active. Mode G ran the real
  entry-point hook through `KedroSession`.

Scripts (SHA-256): `scripts/f0_04_telemetry.py`
`be96c63fcc8699ab3ebec7f6ad73402c5faa139f570a921be93a496d1c26e51a`;
`scripts/run_f0_04.sh`
`c79e695361c6c7cb0d186e3d0ad8c57af1c42f81060a44e7a281c324349a05bb`.

## Results by mode

All nine runs exited with code 0. Outputs are in
`/tmp/f0-scratch-20261024/f0-04/<mode>/out.json`.

| Mode | What ran | Consent setting | Socket attempts | New files under HOME |
| --- | --- | --- | --- | --- |
| A import and run | Import `kedro.io`, `kedro.pipeline`, `kedro.runner`; run a one-node in-memory pipeline with `SequentialRunner`; no session | none | 0 | none |
| B entry-point hooks | Build a hook manager, register `kedro.hooks` entry points, run the pipeline | none | 0 | none |
| C hook, implicit consent | Real `KedroTelemetryHook`: `after_context_created` then `after_catalog_created` | none (check returns `None`) | 1: `getaddrinfo('heapanalytics.com')` | `.config/kedro/telemetry.toml` |
| D hook, env opt-out | Same sequence as C | `DO_NOT_TRACK=1` (check returns `False`) | 0 | none |
| E hook, no context step | Only `after_catalog_created` | `DO_NOT_TRACK=1` | 0 (see note below) | `.config/kedro/telemetry.toml` |
| F hook, file opt-out | Same sequence as C | `.telemetry` file, `consent: false` | 0 | none |
| G session, default | Minimal project, `KedroSession.create`, `session.run` | none | 1: `getaddrinfo('heapanalytics.com')` | `.config/kedro/telemetry.toml` (and the project `pyproject.toml` was appended to) |
| H session, env opt-out | Same project | `DO_NOT_TRACK=1` | 0 | none |
| I session, plugin disabled | Same project, `DISABLE_HOOKS_FOR_PLUGINS = ("kedro-telemetry",)` | none | 0 | none |

Extra observations:

- Mode A and B: `kedro_telemetry` and `requests` are not imported by
  `import kedro` alone. They load when entry-point hooks are registered
  (mode B) or when the plugin module is imported.
- Mode B: registering entry points with an empty disable tuple registered
  one plugin, `kedro-telemetry`. Registering with the disable tuple
  `("kedro-telemetry",)` registered none.
- Mode E: with the environment opt-out set but the context step skipped,
  `after_catalog_created` still ran its UUID step and wrote
  `telemetry.toml`. It then failed with `AttributeError` for the missing
  attribute `_consent_is_implicit`, before any network call. The plugin
  reads the consent decision in `after_context_created`. Out-of-order use
  skips that decision. The failure stopped the send in this version. That
  is not a designed control.
- Mode C, E, G: the plugin wrote a random UUID file to
  `~/.config/kedro/telemetry.toml` (via `appdirs.user_config_dir("kedro")`).
  That is a file write outside the project.
- Mode A: Kedro printed 2025 bytes of Rich-formatted log lines to stdout.
  The first line says `Using '.../kedro/framework/project/rich_logging.yml'
  as logging configuration`. Kedro configures logging when it loads
  `kedro.framework.project`. A msgloom process with its own stdout contract
  would see this output. The probe captured it. It did not reach the real
  stdout. This matches the Q0 R2 remark about stdout.
- Mode G stdout is 7614 bytes. Modes H and I are 6237 bytes. The cause of
  the 1377-byte difference was not isolated (the probe stored only the
  first 300 bytes). It is not shown to be the plugin consent notice.
- Mode G: the plugin appended a `[tool.kedro_telemetry]` table with a
  random `project_id` to the scratch project's `pyproject.toml`. Modes H
  and I did not change that file. The code does this only when the file has
  a `[tool.kedro]` section (`_get_or_create_project_id`). The msgloom
  `pyproject.toml` has no such section. This task did not test a project
  without `[tool.kedro]`.
- stderr was 0 bytes in every run that exited with code 0.

## Plugin source facts (kedro-telemetry 0.9.0, `plugin.py`)

- Endpoint constant: `HEAP_ENDPOINT = "https://heapanalytics.com/api/track"`.
  `_send_heap_event` calls `requests.post(..., timeout=10)`.
- `_check_for_telemetry_consent` returns `False` if `DO_NOT_TRACK` or
  `KEDRO_DISABLE_TELEMETRY` is set to any non-empty value, if
  `GITHUB_REPOSITORY_OWNER == "kedro-org"`, or if `<project>/.telemetry`
  holds `consent: false`. It returns `None` otherwise. `None` is treated as
  implicit consent.
- The `.telemetry` file is read only when a `project_path` is known.
- Hook registration: the wheel declares entry points `kedro.hooks` and
  `kedro.cli_hooks`, both to `kedro_telemetry.plugin:telemetry_hook`.
  The Kedro session code calls `_register_hooks_entry_points(hook_manager,
  settings.DISABLE_HOOKS_FOR_PLUGINS)` (`session.py:121`,
  `service_session.py:75`).
- `SequentialRunner.run(..., hook_manager=None)` uses a null plugin manager
  (`runner.py`: `hook_manager or _NullPluginManager()`). Without a session
  or an explicit hook manager, the telemetry hook does not run.
- Properties built by `_get_project_properties` (source reading): the
  user UUID as `username`, a SHA-512 hashed project id, Kedro and plugin
  versions, the full `sys.version` string, `sys.platform`, a CI flag, tool
  properties from `pyproject.toml`, and project statistics. This task read the source. It did not capture a
  payload.

## Commands and exit codes

| Command | Exit code |
| --- | --- |
| `uv venv --python 3.13 venv-kedro` | 0 |
| `uv pip install --only-binary :all: kedro-1.7.0-py3-none-any.whl` | 0 |
| `unshare -rn sh -c 'ip -brief link'` | 0 |
| `scripts/run_f0_04.sh A_import_run` | 0 |
| `scripts/run_f0_04.sh B_entrypoint_hooks` | 0 |
| `scripts/run_f0_04.sh C_hook_implicit` | 0 |
| `scripts/run_f0_04.sh D_hook_env_optout DO_NOT_TRACK=1` | 0 |
| `scripts/run_f0_04.sh E_hook_skip_context DO_NOT_TRACK=1` | 0 |
| `scripts/run_f0_04.sh F_hook_file_optout` | 0 |
| `scripts/run_f0_04.sh G_session_default` | 0 |
| `scripts/run_f0_04.sh H_session_env_optout DO_NOT_TRACK=1` | 0 |
| `scripts/run_f0_04.sh I_session_plugin_disabled` | 0 |

The first run of modes A and B failed with exit code 1 because the probe
tried to serialize dataset objects. The first run of G, H and I failed with
exit code 1 because the test pipeline input `a` was missing from the
catalog. The scripts were fixed and the modes were rerun. Only the reruns
are reported above. The first runs made no socket attempt that this note
relies on.

## Candidate controls (design options, not tested as a package)

- Never create a `KedroSession` or `ServiceSession` in msgloom. Run
  `Pipeline`, `DataCatalog` and `SequentialRunner` directly (modes A, B).
- Never register `kedro.hooks` entry points.
- If a session is ever needed, set `DISABLE_HOOKS_FOR_PLUGINS` (mode I) and
  set `DO_NOT_TRACK=1` (mode H).
- Add a test that runs the msgloom Kedro bridge in a network namespace and
  fails on any recorded socket call.

## Source URLs

- `https://pypi.org/project/kedro/1.7.0/`
- `https://pypi.org/project/kedro-telemetry/` (version 0.9.0 installed)
- `https://docs.kedro.org/en/stable/about/telemetry/` (cited in the plugin
  source; not fetched in this task)

## Status / Open items

- F0-04: DONE for the observed modes. No unexpected attempt in modes A, B,
  D, E, F, H and I. Expected attempts in C and G (denied).
- Open: the sandbox blocked all traffic. This task did not capture a real
  payload, so the payload content comes from source reading only.
- Open: a `kedro-telemetry` wheel hash was not recorded. The package came
  from PyPI through `uv pip install --only-binary :all:` and may change.
- Open: other plugins, the Kedro CLI and the `kedro/server` module were not
  tested.
- Open: other network paths (for example `fsspec` remote filesystems,
  `cookiecutter` templates, `gitpython`) were not exercised. Static
  in-memory datasets do not use them. This task did not prove it for the
  production bridge.
- Open: the DNS lookup in modes C and G ran against a sandbox. Behavior on
  a networked host was not exercised on purpose.

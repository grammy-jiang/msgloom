# Phase 1 dependency qualification

The manager locked one shared Phase 1 dependency candidate on 2026-09-29.
Every existing dependency version remains unchanged, including Scrapy 2.19.0,
MSAL 1.39.0, and SQLAlchemy 2.0.54. Python 3.13 remains the default through
``.python-version``. The declared minimum is now Python 3.12.

## Interpreter evidence

The same 1,092 tests passed on ARM64 CPython 3.12.14, 3.13.5, and 3.14.7. Raw
counts, runtimes, and API checks are in phase1-dependency-qualification.json.
The tested candidate starts at ``d245244`` and adds this dependency change.
Later source and product commits still require their own regression checks.

The initial Python 3.12 run found one fixture defect: Scrapy's generator-return
diagnostic could not inspect a callback defined through ``python -c``. The
fixture now runs from a temporary source file. Its assertions and Scrapy
checks remain unchanged. All six tests in that module passed on all three
interpreters, and the corrected full Python 3.12 run passed.

## Selected dependencies

The parser pins and synthetic extraction evidence remain in
[parser qualification](parser-qualification.md). The manager also selected
[Pydantic 2.13.5](https://pypi.org/project/pydantic/2.13.5/),
[pydantic-settings 2.15.0](https://pypi.org/project/pydantic-settings/2.15.0/),
[Cyclopts 5.0.0](https://pypi.org/project/cyclopts/5.0.0/),
[Jinja2 3.1.6](https://pypi.org/project/Jinja2/3.1.6/), and
[Claude Agent SDK 0.2.161](https://pypi.org/project/claude-agent-sdk/0.2.161/).
These exact versions and their transitive resolution are recorded in uv.lock.

Synthetic API probes on all three interpreters verified strict Pydantic
validation, explicit settings construction, a finite Cyclopts invocation,
escaped Jinja output, and construction of SDK options for explicit tools,
settings sources, environment, working directory, plugins, and MCP servers.
Cyclopts 5 interprets integer results as exit codes by default; callers that
need the Python value must select ``result_action="return_value"``.

The installed SDK CLI artifact is ELF ARM aarch64. No CLI process, AI session,
or paid model call was started. Option construction alone does not qualify
SDK session isolation; the A3 lane must test effective lifecycle and controls.
Prefect and FastMCP are absent from the qualified runtime environments.
Native extraction API probes also do not establish parser sandbox safety.

## Validation ownership

The manager owns the shared lock and environment. Workers use that environment
read-only. Source and test checks now include the ``msgloom`` package; Ruff
uses the Python 3.12 target. New runtime scripts receive the same pre-commit
Ruff checks as source and tests. Live LSP diagnostics are clean for the changed
qualification script and feed-export fixture.

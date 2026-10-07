# CI execution policy

The authoritative workflow is .github/workflows/ci.yml. Keep this note
descriptive; do not duplicate workflow selectors or numeric coverage floors
in another configuration.

## Runtime and security changes

Changes outside the eligible documentation paths run the full Python 3.12,
3.13 and 3.14 test matrix, FastMCP compatibility matrix, Linux cgroup-v2
safety gate, and macOS/Windows portable smoke checks.

The same full verification applies to manual workflow runs, missing Git
history, or uncertain change classification. The coverage thresholds and
critical-module budgets are defined in scripts/quality/coverage_gate.py.

## Documentation-only changes

Only changes entirely beneath docs/, with .md, .rst or .txt filenames,
qualify for the fast path. Classification uses the complete changed-file list;
a rename is checked on both its source and destination.

In this case, runtime test steps are intentionally skipped. The required
job names remain visible, but a green skipped job does **not** mean its
test suite was executed. The Quality job still runs Actionlint and the
changed-file pre-commit hooks, including Markdown and secret checks.

The classifier lives in scripts/quality/ci_change_scope.py. Its focused
failure-path and portability tests live in
tests/quality/test_ci_change_scope.py.

## Forcing a full verification

Use **Actions > CI > Run workflow** to request a full manual matrix.
The documentation-only shortcut never applies to manual dispatches.

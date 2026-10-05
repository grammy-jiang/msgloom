# Teams branch GitHub Actions qualification

The user authorized pushing ``program/a1-teams-spider`` and qualifying its
GitHub Actions checks on 2026-10-05. The completed local report remains the
record for reviewed application code ``b3039f1``. Publishing this branch does
not satisfy the company-tenant acceptance or merge gates.

The repository had no Actions workflows. ``.github/workflows/ci.yml`` adds
push, pull-request, and manual triggers using the existing locked commands.
It grants only repository read permission, does not retain checkout
credentials, and pins each action to a commit. Synthetic Graph fixtures run
without company credentials. The workflow uses the standard
[ARM64 GitHub-hosted runner](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
and the official [uv setup integration](https://docs.astral.sh/uv/guides/integration/github/).

The quality job runs Ruff, format checking, Pyright, native Scrapy contracts,
and the existing pre-commit checks over the branch's changed files. A feature
branch compares against the default branch; a pull request compares against
its target branch. A default-branch push checks its pushed commit range.
The job fails if hooks change tracked files.

Six separate jobs run the existing ``py312``, ``py313``, ``py314``, and three
FastMCP tox environments. Tox retains locked dependencies, coverage, four
workers for ordinary tests, and the separate serial exclusive-state suite.
No interpreter, test selection, timeout, or expectation is relaxed for CI.
Full test runners install the required ``bubblewrap`` system package, as the
deployment image does. The namespace sentinel test uses the active Python
runtime and checks its version instead of assuming a system Python path.
The runner loads Ubuntu's packaged ``bwrap-userns-restrict`` AppArmor profile
and probes namespace creation before tox. This follows Ubuntu's
[per-application namespace configuration](https://discourse.ubuntu.com/t/understanding-apparmor-user-namespace-restriction/58007)
and retains system-wide AppArmor restrictions.
Each full test job also rebuilds a wheel from the source distribution and
checks that exact wheel outside the checkout with the existing qualification
script. Coverage, tox logs, and package reports are retained as artifacts.

The local Python 3.14 serial qualification documented in the final report is
not a substitute for the hosted run. Hosted success requires all seven jobs
to finish successfully at the pushed candidate. Failed runs remain visible;
any repair must be validated and pushed before a new success claim.

The branch remains separate from ``master``. Live T1/T2 acquisition, repeat
acquisition, and applicable real notification acceptance still require the
approved company tenant and consent described in the final report.

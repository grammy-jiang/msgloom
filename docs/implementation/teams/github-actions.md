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

Ubuntu 24.04's ``apparmor`` package owns ``/etc/apparmor.d/abi/4.0`` but does
not install ``bwrap-userns-restrict`` into ``/etc/apparmor.d``. The matching
Noble ``apparmor-profiles`` package keeps the purpose-built profile under
``/usr/share/apparmor/extra-profiles/`` instead. Canonical recommends adding
that upstream profile when it is absent rather than disabling the global
user-namespace restriction. The Noble 4.0.1 package copy is byte-for-byte the
AppArmor ``v4.0.1`` profile at upstream commit
``b0eb95457bc2de401920308869d016e696c73664`` with SHA-256
``11d39094f044f0cda0febb3ad517b830301da6b2ce929664af09ee9e4dd264f9``.

CI therefore vendors only that exact upstream file at
``.github/apparmor/bwrap-userns-restrict`` instead of installing the broader
experimental profile package. The isolation step verifies the pinned digest
and Noble's 4.0 ABI file, loads the profile directly with ``apparmor_parser``,
then runs the real bwrap namespace probe before tox. The repository owns only
the vendored CI policy source; Ubuntu continues to own the parser, ABI,
tunables, and system-wide restriction. The profile deliberately gives bwrap
the namespace/capability access needed to construct the sandbox and stacks
children into ``unpriv_bwrap``, where capabilities are denied. No sysctl is
relaxed and no unconfined replacement profile is used. See Canonical's
[namespace restriction guidance](https://discourse.ubuntu.com/t/understanding-apparmor-user-namespace-restriction/58007),
Ubuntu's
[Noble AppArmor file list](https://packages.ubuntu.com/noble/arm64/apparmor/filelist),
the
[Noble profile-package file list](https://packages.ubuntu.com/noble-updates/all/apparmor-profiles/filelist),
and the
[immutable upstream profile](https://gitlab.com/apparmor/apparmor/-/blob/b0eb95457bc2de401920308869d016e696c73664/profiles/apparmor/profiles/extras/bwrap-userns-restrict).

Each full test job also rebuilds a wheel from the source distribution and
checks that exact wheel outside the checkout with the existing qualification
script. Coverage, tox logs, and package reports are retained as artifacts.

The local Python 3.14 serial qualification documented in the final report is
not a substitute for the hosted run. Hosted success requires all seven jobs
to finish successfully at the pushed candidate. Failed runs remain visible;
any repair must be validated and pushed before a new success claim.

The accepted Teams branch was later rebased onto the final ownership-cleanup
master baseline and fast-forwarded into master on 2026-10-08. Live
personal-account qualification of the other selected Microsoft A1 sources
passed after the merge. Live T1/T2 acquisition, repeat acquisition, and
applicable real notification acceptance still require the approved work or
school tenant and consent described in the final report.

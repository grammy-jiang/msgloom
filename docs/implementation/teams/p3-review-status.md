# Teams P3 review status

The lifecycle review is accepted at the original code candidate
`ac8fb304942cbe36788641ce7f55fdfee96f1cdd`. The provider review found a
confirmed scope-validation defect. The focused repair passes its tests. All nine final
reviews must name the repaired candidate before local completion.

The frozen inventory SHA-256 is
`a5da64858930628926f3c9195c891eb6c16c69b092e5f4341bd66ea3a5ae7ea1`.
All 11 local gate receipts pass at this candidate. Documentation updates after
that commit do not change the frozen source archive.

| Review lane | State |
| --- | --- |
| Provider/API/permissions | Major scope-override finding repaired; final closure pending |
| Graph-over-Scrapy ownership | Pending; bounded recovery owns the first unconfirmed send |
| Lifecycle/cancellation | Accepted PASS at original candidate; final repaired-candidate closure required |
| Privacy/security | Pending |
| Evidence/provenance/replay | Pending |
| Persistence/history/deletion | Pending |
| Shared topology | Pending |
| Fixture completeness | Pending |
| Compatibility | Pending |

The [lifecycle reviewer](https://chatgpt.com/c/6ac2081c-4558-83ec-9477-62b9e8c5e262)
returned PASS for all three criteria with no findings. The coordinator checked
the actual `gpt-5-6-thinking` / `max` transcript, exact task and candidate,
frozen inventory, posted prompt, and source inspection through the MCP connector.
The coordinator checked the cited source and eight passing JUnit cases for
terminal requests, item failures, JOBDIR rejection, and cancellation drain.
The review confirms the existing failure path, awaited serialized writes, and
explicit unsupported-resume policy. It introduces no checkpoint or promotion.

The durable acceptance receipt is
`.superpowers/teams-a1/p3-r1-lifecycle-cancellation-acceptance.json`.
The HTTP transcript exposes MCP calls and source-read arguments but returns
empty tool-response text. The coordinator checked the source and saved test
results directly. No test rerun was needed because production code is unchanged.

This is not final closure. Any production repair requires all nine final
reviews to name the repaired candidate. Real tenant T1/T2, repeat acquisition,
and applicable webhook acceptance remain unexecuted. Master remains untouched.

## Provider scope repair

The [provider reviewer](https://chatgpt.com/c/6ac2074e-9bf4-83ec-b310-4ff97f862994)
reported `P3-PROVIDER-SCOPE-OVERRIDE-001`. Command-priority `MS_GRAPH_SCOPES`
settings could bypass the frozen T2 and notification profiles. Ten failing
regressions reproduced extra read, write, application, missing, and empty scope
sets reaching construction. The existing T1 guard rejected these inputs.

The shared Teams application base now checks its effective permission set
before construction. The check uses the selected provider declaration and
allows a different scope order. Standalone provider consumers keep explicit
scope overrides. The redundant T1-only forwarding method is removed.
The focused suite passes 32 tests. Ruff, format, Pyright, and live LSP diagnostics
pass for the three changed Python files. All 21 native CLI, contract, notification, and public-reader integration tests
pass in 87.62 seconds. Changed-file pre-commit hooks also pass. Full final convergence and nine exact-candidate closures remain due.

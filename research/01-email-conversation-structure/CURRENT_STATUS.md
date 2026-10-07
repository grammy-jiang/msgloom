# Topic 01 current status

**This topic is CLOSED.** It stopped on `review_decision`: after round 2 a
project-value review read the retained gaps and declined to authorise a third
academic round. That is a decision about the evidence, and it is a stronger
closure signal than the `round_cap_reached` the later topics hit — those
stopped because a four-round budget ran out while papers were still arriving.

Topic 01 ran before the current pipeline existed, so its shape differs from
Topics 03–10. Nothing below is missing; it is filed differently:

| What | Where |
| --- | --- |
| Round reports | `local-corpus-20260914/` (round 1), `round2-20260915/` (round 2) |
| Index at the conventional path | `msgloom-topic-01-email-conversation-structure-research-report.md` — a pointer, not a synthesis |
| Gaps, current state | `gaps.json` at this root |
| Gaps, round-2 snapshot | `round2-20260915/gaps.json` |
| Gap id namespace | `A<n>` / `E<n>`, not `gap-<n>` |
| Built-and-measured work | `engineering-validation/` |
| Rounds | 2 academic, not 4 |

## Academic research

- Round 1: complete.
- Round 2: complete, independently reviewed and strictly validated.
- Automatic Academic Round 3: **not started** — declined by the post-round-2
  project-value review, not abandoned.
- Retained academic gaps:
  - A2 structural quote-to-source-span alignment: medium, targeted refresh only if later candidate selection needs it or stronger candidates still fail relevant strata.
  - A7 modern/incremental/LLM direct-email reconstruction: high, retained but not sufficient by itself to trigger another broad round now.

## Engineering research after Round 2

**E1–E4 are accepted at the synthetic/adversarial engineering-research level.**

The final fresh independent review (`engineering-validation/audit/independent-review-03/verdict.json`) returned `accepted` with confidence 0.98, zero blocking issues, zero nonblocking issues, and zero recommended fixes after two earlier review cycles exposed and repaired methodology defects.

This is the strongest conclusion justified now without production mailbox data:

> Topic 01 has completed the academic work and the synthetic engineering validation that can reasonably be finished at this stage. It should not wait for production examples. Future Topic 01 work is conditional on candidate implementation choices, later domain validation, or a separate decision to reopen A2/A7.

## Deferred / hand-offs

- Production-domain validation: future, when suitable user-reviewed data becomes available; not a blocker now.
- A2 targeted academic refresh: conditional on later method selection/failure evidence.
- A7 modern/incremental/LLM refresh: separate user decision or later implementation need.
- Semantic response/partial agreement: Topic 04.
- General calibration and reliability methodology: Topic 10.
- E5 external artifacts/licenses/reproduction: after candidate method selection.
- ~~E6 Raspberry Pi performance: after candidate correctness/preservation is established.~~ **Void 2026-09-17 (owner decision D-8):** the deployment target is x86 plus cloud services. E6's premise is gone. Throughput and peak memory still matter; arm64 and 16 GB do not.
- Cross-group/source Topic identity: Topic 03 / Phase 2.

Historical Academic Round 1 and Round 2 reports, syntheses, and gap snapshots remain unchanged. This status file records subsequent engineering evidence rather than rewriting research history.

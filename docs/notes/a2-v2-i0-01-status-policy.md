# A2 v2 I0-01 scheduler status policy (CANDIDATE/RESEARCH)

Code: `msgloom/a2_kedro/activation/status_policy.py`.

The policy is a pure state machine. It has no I/O, clock or randomness.

## States and events

States: `pending`, `busy`, `held`, `blocked`, `failed`, `cancelled`.
Events: `claim`, `release`, `hold`, `resume`, `block`, `fail`, `cancel`.

| State     | Allowed events and result                               |
| --------- | ------------------------------------------------------- |
| pending   | claim to busy; hold to held; block; cancel              |
| busy      | release to pending; hold; block; fail to failed; cancel |
| held      | resume to pending; block; cancel                        |
| blocked   | none (terminal)                                         |
| failed    | none (terminal)                                         |
| cancelled | none (terminal)                                         |

Every other pair is rejected, including a repeated event.

## Open design questions

- Is `blocked` terminal? This draft says yes. A resolved block would need
  a new scheduler item.
- C0-18 splits `BLOCKED` into source, reference and catalog. This policy
  keeps one `blocked` state. The reason belongs to the caller.
- A completed scope has no scheduler state. The C0-18 receipt records it.
- `fail` is allowed only from `busy` (a lost or failed attempt).
- Wire names are provisional.

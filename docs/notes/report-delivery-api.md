# Report delivery API

## Ownership and public seam

Delivery accepts only an exact accepted saved `report@1` produced by reporting.
`ReportSubmissionPlan` binds the report, report policy, configured owner and
destination, complete ordered parts, request parameters, and durable result
identities. The saved report is decoded and passed through `ReportCodec`
coverage validation again before any effect. The destination must exactly match
the saved report and the trusted plan. It is one bare owner mailbox; recipient
lists, CC/BCC fields, newlines, and source/model-selected addresses are not
accepted.

`ReportSubmissionHandler` is the awaited `REPORT_SUBMIT` operation seam for
later Application/CLI composition. Application remains responsible for caller
admission and terminal OperationOutcome persistence. Delivery does not add a
registry entry, capability, CLI, authentication flow, or credential source.
`ReportSubmissionCodec` is exported for manager-owned registry composition.

## Lifecycle and retry

Each report part has a stable claim scope over report, policy, and part number.
Before an external call, delivery persists a `SubmissionAttempt` containing
the deterministic exact MIME bytes and their SHA-256 under the live claim, then
marks the effect `PENDING`. Retry of a proven rejected part requires the prior
attempt ResultRef and reuses those saved bytes. Accepted, confirmed, pending,
or unknown part claims are never resent. A repeat command skips already
accepted/confirmed parts. Multipart acceptance is complete only when every part
is accepted or confirmed.

A definite provider response is persisted as a `SubmissionReceipt` before the
claim effect advances. `ACCEPTED` means submission was accepted by the
provider; `CONFIRMED` is stronger delivery evidence and is kept distinct.
Receipt persistence failure after a call, transport exception, timeout, or
cancellation after `PENDING` finishes as `UNKNOWN`. An accepted/confirmed
effect is never downgraded by later cleanup failure.

For each accepted/confirmed part, delivery also persists one singular history
record per exact topic assessment. `DeliveryReportHistoryResolver` exposes
that durable `report_submission@1` evidence to report selection. Mere
attempts, rejected receipts, unknown effects, and reconciliation proof are not
reporting history. Partial submissions retain history only for assessments
covered by accepted/confirmed parts.

## Reconciliation

`ReportReconciler.reconcile` is the public async recovery API and never
constructs or invokes a sending transport. It requires an exact original
ClaimToken and report/policy/part binding. Provider proof is first persisted
under a separate authorized `REPORT_SUBMIT` recovery claim. Only then does it
call the persistence `reconcile_external_effect` API. Missing or inconclusive
proof can retain `UNKNOWN`; definite accepted, confirmed, or rejected
decisions require bounded provider evidence. Persistence remains authoritative
for terminal/expired-owner eligibility, idempotency, downgrade prevention, and
release of only proven `REJECTED` effects.

## Microsoft Graph adapter

`GraphSendMailTransport` accepts an injected mailbox, bearer token, and
one-shot HTTP transport. The token is private construction state and is never
put in attempts, receipts, logs, or semantic data. The adapter sends base64
MIME to the v1.0 `/users/{id}/sendMail` endpoint with
`Content-Type: text/plain`, redirects disabled, and retries set to zero.

The Microsoft Graph v1.0 sendMail documentation checked on 2026-09-29 states
that success returns HTTP 202 Accepted with no response body, and explicitly
notes that 202 indicates request acceptance rather than completed processing.
Accordingly, Graph 202 maps only to `ACCEPTED`, never `CONFIRMED`.
Authentication and Mail.Send consent remain deployment-owned inputs.

Reference:
[Microsoft Graph sendMail API](https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0)

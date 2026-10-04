# Local Teams notification intake

`microsoft_teams_notification_reconcile` reads a saved basic notification
envelope and reconciles its message targets through the existing Graph
Downloader. It does not run a webhook server or manage subscriptions.

The caller supplies these spider arguments to native `scrapy crawl`:

| Argument | Contract |
| --- | --- |
| `envelope_path` | Local file containing the exact inbound POST body |
| `trusted_subscriptions_path` | Caller-controlled JSON subscription records |
| `envelope_id` | Stable 32-character lowercase hexadecimal capture ID |
| `captured_at` | Original UTC capture time, inside the trusted validity window |
| `delivery_url` | Caller-trusted inbound delivery URL; never fetched |
| `local_gap_path` | Optional caller-trusted JSON delivery-gap record |

The trusted file contains a `subscriptions` list. Each record requires
`subscription_id`, `source_id`, `tenant_id`, `client_state`, `valid_from`,
`valid_until`, and `scope_kind`. A `chat-messages` scope also requires `chat_id`.
A `channel-messages` scope requires `host_team_id` and `channel_id`. Every record
must match the configured logical source. Keep this file private. The untrusted
envelope cannot supply or replace these bindings.

The saved inbound body is persisted before envelope parsing. The complete
envelope must pass client-state, tenant, subscription, scope, and validity
checks before any semantic write or Graph request. Basic identity-only
`resourceData` and documented OData key paths are supported. Identity metadata
must agree with the target path. Encrypted payloads, full message resource data,
validation tokens, unsupported lifecycle events, and arbitrary URLs fail
closed. Invalid envelopes retain raw evidence and mark the run failed.

Native item completion signals gate dependent work. One immutable coverage
fact preserves the ordered events for each scope and capture. Explicit deletion
facts are persisted before readback. Later GET evidence and readback outcomes
are separate facts. A failed GET cannot remove the deletion declaration or an
earlier message body. Created or updated events with failed readback do not
invent a message or deletion.

Replaying a capture requires the same ID, time, bytes, and receipt metadata.
Reusing the ID for changed input fails. Raw inbound evidence records request
bytes with no fabricated Graph response. The public saved-source reader checks
those bytes when it reconstructs deletion and coverage history.

The optional local gap file requires `evidence_id`, `captured_at`,
`subscription_id`, and `gap_kind`. Supported local kinds are
`delivery-interruption` and `subscription-expired`. Its scope comes from the
trusted subscription record. It preserves the original local bytes separately
from the webhook body. Reauthorization, removal, and local gaps keep history
incomplete after successful current-state reconciliation.

The spider uses the existing delegated account binding, catalog lock, pipelines,
and run-integrity handling. Its declared permissions are `Chat.Read` and
`ChannelMessage.Read.All`. It rejects `JOBDIR`. No polling, checkpoint, renewal,
or continuous-delivery claim is introduced. The unresolved provider lifetime
conflict remains in the [N0 contract](n0-notification-contract.md).

Worker `91bf3c338a4d3da481777b35f58982c774a60334` was integrated at
`cdedf00d75964a624cac9d55b49a7292e82695b9`. Independent preacceptance passed
59 tests, Ruff, format checks, and Pyright. Coordinator probes passed the
documented payload forms and native public-reader deletion/gap replay. These
local results do not qualify a real tenant or webhook deployment.

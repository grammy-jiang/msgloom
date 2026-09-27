# Scrapy statistics and crawl status

msgloom uses Scrapy's built-in Stats Collector. It does not replace
`STATS_CLASS` or maintain a second statistics backend.

Stats are observability, not correctness state. Delta checkpoint promotion is
decided from Spider execution state plus durable SQLAlchemy checkpoint
candidates. Stats only report the outcome.

Scrapy's normal `STATS_DUMP = True` remains enabled, so final stats are emitted
when the Spider closes. Long-running crawls also use Scrapy 2.19's native
`PeriodicLog` extension at `LOGSTATS_INTERVAL = 60` seconds. PeriodicLog is
progress reporting only: signal-handler order is undefined, so its final
snapshot is not the authoritative terminal summary.

## Native Scrapy stats

Use existing Scrapy families instead of msgloom copies where they already
describe the framework:

- `downloader/*`
- `response_received_count`
- `scheduler/*`
- `dupefilter/*`
- `retry/*`
- `httpcache/*` when development cache is enabled
- `item_scraped_count`
- `item_dropped_count`
- `spider_exceptions/*`
- `elapsed_time_seconds`
- `finish_reason`

The project replaces only the built-in RetryMiddleware class with
`PrivacySafeRetryMiddleware`, a thin subclass that preserves Scrapy 2.19
retry construction, settings, metadata, and native `retry/*` stats while
suppressing log messages that would include full Request URLs.

## Final execution status

`OutlookCrawlStatusExtension` publishes one attempt-scoped terminal status
under `msgloom/final/*`. It observes lifecycle/error signals; it does not own
checkpoint correctness or query the catalog.

Common fields:

- `msgloom/final/schema_version`
- `msgloom/final/spider`
- `msgloom/final/mode`
- `msgloom/final/run_id`
- `msgloom/final/attempt_id`
- `msgloom/final/status`
- `msgloom/final/close_reason`
- `msgloom/final/reason_codes`
- `msgloom/final/jobdir_enabled`
- `msgloom/final/counter_scope`
- `msgloom/final/framework_close_error_count`

Status values are deliberately small:

- `completed`: the mode's execution-completion condition is proven.
- `truncated`: Discovery stopped at an explicit `max_pages` limit while a
  continuation still existed.
- `incomplete`: Delta reached its checkpoint integrity gate but did not have a
  complete promotable round.
- `failed`: a known request, callback, pipeline, or checkpoint error occurred.
- `interrupted`: Scrapy closed for a non-`finished` reason without a more
  specific failure state.
- `unverified`: Scrapy finished, but the mode-specific completion condition
  cannot be proven.

For Full acquisition, `status=completed` means the requested execution
finished without known failures. It does not claim every Full-profile surface
is `acquired`. The final stat
`msgloom/final/profile_completeness=not_evaluated` makes that distinction
explicit.

## Discovery

Useful `msgloom/crawl/discovery/*` fields include:

- `scope`, `page_size`, `max_pages`
- `page_count`, `message_count`, `continuation_count`
- `pagination_exhausted`
- `truncated_count`

`pagination_exhausted=True` is set only when a provider page has no next link.
`truncated_count` increments only when a next link exists and the explicit
`max_pages` limit stops traversal.

The final layer exposes `msgloom/final/pagination_outcome` as
`exhausted`, `truncated`, or `unknown`.

## Delta, reconciliation, and checkpoints

Traversal/reconciliation examples:

- `msgloom/crawl/delta/checkpoint_loaded_count`
- `msgloom/crawl/delta/folder_started_count`
- `msgloom/crawl/delta/folder_completed_count`
- `msgloom/crawl/delta/folder_page_count`
- `msgloom/crawl/delta/message_page_count`
- `msgloom/crawl/delta/message_upsert_count`
- `msgloom/crawl/delta/message_removed_count`
- `msgloom/crawl/delta/job_resumed`
- `msgloom/crawl/reconcile/enabled`
- `msgloom/crawl/reconcile/completed`
- `msgloom/crawl/reconcile/message_count`
- `msgloom/crawl/reconcile/orphan_count`
- `msgloom/crawl/reconcile/message_recovered_count`

Checkpoint-owner fields include:

- `msgloom/checkpoint/outcome`:
  `evaluating|committed|skipped|error`
- `msgloom/checkpoint/error_stage`: `snapshot`, `candidate_load`, or `commit`
- `msgloom/checkpoint/commit_count`
- `msgloom/checkpoint/commit_skipped_count`
- `msgloom/checkpoint/error_count`
- `msgloom/checkpoint/candidate_read_error_count`
- `msgloom/checkpoint/commit_error_count`
- expected/completed/candidate/committed folder counts

The final layer mirrors the outcome as
`msgloom/final/checkpoint_outcome`. If checkpointing is disabled, a normally
finished Delta run is `unverified`, not `completed`.

On a clean JOBDIR resume, Delta restores logical run state such as completed
folders, reconciliation completion, run failure state, and reason codes.
Ordinary Scrapy counters remain per process attempt, so the final
`counter_scope` becomes `attempt_with_restored_run_state` for resumed Delta.

## Lifecycle failure observation

Scrapy 2.19 logs downloader, scraper/pipeline, scheduler, and slot close
failures and continues shutdown. `OutlookScrapyPrivacyFilter` observes these
core engine records before `spider_closed`, strips traceback text, and records
`msgloom/lifecycle/close_error_count` plus a bounded stage counter. Any such
failure makes the final status `failed`, even when Scrapy closes with
`reason=finished`.

Scrapy owns `spider_exceptions/count` and `item_dropped_count`. msgloom adds
only the missing pipeline-exception counter
`msgloom/persistence/item_error_count`, avoiding project-level duplicates.

## Graph transport diagnostics

`MicrosoftGraphDiagnosticsMiddleware` counts Graph network attempts and network
responses without putting URLs or message identifiers into stat keys:

- `msgloom/graph/request_count`
- `msgloom/graph/request_purpose_count/{purpose}`
- `msgloom/graph/response_count`
- `msgloom/graph/response_purpose_count/{purpose}`
- `msgloom/graph/response_status_count/{status}`
- `msgloom/graph/response_purpose_status_count/{purpose}/{status}`
- `msgloom/graph/response_missing_request_id_count`
- `msgloom/graph/exception_count`
- `msgloom/graph/exception_purpose_count/{purpose}`
- `msgloom/graph/exception_type_count/{error_type}`

Its priority makes it run after auth on the request path and before auth on the
response path, so a 401 that becomes an authentication retry is still counted.

Development HttpCache replays are not counted as network responses. They use
`msgloom/graph/cache_replay_count` and
`msgloom/graph/cache_replay_purpose_count/{purpose}` instead, so a cached
response does not appear as a transport attempt without a matching request.

## Graph provider retries

Provider-specific 409/429/503/509 handling uses Scrapy's
`get_retry_request()` with `stats_base_key="msgloom/graph_error_retry"`.
The native helper therefore owns:

- `msgloom/graph_error_retry/count`
- `msgloom/graph_error_retry/reason_count/*`
- `msgloom/graph_error_retry/max_reached`

Additional provider-policy stats include:

- `msgloom/graph_error/retry_purpose_count/{purpose}`
- `msgloom/graph_error/status_count/{status}`
- `msgloom/graph_error/delay_source_count/{source}`
- `msgloom/graph_error/wait_seconds_total`
- `msgloom/graph_error/max_delay_seconds`
- `msgloom/graph_error/exhausted_purpose_count/{purpose}`
- `msgloom/graph_error/exhausted_status_count/{status}`

`wait_seconds_total` is the scheduled backoff budget recorded before the
sleep. It should not be interpreted as measured wall-clock sleep time.

## Persistence stats

Raw evidence pipeline examples:

- `msgloom/evidence/response_persisted_count`
- `msgloom/evidence/origin_count/{origin}`
- `msgloom/evidence/raw_blob_created_count`
- `msgloom/evidence/raw_blob_reused_count`
- `msgloom/evidence/cache_link_count`
- `msgloom/evidence/cache_recovery_count`

Catalog pipeline examples:

- `msgloom/catalog/message_item_processed_count`
- `msgloom/catalog/message_observation_created_count`
- `msgloom/catalog/message_observation_replay_count`
- `msgloom/catalog/message_detail_item_processed_count`
- `msgloom/catalog/attachment_item_processed_count`
- `msgloom/catalog/folder_item_processed_count`
- `msgloom/catalog/delta_checkpoint_candidate_processed_count`
- `msgloom/catalog/surface_item_processed_count/{surface_kind}/{status}`

Surface stats use only the fixed kind before the first colon, for example
`attachment_raw` rather than `attachment_raw:<attachment-id>`. Provider
identifiers therefore do not become stat-key labels or leak through the final
Scrapy stats dump.

## Periodic logging

`scrapy.extensions.periodic_log.PeriodicLog` is explicitly enabled because it
is not part of Scrapy 2.19's `EXTENSIONS_BASE`. Both
`PERIODIC_LOG_STATS` and `PERIODIC_LOG_DELTA` use reviewed include lists;
the project does not enable a blanket dump of all current or future stats.

Periodic filters do not decide crawl success. Catalog stats are safe to
include because dynamic surface identifiers are normalized to fixed surface
kinds before they become stat keys. The authoritative terminal record is the
mode-specific `Outlook ... final summary` plus the final Scrapy stats dump;
the final PeriodicLog snapshot is only best-effort because signal handler order
is not guaranteed.

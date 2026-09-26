# Scrapy statistics

msgloom uses Scrapy's built-in Stats Collector. It does not replace
`STATS_CLASS` and does not maintain a second run-statistics system.

With Scrapy's default `STATS_DUMP = True`, all built-in and msgloom-specific
stats are printed in the normal `Dumping Scrapy stats` log record when the
spider closes.

## Namespaces

### `msgloom/crawl/*`

Owned by the Outlook spider. These stats describe what the spider traversed and
interpreted, for example:

- `msgloom/crawl/mode`: `discovery` or `full`
- `msgloom/crawl/discovery/scope`: `mailbox` or `folder`
- `msgloom/crawl/discovery/page_count`
- `msgloom/crawl/discovery/message_count`
- `msgloom/crawl/discovery/continuation_count`
- `msgloom/crawl/discovery/truncated_count`
- `msgloom/crawl/response_count/{purpose}`
- `msgloom/crawl/response_bytes/{purpose}`
- `msgloom/crawl/enrichment/target_message_count`
- `msgloom/crawl/enrichment/message_detail_count`
- `msgloom/crawl/enrichment/message_mime_count`
- `msgloom/crawl/enrichment/attachment_page_count`
- `msgloom/crawl/enrichment/attachment_count`
- `msgloom/crawl/enrichment/attachment_type_count/{type}`
- `msgloom/crawl/enrichment/attachment_raw_count`
- `msgloom/crawl/enrichment/item_attachment_detail_count`
- `msgloom/crawl/failure_count`
- `msgloom/crawl/failure_purpose_count/{purpose}`
- `msgloom/crawl/failure_type_count/{exception}`

`truncated_count` is expected to remain absent/zero in normal production
Discovery. It becomes non-zero when an explicit development `max_pages` limit
prevents following a Graph `@odata.nextLink`.

### `msgloom/auth/*`

Owned by the selected Microsoft authentication downloader middleware. Examples:

- `msgloom/auth/method`
- `msgloom/auth/token_cache_loaded`
- `msgloom/auth/request_authenticated_count`
- `msgloom/auth/memory_token_hit_count`
- `msgloom/auth/silent_attempt_count`
- `msgloom/auth/silent_success_count`
- `msgloom/auth/user_interaction_count`
- `msgloom/auth/device_code_count`
- `msgloom/auth/browser_interactive_count`
- `msgloom/auth/401_retry_count`
- `msgloom/auth/401_final_count`
- `msgloom/auth/token_cache_save_count`

A Scrapy HTTP-cache hit happens before the authentication middleware in the
request chain, so a fully cached run may show the selected auth method but no
authenticated-request counter.

### `msgloom/storage/*`

Owned by the item pipeline and incremented only after the corresponding local
persistence operation succeeds. Examples:

- `msgloom/storage/item_count/graph_response`
- `msgloom/storage/item_count/outlook_mail`
- `msgloom/storage/item_count/outlook_mail_detail`
- `msgloom/storage/item_count/outlook_attachment`
- `msgloom/storage/item_count/acquisition_failure`
- `msgloom/storage/raw_blob_created_count`
- `msgloom/storage/raw_blob_reused_count`
- `msgloom/storage/raw_blob_created_bytes`

## Built-in Scrapy stats remain authoritative for framework behavior

Do not duplicate Scrapy's existing counters. Use its native stats such as:

- `downloader/*`
- `httpcache/*`
- `retry/*`
- `dupefilter/*`
- `item_scraped_count`
- `elapsed_time_seconds`
- `finish_reason`

The `msgloom/*` namespace adds source/business visibility; it does not replace
Scrapy's framework-level observability.

### Delta, reconciliation, checkpoint, and throttling stats

Additional run-level keys include:

- `msgloom/crawl/delta/folder_count`
- `msgloom/crawl/delta/folder_resumed_count`
- `msgloom/crawl/delta/folder_initial_count`
- `msgloom/crawl/delta/folder_completed_count`
- `msgloom/crawl/delta/message_observation_count`
- `msgloom/crawl/delta/message_removed_count`
- `msgloom/crawl/reconcile/message_count`
- `msgloom/crawl/reconcile/orphan_count`
- `msgloom/crawl/reconcile/message_recovered_count`
- `msgloom/checkpoint/commit_count`
- `msgloom/checkpoint/committed_folder_count`
- `msgloom/checkpoint/commit_skipped_count`
- `msgloom/throttle/429_count`
- `msgloom/throttle/retry_count`
- `msgloom/throttle/wait_seconds_total`

These keys make it possible to distinguish normal Graph delta work from the
coverage reconciliation safety net and from transport-level throttling.

### Raw evidence and catalog stats

The Scrapy-native storage split adds:

- `msgloom/evidence/response_persisted_count`
- `msgloom/evidence/origin_count/network`
- `msgloom/evidence/cache_link_count`
- `msgloom/evidence/cache_recovery_count`
- `msgloom/catalog/message_observation_count`
- `msgloom/catalog/message_detail_count`
- `msgloom/catalog/folder_observation_count`
- `msgloom/catalog/delta_checkpoint_candidate_count`
- `msgloom/persistence/item_error_count`
- `msgloom/persistence/item_dropped_count`

Raw network evidence is persisted in downloader middleware before the Response
is allowed to reach the Spider. Semantic Items are persisted later by the Item
Pipeline, matching Scrapy's component boundaries.

# P0-D — Teams synthetic Graph fixture harness

## Decision

Use the established real-crawl pattern: a local `ThreadingHTTPServer` returns deterministic Graph bytes while production Teams application spiders run in a subprocess through the real Scrapy Scheduler/Downloader, Graph add-on/fingerprinter, Graph error/retry middleware, `RawEvidencePipeline`, `EvidenceLinkPipeline`, Teams pipeline, and `MicrosoftGraphIntegrityExtension`. No fake Downloader/Scheduler, Requests/HTTPX client, retry loop, pagination engine, or second evidence path.

Minimal test support:

- `tests/teams_support.py` (<500 lines): exact-route HTTP server, `FixtureReply`, `SeenRequest`, `GraphFixture`, pytest server fixture, thin subprocess/settings helper.
- `tests/teams_failures.py` (<500 lines): late exception and `DropItem` pipelines for the final Teams semantic item type, mirroring `tests/todo_sync_failures.py`.
- `tests/fixtures/microsoft_graph/teams/` only for large JSON/binary assets. Endpoint/path builders stay in production helpers or individual test oracles, never support code. A `tests/teams/` runtime framework is unnecessary; split only for the line limit.

## Fixture contract

`FixtureReply(status=200, body=b"", headers=())`; `json_reply(...)` is serialization sugar. `GraphFixture` exposes `origin`, `graph_root=origin+"/v1.0"`, exact-target `add(target,*replies)`, `url(target)`, and ordered `seen`. Match `BaseHTTPRequestHandler.path` literally: never parse, unquote, normalize, sort, or rebuild query parameters. Protect reply-sequence consumption/logging with a lock. Unexpected targets return deterministic 404 `FixtureRouteMissing`. Support arbitrary headers, exact binary bodies, and per-target sequences such as `429->200` or `503->200`; the server implements no retry policy.

Run normal project code in a subprocess. Common overrides are local `MS_GRAPH_SERVICE_ROOT`, `MS_GRAPH_AUTH_METHOD=none`, temporary catalog/raw paths, a synthetic source ID with `MSGLOOM_SOURCE_IDENTITY_REQUIRED=False` only in isolated auth-disabled fixtures, `AUTOTHROTTLE_ENABLED=False`, normally `HTTPCACHE_ENABLED=False`. Do not override `CONCURRENT_ITEMS`; the ordering test must consume project value `1`. Use `Retry-After: 0` for deterministic retry tests and leave Graph middleware/fingerprinting enabled.

Auth-disabled 401: assert no `Authorization`, one terminal 401, application-spider errback evidence, and failed integrity. MSAL refresh remains owned by existing auth tests; delegated auth intentionally refuses this HTTP fixture. Raw evidence is the final spider-visible exchange, not each retry attempt, so 429/503 success asserts server hits/retry stats plus final-200 evidence; retry exhaustion asserts terminal error evidence.

Every core crawl must resolve each semantic evidence ID to committed `RawHttpEvidence` with matching observation/source and stored body/header metadata. The ordering sentinel delays `RawEvidencePipeline.process_item()` as the OneDrive crawl test already does; `EvidenceLinkPipeline` must still find committed evidence before Teams persistence. This proves per-callback ordering under Scrapy 2.19 `CONCURRENT_ITEMS=1`, not global response serialization.

Terminal request/download failures use `message_ingest.spiders.microsoft._graph.MicrosoftGraphSpider.errback`; malformed callback output must signal `spider_error`; late pipeline exception/drop must signal `item_error`/`item_dropped`. Each sets `run_failed` and blocks any completion/checkpoint/promotion. Observation discovery never treats absence as deletion.

## Mandatory 36-fixture map

1. 1:1 chat -> `test_teams_chat_crawl::test_chat_topology_matrix`; persist chat/member/message + evidence.
2. >25-member group -> same crawl, 26+ explicit members; no 25-member truncation.
3. meeting chat -> same; preserve type/context without T4 fetches.
4. federated members -> same; preserve foreign tenant/member identity.
5. standard channel + multipage replies -> `test_teams_channel_crawl::test_channel_thread_pagination`.
6. private channel -> `test_teams_channel_crawl::test_channel_type_matrix`.
7. shared channel + host team -> `test_teams_shared_channel_crawl::test_shared_topology`.
8. incoming shared channel -> same shared crawl.
9. hydrate team after `associatedTeams` -> shared crawl; observe full provider-built team GET.
10. hydrate channel after list/allChannels -> channel/shared crawl; observe full channel GET.
11. edits -> `test_teams_chat_crawl::test_message_versions`; two etag/body/evidence versions retained.
12. direct deletion -> same; `deletedDateTime` changes current state, old evidence/content remains.
13. deleted notification/no readback -> notification reconciliation test; persist notification first, GET 404/410, keep deletion declaration.
14. delivery gap -> reconciliation test; reauthorization/removal or simulated gap + current read, history remains incomplete.
15. reactions/messageHistory -> provider + fidelity crawl; no invented old bodies.
16. system event -> provider + fidelity crawl; retain message/event detail.
17. mentions/custom emoji -> provider + fidelity crawl; retain mention identities and stable payload/body emoji occurrences.
18. `reference` attachment -> provider + fidelity crawl; retain reference, no core Files fetch/permission.
19. `forwardedMessageReference` -> provider + fidelity crawl; retain embedded reference.
20. chat-reply `messageReference` -> provider + fidelity crawl; retain scoped relation.
21. `meetingReference` -> provider + fidelity crawl; retain Exchange event linkage, no T4 acquisition.
22. `tabReference` -> provider + fidelity crawl; retain unresolved relation with T3 off.
23. Loop/code/announcement/ordinary/unknown cards -> provider + fidelity crawl; lossless unknown retention.
24. hosted image/code on normal/edited/deleted -> hosted-content crawl; exact bytes/headers, no unproved exact-version claim.
25. hosted-content failure on deleted thread -> integrity crawl; terminal evidence retained, no false completeness.
26. denied/missing/stale file reference -> provider+persistence; test explicit resolution observations without fetching arbitrary `contentUrl` values. Core acquisition defaults to `not-attempted` when the broad file profile is unselected; a reference alone does not prove denied, missing, or stale state.
27. pinned chat-message -> chat crawl; pin is a relation separate from message history.
28. shared `allMembers` direct+indirect -> shared crawl; keep multiple membership paths for one user.
29. cross-tenant `incomingChannels` link -> shared crawl; accept only P0-C-frozen documented rewrite target.
30. collection/reply pagination -> chat/channel crawl with awkward `%2f/%2F`, `+/%20`, repeated params; replay returned absolute URL exactly.
31. malformed envelopes -> integrity crawl; callback yields raw evidence before parsing the invalid Graph shape. Assert that raw evidence is durable after crawl completion and the callback failure marks integrity failed. Do not require the parser to wait for the raw write; native output prefetch can parse while that write is pending.
32. request/callback/pipeline failures -> terminal 401/403/exhausted retry, malformed callback, late fail/drop; assert all integrity signals and no promotion.
33. evidence-before-semantics -> `test_teams_persistence_ordering`; delayed evidence still precedes dependent semantic storage.
34. duplicate IDs across scopes -> `test_teams_pipeline::test_scoped_message_identity`; distinct durable identities/evidence.
35. empty chat/team/channel sets -> later empty crawl preserves observations; absence is not deletion.
36. JOBDIR -> `test_teams_commands::test_teams_rejects_jobdir_before_crawl`, chat/channel parameterized; fail before any HTTP request.

## Notification/T0 boundaries

Do not fake notification delivery through Graph HTTP. Feed notification JSON to the notification evidence/parser layer; only reconciliation GET uses `GraphFixture`. Current lifecycle docs list `reauthorizationRequired` for all resources and `subscriptionRemoved` for Teams `chatMessage`, but not `missed`; fixture 14 must not invent a Teams `missed` event. [Microsoft lifecycle contract](https://learn.microsoft.com/en-us/graph/change-notifications-lifecycle-events)

Do not hard-code subscription lifetime. Current Microsoft pages still conflict (generic Teams chat/channel/chatMessage: 4,320 minutes; Teams overview: 60 minutes). N0 must resolve the accepted renewal contract before subscription scheduling is implemented. Fixtures 13 and 14 remain mandatory local core persistence/semantics gates even while live notification delivery is unavailable. [Subscription resource](https://learn.microsoft.com/en-us/graph/api/resources/subscription?view=graph-rest-1.0) and [Teams notification overview](https://learn.microsoft.com/en-us/graph/teams-change-notification-in-microsoft-teams-overview)

Keep shared-channel membership IDs/resource links opaque except the single P0-C-frozen Microsoft-documented cross-tenant `@odata.id` workaround. Generic `@odata.nextLink` is replayed as the entire returned URL. [Microsoft paging contract](https://learn.microsoft.com/en-us/graph/paging)

## Harness acceptance

PASS when real Scrapy performs all requests; opaque links survive byte-for-byte; 429/503 use existing Graph retry; terminal failures use application errback/integrity; arbitrary headers/binary bodies reach raw evidence; malformed callbacks/late item failures fail closed; all 36 cases are traceable to named tests; and support code duplicates none of production path/parser/auth/retry/fingerprint/persistence/checkpoint logic.

## Delivery and coordinator validation

Worker: [P0-D conversation](https://chatgpt.com/c/6ac107e1-c520-83ec-966e-efe48588b0f8).
Task: `MSGLOOM_TEAMS_A1_P0-D_20261003_R1`.
Input: `7b9a7572b935f0e6ce6a96057b55951190afc8bf`.
Worker verdict: PASS for the harness design, not implemented tests.
Transcript model/effort validation: all four visible assistant replies record
`gpt-5-6-thinking` / `max`; the final turn is finished.
P0-E closure is still required.

The coordinator inspected the application Graph errback, evidence/link
pipelines, integrity extension, auth middleware, and existing Contacts, To Do,
and delayed-evidence OneDrive crawl tests. These support the proposed harness.
The coordinator reopened the linked Microsoft lifecycle, paging, subscription,
and Teams overview pages on 2026-10-03 UTC. The lifetime conflict remains real.

Coordinator clarifications require fixture-only identity bypass, core file
references to default to `not-attempted`, and deletion/gap persistence fixtures
to pass before local core completion. No live webhook prerequisite applies to
those local fixtures. These clarifications will be included in P0-E closure.

P0-E identified the callback-prefetch distinction. The coordinator verified it
against installed Scrapy 2.19.0 `Scraper.handle_spider_output_async()` and
`_parallel_asyncio()`: the bounded producer queue can advance the callback before
the evidence item finishes. A native-helper probe with concurrency one produced
`yield_evidence`, `parse_provider_payload`, `commit_evidence`, `commit_semantic`.
The required contract is yield-before-parse plus durable evidence before
dependent semantic persistence. The probe is not a substitute for real crawls.

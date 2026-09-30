# Outlook Mail Acquisition-Policy Spider Middleware Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Outlook-Mail-only Scrapy Spider Middleware adapter that preserves every Mail observation, delegates deterministic decisions to a future pure RuleEvaluator, schedules bounded rule probes, records privacy-safe audit logs/stats, and exposes attempt-local profile selections without persisting rule decisions.

**Architecture:** `OutlookMailCollectionSpider` is the only activation and request-serialization seam. A new `OutlookMailAcquisitionRuleMiddleware` runs at Spider Middleware priority 1100, streams Spider output, converts `OutlookMailItem` into a bounded evaluator observation, and handles `FINAL`, `NEEDS_DATA`, and `UNRESOLVED` results. This plan implements only the Scrapy adapter and contracts; actual Outlook-like rule semantics, TOML configuration, rule-decision SQL persistence, and Mail sync planner consumption remain out of scope.

**Tech Stack:** Python 3.13 active runtime; Scrapy 2.19.0; dataclasses/StrEnum/Protocol from the standard library; pytest 8; pytest-xdist 3.8; Ruff 0.16.9; Pyright; existing msgloom Microsoft Graph acquisition/logging infrastructure.

**Spec:** `docs/superpowers/specs/2026-09-30-outlook-mail-acquisition-rules-design.md`

## Global Constraints

- Scrapy runtime contract is exactly 2.19.0 for this implementation; do not use unreleased/master APIs.
- Do not add a global `SPIDER_MIDDLEWARES` entry in `message_ingest/settings.py`.
- Register the Mail rule middleware only from `OutlookMailCollectionSpider.update_settings()`.
- Use Spider Middleware component priority `1100`.
- Every original `OutlookMailItem` must pass through unchanged before any additional policy work.
- Non-Mail outputs must pass through unchanged.
- The middleware must stream output; it must not materialize callback output into a list.
- The middleware must not implement sender/subject/body/etc. rule semantics.
- The middleware must not perform Full-v1 acquisition.
- The middleware must not add rule-decision Items, SQL tables, pipeline persistence, or canonical rule snapshots.
- Logs are audit/observability only and must never be read as business-control state.
- Rule decisions are not persisted in the Mail database.
- Probe callbacks/errbacks must be named Spider methods so Scrapy JOBDIR can serialize them.
- A Mail observation may schedule at most one V1 body probe per evaluation attempt.
- Expected source-data probe failure becomes `UNRESOLVED`; programming failure marks the logical run failed.
- Per-message final decision logs are INFO; probe mechanics DEBUG; expected unresolved WARNING; programming failure ERROR.
- Never log subject/body/bodyPreview, email addresses, configured match values, label values, Graph URLs, tokens, arbitrary exception text, or traceback text.
- Do not add new third-party dependencies.
- Keep each Python module below 500 lines.
- Preserve existing no-rules behavior, Full spider behavior, checkpoint behavior, and other Microsoft products.
- The implementation scope baseline is spec commit `deed21a`; final scope audit compares `deed21a..HEAD`.

## Review Focus

1. **User-controlled rule/ruleset identifiers containing whitespace/newlines or format characters** — contract validation must reject unsafe correlation tokens so key/value logs cannot be injected or split. Task 1 adds explicit tests.
2. **The same message observed more than once in one crawl with a later profile change** — attempt-local runtime state must use the latest evaluated profile while preserving every decision log. Task 3 adds this regression.
3. **Probe response is HTTP-successful but body/version fields are missing or malformed** — raw source evidence still passes through and the internal probe result must be bounded/failable rather than crashing or becoming NO_MATCH. Task 4 adds these cases.
4. **A queued probe survives JOBDIR serialization/resume** — callback, errback, observation snapshot, Prefer header, and request metadata must round-trip without `scheduler/unserializable`. Task 6 proves both serialization and a controlled scheduler/crawl path.
5. **Evaluator throws after the original Mail Item was received** — the original Item must remain downstream, the logical run must fail, logs must expose only the exception class, and sensitive exception text must not appear in text or structured extras. Task 5 adds this failure-path test.

---

## File Structure

### New production files

- `message_ingest/acquisition/microsoft/outlook/email/rule_evaluation.py`
  - Pure, Scrapy-independent evaluator contracts and the bounded Mail observation snapshot.
- `message_ingest/acquisition/microsoft/outlook/email/rule_probe.py`
  - Internal probe-result contract shared by the Mail collection Spider callback and middleware.
- `message_ingest/spidermiddlewares/__init__.py`
- `message_ingest/spidermiddlewares/microsoft/__init__.py`
- `message_ingest/spidermiddlewares/microsoft/outlook/__init__.py`
- `message_ingest/spidermiddlewares/microsoft/outlook/email.py`
  - Scrapy adapter only: streaming output processing, evaluator calls, probe scheduling, runtime profile publication, logging/stats/integrity behavior.

### Existing production files to modify

- `message_ingest/acquisition/microsoft/outlook/email/__init__.py`
  - Re-export only the stable middleware-facing contracts that are useful outside their module.
- `message_ingest/spiders/microsoft/outlook/email/_base.py`
  - Register the middleware per collection Spider, provide evaluator factory/runtime-state seam, and own named probe request/callback/errback methods.
- `message_ingest/extensions/microsoft/outlook/email/status.py`
  - Add aggregate Mail-rule summary logging only when rule evaluation ran.
- `docs/statistics.md`
  - Document Mail-rule stats, audit event levels, and the log-retention boundary.
- `docs/component-layout.md`
  - Document new component ownership and the Mail-only activation seam.

### New/modified tests

- Create `tests/test_outlook_mail_rule_contracts.py`
- Create `tests/test_outlook_mail_rule_middleware.py`
- Create `tests/test_outlook_mail_rule_probe.py`
- Modify `tests/test_outlook_mail_collection_boundary.py`
- Modify `tests/test_jobdir_resume.py`
- Modify `tests/test_crawl_status_extension.py`
- Modify `tests/test_outlook_crawls.py` only if the controlled scheduler/JOBDIR proof cannot be expressed cleanly in a smaller dedicated test; prefer a new dedicated crawl test over expanding this file substantially.

---

### Task 1: Define the Pure Evaluator and Probe Contracts

**Files:**

- Create: `message_ingest/acquisition/microsoft/outlook/email/rule_evaluation.py`
- Create: `message_ingest/acquisition/microsoft/outlook/email/rule_probe.py`
- Modify: `message_ingest/acquisition/microsoft/outlook/email/__init__.py`
- Test: `tests/test_outlook_mail_rule_contracts.py`

**Interfaces:**

- Produces:
  - `MailRuleEvaluationState(StrEnum)` with exact values `FINAL = "final"`, `NEEDS_DATA = "needs_data"`, `UNRESOLVED = "unresolved"`.
  - `MailRuleDecisionOutcome(StrEnum)` with exact values `MATCHED = "matched"`, `DEFAULT = "default"`, `UNRESOLVED = "unresolved"`.
  - `MailRuleRequiredData(StrEnum)` with exact value `BODY = "body"`.
  - `MailRuleProbeStatus(StrEnum)` with exact values `COMPLETE = "complete"`, `FAILED = "failed"`.
  - `MailRuleObservation` as a frozen/slotted dataclass containing only discovery-visible facts required by the future V1 RuleEngine:
    `message_id`, `run_id`, `evidence_id`, `observation_kind`,
    `last_modified_date_time`, `subject`, `sender_address`, `from_address`,
    `to_addresses`, `cc_addresses`, `bcc_addresses`, `importance`,
    `categories`, `has_attachments`, `body_preview`.
  - `MailRuleProbeData` as a frozen/slotted dataclass containing
    `status`, `body`, `last_modified_date_time`, `evidence_id`,
    `reason_code`.
  - `MailRuleEvaluation` as a frozen/slotted dataclass containing
    `state`, `selected_profile`, `outcome`, `required_data`,
    `ruleset_id`, `ruleset_digest`, `matched_rule_ids`, `stop_rule_id`,
    `probe_used`, `fallback_used`, `reason_code`.
  - `MailRuleEvaluator(Protocol)`:
    `evaluate(observation: MailRuleObservation, *, probe: MailRuleProbeData | None = None) -> MailRuleEvaluation`.
  - `mail_rule_observation_from_item(item: OutlookMailItem) -> MailRuleObservation`.
  - `OutlookMailRuleProbeResult` in `rule_probe.py` as a frozen/slotted dataclass with `observation: MailRuleObservation` and `probe: MailRuleProbeData`.
- Consumes:
  - `OutlookMailItem.raw` only to project fixed discovery facts; the snapshot must not retain `raw`.

- [ ] **Step 1: Write failing tests for observation projection and state-shape validation**

Add tests named:

- `test_rule_observation_projects_discovery_facts_without_retaining_raw`
- `test_final_evaluation_requires_profile_and_terminal_outcome`
- `test_needs_data_requires_body_and_has_no_terminal_profile`
- `test_unresolved_requires_profile_reason_and_fallback`
- `test_rule_correlation_tokens_reject_log_injection_characters`
- `test_stop_rule_must_be_one_of_the_matched_rules`

The projection test must build an `OutlookMailItem` whose raw Graph object includes To/Cc/Bcc recipients, categories, and `lastModifiedDateTime`, then assert the snapshot contains those exact projected values and has no `raw` attribute.

The unsafe-token test must try at least `"rule\nforged"` and `"rule with spaces"` for `ruleset_id` or matched rule IDs and expect `ValueError`.

- [ ] **Step 2: Run the contract tests and verify RED**

Run:

`uv run --locked pytest -q tests/test_outlook_mail_rule_contracts.py`

Expected: collection/import failure because the new contracts do not exist.

- [ ] **Step 3: Implement the contract types and validation**

Use standard-library dataclasses, `StrEnum`, and `Protocol`; do not introduce Pydantic into `message_ingest`.

Use one shared safe-token validator equivalent to `[A-Za-z0-9_.:-]{1,96}` for log-correlated rule/ruleset/reason/profile tokens. A ruleset digest, when present, must be lowercase 64-character hexadecimal.

State-shape invariants:

- `FINAL`: `selected_profile` and terminal `outcome` required; `required_data is None`.
- `NEEDS_DATA`: `required_data is BODY`; no terminal profile/outcome/reason.
- `UNRESOLVED`: terminal profile, `outcome=UNRESOLVED`, `fallback_used=True`, and bounded `reason_code` required.
- `stop_rule_id`, when present, must appear in `matched_rule_ids`.

`mail_rule_observation_from_item()` must normalize recipient address lists into tuples while retaining exact source strings; it must not case-fold or perform rule semantics.

- [ ] **Step 4: Run the contract tests and verify GREEN**

Run:

`uv run --locked pytest -q tests/test_outlook_mail_rule_contracts.py`

Expected: all tests PASS.

- [ ] **Step 5: Run Ruff and Pyright on the new contracts**

Run:

`uv run --locked ruff check message_ingest/acquisition/microsoft/outlook/email tests/test_outlook_mail_rule_contracts.py`

Run:

`pyright message_ingest/acquisition/microsoft/outlook/email tests/test_outlook_mail_rule_contracts.py`

Expected: zero Ruff/Pyright errors.

- [ ] **Step 6: Commit Task 1**

```bash
git add message_ingest/acquisition/microsoft/outlook/email tests/test_outlook_mail_rule_contracts.py
git commit -m "Add Outlook Mail rule evaluation contracts"
```

---

### Task 2: Add the Mail-Only Activation Seam and Pass-Through Middleware Shell

**Files:**

- Create: `message_ingest/spidermiddlewares/__init__.py`
- Create: `message_ingest/spidermiddlewares/microsoft/__init__.py`
- Create: `message_ingest/spidermiddlewares/microsoft/outlook/__init__.py`
- Create: `message_ingest/spidermiddlewares/microsoft/outlook/email.py`
- Modify: `message_ingest/spiders/microsoft/outlook/email/_base.py`
- Modify: `tests/test_outlook_mail_collection_boundary.py`
- Test: `tests/test_outlook_mail_rule_middleware.py`

**Interfaces:**

- Consumes Task 1:
  - `MailRuleEvaluator`.
- Produces in `OutlookMailCollectionSpider`:
  - classmethod `build_mail_rule_evaluator(crawler) -> MailRuleEvaluator | None`, default `None`.
  - property `mail_rule_evaluator -> MailRuleEvaluator | None`.
  - `record_mail_rule_profile(*, message_id: str, profile: str) -> None`.
  - property `mail_rule_profiles -> tuple[tuple[str, str], ...]`.
- Produces in middleware:
  - `OutlookMailAcquisitionRuleMiddleware.from_crawler(crawler)`.
  - `async process_spider_output(response, result)` as an async generator.
  - constant `OUTLOOK_MAIL_RULE_MIDDLEWARE_PRIORITY = 1100`.
- Registration:
  - `OutlookMailCollectionSpider.update_settings()` lazily imports the middleware class and calls `settings.setdefault_in_component_priority_dict("SPIDER_MIDDLEWARES", ..., 1100)`.
  - Do not touch global `message_ingest/settings.py`.

- [ ] **Step 1: Extend the activation test to require the exact effective component matrix**

Update `tests/test_outlook_mail_collection_boundary.py` so it applies each Spider class's `update_settings()` to a fresh `Settings` object and asserts:

- Discover: custom middleware present at 1100.
- Delta: present at 1100.
- FolderDelta: absent.
- Full: absent.
- At least one Calendar Spider, To Do Spider, OneDrive Spider, Contacts Spider, and Microsoft profile Spider: absent.
- `message_ingest.settings` has no global custom Mail middleware entry.

Do not merely test inheritance.

- [ ] **Step 2: Add failing middleware construction tests**

In `tests/test_outlook_mail_rule_middleware.py`, add:

- `test_middleware_is_not_configured_without_collection_evaluator`
- `test_middleware_builds_for_collection_spider_with_evaluator`
- `test_middleware_rejects_non_collection_spider_even_if_misconfigured`

Use a tiny fake evaluator implementing Task 1's protocol. For construction tests, define a test-only `OutlookDiscoverSpider` subclass whose `build_mail_rule_evaluator(crawler)` returns that fake; do not add a temporary production setting solely for test injection.

- [ ] **Step 3: Run the activation/construction tests and verify RED**

Run:

`uv run --locked pytest -q tests/test_outlook_mail_collection_boundary.py tests/test_outlook_mail_rule_middleware.py`

Expected: failures because the middleware package, evaluator seam, and per-Spider registration do not exist.

- [ ] **Step 4: Implement the collection-Spider evaluator/runtime seam**

In `_base.py`:

- override `update_settings()` and register the middleware at 1100;
- override `from_crawler()` only as needed to call `build_mail_rule_evaluator(crawler)` after Scrapy has bound the crawler;
- initialize an insertion-ordered `dict[str, str]` for current attempt message/profile selections;
- expose immutable tuple snapshots through `mail_rule_profiles`.

`record_mail_rule_profile()` must overwrite the latest profile for an already-seen message ID without duplicating the message key.

- [ ] **Step 5: Implement the pass-through middleware shell**

`from_crawler()` must:

- require `crawler.spider` to be an `OutlookMailCollectionSpider`;
- read `spider.mail_rule_evaluator`;
- raise `NotConfigured` when it is `None`;
- otherwise retain only `crawler`, `spider`, and evaluator references.

The initial `process_spider_output()` implementation must stream/yield every output unchanged. Do not evaluate rules yet.

- [ ] **Step 6: Run tests and verify GREEN**

Run:

`uv run --locked pytest -q tests/test_outlook_mail_collection_boundary.py tests/test_outlook_mail_rule_middleware.py`

Expected: all current Task 2 tests PASS.

- [ ] **Step 7: Run the existing Graph add-on/extraction tests**

Run:

`uv run --locked pytest -q tests/test_graph_addon.py tests/test_graph_framework_extraction.py tests/test_microsoft_graph_package_layout.py`

Expected: PASS; the reusable `microsoft_graph` package remains uncoupled from msgloom rule policy.

- [ ] **Step 8: Commit Task 2**

```bash
git add message_ingest/spidermiddlewares message_ingest/spiders/microsoft/outlook/email/_base.py tests/test_outlook_mail_collection_boundary.py tests/test_outlook_mail_rule_middleware.py
git commit -m "Add Outlook Mail rule middleware activation seam"
```

---

### Task 3: Implement Streaming FINAL Decisions and Attempt-Local Profile State

**Files:**

- Modify: `message_ingest/spidermiddlewares/microsoft/outlook/email.py`
- Modify: `tests/test_outlook_mail_rule_middleware.py`

**Interfaces:**

- Consumes Task 1:
  - `mail_rule_observation_from_item()`;
  - `MailRuleEvaluationState.FINAL`;
  - `MailRuleEvaluation`.
- Consumes Task 2:
  - `OutlookMailCollectionSpider.record_mail_rule_profile()`.
- Produces:
  - FINAL evaluation path only; no probe behavior yet.
  - Helper methods may be private, but no new public interface is required.

- [ ] **Step 1: Add failing tests for pass-through, FINAL evaluation, duplicate observations, and streaming**

Add tests:

- `test_non_mail_outputs_pass_through_without_evaluator_call`
- `test_mail_item_is_yielded_unchanged_before_final_policy_side_effects`
- `test_final_profile_is_recorded_in_attempt_local_state`
- `test_later_observation_overwrites_profile_for_same_message`
- `test_process_spider_output_remains_streaming`

For the duplicate-observation test, evaluate the same message first as Full and then as discovery-only; assert `spider.mail_rule_profiles` contains one message entry with discovery-only as the latest value.

For the streaming test, use an async source generator that records whether its second element was requested. Consume only the first middleware output and assert the source has not been exhausted or pre-consumed.

- [ ] **Step 2: Run the new middleware tests and verify RED**

Run:

`uv run --locked pytest -q tests/test_outlook_mail_rule_middleware.py`

Expected: FINAL-path assertions fail because the middleware is still pass-through only.

- [ ] **Step 3: Implement FINAL evaluation without logging/stats yet**

For every `OutlookMailItem`:

1. yield the exact original Item object first;
2. build a `MailRuleObservation`;
3. call `evaluator.evaluate(observation, probe=None)`;
4. when state is FINAL, call `record_mail_rule_profile(message_id=..., profile=...)`;
5. yield no extra output for FINAL.

Requests and all non-Mail objects bypass the evaluator.

Do not add logging/stats in this task; Task 5 owns observability.

- [ ] **Step 4: Run Task 3 tests and verify GREEN**

Run:

`uv run --locked pytest -q tests/test_outlook_mail_rule_middleware.py`

Expected: PASS.

- [ ] **Step 5: Run existing Mail discovery/delta unit tests**

Run:

`uv run --locked pytest -q tests/test_outlook_spiders.py tests/test_outlook_mail_delta.py tests/test_outlook_shared_mailbox.py tests/test_outlook_folder_delta.py tests/test_outlook_mail_full_enrichment.py`

Expected: PASS; no existing Item is dropped or mutated.

- [ ] **Step 6: Commit Task 3**

```bash
git add message_ingest/spidermiddlewares/microsoft/outlook/email.py tests/test_outlook_mail_rule_middleware.py
git commit -m "Evaluate final Outlook Mail acquisition decisions"
```

---

### Task 4: Add the Named Body-Probe Request/Callback/Errback and NEEDS_DATA Flow

**Files:**

- Modify: `message_ingest/spiders/microsoft/outlook/email/_base.py`
- Modify: `message_ingest/spidermiddlewares/microsoft/outlook/email.py`
- Modify: `message_ingest/acquisition/microsoft/outlook/email/rule_probe.py`
- Create: `tests/test_outlook_mail_rule_probe.py`
- Modify: `tests/test_outlook_mail_rule_middleware.py`

**Interfaces:**

- Consumes Task 1:
  - `MailRuleRequiredData.BODY`;
  - `MailRuleProbeData`;
  - `MailRuleProbeStatus`;
  - `OutlookMailRuleProbeResult`.
- Produces on `OutlookMailCollectionSpider`:
  - `mail_rule_probe_request(observation: MailRuleObservation) -> scrapy.Request`.
  - `parse_mail_rule_probe(response: TextResponse, *, purpose: str, observation: MailRuleObservation) -> Iterator[Any]`.
  - `mail_rule_probe_errback(failure: Failure) -> Iterator[Any]`.
- Probe request contract:
  - purpose/Graph operation: `"mail-rule-probe"`;
  - selected fields: `id,lastModifiedDateTime,body,bodyPreview`;
  - `Prefer` combines immutable ID preference with `outlook.body-content-type="text"`;
  - `dont_cache=True`;
  - callback and errback are the named Spider methods above;
  - `cb_kwargs` carries `purpose` and the frozen/slotted `MailRuleObservation`.
- Middleware:
  - first `NEEDS_DATA(BODY)` emits exactly one probe Request;
  - `OutlookMailRuleProbeResult` is consumed, never yielded to pipelines;
  - the evaluator is called again with `probe=result.probe`.

- [ ] **Step 1: Write failing probe request/callback tests**

In `tests/test_outlook_mail_rule_probe.py`, add:

- `test_probe_request_selects_only_rule_fields_and_text_body`
- `test_probe_request_uses_named_callback_errback_and_disables_cache`
- `test_successful_probe_emits_raw_evidence_and_internal_result`
- `test_malformed_successful_probe_becomes_failed_probe_result`
- `test_probe_errback_emits_failure_evidence_and_failed_probe_without_marking_run_failed`

The malformed-success case must include one missing/non-string `body.content` example and assert the source evidence Item still exists.

The errback test must assert the Spider does **not** call the generic `_request_failure_item` path and therefore does not set `run_failed` merely because rule data was unavailable.

- [ ] **Step 2: Write failing middleware NEEDS_DATA tests**

Add to `tests/test_outlook_mail_rule_middleware.py`:

- `test_needs_body_schedules_one_probe_after_original_item`
- `test_multiple_needs_data_for_same_initial_observation_do_not_schedule_duplicate_probe`
- `test_probe_result_is_consumed_and_re_evaluated`
- `test_needs_data_after_probe_marks_integrity_failure_instead_of_looping`

The probe-result test must assert the internal `OutlookMailRuleProbeResult` does not appear in middleware output.

- [ ] **Step 3: Run the probe/middleware tests and verify RED**

Run:

`uv run --locked pytest -q tests/test_outlook_mail_rule_probe.py tests/test_outlook_mail_rule_middleware.py`

Expected: FAIL because probe methods/NEEDS_DATA handling do not exist.

- [ ] **Step 4: Implement the Spider probe request builder**

Use `graph_request()` directly rather than widening the shared application `_request()` helper just to support a custom errback.

Pass:

- `callback=self.parse_mail_rule_probe`;
- `errback=self.mail_rule_probe_errback`;
- `operation="mail-rule-probe"`;
- `cb_kwargs={"purpose": "mail-rule-probe", "observation": observation}`;
- `prefer=self.compose_prefer('outlook.body-content-type="text"')`;
- `dont_cache=True`.

Do not log the URL.

- [ ] **Step 5: Implement success and failure callbacks**

Success callback:

1. emit `_raw_http_evidence_item(response, purpose)`;
2. parse the bounded body/version fields;
3. emit `OutlookMailRuleProbeResult` with `COMPLETE` or `FAILED`;
4. use bounded reason code `invalid_probe_payload` for malformed/missing body fields.

Errback:

1. call the existing `_failure_evidence_item(failure)` to preserve source/transport evidence;
2. emit that evidence Item;
3. emit a failed `OutlookMailRuleProbeResult` with reason `probe_request_failed`;
4. do **not** call `_request_failure_item()`, because expected rule-probe unavailability is resolved by fail-safe policy rather than immediately invalidating the source crawl.

- [ ] **Step 6: Implement middleware probe scheduling/re-evaluation**

Maintain an attempt-local set keyed by the immutable observation identity needed to prevent duplicate body probes. Use message ID + source evidence ID + observation kind; include run ID when present.

On first `NEEDS_DATA(BODY)`, yield one probe Request.

On an internal probe result:

- consume it;
- call the evaluator with the original observation and probe;
- handle FINAL/UNRESOLVED terminal states;
- if it again returns NEEDS_DATA, call `spider.mark_run_failed("mail_rule_probe_loop")` and do not schedule another request.

- [ ] **Step 7: Run the probe/middleware tests and verify GREEN**

Run:

`uv run --locked pytest -q tests/test_outlook_mail_rule_probe.py tests/test_outlook_mail_rule_middleware.py`

Expected: PASS.

- [ ] **Step 8: Commit Task 4**

```bash
git add message_ingest/spiders/microsoft/outlook/email/_base.py message_ingest/spidermiddlewares/microsoft/outlook/email.py message_ingest/acquisition/microsoft/outlook/email/rule_probe.py tests/test_outlook_mail_rule_probe.py tests/test_outlook_mail_rule_middleware.py
git commit -m "Add Outlook Mail rule body probe lifecycle"
```

---

### Task 5: Add Privacy-Safe Logs, Aggregate Stats, UNRESOLVED Handling, and Programming-Failure Integrity

**Files:**

- Modify: `message_ingest/spidermiddlewares/microsoft/outlook/email.py`
- Modify: `tests/test_outlook_mail_rule_middleware.py`
- Test/inspect: existing `message_ingest/observability/formatter.py` and Graph privacy filter; do not modify unless a failing test proves it is necessary.

**Interfaces:**

- Final decision event token: `outlook_mail_rule_decision`.
- Probe tokens:
  - `outlook_mail_rule_probe_scheduled`;
  - `outlook_mail_rule_probe_completed`.
- Expected unresolved token: `outlook_mail_rule_unresolved`.
- Programming-error token: `outlook_mail_rule_error`.
- Required stat keys:
  - `msgloom/crawl/mail_rules/evaluated_count`
  - `msgloom/crawl/mail_rules/matched_count`
  - `msgloom/crawl/mail_rules/default_count`
  - `msgloom/crawl/mail_rules/unresolved_count`
  - `msgloom/crawl/mail_rules/probe_scheduled_count`
  - `msgloom/crawl/mail_rules/probe_completed_count`
  - `msgloom/crawl/mail_rules/probe_failed_count`
  - `msgloom/crawl/mail_rules/stop_processing_count`
  - `msgloom/crawl/mail_rules/fallback_count`
  - `msgloom/crawl/mail_rules/evaluation_error_count`

- [ ] **Step 1: Write failing log-level and counter tests**

Add tests:

- `test_final_decision_logs_one_info_event_with_safe_correlation_fields`
- `test_probe_events_are_debug_only`
- `test_unresolved_logs_warning_and_final_info_and_records_fail_safe_profile`
- `test_evaluator_exception_preserves_item_marks_run_failed_and_logs_error_type_only`
- `test_rule_stats_are_aggregate_and_identifier_free`
- `test_sensitive_mail_rule_data_is_absent_from_log_text_and_record_extras`

The sensitive-data test must place distinct sentinel strings in:

- subject;
- body preview;
- sender/from/recipient address;
- a fake evaluator exception message.

Assert none appear in `caplog.text` or serialized safe representations of captured LogRecord extras.

- [ ] **Step 2: Run the middleware tests and verify RED**

Run:

`uv run --locked pytest -q tests/test_outlook_mail_rule_middleware.py`

Expected: logging/stats/failure assertions fail.

- [ ] **Step 3: Implement the module logger and safe formatting helpers**

Use `logging.getLogger(__name__)`.

Do not use `logger.exception()`.

Use safe bounded correlation values only. Render opaque message IDs with `%r` so control characters are escaped by representation rather than inserted literally.

Do not attach observation/evaluator/probe objects to `extra`. If `extra` is used, restrict it to the Spider object following the existing project pattern.

- [ ] **Step 4: Implement final-decision publication**

For FINAL:

- increment `evaluated_count`;
- increment exactly one of matched/default;
- update stop-processing count when applicable;
- record the selected profile in Spider runtime state;
- emit one INFO `outlook_mail_rule_decision` event.

For UNRESOLVED:

- increment `evaluated_count`, `unresolved_count`, and fallback count;
- record fail-safe profile in runtime state;
- emit WARNING `outlook_mail_rule_unresolved`;
- emit one INFO final decision event with `outcome=unresolved`.

- [ ] **Step 5: Implement probe stats/logs**

When scheduling:

- increment `probe_scheduled_count`;
- DEBUG log scheduled event.

When consuming probe result:

- increment `probe_completed_count` for complete;
- increment `probe_failed_count` for failed;
- DEBUG log completed event with only bounded status/reason.

- [ ] **Step 6: Implement programming-failure handling**

Catch exceptions around evaluator invocation and validate evaluator return type/state.

On programming failure:

- original Mail Item must already have been yielded;
- call `spider.mark_run_failed("mail_rule_evaluation_error")` or the more specific bounded probe-loop reason;
- increment `evaluation_error_count`;
- ERROR log event with `error_type=type(exc).__name__`;
- never include `str(exc)`, traceback, evaluator repr, observation repr, or Mail content.

- [ ] **Step 7: Run middleware and privacy tests and verify GREEN**

Run:

`uv run --locked pytest -q tests/test_outlook_mail_rule_middleware.py tests/test_graph_log_privacy.py tests/test_logformatter.py`

Expected: PASS.

- [ ] **Step 8: Run Ruff/Pyright for middleware-related modules**

Run:

`uv run --locked ruff check message_ingest/spidermiddlewares message_ingest/acquisition/microsoft/outlook/email message_ingest/spiders/microsoft/outlook/email tests/test_outlook_mail_rule_middleware.py tests/test_outlook_mail_rule_probe.py`

Run:

`pyright message_ingest/spidermiddlewares message_ingest/acquisition/microsoft/outlook/email message_ingest/spiders/microsoft/outlook/email tests/test_outlook_mail_rule_middleware.py tests/test_outlook_mail_rule_probe.py`

Expected: zero errors.

- [ ] **Step 9: Commit Task 5**

```bash
git add message_ingest/spidermiddlewares/microsoft/outlook/email.py tests/test_outlook_mail_rule_middleware.py
git commit -m "Add Outlook Mail rule observability and fail-safe handling"
```

---

### Task 6: Prove Real Scrapy Ordering and JOBDIR Serialization/Resume

**Files:**

- Modify: `tests/test_jobdir_resume.py`
- Create: `tests/test_outlook_mail_rule_middleware_integration.py`
- Modify: `message_ingest/spidermiddlewares/microsoft/outlook/email.py` or `_base.py` only if the real-framework tests expose a contract bug.

**Interfaces:**

- Consumes Tasks 2-5 as-is.
- No new public production interfaces should be introduced solely to satisfy tests.

- [ ] **Step 1: Add failing Request serialization coverage**

Extend `tests/test_jobdir_resume.py` with a test that:

1. creates an Outlook Mail collection Spider;
2. builds a `MailRuleObservation`;
3. calls `mail_rule_probe_request()`;
4. serializes with `request.to_dict(spider=spider)`;
5. pickle round-trips the request dict;
6. restores with `request_from_dict(..., spider=spider)`;
7. asserts callback, errback, `cb_kwargs`, meta, headers, and URL are equivalent.

Explicitly assert the restored callback is `spider.parse_mail_rule_probe` and errback is `spider.mail_rule_probe_errback`.

- [ ] **Step 2: Add failing real SpiderMiddlewareManager priority test**

In `tests/test_outlook_mail_rule_middleware_integration.py`, construct a real crawler/Spider with a fake evaluator returning NEEDS_DATA and build the actual `SpiderMiddlewareManager`.

Feed it a real `Response` linked to a Request with an existing depth.

Assert the probe Request emitted by the custom middleware later contains the expected incremented depth and normal Referer-compatible output behavior, proving priority 1100 places the middleware before lower-priority built-ins on the output path.

Do not mock the middleware manager.

- [ ] **Step 3: Add a controlled scheduler/JOBDIR proof**

Use a temporary JOBDIR and either:

- a minimal real Crawler/Scheduler fixture, or
- a dedicated subprocess crawl with a tiny local Graph fixture and a test-only evaluator factory.

Prove:

- the rule probe reaches the disk-backed scheduler path;
- no `scheduler/unserializable` stat/log is produced;
- after clean stop/reconstruction, the queued request can restore its named callback/errback and observation context.

Keep this test independent of actual Microsoft credentials/network.

- [ ] **Step 4: Run the new integration tests and verify RED if any contract is incomplete**

Run:

`uv run --locked pytest -q tests/test_jobdir_resume.py tests/test_outlook_mail_rule_middleware_integration.py`

Expected before any necessary framework fixes: at least the new integration assertion demonstrates the missing behavior; after prior tasks it may already pass. If it passes immediately, do not manufacture a code change—record that Tasks 2-5 already satisfy the contract and proceed.

- [ ] **Step 5: Apply only framework-driven fixes exposed by the tests**

Allowed fixes include:

- correcting middleware priority registration;
- making a callback/errback method discoverable by `Request.to_dict`;
- replacing non-picklable probe context with the Task 1 frozen dataclass;
- correcting async generator signature/manager compatibility.

Do not expand into RuleEngine semantics or planner integration.

- [ ] **Step 6: Re-run integration/JOBDIR tests and verify GREEN**

Run:

`uv run --locked pytest -q tests/test_jobdir_resume.py tests/test_outlook_mail_rule_middleware_integration.py`

Expected: PASS and no unserializable scheduler output.

- [ ] **Step 7: Run existing Outlook crawl/serialization regressions**

Run:

`uv run --locked pytest -q tests/test_outlook_crawls.py tests/test_outlook_attachment_contract.py tests/test_outlook_shared_sync_crawl.py tests/test_outlook_sync_workflows.py`

Expected: PASS.

- [ ] **Step 8: Commit Task 6**

```bash
git add tests/test_jobdir_resume.py tests/test_outlook_mail_rule_middleware_integration.py message_ingest/spidermiddlewares/microsoft/outlook/email.py message_ingest/spiders/microsoft/outlook/email/_base.py
git commit -m "Prove Outlook Mail rule middleware resume behavior"
```

Only add production files to this commit when they actually changed.

---

### Task 7: Add Crawl-Level Rule Summary and Documentation

**Files:**

- Modify: `message_ingest/extensions/microsoft/outlook/email/status.py`
- Modify: `tests/test_crawl_status_extension.py`
- Modify: `docs/statistics.md`
- Modify: `docs/component-layout.md`

**Interfaces:**

- Produces log event `outlook_mail_rule_summary` at INFO when and only when `msgloom/crawl/mail_rules/evaluated_count > 0`.
- Summary fields are aggregate counts only; no message IDs, rule IDs, labels, addresses, or rule text.

- [ ] **Step 1: Add failing crawl-summary tests**

In `tests/test_crawl_status_extension.py`, add:

- `test_rule_summary_logs_aggregate_counts_when_rule_evaluation_ran`
- `test_rule_summary_is_absent_when_rule_evaluation_did_not_run`

The positive test must seed stats for evaluated/matched/default/unresolved/probe/fallback/error counts and assert the INFO summary includes those values but no identifier sentinel.

- [ ] **Step 2: Run status tests and verify RED**

Run:

`uv run --locked pytest -q tests/test_crawl_status_extension.py`

Expected: FAIL because the summary event is not emitted yet.

- [ ] **Step 3: Implement aggregate summary publication in the existing status extension**

Add one private helper, for example `_publish_mail_rule_summary(spider)`, called after discovery/delta mode summaries.

Return immediately when evaluated count is zero.

Emit one INFO line with `event=outlook_mail_rule_summary` and aggregate counts only.

Do not make the extension decide correctness or targets.

- [ ] **Step 4: Run status tests and verify GREEN**

Run:

`uv run --locked pytest -q tests/test_crawl_status_extension.py`

Expected: PASS.

- [ ] **Step 5: Update observability/component documentation**

In `docs/statistics.md`, document:

- the `msgloom/crawl/mail_rules/*` counters;
- event-level severity;
- prohibited content;
- stats/logs are not control state;
- repository currently does not guarantee long-term log retention without deployment configuration.

In `docs/component-layout.md`, document:

- `rule_evaluation.py`;
- `rule_probe.py`;
- Mail-only Spider Middleware;
- `OutlookMailCollectionSpider` activation/request serialization ownership;
- no coupling into `microsoft_graph`.

- [ ] **Step 6: Run Markdown/pre-commit checks for documentation**

Run:

`git diff --check`

Run:

`pre-commit run --all-files`

Expected: all hooks PASS.

- [ ] **Step 7: Commit Task 7**

```bash
git add message_ingest/extensions/microsoft/outlook/email/status.py tests/test_crawl_status_extension.py docs/statistics.md docs/component-layout.md
git commit -m "Document Outlook Mail rule middleware observability"
```

---

### Task 8: Final Middleware-Phase Verification and Scope Audit

**Files:**

- No planned production changes.
- Modify only if verification exposes a real defect within the approved middleware scope.

**Interfaces:**

- Verifies all prior task interfaces and the formal spec acceptance criteria.

- [ ] **Step 1: Run the focused middleware suite**

Run:

`uv run --locked pytest -q tests/test_outlook_mail_rule_contracts.py tests/test_outlook_mail_collection_boundary.py tests/test_outlook_mail_rule_middleware.py tests/test_outlook_mail_rule_probe.py tests/test_outlook_mail_rule_middleware_integration.py tests/test_jobdir_resume.py tests/test_crawl_status_extension.py tests/test_graph_log_privacy.py tests/test_logformatter.py`

Expected: PASS.

- [ ] **Step 2: Run the relevant Outlook regression suite**

Run:

`uv run --locked pytest -q tests/test_outlook_spiders.py tests/test_outlook_mail_delta.py tests/test_outlook_folder_delta.py tests/test_outlook_mail_full_enrichment.py tests/test_outlook_shared_mailbox.py tests/test_outlook_sync_workflows.py tests/test_outlook_crawls.py tests/test_outlook_shared_sync_crawl.py`

Expected: PASS.

- [ ] **Step 3: Run Ruff**

Run:

`uv run --locked ruff check message_ingest microsoft_graph tests`

Expected: no Ruff errors.

- [ ] **Step 4: Run Pyright**

Run:

`pyright message_ingest microsoft_graph tests`

Expected: zero errors/warnings according to repository policy.

- [ ] **Step 5: Run the repository-supported xdist/non-xdist pytest split**

Run:

`uv run --locked pytest -q -n 4 -m "not exclusive_state and not fastmcp_compat"`

Expected: all selected tests PASS; no xdist collection mismatch.

Then:

`uv run --locked pytest -q -n 0 -m "exclusive_state and not fastmcp_compat"`

Expected: all selected tests PASS.

- [ ] **Step 6: Run the packaged py313 tox environment if available in the executor environment**

Run:

`uv run --locked tox -e py313`

Expected: PASS.

If the environment cannot run the tox packaging lane, record the exact infrastructure limitation and do not replace it with a success claim.

- [ ] **Step 7: Audit the diff against the spec's forbidden scope**

Run searches:

```bash
git diff --name-only deed21a..HEAD
rg -n "MailRule|mail_rule|outlook_mail_rule" message_ingest microsoft_graph
rg -n "SPIDER_MIDDLEWARES" message_ingest/settings.py message_ingest/spiders
```

Verify manually:

- no rule-decision SQL/table migration;
- no rule-decision pipeline;
- no TOML rule parser;
- no sender/subject/body predicate implementation;
- no Mail sync planner consumption;
- no Full spider behavior change;
- no `microsoft_graph` import of msgloom rule policy;
- no global Mail middleware registration.

- [ ] **Step 8: Confirm log privacy with a final targeted run**

Run the middleware sensitive-data log test at INFO/DEBUG capture and inspect captured text/extras.

Expected: only allowed correlation fields and error type; no source content or arbitrary exception message.

- [ ] **Step 9: Commit any verification-only fixes, otherwise leave the branch unchanged**

If no defects were found, do not create an empty commit.

If fixes were required, use one narrow commit such as:

```bash
git add <only-fixed-files>
git commit -m "Fix Outlook Mail rule middleware verification gaps"
```

- [ ] **Step 10: Produce the implementation completion report**

Report:

- commit range;
- files added/changed;
- exact tests/checks run and outcomes;
- Scrapy version verified;
- whether controlled JOBDIR probe resume passed;
- whether xdist split passed;
- confirmation that no rule-decision DB persistence or RuleEngine semantics were added;
- remaining next phase: deterministic RuleEngine/config implementation.

---

## Self-Review Results

### Spec coverage

Every middleware-phase requirement in the approved spec is mapped:

- Mail-only activation: Task 2.
- Priority 1100 and real output-chain ordering: Tasks 2 and 6.
- Streaming output and original Item preservation: Task 3.
- Pure evaluator boundary: Task 1.
- Body probe, named callback/errback, one-probe bound: Task 4.
- JOBDIR serialization/resume: Task 6.
- Runtime-only profile selection state: Tasks 2 and 3.
- Expected unresolved vs programming failure: Tasks 4 and 5.
- Per-message INFO audit and privacy-safe logs: Task 5.
- Aggregate stats/crawl summary: Tasks 5 and 7.
- No decision DB/pipeline persistence: Global Constraints and Task 8 audit.
- No-rules backward compatibility: Tasks 2, 6, and 8.
- Documentation/log-retention boundary: Task 7.
- Full regression/xdist stability: Task 8.

### Type consistency

The plan uses one evaluator input model (`MailRuleObservation`), one optional probe model (`MailRuleProbeData`), one terminal/intermediate result (`MailRuleEvaluation`), and one internal Spider-output wrapper (`OutlookMailRuleProbeResult`) throughout Tasks 1-8.

### Scope boundary

This plan intentionally stops before:

- actual Outlook-like predicate semantics;
- owner TOML configuration;
- canonical ruleset binding to JOBDIR;
- Mail sync planner consumption.

Those belong to later phases after this middleware adapter is proven.

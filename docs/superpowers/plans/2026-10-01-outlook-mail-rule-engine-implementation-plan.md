# Outlook Mail Deterministic RuleEngine and User Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Do not dispatch subagents for this project. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved Outlook Mail deterministic acquisition RuleEngine, universal user-configuration slice, composite probe, policy/JOBDIR binding, and rules-aware Mail sync/checkpoint handoff without persisting per-message policy decisions.

**Architecture:** The implementation keeps two configuration planes: Scrapy settings continue to own crawler mechanics, while one XDG-resolved `msgloom.toml` owns user policy. A pure Mail policy/evaluation layer consumes bounded source facts and may request at most one composite provider probe; Scrapy adapters only acquire facts, preserve evidence, and publish attempt-local Full targets. Rules-enabled sync defers message-delta promotion until current-attempt Full-v1 terminal completeness is proven, then atomically promotes lifecycle and cursors.

**Tech Stack:** Python 3.12/3.13/3.14 supported, active development runtime Python 3.13.5; Scrapy 2.19.0; Pydantic 2.13.5 / pydantic-settings 2.15.0; SQLAlchemy 2.0.x; selectolax/Lexbor 0.4.12; Google RE2 Python binding `google-re2==1.1.20251105`; pytest 8; pytest-xdist 3.8; Ruff 0.16.9; Pyright; SQLite catalog/evidence store; Microsoft Graph v1.0.

**Spec:** `docs/superpowers/specs/2026-10-01-outlook-mail-rule-engine-configuration-design.md`

**Completed adapter baseline:** `docs/superpowers/specs/2026-09-30-outlook-mail-acquisition-rules-design.md`

## Global Constraints

- Work only in the existing `feature/outlook-mail-rule-middleware` worktree/branch unless the user explicitly changes that direction.
- Do not use subagents. Execute serially with `superpowers:executing-plans`.
- Use TDD for every production change: failing test, observed RED, minimal implementation, observed GREEN, focused static checks, commit.
- Scrapy runtime contract is exactly 2.19.0; do not design against unreleased/master APIs.
- The universal user config default is `$XDG_CONFIG_HOME/msgloom/msgloom.toml`, falling back to `~/.config/msgloom/msgloom.toml`; a missing default file is valid empty config, while a missing explicit `--config FILE` is an error.
- There is one universal TOML file. Do not create `mail-rules.toml`, a Mail-only env precedence tree, or a Scrapy setting containing raw rules.
- Existing legacy A2/A3/A5 operator config models remain strict; operation-specific projection prevents unrelated sections from blocking Mail acquisition.
- Mail policy is active only for `enabled = true`; absent/disabled policy preserves current acquisition behavior.
- User profile vocabulary is exactly `discovery` / `full`; internal contracts remain `outlook-mail-discovery-v1` and `outlook-mail-full-v1`.
- Rule IDs and sequence values are unique. Rule IDs are bounded non-secret audit tokens; sequence is `0..2_147_483_647`.
- Different fields in one block are AND; values inside one field are OR; exception blocks are OR; no arbitrary nested boolean expressions in V1.
- Ordinary literal text matching uses Unicode `str.casefold()`; no Unicode normalization/accent folding/transliteration. Address config values strip surrounding whitespace.
- Regex contract is `msgloom-regex-v1`, search semantics, default case-insensitive, user pattern unchanged, RE2 `log_errors=false`, `max_mem=4 MiB`, maximum 64 configured regex patterns, maximum 4096 characters per pattern.
- Do not silently widen `msgloom-regex-v1`; compatibility tests include accepted and rejected syntax.
- Mail source facts distinguish known empty/null from unavailable/malformed. Never truncate an oversized provider value and then treat the truncated value as complete truth.
- One observation schedules at most one composite rule probe. Rule probe HTTP response cap is 8 MiB; logical projected BODY cap is 8 MiB UTF-8.
- `bodyPreview` is not terminal body-match evidence in V1.
- Probe mutation fence uses exact `changeKey`, not `lastModifiedDateTime`.
- Expected relevant source/probe/regex uncertainty becomes per-message `UNRESOLVED -> full`; programming/integrity failures mark the logical run failed.
- Rule selection is monotonic `discovery < full`; duplicate observations accumulate strongest profile.
- Do not persist per-message rule decisions or recover control state from logs.
- Raw rules and the private effective-policy digest must never enter Scrapy settings, SpiderState, Request serialization, stats, Items, config inspection, logs, or arbitrary error text.
- The effective-policy digest is private control state: memory plus owner-only `0600` JOBDIR marker only.
- Rule predicates must use the existing Mail read permissions only (`Mail.Read` / current shared-mailbox `Mail.Read.Shared` path). Do not add profile/directory/write scopes.
- Rules-enabled sync must not use the legacy global incomplete-Full backlog.
- Rules-enabled message-delta commit is deferred until required Full targets reach current-attempt Full-v1 terminal completeness.
- Rule-planned Full refresh is authoritative/no-cache.
- Final rules-enabled lifecycle + message-delta cursor promotion is one SQLite transaction.
- Rules-disabled sync, explicit operator Full, Calendar, To Do, OneDrive, Contacts, auth, and profile behavior remain unchanged unless a task below explicitly names the shared helper it must extend.
- Do not claim the phase complete until the real Microsoft Graph composite-probe qualification passes.
- Do not merge, push, or clean the branch unless the user explicitly asks.

## Review Focus

1. **An unrelated, partially-written legacy `[triage]` section sits beside valid Mail policy.** A Mail command must still run because it validates only the Mail projection, while `msgloom config validate` and a legacy triage command must reject the incomplete legacy projection. Tasks 4 and 12 pin both sides.
2. **A relevant source fact is unavailable while another field already makes the rule false/excluded.** The engine must not probe merely because one fact is unknown; a cheap false condition or true exception must dominate. Tasks 7 and 9 pin this.
3. **One regex alternative has a bounded engine failure while another alternative matches.** OR truth must be TRUE, not unresolved, and result must not depend on value ordering. Task 7 pins this.
4. **HTTP cache contains an older successful Full response for a rule-selected target.** The rules-enabled authoritative refresh must bypass cache and the completion verifier must require current-run evidence. Task 16 pins this.
5. **Final delta promotion fails after lifecycle mutations have started.** One SQLite transaction must roll back lifecycle, cursor, and candidate committed timestamps together, leaving the prior authoritative cursor/state unchanged. Task 15 injects this failure.

---

## File Structure

### New production modules

- `msgloom/configuration/universal.py`
  - Hardened XDG/default/explicit universal document resolution, bounded TOML read, closed top-level vocabulary, operation projections.
- `message_ingest/acquisition/microsoft/outlook/email/rule_regex.py`
  - `msgloom-regex-v1` RE2 adapter and privacy/resource bounds.
- `message_ingest/acquisition/microsoft/outlook/email/rule_config.py`
  - Closed Mail user-policy models, profile mapping, rule validation, canonical effective-policy digest.
- `message_ingest/acquisition/microsoft/outlook/email/rule_body.py`
  - Deterministic bounded text/HTML -> logical BODY projection.
- `message_ingest/acquisition/microsoft/outlook/email/rule_predicates.py`
  - Pure tri-state predicate/block evaluation over bounded facts.
- `message_ingest/acquisition/microsoft/outlook/email/rule_engine.py`
  - Ordered deterministic RuleEngine, required-data union, mutation fence, final/fallback result construction.
- `message_ingest/acquisition/microsoft/outlook/email/policy_context.py`
  - Private Mail policy JOBDIR marker and pre-Scheduler extension.
- `message_ingest/acquisition/microsoft/outlook/email/full_completion.py`
  - Current-attempt Full-v1 terminal-completeness verifier.
- `message_ingest/sync/microsoft/outlook/email/promotion.py`
  - Validated message-delta run contract and atomic lifecycle/cursor promotion service.

### Existing production modules to modify

- `pyproject.toml`, `uv.lock`
  - Pin `google-re2==1.1.20251105`.
- `msgloom/configuration/errors.py`, `msgloom/configuration/loader.py`, `msgloom/configuration/__init__.py`
  - Add privacy-safe structured diagnostics and reuse universal document projection for existing operator config without weakening legacy strictness.
- `msgloom/cli/app.py`, `msgloom/cli/models.py`, `msgloom/cli/runner.py`
  - XDG-default `config validate/inspect`, whole-file `--config`, all-present projection validation, redacted Mail metadata.
- `microsoft_graph/spiders/outlook/mail.py`
  - Add `changeKey` to discovery fields and add a bounded message-detail query seam for `$select` + `$expand`.
- `message_ingest/acquisition/microsoft/outlook/email/profile.py`
  - Add internal discovery profile constant/mapping helpers without changing Full-v1 completion semantics.
- `message_ingest/acquisition/microsoft/outlook/email/rule_evaluation.py`
  - Expand facts/availability, required-data set, partial probe contract, private digest handling.
- `message_ingest/acquisition/microsoft/outlook/email/rule_probe.py`
  - Carry composite probe result.
- `message_ingest/acquisition/microsoft/outlook/email/__init__.py`
  - Re-export stable Mail policy/evaluator contracts only.
- `message_ingest/spiders/microsoft/outlook/email/_base.py`
  - Consume private policy argument, direct-crawl default resolver, evaluator construction, composite probe request/parser, strongest-profile handoff, policy extension registration.
- `message_ingest/spidermiddlewares/microsoft/outlook/email.py`
  - Handle required-data sets/partial probes, private digest privacy, strongest-profile accumulation.
- `message_ingest/spiders/microsoft/outlook/email/_attachments.py`
  - Honor private authoritative-refresh no-cache flag for attachment requests.
- `message_ingest/spiders/microsoft/outlook/email/full.py`
  - Honor private authoritative-refresh no-cache flag for base Full requests without changing explicit Full semantics.
- `message_ingest/spiders/microsoft/outlook/email/delta.py`, `_delta_state.py`
  - Derive private immediate/deferred/blocked checkpoint mode and expose validated run state.
- `message_ingest/extensions/microsoft/outlook/email/checkpoint.py`
  - Single-sourced validation plus immediate/deferred/blocked handling.
- `message_ingest/extensions/microsoft/outlook/email/status.py`
  - Recognize clean deferred delta as completed collection phase while preserving observability-only ownership.
- `message_ingest/sync/microsoft/outlook/email/checkpoints.py`
  - Session-scoped checkpoint promotion helper.
- `message_ingest/catalog/stores/microsoft/outlook/_email_lifecycle.py`
  - Session-scoped lifecycle promotion helper.
- `message_ingest/catalog/stores/evidence.py`
  - Bounded evidence provenance query for current-run completion proof.
- `message_ingest/commands/_common.py`
  - Phase-specific completion validator and one workflow `on_success` finalizer.
- `message_ingest/commands/microsoft/options.py`, `message_ingest/commands/microsoft/__init__.py`, `message_ingest/commands/microsoft/outlook/mail.py`
  - `--config` path matrix, policy load once per invocation, public delta/max-enrich fail-closed rules.
- `message_ingest/commands/microsoft/outlook/sync.py`
  - Attempt-local rule target planner, authoritative Full phases, current-run completion gate, zero-target finalization, atomic promotion.
- `scripts/microsoft-live-acceptance.py`
  - Read-only real-Graph Mail rule/composite-probe qualification.
- `docs/component-layout.md`, `docs/statistics.md`, `docs/outlook-mail-rules.md`
  - Component ownership, safe stats/log contract, comprehensive non-technical user guide.

### New focused tests

- `tests/configuration/test_universal.py`
- `tests/test_outlook_mail_rule_regex.py`
- `tests/test_outlook_mail_rule_config.py`
- `tests/test_outlook_mail_rule_body.py`
- `tests/test_outlook_mail_rule_predicates_metadata.py`
- `tests/test_outlook_mail_rule_predicates_probe.py`
- `tests/test_outlook_mail_rule_engine.py`
- `tests/test_outlook_mail_policy_context.py`
- `tests/test_outlook_mail_full_completion.py`
- `tests/test_outlook_mail_atomic_promotion.py`

Existing focused suites are modified rather than duplicated where they already own the behavior.

---

## Phase A — Configuration, dependency, and source-fact contracts

### Task 1: Add the Universal Config Document and Preserve Legacy Operator Strictness

**Session boundary:** stop after the Task 1 commit.

**Files:**

- Create: `msgloom/configuration/universal.py`
- Modify: `msgloom/configuration/errors.py`
- Modify: `msgloom/configuration/loader.py`
- Modify: `msgloom/configuration/__init__.py`
- Test: `tests/configuration/test_universal.py`
- Modify: `tests/configuration/test_loading.py`

**Interfaces:**

- Produces in `errors.py`:
  - frozen/slotted `ConfigurationDiagnostic` with `source_label: str | None`, `field_path: str | None`, `line: int | None`, `column: int | None`, `reason_code: str | None`, `suggestion: str | None`.
  - `ConfigurationError(code: ConfigurationErrorCode, diagnostic: ConfigurationDiagnostic | None = None)`; `str(error)` stays the existing fixed generic message.
  - `configuration_error_payload(error: ConfigurationError) -> dict[str, object]` returning only safe code/diagnostic fields.
  - `format_configuration_error(error: ConfigurationError) -> str` selecting human text from a closed reason-code map and never echoing filesystem paths, Pydantic/TOML exception messages, values, or regex text.
- Produces:
  - `UniversalConfigSource = Literal["builtin", "default", "explicit"]`.
  - frozen/slotted `UniversalConfigDocument` with:
    - `source: UniversalConfigSource`
    - `path: Path | None`
    - `values: Mapping[str, object]`
    - `operator_values() -> dict[str, object] | None`
    - `outlook_mail_values() -> dict[str, object] | None`
  - `load_universal_config(config_file: Path | None = None) -> UniversalConfigDocument`.
  - `load_operator_configuration_from_document(document: UniversalConfigDocument, *, command_options: Mapping[str, object] | None = None, mounted_secret_dir: Path | None = None) -> OperatorConfiguration`.
- Preserves:
  - existing `load_operator_configuration(config_file: Path, ...)` public signature as a compatibility wrapper.
  - existing env/mounted/command precedence only inside the legacy operator projection.
- Closed universal top-level vocabulary is existing `OperatorSettings.model_fields` plus `acquisition`.
- The universal reader owns the 256 KiB file cap and existing regular-file/`O_NOFOLLOW` safety.

- [ ] **Step 1: Write failing universal-document tests**

Add tests:

- `test_missing_default_config_returns_builtin_empty_document`
- `test_xdg_config_home_selects_msgloom_toml`
- `test_relative_xdg_config_home_falls_back_to_home_config`
- `test_explicit_missing_config_fails_without_default_fallback`
- `test_empty_comment_only_default_file_is_valid`
- `test_universal_reader_rejects_unknown_top_level_and_nonregular_file`
- `test_operator_projection_ignores_known_acquisition_section`
- `test_mail_only_document_has_no_operator_projection`
- `test_reader_decodes_file_only_once_for_projection_consumers`
- `test_toml_syntax_error_reports_only_safe_source_line_and_column`
- `test_configuration_error_string_never_echoes_explicit_path_or_private_value`

For TOML decode failures, extract only the numeric `(line, column)` suffix from `TOMLDecodeError`; never surface the dependency's complete exception string.

The coexistence fixture must contain a valid existing operator config plus a harmless `[acquisition.microsoft.outlook.mail]` table and prove the legacy loader no longer treats `acquisition` as an unknown operator field.

- [ ] **Step 2: Run Task 1 tests and verify RED**

Run:
`uv run --locked pytest -q tests/configuration/test_universal.py tests/configuration/test_loading.py`

Expected: new tests fail because the universal document/resolver does not exist and legacy loader rejects `acquisition`.

- [ ] **Step 3: Implement the hardened universal reader**

Move/reuse the existing bounded regular-file/TOML helpers instead of creating a weaker second reader.

Required behavior:

- default path resolution exactly follows the spec;
- only default `FileNotFoundError` becomes builtin empty;
- explicit missing path is `ConfigurationError`;
- do not echo filesystem paths in errors;
- empty/comment-only TOML decodes as `{}`;
- unknown top-level keys fail;
- operation projection returns detached dictionaries;
- syntax/I/O/top-level errors attach only `ConfigurationDiagnostic` safe metadata; filesystem paths stay internal.

- [ ] **Step 4: Refactor the legacy operator loader onto the projection**

`load_operator_configuration()` loads the explicit file as one universal document, then delegates to `load_operator_configuration_from_document()`.

Do not alter:

- legacy command/env/mounted precedence;
- required `code_version/storage/admissions`;
- prompt/schema file semantics;
- legacy snapshot/version composition.

- [ ] **Step 5: Run Task 1 GREEN/static checks**

Run:

- `uv run --locked pytest -q tests/configuration/test_universal.py tests/configuration/test_loading.py tests/configuration/test_composition.py`
- `uv run --locked ruff check msgloom/configuration tests/configuration`
- `pyright msgloom/configuration tests/configuration`

Expected: PASS / zero static errors.

- [ ] **Step 6: Commit Task 1**

`git add msgloom/configuration tests/configuration && git commit -m "Add universal msgloom config document"`

---

### Task 2: Pin Google RE2 and Implement the Privacy-Safe Regex Adapter

**Session boundary:** stop after the Task 2 commit.

**Files:**

- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `message_ingest/acquisition/microsoft/outlook/email/rule_regex.py`
- Test: `tests/test_outlook_mail_rule_regex.py`

**Interfaces:**

- Produces:
  - `MSGLOOM_REGEX_VERSION = "msgloom-regex-v1"`
  - `MAX_REGEX_PATTERNS = 64`
  - `MAX_REGEX_PATTERN_CHARS = 4096`
  - `RE2_MAX_MEM_BYTES = 4 * 1024 * 1024`
  - `MailRegexSyntaxError(ValueError)`
  - frozen/slotted opaque `CompiledMailRegex`
  - `MailRegexEngine.compile(pattern: str) -> CompiledMailRegex`
  - `MailRegexEngine.search(compiled: CompiledMailRegex, text: str) -> bool`
- RE2 options are exactly:
  - `case_sensitive = False`
  - `log_errors = False`
  - `max_mem = RE2_MAX_MEM_BYTES`
- Public regex semantics are search, not fullmatch.

- [ ] **Step 1: Write failing regex compatibility/privacy tests**

Cover:

- ordinary substring search;
- `^...$` anchors;
- default case-insensitive matching;
- explicit RE2 inline case-sensitive override;
- rejected lookahead/lookbehind/backreference corpus;
- empty regex rejected;
- >4096-char regex rejected before compile;
- invalid pattern containing `PRIVATE_CUSTOMER_TOKEN_93` never appears in exception text, stdout, stderr, or `caplog`;
- bounded runtime engine exception is surfaced as a fixed adapter error class without pattern text.

- [ ] **Step 2: Run tests and verify RED**

Run:
`uv run --locked pytest -q tests/test_outlook_mail_rule_regex.py`

Expected: import/dependency failure.

- [ ] **Step 3: Add the exact dependency pin and lock it**

Add `google-re2==1.1.20251105` to runtime dependencies.

Run:
`uv lock`

Verify the lock resolves for the project without unrelated upgrades.

- [ ] **Step 4: Implement the adapter**

Use only RE2-supported syntax. Do not rewrite/prepend `(?i)` to user patterns.

The adapter must translate compile/runtime dependency exceptions into bounded msgloom exceptions with no pattern content.

- [ ] **Step 5: Verify GREEN on active runtime**

Run:

- `uv run --locked pytest -q tests/test_outlook_mail_rule_regex.py`
- `uv run --locked ruff check message_ingest/acquisition/microsoft/outlook/email/rule_regex.py tests/test_outlook_mail_rule_regex.py`
- `pyright message_ingest/acquisition/microsoft/outlook/email/rule_regex.py tests/test_outlook_mail_rule_regex.py`

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

`git add pyproject.toml uv.lock message_ingest/acquisition/microsoft/outlook/email/rule_regex.py tests/test_outlook_mail_rule_regex.py && git commit -m "Add bounded Outlook Mail regex engine"`

---

### Task 3: Define Mail Policy Models and the Private Effective Digest

**Session boundary:** stop after the Task 3 commit.

**Files:**

- Create: `message_ingest/acquisition/microsoft/outlook/email/rule_config.py`
- Modify: `message_ingest/acquisition/microsoft/outlook/email/profile.py`
- Modify: `message_ingest/acquisition/microsoft/outlook/email/__init__.py`
- Test: `tests/test_outlook_mail_rule_config.py`

**Interfaces:**

- Produces:
  - `DISCOVERY_V1 = "outlook-mail-discovery-v1"` in `profile.py`.
  - `MAIL_RULE_POLICY_FAMILY = "outlook-mail-acquisition-rules-v1"`.
  - user enum `MailRuleProfile` with `DISCOVERY="discovery"`, `FULL="full"`.
  - frozen/strict/extra-forbid `MailRulePredicates` with exactly these 55 public fields:
    `subject_contains`, `subject_exact`, `subject_regex`, `body_contains`, `body_regex`, `body_or_subject_contains`, `body_or_subject_regex`, `from_addresses`, `from_contains`, `from_address_contains`, `from_address_regex`, `sender_addresses`, `sender_contains`, `sender_address_contains`, `sender_address_regex`, `to_addresses`, `to_address_contains`, `to_address_regex`, `cc_addresses`, `cc_address_contains`, `cc_address_regex`, `bcc_addresses`, `bcc_address_contains`, `bcc_address_regex`, `recipient_contains`, `recipient_address_contains`, `recipient_address_regex`, `reply_to_addresses`, `reply_to_address_contains`, `reply_to_address_regex`, `categories`, `importance`, `has_attachments`, `header_contains`, `header_regex`, `sensitivity`, `message_size_min_kb`, `message_size_max_kb`, `received_after`, `received_before`, `sent_after`, `sent_before`, `created_after`, `created_before`, `is_read`, `is_draft`, `inference_classification`, `followup_status`, `item_class_exact`, `item_class_contains`, `item_class_regex`, `is_meeting_request`, `is_meeting_response`, `is_non_delivery_report`, `is_read_receipt`.
  - frozen/strict `MailRuleDefinition`.
  - frozen/strict `MailRulePolicy`.
  - `parse_mail_rule_policy(raw: Mapping[str, object] | None, *, source_label: str | None = None) -> MailRulePolicy`.
  - `effective_mail_policy_digest(policy: MailRulePolicy) -> str`.
  - `internal_mail_profile(profile: MailRuleProfile) -> str`.
  - `mail_policy_inspection(policy: MailRulePolicy) -> dict[str, object]` containing only enabled state, fixed family ID, total/enabled rule counts; no digest or values.
- Policy validation converts Pydantic validation locations into `ConfigurationDiagnostic.field_path` using only known schema field names and numeric indices. Any user-supplied unknown/extra key segment is rendered as the literal `<unknown>` rather than echoed. Validator failures use closed reason codes such as `unknown_field`, `unsupported_profile`, `duplicate_rule_id`, `duplicate_sequence`, `invalid_regex`, `invalid_range`, and `bound_exceeded`; never use Pydantic's arbitrary rendered input/value text. `source_label` is copied only from the safe universal-document source enum (`builtin`, `default`, `explicit`).
- Policy validation:
  - 256 rules;
  - 32 exception blocks/rule;
  - 128 values/predicate;
  - 64 total regex entries including disabled rules;
  - unique IDs and sequence;
  - IDs match `[A-Za-z0-9_.:-]{1,96}`;
  - nonempty condition/exception blocks/lists;
  - disabled rules still validate;
  - datetime values timezone-aware;
  - size bounds `0..2_097_151`;
  - deferred fields are unknown/invalid, not ignored.
- Digest:
  - private lowercase SHA-256;
  - includes family/regex/profile-lattice semantic versions and active rule identity;
  - excludes disabled individual rules when global policy enabled;
  - globally disabled digest ignores draft rule content;
  - case-insensitive literal canonicalization uses effective `casefold()`;
  - regex pattern text remains exact;
  - OR-value/exception block order canonicalized.

- [ ] **Step 1: Write failing policy-model tests**

Cover every structural bound/uniqueness/default plus:

- absent section -> disabled policy;
- empty enabled policy -> default discovery;
- default full maps to internal Full-v1;
- disabled invalid regex still fails;
- deferred `messageActionFlag` key fails;
- semantically equal case-only literal change keeps digest;
- regex case/text change changes digest;
- disabled rule edit leaves enabled-policy digest stable;
- enabled rule ID rename changes digest;
- comments/TOML ordering are irrelevant because digest starts from validated model;
- invalid profile/regex/unknown predicate raises `ConfigurationError` with a safe field path + closed reason, never the offending value;
- an unknown key named `PRIVATE_CLIENT_NAME` is rendered as `<unknown>` and never echoed.

- [ ] **Step 2: Run Task 3 tests and verify RED**

Run:
`uv run --locked pytest -q tests/test_outlook_mail_rule_config.py`

Expected: new policy models/digest are unavailable.

- [ ] **Step 3: Implement models/digest/profile mapping**

Use Pydantic only at the user-config validation boundary. Do not put Pydantic models into Scrapy Request state.

Regex fields validate through Task 2 `MailRegexEngine.compile()` but do not retain compiled RE2 objects in the Pydantic model.

- [ ] **Step 4: Verify GREEN/static**

Run:

- `uv run --locked pytest -q tests/test_outlook_mail_rule_config.py`
- `uv run --locked ruff check message_ingest/acquisition/microsoft/outlook/email/rule_config.py message_ingest/acquisition/microsoft/outlook/email/profile.py message_ingest/acquisition/microsoft/outlook/email/__init__.py tests/test_outlook_mail_rule_config.py`
- `pyright message_ingest/acquisition/microsoft/outlook/email/rule_config.py message_ingest/acquisition/microsoft/outlook/email/profile.py message_ingest/acquisition/microsoft/outlook/email/__init__.py tests/test_outlook_mail_rule_config.py`

Expected: PASS / zero static errors.

- [ ] **Step 5: Commit Task 3**

`git add message_ingest/acquisition/microsoft/outlook/email/rule_config.py message_ingest/acquisition/microsoft/outlook/email/profile.py message_ingest/acquisition/microsoft/outlook/email/__init__.py tests/test_outlook_mail_rule_config.py && git commit -m "Add Outlook Mail rule configuration models"`

---

### Task 4: Expose Universal Config Validate and Inspect Commands

**Session boundary:** stop after the Task 4 commit.

**Files:**

- Modify: `msgloom/cli/app.py`
- Modify: `msgloom/cli/models.py`
- Modify: `msgloom/cli/runner.py`
- Modify: `tests/application_cli/test_help_config_status.py`
- Modify: `tests/configuration/test_universal.py`

**Interfaces:**

- `msgloom config validate [--config FILE]` and `msgloom config inspect [--config FILE]` use Task 1 `load_universal_config()`.
- With no `--config`, both commands use the XDG default/builtin-empty behavior.
- `CliRequest.config_file` becomes optional only for `config-validate` / `config-inspect`; existing execution/status actions retain their explicit-config contract.
- `config validate` validates every present supported projection:
  - legacy projection through `load_operator_configuration_from_document()` when present;
  - Mail acquisition through Task 3 `parse_mail_rule_policy(..., source_label=document.source)` when present.
- `config inspect` first performs the same all-present validation, then emits only safe metadata:
  - existing legacy redacted snapshot version when a legacy projection exists;
  - Mail `enabled`, fixed policy-family ID, total/enabled rule counts when Mail exists;
  - never private Mail digest, paths, addresses, keywords, regex strings, or configured values.
- On `ConfigurationError`, merge Task 1 `configuration_error_payload()` into the fixed JSON error envelope.

- [ ] **Step 1: Write failing config CLI tests**

Update expectations to cover:

- no positional config path;
- optional explicit whole-file `--config FILE`;
- XDG default and builtin-empty behavior;
- Mail-only config validates without legacy root fields;
- valid Mail + valid legacy document validates both;
- Mail-only command projection can coexist with an incomplete known `[triage]`, while `config validate` rejects that document and a legacy triage execution rejects its own projection;
- inspect contains no config path, private policy digest, addresses, keywords, or regex text;
- invalid profile/regex/unknown predicate output contains safe field path + closed reason text, but not the offending value;
- TOML syntax output contains safe source label + line/column only, not parser exception prose.

- [ ] **Step 2: Run Task 4 tests and verify RED**

Run:
`uv run --locked pytest -q tests/application_cli/test_help_config_status.py tests/configuration/test_universal.py tests/test_outlook_mail_rule_config.py`

- [ ] **Step 3: Implement universal config validate/inspect CLI**

Do not change prepare/triage/report/status invocation syntax in this task.

Load the universal document exactly once per config command, validate all present projections, and render only the closed safe diagnostic payload on error.

- [ ] **Step 4: Verify GREEN/static**

Run:

- `uv run --locked pytest -q tests/application_cli/test_help_config_status.py tests/configuration/test_universal.py tests/configuration/test_loading.py tests/test_outlook_mail_rule_config.py`
- `uv run --locked ruff check msgloom/cli tests/application_cli/test_help_config_status.py tests/configuration/test_universal.py`
- `pyright msgloom/cli tests/application_cli/test_help_config_status.py tests/configuration/test_universal.py`

Expected: PASS / zero static errors.

- [ ] **Step 5: Commit Task 4**

`git add msgloom/cli tests/application_cli/test_help_config_status.py tests/configuration/test_universal.py && git commit -m "Use universal config for config commands"`

---

### Task 5: Expand the Bounded Observation and Composite Probe Contracts

**Session boundary:** stop after the Task 5 commit.

**Files:**

- Modify: `microsoft_graph/spiders/outlook/mail.py`
- Modify: `message_ingest/acquisition/microsoft/outlook/email/rule_evaluation.py`
- Modify: `message_ingest/acquisition/microsoft/outlook/email/rule_probe.py`
- Modify: `message_ingest/acquisition/microsoft/outlook/email/__init__.py`
- Modify: `message_ingest/spiders/microsoft/outlook/email/_base.py`
- Modify: `message_ingest/spidermiddlewares/microsoft/outlook/email.py`
- Modify: `tests/test_outlook_mail_rule_contracts.py`
- Modify: `tests/test_outlook_mail_graph_examples.py`
- Modify: `tests/test_outlook_mail_rule_probe.py`
- Modify: `tests/test_outlook_mail_rule_middleware.py`
- Modify: `tests/test_jobdir_resume.py`

**Interfaces:**

- Produces `MailRuleFact(StrEnum)` for:
  `CHANGE_KEY`, `LAST_MODIFIED_DATE_TIME`, `SUBJECT`, `FROM_RECIPIENT`, `SENDER_RECIPIENT`, `TO_RECIPIENTS`, `CC_RECIPIENTS`, `BCC_RECIPIENTS`, `REPLY_TO_RECIPIENTS`, `RECEIVED_DATE_TIME`, `SENT_DATE_TIME`, `CREATED_DATE_TIME`, `IMPORTANCE`, `CATEGORIES`, `HAS_ATTACHMENTS`, `IS_READ`, `IS_DRAFT`, `INFERENCE_CLASSIFICATION`, `FOLLOWUP_STATUS`, `BODY_PREVIEW`, `BODY`, `HEADERS`, `SENSITIVITY`, `MESSAGE_SIZE_BYTES`, `ITEM_CLASS`.
- Produces frozen/slotted `MailRecipientFact(name: str | None, address: str | None)`.
- Produces frozen/slotted `MailRuleFacts` with exact fields:
  - `change_key: str | None`
  - `last_modified_date_time: str | None`
  - `subject: str | None`
  - `from_recipient: MailRecipientFact | None`
  - `sender_recipient: MailRecipientFact | None`
  - `to_recipients: tuple[MailRecipientFact, ...]`
  - `cc_recipients: tuple[MailRecipientFact, ...]`
  - `bcc_recipients: tuple[MailRecipientFact, ...]`
  - `reply_to_recipients: tuple[MailRecipientFact, ...]`
  - `received_date_time: str | None`
  - `sent_date_time: str | None`
  - `created_date_time: str | None`
  - `importance: str | None`
  - `categories: tuple[str, ...]`
  - `has_attachments: bool | None`
  - `is_read: bool | None`
  - `is_draft: bool | None`
  - `inference_classification: str | None`
  - `followup_status: str | None`
  - `body_preview: str | None`
  - `body: str | None`
  - `headers: tuple[str, ...]`
  - `sensitivity: str | None`
  - `message_size_bytes: int | None`
  - `item_class: str | None`
  - `available_facts: frozenset[MailRuleFact]`
  Known-empty list facts use empty tuples while remaining present in `available_facts`; unavailable list facts also have empty tuples but are absent from `available_facts`.
- `MailRuleObservation` retains correlation fields and `facts: MailRuleFacts`; no raw provider object.
- `MailRuleRequiredData`: exactly `METADATA`, `BODY`, `HEADERS`, `EXTENDED_PROPERTIES`.
- `MailRuleProbeStatus`: `COMPLETE`, `PARTIAL`, `FAILED`.
- frozen/slotted `MailRuleProbeFailure(fact: MailRuleFact, reason_code: str)`.
- `MailRuleProbeData(status, facts, evidence_id, failures)`.
- `MailRuleEvaluation.required_data: frozenset[MailRuleRequiredData]`.
- Discovery `$select` includes `changeKey`; remove duplicate `changeKey` from `full_fields`.
- Transitional adapter compatibility for this commit:
  - the existing Spider method remains `mail_rule_probe_request(observation: MailRuleObservation)` and is still BODY-only until Task 10;
  - that request now selects `id,changeKey,body,bodyPreview`, and its callback emits the new `MailRuleProbeData`/`MailRuleFacts` shape;
  - the existing middleware accepts `NEEDS_DATA` only when `required_data == frozenset({MailRuleRequiredData.BODY})`; any other requirement before Task 10 is a programming/integrity failure and does not schedule a request;
  - one-body-probe cardinality, named callbacks/errback, JOBDIR serialization, source-item-first ordering, and no-rules behavior remain unchanged.

**Projection bounds from spec:**

- subject 16,384 code points;
- recipient name/address 1,024 each;
- total To+Cc+Bcc+Reply-To retained <=256;
- categories <=128, category <=1,024;
- changeKey/timestamp/enum-like scalar <=2,048;
- bodyPreview <=1,024;
- oversize -> fact unavailable, never truncated.

- [ ] **Step 1: Rewrite contract tests for fact availability**

Add explicit known-empty vs unavailable cases:

- present `categories=[]` available empty;
- absent categories unavailable;
- present `toRecipients=[]` available empty;
- malformed recipient list unavailable;
- explicit `from=null` is known nullable;
- absent/malformed `from` unavailable;
- explicit `subject=null` known null;
- absent subject unavailable;
- aggregate recipients >256 makes recipient-list facts unavailable without retaining values;
- oversized subject/category/bodyPreview unavailable without truncation.

- [ ] **Step 2: Add discovery-field test for `changeKey`**

Assert discovery and delta initial requests select `changeKey`, while Full selection contains it exactly once.

- [ ] **Step 3: Rewrite the existing body-probe/middleware tests for the new contract shape**

Update current fake evaluations from scalar `BODY` to `frozenset({BODY})`; update probe assertions to read `facts.body` / fact availability; assert the transitional body probe selects and returns `changeKey`; add one test where a non-BODY required-data set fails policy integrity instead of scheduling a request. Preserve existing source-item-first, one-probe, and JOBDIR serialization assertions.

- [ ] **Step 4: Run Task 5 tests and verify RED**

Run:
`uv run --locked pytest -q tests/test_outlook_mail_rule_contracts.py tests/test_outlook_mail_graph_examples.py tests/test_outlook_mail_rule_probe.py tests/test_outlook_mail_rule_middleware.py tests/test_jobdir_resume.py`

Expected: failures describe the old scalar/body-only contract and missing `changeKey`/availability model.

- [ ] **Step 5: Implement fact models/projection and evaluation-shape validation**

Keep matching semantics out of this task. Projection only:

- validates representation/type;
- applies size bounds;
- preserves source strings within bounds;
- records availability.

The recipient value object contains only name/address and remains pickle/JOBDIR serializable.

`NEEDS_DATA` requires a nonempty immutable required-data set; `FINAL` and `UNRESOLVED` carry no pending required-data. Private `ruleset_digest` validation remains lowercase SHA-256 but is not loggable.

- [ ] **Step 6: Mechanically adapt the existing BODY-only Spider/middleware path**

Update the existing body probe callback/errback and middleware constructors to the new facts/probe/result types while retaining the transitional BODY-only behavior defined above. Do not add METADATA/HEADERS/EXTENDED_PROPERTIES acquisition here; Task 10 owns the dynamic request builder.

- [ ] **Step 7: Verify GREEN/static**

Run:

- `uv run --locked pytest -q tests/test_outlook_mail_rule_contracts.py tests/test_outlook_mail_graph_examples.py tests/test_outlook_mail_rule_probe.py tests/test_outlook_mail_rule_middleware.py tests/test_jobdir_resume.py`
- `uv run --locked ruff check microsoft_graph/spiders/outlook/mail.py message_ingest/acquisition/microsoft/outlook/email message_ingest/spiders/microsoft/outlook/email/_base.py message_ingest/spidermiddlewares/microsoft/outlook/email.py tests/test_outlook_mail_rule_contracts.py tests/test_outlook_mail_graph_examples.py tests/test_outlook_mail_rule_probe.py tests/test_outlook_mail_rule_middleware.py tests/test_jobdir_resume.py`
- `pyright microsoft_graph/spiders/outlook/mail.py message_ingest/acquisition/microsoft/outlook/email message_ingest/spiders/microsoft/outlook/email/_base.py message_ingest/spidermiddlewares/microsoft/outlook/email.py tests/test_outlook_mail_rule_contracts.py tests/test_outlook_mail_rule_probe.py tests/test_outlook_mail_rule_middleware.py tests/test_jobdir_resume.py`

Expected: PASS / zero static errors; repository remains runnable with the old BODY-only adapter expressed through the new contracts.

- [ ] **Step 8: Commit Task 5**

`git add microsoft_graph/spiders/outlook/mail.py message_ingest/acquisition/microsoft/outlook/email message_ingest/spiders/microsoft/outlook/email/_base.py message_ingest/spidermiddlewares/microsoft/outlook/email.py tests/test_outlook_mail_rule_contracts.py tests/test_outlook_mail_graph_examples.py tests/test_outlook_mail_rule_probe.py tests/test_outlook_mail_rule_middleware.py tests/test_jobdir_resume.py && git commit -m "Expand Outlook Mail rule fact contracts"`

---

## Phase B — Pure deterministic policy evaluation

### Task 6: Implement the Bounded Logical BODY Projector

**Session boundary:** stop after the Task 6 commit.

**Files:**

- Create: `message_ingest/acquisition/microsoft/outlook/email/rule_body.py`
- Test: `tests/test_outlook_mail_rule_body.py`

**Interfaces:**

- Produces:
  - `MAX_LOGICAL_BODY_BYTES = 8 * 1024 * 1024`
  - `MailBodyUnavailable(ValueError)` with fixed non-content reasons.
  - `logical_mail_body(body: object) -> str`.
- Input is a Graph `body` representation only; no Scrapy/Response imports.

**Required body semantics:**

- `contentType=text`: use content as supplied after size check.
- HTML: Lexbor/selectolax visible-text projection.
- Remove active elements: script/style/noscript/template/iframe/object/embed.
- `br` and block boundaries yield line boundaries.
- Collapse normal-flow whitespace.
- Preserve preformatted whitespace inside `pre`.
- Include visible text inside ordinary tables.
- Never match raw markup/MIME.
- malformed/unsupported/oversize -> `MailBodyUnavailable`.

- [ ] **Step 1: Write failing body projection tests**

Cover:

- text body exact preservation;
- normal HTML inline/block/br whitespace;
- scripts/styles omitted;
- table cell text retained;
- preformatted text retained;
- HTML entities decode deterministically;
- malformed representation unavailable;
- >8 MiB UTF-8 logical result unavailable;
- body containing private text never appears in exception messages.

- [ ] **Step 2: Run RED**

`uv run --locked pytest -q tests/test_outlook_mail_rule_body.py`

- [ ] **Step 3: Implement focused projector**

Do not call/import the A2 preparation parser whose table semantics intentionally differ.

- [ ] **Step 4: Run GREEN/static**

Run:

- `uv run --locked pytest -q tests/test_outlook_mail_rule_body.py`
- `uv run --locked ruff check message_ingest/acquisition/microsoft/outlook/email/rule_body.py tests/test_outlook_mail_rule_body.py`
- `pyright message_ingest/acquisition/microsoft/outlook/email/rule_body.py tests/test_outlook_mail_rule_body.py`

- [ ] **Step 5: Commit Task 6**

`git add message_ingest/acquisition/microsoft/outlook/email/rule_body.py tests/test_outlook_mail_rule_body.py && git commit -m "Add bounded Outlook Mail body projection"`

---

### Task 7: Implement Metadata Predicate Truth Evaluation

**Session boundary:** stop after the Task 7 commit.

**Files:**

- Create: `message_ingest/acquisition/microsoft/outlook/email/rule_predicates.py`
- Test: `tests/test_outlook_mail_rule_predicates_metadata.py`

**Interfaces:**

- Produces:
  - `MailTruth(StrEnum)`: `TRUE`, `FALSE`, `UNKNOWN`.
  - frozen/slotted `MailPredicateResult`:
    - `truth: MailTruth`
    - `required_data: frozenset[MailRuleRequiredData] = frozenset()`
    - `reason_codes: tuple[str, ...] = ()`
  - `evaluate_predicate_block(predicates: MailRulePredicates, facts: MailRuleFacts, *, regex_engine: MailRegexEngine) -> MailPredicateResult`.
  - private helpers for fixed OR/AND tri-state composition.
- This task implements discovery/metadata-backed fields only:
  - subject exact/contains/regex;
  - From exact/name-or-address/address-only;
  - actual Sender variants;
  - To/Cc/Bcc/address-only;
  - Outlook recipient To+Cc name-or-address/address-only;
  - Reply-To;
  - categories;
  - importance;
  - has attachments;
  - received/sent/created time bounds;
  - is_read/is_draft;
  - inference classification;
  - followup status.
- Probe-backed fields may return UNKNOWN with their required-data category until Task 8 supplies their concrete evaluator.

- [ ] **Step 1: Write failing metadata predicate truth-table tests**

Include:

- field AND/value OR;
- ordinary casefold;
- address whitespace normalization;
- exact vs contains;
- display-name + address Outlook baseline behavior;
- Bcc excluded from `recipient_contains`;
- known-empty recipient/category collections make their membership/contains/regex predicates FALSE; known-null scalar text makes its text predicate FALSE;
- unavailable relevant fact -> UNKNOWN + METADATA;
- unavailable irrelevant field dominated by another FALSE -> block FALSE;
- datetime offsets normalized to same UTC instant;
- lower-inclusive/upper-exclusive time range;
- regex search semantics.

- [ ] **Step 2: Add Review Focus regex failure OR test**

Construct one regex list where one compiled/search alternative raises the bounded runtime regex error and another alternative matches.

Assert:

- OR result TRUE;
- reversing value order still TRUE;
- no unresolved reason escapes the successful OR.

- [ ] **Step 3: Run RED**

`uv run --locked pytest -q tests/test_outlook_mail_rule_predicates_metadata.py`

- [ ] **Step 4: Implement deterministic metadata predicates**

Do not import Scrapy or provider JSON.

Use the exact tri-state truth tables from the spec; predicate result order must not affect truth.

- [ ] **Step 5: Run GREEN/static**

Run:

- `uv run --locked pytest -q tests/test_outlook_mail_rule_predicates_metadata.py tests/test_outlook_mail_rule_regex.py`
- `uv run --locked ruff check message_ingest/acquisition/microsoft/outlook/email/rule_predicates.py tests/test_outlook_mail_rule_predicates_metadata.py`
- `pyright message_ingest/acquisition/microsoft/outlook/email/rule_predicates.py tests/test_outlook_mail_rule_predicates_metadata.py`

- [ ] **Step 6: Commit Task 7**

`git add message_ingest/acquisition/microsoft/outlook/email/rule_predicates.py tests/test_outlook_mail_rule_predicates_metadata.py && git commit -m "Evaluate Outlook Mail metadata predicates"`

---

### Task 8: Add Probe-Backed Predicate Evaluation

**Session boundary:** stop after the Task 8 commit.

**Files:**

- Modify: `message_ingest/acquisition/microsoft/outlook/email/rule_predicates.py`
- Test: `tests/test_outlook_mail_rule_predicates_probe.py`

**Interfaces consumed:**

- Task 6 `logical_mail_body()` output arrives as available BODY fact; predicate layer does not parse HTML.
- Task 5 normalized probe facts.
- Task 7 tri-state result/composition.

**Implements:**

- body contains/regex;
- body-or-subject contains/regex;
- header contains/regex over canonical `name: value` lines;
- sensitivity;
- min/max message size;
- item class exact/contains/regex;
- special message predicates from item class:
  - meeting request exact `IPM.Schedule.Meeting.Request`;
  - meeting response exact Pos/Tent/Neg classes;
  - NDR `REPORT.*.NDR`;
  - read receipt `REPORT.*.IPNRN` or exact `IPM.Note.Receipt.SMIME`.
- Fact -> required-data mapping:
  - missing body -> BODY;
  - missing headers -> HEADERS;
  - missing sensitivity/size/item class -> EXTENDED_PROPERTIES.

- [ ] **Step 1: Write failing probe-backed tests**

Cover every supported probe predicate, including size byte/KiB boundary exactly.

- [ ] **Step 2: Pin body-or-subject short-circuit**

Assert:

- subject TRUE => body unavailable does not request BODY;
- subject FALSE + body unavailable => UNKNOWN/BODY;
- subject unavailable + body TRUE => TRUE;
- neither TRUE and at least one unavailable => UNKNOWN.

`bodyPreview` must never change any body result.

- [ ] **Step 3: Pin cheap exception dominance**

A rule-block-like AND example where body is unavailable but another available field is FALSE must return FALSE with no BODY requirement.

- [ ] **Step 4: Run RED**

`uv run --locked pytest -q tests/test_outlook_mail_rule_predicates_probe.py`

- [ ] **Step 5: Implement probe-backed predicates**

Do not introduce provider heuristics for deferred conditions.

- [ ] **Step 6: Run GREEN/static**

Run:

- `uv run --locked pytest -q tests/test_outlook_mail_rule_predicates_metadata.py tests/test_outlook_mail_rule_predicates_probe.py`
- `uv run --locked ruff check message_ingest/acquisition/microsoft/outlook/email/rule_predicates.py tests/test_outlook_mail_rule_predicates_probe.py`
- `pyright message_ingest/acquisition/microsoft/outlook/email/rule_predicates.py tests/test_outlook_mail_rule_predicates_probe.py`

- [ ] **Step 7: Commit Task 8**

`git add message_ingest/acquisition/microsoft/outlook/email/rule_predicates.py tests/test_outlook_mail_rule_predicates_probe.py && git commit -m "Evaluate Outlook Mail probe predicates"`

---

### Task 9: Implement the Ordered Deterministic RuleEngine

**Session boundary:** stop after the Task 9 commit.

**Files:**

- Create: `message_ingest/acquisition/microsoft/outlook/email/rule_engine.py`
- Modify: `message_ingest/acquisition/microsoft/outlook/email/__init__.py`
- Test: `tests/test_outlook_mail_rule_engine.py`

**Interfaces:**

- Produces:
  - `DeterministicMailRuleEvaluator(policy: MailRulePolicy, *, regex_engine: MailRegexEngine | None = None)`.
  - `evaluate(observation: MailRuleObservation, *, probe: MailRuleProbeData | None = None) -> MailRuleEvaluation`.
- Every enabled-policy evaluation carries fixed family ID + private effective digest.
- Global disabled policy does not construct this evaluator.
- Outcome:
  - MATCHED if at least one actually-evaluated rule matches;
  - DEFAULT if none matches;
  - UNRESOLVED only for semantically relevant unresolved/failure.
- Matched IDs are sequence order.
- `full` is maximal; once selected, the evaluator terminally short-circuits later audit-only rules.
- default Full immediately returns DEFAULT/full without evaluating no-op rules.
- Probe merge uses only available facts.
- Probe mutation fence:
  - initial probe-needed observation must have trustworthy `changeKey`;
  - probe must have matching `changeKey`;
  - absent/mismatch -> UNRESOLVED/full.

**Required-data algorithm:**

- first pass unions missing data across every branch that can still become reachable;
- an unresolved stop-processing rule must include later-rule data needed if that rule becomes FALSE;
- already-proven stop match cuts later branches;
- already-proven Full cuts later rules;
- after a probe, remaining relevant UNKNOWN becomes UNRESOLVED, never another NEEDS_DATA.

- [ ] **Step 1: Write failing ordered-rule tests**

Cover:

- default discovery no-match;
- matching Full upgrade;
- later discovery cannot downgrade Full;
- stop-processing;
- matched rule that keeps already-selected profile still yields MATCHED;
- default Full immediate terminal behavior;
- disabled rules ignored at evaluation.

- [ ] **Step 2: Write failing exception/branch-union tests**

Cover:

- conditions TRUE + exception TRUE => rule FALSE and not matched ID;
- cheap TRUE exception suppresses unknown BODY condition and avoids probe;
- unresolved stop rule + later header Full rule => one NEEDS_DATA with `{BODY, HEADERS}`;
- proven stop rule excludes later required data.

- [ ] **Step 3: Write failing probe/fallback tests**

Cover:

- same changeKey + complete facts => terminal result;
- changed/missing changeKey => source-change/version-unavailable Full fallback;
- PARTIAL probe with irrelevant missing fact can still FINAL;
- PARTIAL probe with relevant missing fact => UNRESOLVED/full;
- regex runtime failure irrelevant due another OR match => normal final;
- relevant regex runtime failure with no data remedy => UNRESOLVED/full.

- [ ] **Step 4: Run RED**

`uv run --locked pytest -q tests/test_outlook_mail_rule_engine.py`

- [ ] **Step 5: Implement evaluator**

Keep the algorithm pure: no logging, Scrapy, catalog, provider URLs, or SQL.

Use fixed reason-code constants; never propagate dependency exception text.

- [ ] **Step 6: Run GREEN/static**

Run:

- `uv run --locked pytest -q tests/test_outlook_mail_rule_engine.py tests/test_outlook_mail_rule_predicates_metadata.py tests/test_outlook_mail_rule_predicates_probe.py`
- `uv run --locked ruff check message_ingest/acquisition/microsoft/outlook/email/rule_engine.py tests/test_outlook_mail_rule_engine.py`
- `pyright message_ingest/acquisition/microsoft/outlook/email/rule_engine.py tests/test_outlook_mail_rule_engine.py`

- [ ] **Step 7: Commit Task 9**

`git add message_ingest/acquisition/microsoft/outlook/email/rule_engine.py message_ingest/acquisition/microsoft/outlook/email/__init__.py tests/test_outlook_mail_rule_engine.py && git commit -m "Add deterministic Outlook Mail rule engine"`

---

## Phase C — Scrapy runtime policy, composite probe, and resume integrity

### Task 10: Build the Dynamic Composite Rule Probe Acquisition Path

**Session boundary:** stop after the Task 10 commit.

**Files:**

- Modify: `microsoft_graph/spiders/outlook/mail.py`
- Modify: `message_ingest/spiders/microsoft/outlook/email/_base.py`
- Modify: `message_ingest/acquisition/microsoft/outlook/email/rule_probe.py`
- Modify: `tests/test_outlook_mail_rule_probe.py`
- Modify: `tests/test_jobdir_resume.py`

**Interfaces:**

- Extend provider helper:
  - `message_path(message_id: str, *, fields: Sequence[str] = (), expand: str | None = None) -> str`.
- Spider:
  - `mail_rule_probe_request(observation: MailRuleObservation, required_data: frozenset[MailRuleRequiredData]) -> scrapy.Request`.
- Request always selects `id,changeKey` plus exact needed metadata/body/header fields.
- EXTENDED_PROPERTIES uses fixed IDs:
  - `Integer 0x0036`
  - `Integer 0x0E08`
  - `String 0x001A`
- Request is `dont_cache=True`, 8 MiB `download_maxsize`, named callback/errback.
- Probe parser:
  - validates message ID/changeKey;
  - projects body through the logical BODY projector;
  - canonicalizes headers to `name: value`;
  - parses extended-property values strictly;
  - returns COMPLETE/PARTIAL/FAILED with fact-level failures.
- The Request/callback state carries only bounded observation + required-data set; never raw policy or private digest.

- [ ] **Step 1: Rewrite probe request tests for dynamic selection**

Cases:

- METADATA-only missing fact;
- BODY only;
- HEADERS only;
- EXTENDED_PROPERTIES only;
- BODY+HEADERS+EXTENDED_PROPERTIES in one Request;
- 8 MiB cap;
- no duplicate `$select` fields;
- exact fixed `$expand` property IDs.

- [ ] **Step 2: Write strict parser/partial-result tests**

Cover malformed/missing individual facts without failing unrelated facts, HTML event-like body, conflicting duplicate extended-property IDs, invalid size/sensitivity/class, and missing/mismatched changeKey representation.

- [ ] **Step 3: Update JOBDIR serialization test**

Round-trip a composite probe Request containing:

- frozen bounded observation;
- required-data frozenset;
- named callback/errback;
- no raw policy object/digest.

- [ ] **Step 4: Run RED**

Run:
`uv run --locked pytest -q tests/test_outlook_mail_rule_probe.py tests/test_jobdir_resume.py`

- [ ] **Step 5: Implement provider/query/parser changes**

Do not introduce multiple provider Requests for one observation. Do not add any new Graph permission.

- [ ] **Step 6: Verify GREEN/static**

Run:

- `uv run --locked pytest -q tests/test_outlook_mail_rule_probe.py tests/test_jobdir_resume.py`
- `uv run --locked ruff check microsoft_graph/spiders/outlook/mail.py message_ingest/spiders/microsoft/outlook/email/_base.py message_ingest/acquisition/microsoft/outlook/email/rule_probe.py tests/test_outlook_mail_rule_probe.py tests/test_jobdir_resume.py`
- `pyright microsoft_graph/spiders/outlook/mail.py message_ingest/spiders/microsoft/outlook/email/_base.py message_ingest/acquisition/microsoft/outlook/email/rule_probe.py tests/test_outlook_mail_rule_probe.py tests/test_jobdir_resume.py`

Expected: PASS / zero static errors.

- [ ] **Step 7: Commit Task 10**

`git add microsoft_graph/spiders/outlook/mail.py message_ingest/spiders/microsoft/outlook/email/_base.py message_ingest/acquisition/microsoft/outlook/email/rule_probe.py tests/test_outlook_mail_rule_probe.py tests/test_jobdir_resume.py && git commit -m "Add Outlook Mail composite rule probe"`

---

### Task 11: Integrate Composite Probes with the Mail Rule Middleware

**Session boundary:** stop after the Task 11 commit.

**Files:**

- Modify: `message_ingest/spiders/microsoft/outlook/email/_base.py`
- Modify: `message_ingest/spidermiddlewares/microsoft/outlook/email.py`
- Modify: `tests/test_outlook_mail_rule_middleware.py`
- Modify: `tests/test_outlook_mail_rule_observability.py`
- Modify: `tests/test_outlook_mail_rule_middleware_integration.py`

**Interfaces/behavior:**

- Middleware passes evaluator `required_data: frozenset[MailRuleRequiredData]` to `mail_rule_probe_request()`.
- Internal composite probe results are consumed before pipelines and re-run the evaluator once.
- A second NEEDS_DATA after a supplied probe is the existing programming/integrity failure path; never schedule another Request.
- `OutlookMailCollectionSpider.record_mail_rule_profile()` accepts only `DISCOVERY_V1` / `FULL_V1` and becomes strongest-profile accumulation using `discovery < full`; a later discovery observation cannot downgrade a Full target. Any other evaluator profile is a programming/integrity error, not a third lattice value.
- Original `OutlookMailItem` still yields unchanged before policy side effects.
- Real content-derived `ruleset_digest` is removed from decision/probe/error logs and every `LogRecord.extra`/stat surface; fixed policy family and non-secret rule IDs remain loggable.

- [ ] **Step 1: Write failing middleware integration tests**

Cover:

- multi-group required-data set schedules exactly the Task 10 composite Request;
- PARTIAL probe is passed to the evaluator and consumed internally;
- second NEEDS_DATA after probe marks run failed without another Request;
- strongest profile retains Full after later discovery observation;
- source Item still yields first;
- private digest never appears in log text, structured extras, or stats.

- [ ] **Step 2: Run RED**

Run:
`uv run --locked pytest -q tests/test_outlook_mail_rule_middleware.py tests/test_outlook_mail_rule_observability.py tests/test_outlook_mail_rule_middleware_integration.py`

- [ ] **Step 3: Implement middleware/profile/logging changes**

Do not change pure RuleEngine semantics here. This task is only the Scrapy adapter from evaluator -> one probe -> evaluator -> attempt-local strongest Full target state.

- [ ] **Step 4: Verify GREEN/static**

Run:

- `uv run --locked pytest -q tests/test_outlook_mail_rule_middleware.py tests/test_outlook_mail_rule_observability.py tests/test_outlook_mail_rule_middleware_integration.py tests/test_outlook_mail_rule_probe.py`
- `uv run --locked ruff check message_ingest/spiders/microsoft/outlook/email/_base.py message_ingest/spidermiddlewares/microsoft/outlook/email.py tests/test_outlook_mail_rule_middleware.py tests/test_outlook_mail_rule_observability.py tests/test_outlook_mail_rule_middleware_integration.py`
- `pyright message_ingest/spiders/microsoft/outlook/email/_base.py message_ingest/spidermiddlewares/microsoft/outlook/email.py tests/test_outlook_mail_rule_middleware.py tests/test_outlook_mail_rule_observability.py tests/test_outlook_mail_rule_middleware_integration.py`

Expected: PASS / zero static errors.

- [ ] **Step 5: Commit Task 11**

`git add message_ingest/spiders/microsoft/outlook/email/_base.py message_ingest/spidermiddlewares/microsoft/outlook/email.py tests/test_outlook_mail_rule_middleware.py tests/test_outlook_mail_rule_observability.py tests/test_outlook_mail_rule_middleware_integration.py && git commit -m "Integrate Outlook Mail composite rule probes"`

---

### Task 12: Wire Universal Mail Policy into the Microsoft Command and Collection Spiders

**Session boundary:** stop after the Task 12 commit.

**Files:**

- Modify: `message_ingest/commands/microsoft/options.py`
- Modify: `message_ingest/commands/microsoft/__init__.py`
- Modify: `message_ingest/commands/microsoft/outlook/mail.py`
- Modify: `message_ingest/commands/microsoft/outlook/sync.py`
- Modify: `message_ingest/spiders/microsoft/outlook/email/_base.py`
- Modify: `tests/test_outlook_commands.py`
- Modify: `tests/test_outlook_mail_collection_boundary.py`
- Modify: `tests/test_outlook_mail_rule_middleware.py`

**Interfaces:**

- Microsoft CLI adds optional `--config FILE`.
- Accepted only for Mail discover/delta/sync.
- Rejected for Mail full/folder-delta, Calendar, To Do, OneDrive, Contacts, auth, profile.
- Mail command loads one universal document and one validated `MailRulePolicy` before creating the first relevant crawler.
- `run_mail_sync(command, opts, *, mail_rule_policy: MailRulePolicy)` becomes the sync entrypoint signature so Task 17 can consume the already-frozen policy without reopening TOML.
- Private spider argument name is exactly `_mail_rule_policy`.
- `OutlookMailCollectionSpider.__init__()` explicitly consumes that argument and does not forward it to generic `Spider.__init__`.
- Direct `scrapy crawl outlook_discover/outlook_delta` with no private argument resolves the default universal config once for that crawler.
- `build_mail_rule_evaluator()` becomes instance-owned and returns:
  - None for disabled policy;
  - `DeterministicMailRuleEvaluator` for enabled policy.
- Spider exposes safe/private:
  - `mail_rule_policy_enabled: bool`
  - `mail_rule_policy_family: str`
  - `mail_rule_policy_digest: str` private control state.

- [ ] **Step 1: Write failing CLI path-matrix tests**

Add `--config` acceptance/rejection tests for every path in spec §1.5.

Public standalone Mail delta with enabled policy must fail before crawl start and direct the user to Mail sync.

Active-policy Mail sync + explicit `--max-enrich` must fail before crawl start.

Until Task 17 installs the rules-aware planner, an enabled-policy sync with no `--max-enrich` also fails closed with a fixed temporary `rules_enabled_sync_not_implemented` UsageError rather than calling the legacy global-backlog planner. Task 17 removes this staging guard in the same commit that installs the correct planner. Rules-disabled sync remains unchanged throughout.

- [ ] **Step 2: Write failing spider handoff/privacy tests**

Assert:

- raw policy is consumed explicitly;
- raw policy does not appear in SpiderState, stats, Request meta/cb_kwargs, Scrapy overridden settings, or Spider repr/log startup text;
- disabled policy keeps middleware silently NotConfigured;
- enabled policy constructs the real evaluator.

- [ ] **Step 3: Run RED**

`uv run --locked pytest -q tests/test_outlook_commands.py tests/test_outlook_mail_collection_boundary.py tests/test_outlook_mail_rule_middleware.py`

- [ ] **Step 4: Implement command-level one-time policy load**

Do not load the default config for unrelated Microsoft command paths. Catch `ConfigurationError` at the Microsoft command boundary and raise `UsageError(format_configuration_error(error))` so Scrapy prints only the closed safe diagnostic; do not allow a raw Pydantic/RE2/TOML exception traceback to become the user-facing configuration error. Thread the frozen policy into `run_mail_sync(..., mail_rule_policy=policy)` and keep the temporary enabled-sync fail-closed guard until Task 17.

Do not use `process_options()` for rule policy; mailbox targeting remains there.

- [ ] **Step 5: Implement explicit Spider policy consumption**

Do not store raw Pydantic policy model in `spider.state` or Request state.

The runtime evaluator retains the immutable policy in process memory only; it is never serialized.

- [ ] **Step 6: Verify GREEN/static**

Run:

- `uv run --locked pytest -q tests/test_outlook_commands.py tests/test_outlook_mail_collection_boundary.py tests/test_outlook_mail_rule_middleware.py`
- `uv run --locked ruff check message_ingest/commands message_ingest/spiders/microsoft/outlook/email tests/test_outlook_commands.py tests/test_outlook_mail_collection_boundary.py tests/test_outlook_mail_rule_middleware.py`
- `pyright message_ingest/commands message_ingest/spiders/microsoft/outlook/email tests/test_outlook_commands.py tests/test_outlook_mail_collection_boundary.py tests/test_outlook_mail_rule_middleware.py`

Expected: all tests PASS and Ruff/Pyright report zero errors.

- [ ] **Step 7: Commit Task 12**

`git add message_ingest/commands message_ingest/spiders/microsoft/outlook/email tests/test_outlook_commands.py tests/test_outlook_mail_collection_boundary.py tests/test_outlook_mail_rule_middleware.py && git commit -m "Wire Outlook Mail rule policy into acquisition"`

---

### Task 13: Bind Effective Mail Policy to JOBDIR Before Scheduler Construction

**Session boundary:** stop after the Task 13 commit.

**Files:**

- Create: `message_ingest/acquisition/microsoft/outlook/email/policy_context.py`
- Modify: `message_ingest/spiders/microsoft/outlook/email/_base.py`
- Test: `tests/test_outlook_mail_policy_context.py`
- Modify: `tests/test_source_context.py`
- Modify: `tests/test_jobdir_resume.py`

**Interfaces:**

- `MAIL_POLICY_JOB_MARKER = ".msgloom-mail-policy-context-v1"`
- `MailPolicyContextMismatch(RuntimeError)`
- `ensure_mail_policy_jobdir_context(jobdir: str, *, policy_digest: str, policy_enabled: bool) -> None`
- `OutlookMailPolicyContextExtension.from_crawler(crawler)`
- Collection Spider registers extension priority 60.
- Existing `SourceContextExtension` remains priority 50.
- Marker mode 0600; directory existing source contract stays 0700.

**Marker rules:**

- matching marker -> allow;
- different marker -> reject;
- marker absent, directory has only verified source marker -> new/pre-Scheduler job; create current enabled/disabled marker;
- marker absent + other persisted Scrapy state:
  - disabled current policy -> one-time disabled bootstrap;
  - enabled -> reject.
- policy digest never logged.

- [ ] **Step 1: Write failing pure marker tests**

Cover all marker table rows, permissions, race/existing marker, no digest/path leak in error text.

- [ ] **Step 2: Write real ExtensionManager ordering test**

Build a real Mail collection `Crawler`; assert effective extension component order has SourceContext 50 then MailPolicyContext 60.

Prove mismatch raises before Scheduler/requests can run.

- [ ] **Step 3: Write backward-compat JOBDIR tests**

Explicitly cover:

- source marker only + enabled -> allowed;
- legacy spider.state + no policy marker + disabled -> bootstrap;
- same legacy state + enabled -> reject.

- [ ] **Step 4: Run RED**

`uv run --locked pytest -q tests/test_outlook_mail_policy_context.py tests/test_source_context.py tests/test_jobdir_resume.py`

- [ ] **Step 5: Implement extension/marker**

Use synchronous `from_crawler()`; do not use a signal handler.

- [ ] **Step 6: Verify GREEN/static**

Run:

- `uv run --locked pytest -q tests/test_outlook_mail_policy_context.py tests/test_source_context.py tests/test_jobdir_resume.py`
- `uv run --locked ruff check message_ingest/acquisition/microsoft/outlook/email/policy_context.py message_ingest/spiders/microsoft/outlook/email/_base.py tests/test_outlook_mail_policy_context.py tests/test_source_context.py tests/test_jobdir_resume.py`
- `pyright message_ingest/acquisition/microsoft/outlook/email/policy_context.py message_ingest/spiders/microsoft/outlook/email/_base.py tests/test_outlook_mail_policy_context.py tests/test_source_context.py tests/test_jobdir_resume.py`

Expected: PASS / zero static errors.

- [ ] **Step 7: Commit Task 13**

`git add message_ingest/acquisition/microsoft/outlook/email/policy_context.py message_ingest/spiders/microsoft/outlook/email/_base.py tests/test_outlook_mail_policy_context.py tests/test_source_context.py tests/test_jobdir_resume.py && git commit -m "Bind Outlook Mail policy to JOBDIR"`

---

## Phase D — Deferred checkpointing and rules-aware Full planning

### Task 14: Add Delta Commit Modes, Deferred Status, and Workflow Completion Hooks

**Session boundary:** stop after the Task 14 commit.

**Files:**

- Create: `message_ingest/sync/microsoft/outlook/email/promotion.py`
- Modify: `message_ingest/spiders/microsoft/outlook/email/_delta_state.py`
- Modify: `message_ingest/spiders/microsoft/outlook/email/delta.py`
- Modify: `message_ingest/extensions/microsoft/outlook/email/checkpoint.py`
- Modify: `message_ingest/extensions/microsoft/outlook/email/status.py`
- Modify: `message_ingest/commands/_common.py`
- Modify: `tests/test_mail_delta_state.py`
- Modify: `tests/test_outlook_delta_integrity.py`
- Modify: `tests/test_crawl_status_extension.py`
- Modify: `tests/test_graph_workflow.py`

**Interfaces:**

- frozen/slotted `ValidatedMailDeltaRun` in `promotion.py`:
  - `run_id: str`
  - `expected_folder_ids: frozenset[str]`
  - `reconcile_messages: bool`
  - `candidate_folder_ids: frozenset[str]`
- `validate_mail_delta_run(snapshot: Mapping[str, object], candidates: Mapping[str, DeltaCheckpointCandidate]) -> ValidatedMailDeltaRun` owns the exact candidate/folder/reconciliation validation currently embedded in the checkpoint extension.
- `MailDeltaCommitMode(StrEnum)`: `IMMEDIATE`, `DEFERRED`, `BLOCKED`.
- Delta Spider private constructor arg accepts only `MailDeltaCommitMode | None`, not arbitrary user string.
- Derivation:
  - policy disabled -> IMMEDIATE;
  - policy enabled + internal DEFERRED object supplied by Mail sync -> DEFERRED;
  - policy enabled + no owner -> BLOCKED;
  - policy enabled + IMMEDIATE request -> error.
- Checkpoint outcomes extend with `deferred`.
- BLOCKED clean collection terminates incomplete with `policy_completion_required`.
- `GraphPhase` gains:
  - `completion_validator: Callable[[Crawler], bool] | None = None`.
- `run_graph_workflow(..., on_success: Callable[[tuple[Crawler, ...]], None] | None = None)`.
- When completion_validator exists, it is authoritative after bootstrap; generic `_crawler_failed()` is not separately re-applied to that phase.
- `on_success` runs once after all dynamic phases pass.

- [ ] **Step 1: Write failing shared validation and delta commit-mode tests**

Move the exact candidate-set/snapshot validation expectations into tests for `validate_mail_delta_run()`, then cover immediate/deferred/blocked derivation and impossible combinations.

- [ ] **Step 2: Write failing checkpoint/status tests**

Assert:

- IMMEDIATE current behavior unchanged;
- DEFERRED validates candidates/snapshot but does not promote, sets `msgloom/checkpoint/outcome=deferred`;
- status extension maps clean deferred delta to final `completed`;
- BLOCKED never promotes and returns incomplete/policy_completion_required.

- [ ] **Step 3: Write failing workflow-runner tests**

Cover:

- completion validator overrides generic spider failure gate only when provided;
- validator false/raises stops later phases;
- bootstrap failure always fatal;
- `on_success` runs exactly once after dynamic phases;
- `on_success` raise sets exitcode 1;
- zero dynamic follow-up still calls `on_success`.

- [ ] **Step 4: Run RED**

Run:
`uv run --locked pytest -q tests/test_mail_delta_state.py tests/test_outlook_delta_integrity.py tests/test_crawl_status_extension.py tests/test_graph_workflow.py`

- [ ] **Step 5: Implement the shared validator and mode/status/workflow APIs**

DEFERRED mode retains one `ValidatedMailDeltaRun` on the Spider runtime object for the later workflow finalizer. IMMEDIATE mode still uses the existing promotion calls until Task 15 atomically unifies them. Keep Calendar/To Do/OneDrive workflows on the existing default phase gate.

- [ ] **Step 6: Verify GREEN/static**

Run:

- `uv run --locked pytest -q tests/test_mail_delta_state.py tests/test_outlook_delta_integrity.py tests/test_crawl_status_extension.py tests/test_graph_workflow.py tests/test_outlook_sync_workflows.py`
- `uv run --locked ruff check message_ingest/sync/microsoft/outlook/email/promotion.py message_ingest/spiders/microsoft/outlook/email/_delta_state.py message_ingest/spiders/microsoft/outlook/email/delta.py message_ingest/extensions/microsoft/outlook/email/checkpoint.py message_ingest/extensions/microsoft/outlook/email/status.py message_ingest/commands/_common.py tests/test_mail_delta_state.py tests/test_outlook_delta_integrity.py tests/test_crawl_status_extension.py tests/test_graph_workflow.py tests/test_outlook_sync_workflows.py`
- `pyright message_ingest/sync/microsoft/outlook/email/promotion.py message_ingest/spiders/microsoft/outlook/email/_delta_state.py message_ingest/spiders/microsoft/outlook/email/delta.py message_ingest/extensions/microsoft/outlook/email/checkpoint.py message_ingest/extensions/microsoft/outlook/email/status.py message_ingest/commands/_common.py tests/test_mail_delta_state.py tests/test_outlook_delta_integrity.py tests/test_crawl_status_extension.py tests/test_graph_workflow.py tests/test_outlook_sync_workflows.py`

Expected: PASS / zero static errors.

- [ ] **Step 7: Commit Task 14**

`git add message_ingest/sync/microsoft/outlook/email/promotion.py message_ingest/spiders/microsoft/outlook/email/_delta_state.py message_ingest/spiders/microsoft/outlook/email/delta.py message_ingest/extensions/microsoft/outlook/email/checkpoint.py message_ingest/extensions/microsoft/outlook/email/status.py message_ingest/commands/_common.py tests/test_mail_delta_state.py tests/test_outlook_delta_integrity.py tests/test_crawl_status_extension.py tests/test_graph_workflow.py tests/test_outlook_sync_workflows.py && git commit -m "Add deferred Outlook Mail delta workflow"`

---

### Task 15: Make Message Lifecycle and Delta Cursor Promotion Atomic

**Session boundary:** stop after the Task 15 commit.

**Files:**

- Modify: `message_ingest/sync/microsoft/outlook/email/promotion.py`
- Modify: `message_ingest/catalog/stores/microsoft/outlook/_email_lifecycle.py`
- Modify: `message_ingest/sync/microsoft/outlook/email/checkpoints.py`
- Modify: `message_ingest/extensions/microsoft/outlook/email/checkpoint.py`
- Test: `tests/test_outlook_mail_atomic_promotion.py`
- Modify: `tests/test_outlook_mail_presence.py`
- Modify: `tests/test_outlook_delta_integrity.py`

**Interfaces:**

- Consumes Task 14 `ValidatedMailDeltaRun` and `validate_mail_delta_run()` unchanged.
- `OutlookMailLifecycleStore.commit_delta_lifecycle_in_session(session, validated: ValidatedMailDeltaRun, *, committed_at: str) -> dict[str, int]`.
- `OutlookDeltaCheckpointStore.commit_in_session(session, validated: ValidatedMailDeltaRun, *, committed_at: str) -> int`.
- `promote_validated_mail_delta(catalog: Catalog, *, source_id: str, validated: ValidatedMailDeltaRun) -> dict[str, int]` uses one `catalog.writer_session()`.
- Existing public immediate methods delegate to the same session helpers so rules-disabled behavior stays single-sourced.

- [ ] **Step 1: Write failing atomic promotion happy-path test**

Seed lifecycle candidates + delta candidates; promote; assert lifecycle, cursors, and candidate committed timestamps all advance together.

- [ ] **Step 2: Add Review Focus rollback injection test**

Monkeypatch/inject a failure after lifecycle session mutations but before checkpoint session helper completes.

Assert after rollback:

- prior DeltaCheckpoint remains unchanged;
- lifecycle presence remains prior state;
- candidate committed_at remains null;
- no partial folder/message absence becomes authoritative.

- [ ] **Step 3: Run RED**

`uv run --locked pytest -q tests/test_outlook_mail_atomic_promotion.py tests/test_outlook_mail_presence.py tests/test_outlook_delta_integrity.py`

- [ ] **Step 4: Implement session helpers + promotion service**

Do not open nested independent sessions inside the atomic service.

- [ ] **Step 5: Rewire immediate checkpoint extension**

IMMEDIATE mode invokes the same atomic service after validation.

DEFERRED mode returns/stores the validated-run facts in Spider runtime state for the workflow finalizer; do not serialize provider cursors into SpiderState.

- [ ] **Step 6: Verify GREEN/static**

Run:

- `uv run --locked pytest -q tests/test_outlook_mail_atomic_promotion.py tests/test_outlook_mail_presence.py tests/test_outlook_delta_integrity.py tests/test_outlook_mail_delta.py`
- `uv run --locked ruff check message_ingest/sync/microsoft/outlook/email/promotion.py message_ingest/sync/microsoft/outlook/email/checkpoints.py message_ingest/catalog/stores/microsoft/outlook/_email_lifecycle.py message_ingest/extensions/microsoft/outlook/email/checkpoint.py tests/test_outlook_mail_atomic_promotion.py tests/test_outlook_mail_presence.py tests/test_outlook_delta_integrity.py tests/test_outlook_mail_delta.py`
- `pyright message_ingest/sync/microsoft/outlook/email/promotion.py message_ingest/sync/microsoft/outlook/email/checkpoints.py message_ingest/catalog/stores/microsoft/outlook/_email_lifecycle.py message_ingest/extensions/microsoft/outlook/email/checkpoint.py tests/test_outlook_mail_atomic_promotion.py tests/test_outlook_mail_presence.py tests/test_outlook_delta_integrity.py tests/test_outlook_mail_delta.py`

Expected: PASS / zero static errors.

- [ ] **Step 7: Commit Task 15**

`git add message_ingest/sync/microsoft/outlook/email message_ingest/catalog/stores/microsoft/outlook/_email_lifecycle.py message_ingest/extensions/microsoft/outlook/email/checkpoint.py tests/test_outlook_mail_atomic_promotion.py tests/test_outlook_mail_presence.py tests/test_outlook_delta_integrity.py tests/test_outlook_mail_delta.py && git commit -m "Atomically promote Outlook Mail delta state"`

---

### Task 16: Prove Current-Attempt Full-v1 Completion and Force Authoritative Rule Refresh

**Session boundary:** stop after the Task 16 commit.

**Files:**

- Create: `message_ingest/acquisition/microsoft/outlook/email/full_completion.py`
- Modify: `message_ingest/catalog/stores/evidence.py`
- Modify: `message_ingest/spiders/microsoft/outlook/email/full.py`
- Modify: `message_ingest/spiders/microsoft/outlook/email/_attachments.py`
- Test: `tests/test_outlook_mail_full_completion.py`
- Modify: `tests/test_outlook_mail_full_enrichment.py`
- Modify: `tests/test_terminal_surface_failures.py`
- Modify: `tests/test_raw_content_size_limit_crawl.py`

**Interfaces:**

- Evidence store adds bounded bulk provenance API:
  - `run_ids_for(evidence_ids: Iterable[str]) -> dict[str, str | None]`.
- Full spider private arg:
  - `_authoritative_rule_refresh: bool = False`.
  - when true and operation=refresh, every Full-v1 provider request uses `dont_cache=True`.
- frozen/slotted `MailFullCompletionResult`:
  - `complete: bool`
  - `with_limitations: bool`
  - `reason_code: str`
  - `waivable_failure_reasons: frozenset[str]`
- `verify_current_full_v1(catalog: Catalog, *, source_id: str, run_id: str, message_ids: tuple[str, ...]) -> MailFullCompletionResult`.
- Proof requires current-run non-cache canonical evidence for:
  - detail/mime/attachments terminal base surfaces;
  - current-run attachment metadata when attachment inventory is acquired;
  - every required child surface for current-run attachments.
- Old attachment rows not observed in current run are ignored for current inventory.

- [ ] **Step 1: Write failing current-run provenance tests**

Cases:

- all current-run acquired -> complete;
- profile-terminal unavailable/unauthorized/unsupported -> complete_with_limitations;
- old base surface -> incomplete;
- current attachment inventory but child surface old -> incomplete;
- deleted old attachment row not current-run -> does not block;
- transient missing surface -> incomplete.

- [ ] **Step 2: Pin failure-reason waiver mapping**

A `request_failure:<purpose>` is waivable only when its exact current-run required surface is terminal.

Any spider/item/framework/integrity reason remains non-waivable.

- [ ] **Step 3: Add Review Focus HTTP-cache test**

Enable Scrapy cache, pre-seed an old matching Full response, run a rule-authoritative refresh Request construction/crawl path, assert `dont_cache=True` and current-run evidence is created/used.

- [ ] **Step 4: Run RED**

Run:
`uv run --locked pytest -q tests/test_outlook_mail_full_completion.py tests/test_outlook_mail_full_enrichment.py tests/test_terminal_surface_failures.py tests/test_raw_content_size_limit_crawl.py`

Expected: new current-run/no-cache completion tests FAIL before implementation.

- [ ] **Step 5: Implement no-cache flag propagation**

Do not change explicit operator Full or rules-disabled sync behavior.

- [ ] **Step 6: Implement verifier**

Reuse existing `surface_is_complete()` for status/profile semantics, then add current-run provenance proof.

- [ ] **Step 7: Verify GREEN/static**

Run:

- `uv run --locked pytest -q tests/test_outlook_mail_full_completion.py tests/test_outlook_mail_full_enrichment.py tests/test_terminal_surface_failures.py tests/test_raw_content_size_limit_crawl.py`
- `uv run --locked ruff check message_ingest/acquisition/microsoft/outlook/email/full_completion.py message_ingest/catalog/stores/evidence.py message_ingest/spiders/microsoft/outlook/email/full.py message_ingest/spiders/microsoft/outlook/email/_attachments.py tests/test_outlook_mail_full_completion.py tests/test_outlook_mail_full_enrichment.py tests/test_terminal_surface_failures.py tests/test_raw_content_size_limit_crawl.py`
- `pyright message_ingest/acquisition/microsoft/outlook/email/full_completion.py message_ingest/catalog/stores/evidence.py message_ingest/spiders/microsoft/outlook/email/full.py message_ingest/spiders/microsoft/outlook/email/_attachments.py tests/test_outlook_mail_full_completion.py tests/test_outlook_mail_full_enrichment.py tests/test_terminal_surface_failures.py tests/test_raw_content_size_limit_crawl.py`

Expected: PASS / zero static errors.

- [ ] **Step 8: Commit Task 16**

`git add message_ingest/acquisition/microsoft/outlook/email/full_completion.py message_ingest/catalog/stores/evidence.py message_ingest/spiders/microsoft/outlook/email/full.py message_ingest/spiders/microsoft/outlook/email/_attachments.py tests/test_outlook_mail_full_completion.py tests/test_outlook_mail_full_enrichment.py tests/test_terminal_surface_failures.py tests/test_raw_content_size_limit_crawl.py && git commit -m "Verify current Outlook Mail Full completion"`

---

### Task 17: Integrate Rules-Enabled Mail Sync Planning and Final Promotion

**Session boundary:** stop after the Task 17 commit.

**Files:**

- Modify: `message_ingest/commands/microsoft/outlook/sync.py`
- Modify: `message_ingest/commands/microsoft/outlook/mail.py`
- Modify: `tests/test_outlook_sync_workflows.py`
- Modify: `tests/test_outlook_mail_sync_crawl.py`
- Modify: `tests/test_outlook_sync_crawls.py`
- Modify: `tests/test_outlook_shared_sync_crawl.py`

**Interfaces consumed:**

- Task 12 one frozen policy per invocation.
- Task 11 Spider `mail_rule_profiles` strongest-profile snapshot.
- Task 14 `GraphPhase.completion_validator` and workflow `on_success`.
- Task 15 deferred validated run + atomic promotion.
- Task 16 Full completion verifier.

**Rules-enabled planning:**

- Folder delta remains existing independent stream.
- Message delta Spider receives enabled policy + private DEFERRED mode.
- After delta:
  - read `spider.mail_rule_profiles`;
  - choose only internal `outlook-mail-full-v1` targets;
  - do not call `pending_full_v1_message_ids()`;
  - one authoritative `outlook_full operation=refresh` phase for targets.
- Full phase completion validator uses current-run verifier and waivable failure-reason rules.
- Zero Full targets add no Full phase; workflow finalizer still atomically promotes deferred delta.
- `on_success` atomically promotes the exact validated run from the delta Spider.
- If Full gate/finalizer fails, prior cursor remains authoritative.

**Rules-disabled planning:** exact current changed-refresh + historical backlog logic remains.

- [ ] **Step 1: Rewrite planner tests for enabled vs disabled branches**

Keep existing disabled test unchanged in expected behavior.

Add enabled tests:

- only rule-selected Full targets;
- discovery-only historical records are not backlog-enriched;
- duplicate observations already strongest Full;
- `--max-enrich` rejection was handled before this function;
- zero targets returns no Full phase but installs finalizer.

- [ ] **Step 2: Write Full phase gate tests**

Fake crawler:

- terminal-complete with only waivable request failures -> accepted;
- non-waivable integrity reason -> rejected;
- old/incomplete surfaces -> rejected.

- [ ] **Step 3: Write atomic finalizer tests**

Successful dynamic workflow calls promotion once.

Rejected Full phase never calls promotion.

Zero-target workflow calls promotion once.

- [ ] **Step 4: Run RED**

`uv run --locked pytest -q tests/test_outlook_sync_workflows.py tests/test_graph_workflow.py`

- [ ] **Step 5: Implement rules-enabled branch**

Remove Task 12's temporary `rules_enabled_sync_not_implemented` guard in this same change. Keep the disabled branch visibly separate to minimize regression risk.

- [ ] **Step 6: Update real local Scrapy sync crawl fixtures**

Extend the local HTTP server fixture with a Mail config file and rule-selected/discovery-only messages.

Prove request order:

- folder delta;
- message delta/reconciliation;
- rule probe if required;
- Full only for selected target;
- final cursor committed only after Full proof.

- [ ] **Step 7: Run integration GREEN**

Run:

- `uv run --locked pytest -q tests/test_outlook_sync_workflows.py tests/test_outlook_mail_sync_crawl.py tests/test_outlook_sync_crawls.py tests/test_outlook_shared_sync_crawl.py`
- `uv run --locked ruff check message_ingest/commands/microsoft/outlook tests/test_outlook_sync_workflows.py tests/test_outlook_mail_sync_crawl.py tests/test_outlook_sync_crawls.py tests/test_outlook_shared_sync_crawl.py`
- `pyright message_ingest/commands/microsoft/outlook tests/test_outlook_sync_workflows.py tests/test_outlook_mail_sync_crawl.py tests/test_outlook_sync_crawls.py tests/test_outlook_shared_sync_crawl.py`

Expected: PASS / zero static errors.

- [ ] **Step 8: Commit Task 17**

`git add message_ingest/commands/microsoft/outlook tests/test_outlook_sync_workflows.py tests/test_outlook_mail_sync_crawl.py tests/test_outlook_sync_crawls.py tests/test_outlook_shared_sync_crawl.py && git commit -m "Apply Outlook Mail rules to sync planning"`

---

## Phase E — Provider qualification, documentation, and release verification

### Task 18: Qualify Composite Probe Semantics Against the Real Microsoft Graph Service

**Session boundary:** stop after the Task 18 commit. This is a hard completion gate.

**Files:**

- Modify: `scripts/microsoft-live-acceptance.py`
- Modify: `tests/test_live_acceptance_harness.py`
- Optionally create only if the existing harness becomes unwieldy: `scripts/microsoft-mail-rule-qualification.py` plus a focused dry-run test.

**Interfaces/qualification evidence:**

- Live acceptance remains read-only and requires `--confirm-live`.
- Add exact options:
  - `--mail-rule-qualification` enables the Mail RuleEngine qualification path and makes Calendar start/end unnecessary for this mode;
  - `--mail-rule-message-id MESSAGE_ID` optionally selects a private real normal-message target; otherwise the harness chooses one bounded discovered message without printing its ID;
  - `--mail-rule-event-message-id MESSAGE_ID` optionally supplies a private real eventMessage target for production BODY qualification and the HTML fallback proof.
- The qualification path calls the same production composite-probe request builder/parser for the RuleEngine probe. For an event target it may additionally issue one qualification-only GET without the body-format preference to prove the HTML fallback; that read is counted separately and is not a second rule probe.
- Do not print supplied/discovered message IDs, mailbox locator, addresses, subjects, body, headers, regex values, or private digest.
- Acceptance summary records only booleans/counts/safe reason codes.

**Must prove on real Graph v1.0:**

- discovery/delta `$select` returns usable `changeKey`;
- one message GET can retrieve the supported combination of selected metadata/body/headers and all required single-value extended properties, or the implementation/spec is revised before proceeding;
- extended property IDs parse as designed;
- existing Mail read scopes are sufficient;
- a real eventMessage succeeds through the production one-probe logical-BODY path even if Graph honors `Prefer: outlook.body-content-type="text"`;
- a separate qualification-only GET without that body-format preference returns HTML and succeeds through the same logical BODY projector;
- no second **rule probe** is required.

- [ ] **Step 1: Extend dry-run tests first**

Assert `--mail-rule-qualification --dry-run` needs no Calendar window, plans only safe Mail qualification phase names, and never emits private locator/message IDs.

- [ ] **Step 2: Run harness tests and verify RED**

`uv run --locked pytest -q tests/test_live_acceptance_harness.py`

- [ ] **Step 3: Implement bounded read-only qualification phase**

Reuse existing auth/source isolation. The qualification harness itself remains read-only and does not add Graph write permissions. If the development mailbox contains no eventMessage, a disposable meeting fixture may be created out-of-band with an already-consented development `Calendars.ReadWrite` token only after explicit user authorization; fixture IDs remain private and are never committed. Production RuleEngine scopes remain Mail read-only.

- [ ] **Step 4: Run dry-run GREEN**

`uv run --locked pytest -q tests/test_live_acceptance_harness.py`

- [ ] **Step 5: Execute real live qualification**

Use the currently configured development Microsoft Graph account and explicit `--confirm-live`.

Run the normal-message qualification with a fresh private output directory:
`uv run --locked python scripts/microsoft-live-acceptance.py --confirm-live --mail-rule-qualification --output-dir var/live-acceptance/mail-rule-qualification`

If a known real eventMessage is required because bounded discovery did not find one, rerun with:
`uv run --locked python scripts/microsoft-live-acceptance.py --confirm-live --mail-rule-qualification --mail-rule-event-message-id '<PRIVATE_EVENT_MESSAGE_ID>' --output-dir var/live-acceptance/mail-rule-event-qualification`

Do not paste the private ID into committed files or assistant-visible summaries.

The run is successful only if the acceptance summary proves all required points above.

If the one-GET extended-property shape fails, **stop**: update the design/spec and supported predicate set/probe shape before continuing. Do not silently add a second probe.

If no eventMessage exists in the bounded mailbox sample, record the read-only qualification as incomplete unless an explicitly supplied real eventMessage ID is available. With explicit user authorization, development may create a disposable real meeting fixture out-of-band and rerun the read-only harness against the generated eventMessage; this does not change production permissions or one-probe semantics.

- [ ] **Step 6: Commit Task 18 only after qualification evidence is captured**

Commit only code/tests/docs-safe summary changes; do not commit raw acceptance data or private mailbox content.

Run:
`git add scripts/microsoft-live-acceptance.py tests/test_live_acceptance_harness.py && git commit -m "Qualify Outlook Mail rule probes on Graph"`

---

### Task 19: Write the User Guide, Update Architecture/Stats Docs, and Run Full Verification

**Session boundary:** complete this documentation/verification task in one final session before branch review. It has no artificial RED phase; any defect discovered here must be fixed through a separate focused RED/GREEN fix commit before resuming verification.

**Files:**

- Create: `docs/outlook-mail-rules.md`
- Modify: `docs/component-layout.md`
- Modify: `docs/statistics.md`
- Modify package/layout tests only where public module ownership changed.
- No production behavior changes unless final verification reveals a defect; defects use the systematic-debugging/TDD path and a separate fix commit.

**User guide must cover all spec §12 requirements and 54 example categories**, including:

- XDG config/default/`--config`;
- enabling/disabling;
- discovery/full;
- AND/OR/exceptions;
- ordering/stop/monotonic profile;
- casefold behavior;
- regex literal-string examples and unsupported syntax;
- every supported predicate family;
- Outlook baseline vs msgloom extension vs deferred;
- body probe persistence/data-minimization caveat;
- fail-safe behavior;
- standalone delta/max-enrich restrictions;
- policy-change non-retroactivity;
- explicit operator Full override;
- non-secret rule-ID guidance.

- [ ] **Step 1: Write/update the three documentation files**

Create `docs/outlook-mail-rules.md` and update `docs/component-layout.md` / `docs/statistics.md`. Do not use real addresses/message content from acceptance logs. If an existing package/layout test explicitly asserts a changed public module path, update that named existing test alongside the docs; do not invent a new documentation test framework.

Run:
`pre-commit run markdownlint-cli2 --files docs/outlook-mail-rules.md docs/component-layout.md docs/statistics.md`

Expected: PASS.

- [ ] **Step 2: Run focused RuleEngine/config/runtime suites**

Run the complete focused set:
`uv run --locked pytest -q tests/test_outlook_mail_rule_regex.py tests/test_outlook_mail_rule_config.py tests/test_outlook_mail_rule_contracts.py tests/test_outlook_mail_rule_body.py tests/test_outlook_mail_rule_predicates_metadata.py tests/test_outlook_mail_rule_predicates_probe.py tests/test_outlook_mail_rule_engine.py tests/test_outlook_mail_rule_probe.py tests/test_outlook_mail_rule_middleware.py tests/test_outlook_mail_rule_middleware_integration.py tests/test_outlook_mail_rule_observability.py tests/test_outlook_mail_policy_context.py tests/test_outlook_mail_full_completion.py tests/test_outlook_mail_atomic_promotion.py tests/test_outlook_sync_workflows.py tests/test_outlook_mail_sync_crawl.py`

Expected: all PASS.

- [ ] **Step 3: Run Outlook/Microsoft regression suites**

Run at minimum:
`uv run --locked pytest -q tests/test_outlook_commands.py tests/test_outlook_crawls.py tests/test_outlook_mail_delta.py tests/test_outlook_delta_integrity.py tests/test_outlook_mail_full_enrichment.py tests/test_outlook_mail_presence.py tests/test_outlook_sync_crawls.py tests/test_outlook_shared_sync_crawl.py tests/test_outlook_shared_mailbox.py tests/test_source_context.py tests/test_jobdir_resume.py tests/test_crawl_status_extension.py tests/test_graph_workflow.py tests/test_live_acceptance_harness.py`

Expected: PASS.

- [ ] **Step 4: Run config/CLI regressions**

`uv run --locked pytest -q tests/configuration tests/application_cli`

Expected: PASS.

- [ ] **Step 5: Run Ruff and Pyright**

Run:

- `uv run --locked ruff check msgloom message_ingest microsoft_graph tests`
- `pyright`

Expected: zero errors.

- [ ] **Step 6: Run the complete supported Python matrix**

Run the complete supported matrix:
`uv run --locked tox -e py312,py313,py314`

Expected for all three environments:

- normal parallel suite PASS;
- exclusive suite PASS;
- `re2` imports successfully through the locked runtime dependency;
- no new warnings attributable to this feature.

- [ ] **Step 7: Run privacy/scope audit**

Search staged branch diff for:

- raw regex/address/subject/body logging;
- `ruleset_digest` rendering;
- raw Mail policy in settings/state/request args;
- accidental Graph permission additions;
- decision persistence/schema additions.

Run these non-interactive checks:

- `git diff --name-status dae9123..HEAD -- msgloom message_ingest microsoft_graph docs pyproject.toml uv.lock scripts tests`
- `git diff --stat dae9123..HEAD -- msgloom message_ingest microsoft_graph docs pyproject.toml uv.lock scripts tests`
- `rg -n "ruleset_digest|effective_mail_policy_digest|User\.Read|Directory\.|Mail\.Read|Mail\.Read\.Shared" msgloom message_ingest microsoft_graph`
- `git diff --unified=0 dae9123..HEAD -- msgloom message_ingest microsoft_graph | rg -n "logger\.|logging\.|stats\.|settings\.set|spider\.state|cb_kwargs|meta=|Mail\.Read|User\.Read" || true`
- `git diff --unified=0 dae9123..HEAD -- message_ingest/catalog message_ingest/acquisition/microsoft/outlook/email | rg -n "rule.*decision|matched_rule|selected_profile|ruleset_digest" || true`

Manually inspect every hit. Expected: no raw policy value/private digest observability, no new non-Mail-read Graph scope, and no per-message rule-decision persistence/schema.

- [ ] **Step 8: Update component/statistics docs and commit Task 19**

Commit:
`git add docs tests && git commit -m "Document Outlook Mail rule configuration"`

- [ ] **Step 9: Final worktree verification before claiming completion**

Run:

- `git status --short --branch`
- `git log --oneline dae9123..HEAD`
- `git diff --check dae9123..HEAD`

Expected:

- clean worktree;
- only intended serial commits;
- no whitespace errors.

Do not merge/push. Hand the completed branch to the user for review.

---

## Self-Review Notes

### Spec coverage

- Universal file/XDG/default/explicit selector: Task 1; config-management CLI adoption: Task 4; Microsoft Mail selector adoption: Task 12.
- Legacy operator coexistence and operation-specific strictness: Tasks 1 and 4, with the Mail command side proven again in Task 12.
- Google RE2 dialect/privacy/resource limits: Task 2; policy validation integration Task 3.
- Full predicate config vocabulary/bounds/digest: Task 3; universal config CLI exposure: Task 4.
- Known-empty/unavailable bounded facts/changeKey: Task 5.
- Deterministic HTML/text body semantics: Task 6.
- Metadata predicates/tri-state/casefold: Task 7.
- Probe-backed predicates/special-message class mapping: Task 8.
- Ordered RuleEngine/required-data branch union/fail-safe: Task 9.
- Mail CLI `--config` matrix/direct crawl/runtime handoff: Task 12.
- Composite probe acquisition/JOBDIR serialization: Task 10; middleware integration/privacy/strongest profile: Task 11.
- JOBDIR effective-policy binding/pre-Scheduler order/legacy bootstrap: Task 13.
- Immediate/deferred/blocked delta and workflow gates/finalizer: Task 14.
- Atomic lifecycle+cursor promotion: Task 15.
- Authoritative no-cache Full/current-run terminal completeness: Task 16.
- Rules-enabled sync target handoff/no global backlog/zero targets: Task 17.
- Real Graph one-probe/changeKey/extended-property/eventMessage/permission qualification: Task 18.
- Non-technical guide and complete regression/static verification: Task 19.

No approved spec section is intentionally deferred beyond the explicit V1 out-of-scope items.

### Type/interface consistency

- `MailRulePolicy` is the one immutable user-policy model passed process-locally; Scrapy state carries only bounded `MailRuleObservation`.
- `MailRuleFacts` is shared between initial observation and probe result.
- `MailRuleRequiredData` is an immutable set in both evaluator and Spider probe APIs.
- Private effective digest is present in evaluator/JOBDIR control contracts but absent from observability.
- Task 14 defines `ValidatedMailDeltaRun`; Task 15 reuses that exact type for both immediate and deferred atomic promotion.
- `GraphPhase.completion_validator` and `run_graph_workflow(on_success=...)` are introduced before sync integration consumes them.
- Full current-run verifier is implemented before rules-enabled sync uses it.

### Proportion

The plan intentionally specifies signatures, exact values, tests, commands, and commit boundaries but leaves function bodies to the implementer. Each task is intended to fit one fresh implementation session and end at a meaningful review gate.

# msgloom Design Principles

**Status:** Draft for review

**Product intent:** [Design Brief](design-brief.md)

## 1. Role

These principles guide decisions across all phases. They define lasting constraints, not a processing sequence or a technology stack. Any exception must be explicit, justified and limited in scope.

## 2. Decision order

**Security and privacy come first.** They sit above the ordering below, not inside it. A choice that is faster, clearer or more complete is not taken if it weakens them. This covers the whole product, not only the permission boundary.

User permissions are a fixed boundary. Within that boundary, preserve correct meaning and report coverage first, then traceability and recovery, then ease of use and maintenance, and finally speed, brevity and token savings.

Two constraints follow from the first paragraph. They are boundaries, not preferences:

- **Trust.** Every byte that came from a source is **data**. Only configuration — the prompt template, the triage rules, the working-context snapshot — is **instruction**. This holds for message bodies as much as for attachments.
- **Outbound.** No message reaches any recipient but the owner, by any path. Credentials never leave the process that holds them. There must be no code path that can send, not merely no configuration that does.

Recorded 2026-09-17 from a product-owner decision (`msgloom-security-review.md`, D-0, D-2, D-3).

## 3. Processing and interpretation

### DP-01 — Use code where it is reliable

Use code for mechanical work and AI for language understanding and judgement. **Deterministic triage rules** cover conditions code can evaluate; **semantic triage rules** express conditions that need AI interpretation in plain English.

### DP-02 — Preserve processing history

Save received source bytes unchanged and every stage's input references, outputs and status, including exclusions and failures. Record the versions of inputs, code, configuration, rules, prompts, models and working context needed to trace, replay and compare results. Reruns create new results rather than overwrite earlier ones; AI reruns may differ.

### DP-03 — Group without changing meaning

Group source information before AI only when relationships are reliable. A conversation need not be one topic. Reduce duplicate content without removing distinct information; keep uncertain relationships unmerged.

### DP-04 — Make uncertainty visible

Record missing, conflicting and uncertain information explicitly, with reasons. Keep source statements separate from AI interpretation, and expose uncertainty in both saved results and reports.

### DP-05 — Share context, not sessions

Give each AI run a fresh session and relevant working context. Access must not alter the user's interactive sessions or memory. Working context informs interpretation; triage rules remain the governing criteria.

## 4. Coverage and control

### DP-06 — Protect report coverage

Apply the [report contract](design-brief.md#5-report-contract) from collected source information through delivery. Brevity must come from concise wording and levels of detail, never from omitting or delaying topics due for reporting or removing information essential to a decision.

### DP-07 — Keep responsibilities independent

Separate source integrations, shared processing and report presentation. Keep collection, processing, AI analysis and reporting schedules independently configurable. Exchange structured results so adding a source or report format does not create a separate interpretation of shared data.

### DP-08 — Validate and recover visibly

Advance a stage only after its results and progress are saved and validated. Resume from saved work; retries must account for effects that may already have occurred. Show failed or pending work rather than claim completion.

### DP-09 — Keep authority with the user

User instructions control rule changes, data access and business actions. Source content is data, not authority to expand permissions or direct tool use. Limit access and disclosure to what the task requires.

## 5. Maintenance and change

### DP-10 — Minimise maintenance

Reuse stable, actively maintained open-source components. Prefer a web interface for routine operation. Avoid custom infrastructure and new paid services; [existing service exceptions](tech-stack.md#2-baseline) remain explicit.

### DP-11 — Base changes on evidence

Version changes that affect results and assess them against representative, user-reviewed work. Evaluate missed important information as well as false alerts. Demonstrate that an optimisation preserves higher-priority goals before adopting it.

## 6. Applying the principles

Define each shared concept once and use its term consistently. The [document map](README.md) assigns each design concern to one document. Derive phase designs from the complete-product design, and assign deferred capabilities through the [Phase Roadmap](phase-roadmap.md).

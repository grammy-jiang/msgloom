# msgloom research context

This programme follows the user's ten research topics agreed in the ChatGPT conversation on 2026-09-14. Research one topic at a time, starting with Topic 01. Topics 02–10 are planned and are not authorized to run in this first batch.

## Repository and authoritative context

Repository: /home/grammy-jiang/Projects/msgloom.
Read docs/design-brief.md and docs/design-principles.md, then the relevant sections of docs/design.md. These documents currently say Draft for review. Preserve their terminology and distinguish existing design constraints, published findings, and proposed changes. Research does not approve or rewrite the design.

Before this research, git status contained untracked docs/ and notes/. Preserve them and all existing work. The initial branch was master, with HEAD 60f9dee. No commit, push, deployment, service restart, production mailbox access, or changes outside research/ are requested.

## Product purpose and scenario

msgloom is a personal work-information system processing thousands of messages daily. Sources initially include Outlook email and Microsoft Teams. Its first goal is that no work needing the user's response is missed; its second is reducing reading effort. Reports are organized by Topic: a concrete work matter, potentially spanning messages and Sources. Source, Topic, Triage rules, Working context, Group, Source record, and Stage result retain the definitions in the project documents.

The email scenario periodically collects a fixed interval through Microsoft Graph, reads bodies, attachments, inline images and other available content, identifies approvals, responses, urgent work and important discussions, and produces an overview linked to Topic details and original evidence.

Known difficulties:

- Two people may reply independently to the same parent; neither branch necessarily contains or has seen the other.
- One email can discuss multiple Topics; a reply may answer only some questions or conditions.
- A Topic can span email chains; the same chain may change Topics.
- Current content may depend on earlier messages, attachments or a knowledge database.
- Source time, collection time, versions, unavailable history and uncertainty must remain explicit.

Correct meaning and report coverage precede traceability and recovery, which precede convenience and efficiency. Preserve raw source bytes and unique information. Use deterministic mechanisms where reliable; preserve uncertain links separately. Research must assess latency, incremental-update cost and data requirements without claiming unmeasured performance.

## Research method and outputs

Use the installed research-pipeline Skill through its manifest-governed runner. Read the actual installed Skill and relevant references in the remote Codex session. Preserve query plans, candidate records, screening decisions, available full texts, analyses, citations, reviewer outcomes and workflow state. Use fresh research sessions. Do not fabricate search results, evidence, validation or completion.

Search foundational work as well as recent developments. The package's six-month default must not silently exclude older, directly relevant work. Distinguish direct email evidence from transfer candidates in meetings, group chat and other domains. Prioritize relevant primary research over paper-count targets. Official standards and source documentation may support engineering facts but must be labeled separately from academic evidence.

Use only public research material and synthetic examples. Existing configured services may be used within this research task; do not install new paid services or expose credentials. Record unavailable sources and conversion failures honestly.

The main report should be in English, retaining precise academic terminology. Provide a concise Chinese executive summary for the user. Recommendations are research proposals, not approved architecture changes.

## Research source request policy — user update 2026-09-14

For subsequent msgloom research, use a minimum 30-second interval per provider and run only one project pipeline task at a time. The user explicitly requested longer intervals after the first two failed searches. This is the project's conservative operating default, not a claim about each provider's permitted rate or a guaranteed recovery delay.

Topic 01's prepared profile is [config.next-run.toml](01-email-conversation-structure/config.next-run.toml). Future topic configurations must retain this minimum or a longer applicable provider-specific interval. Verify effective settings before launch.

Current 429 restrictions require a recovery decision before another literature search. Honor server-requested waiting deadlines; do not shorten them through jitter, or discard them when starting another process. The installed retry defects must be addressed before relying on these guarantees. See [request-frequency audit](01-email-conversation-structure/REQUEST_FREQUENCY_AUDIT.md) and [issue register](PIPELINE_ISSUES.md).

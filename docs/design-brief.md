# msgloom Design Brief

**Status:** Draft for review

**Design rules:** [Design Principles](design-principles.md)

## 1. Purpose

msgloom is a personal work-information system. It helps a user keep up with important work. Its first goal is that no work needing the user's response is missed. Its second goal is to reduce the reading needed to keep up.

It is designed for thousands of incoming messages a day across multiple sources. A few dozen work matters a day need the user's own response, such as a reply, an approval or a rejection. Each can span dozens of messages across sources, and missing one is unacceptable.

Its main result is a report organised by topic, not a list of message summaries.

## 2. Scope and boundary

The final product serves one user. Outlook email and Microsoft Teams one-to-one chats, group chats and channels are only the first sources. The product must allow more sources to be added over time without changing its purpose.

msgloom complements the user's work systems and daily AI use. It does not replace those systems or make unrestricted decisions on the user's behalf.

## 3. Core concepts

These terms have the same meaning throughout the design.

| Term | Meaning |
| --- | --- |
| **Source** | A work system that supplies information. |
| **Topic** | A work matter described by information from one or more sources. |
| **Triage rules** | User-defined criteria for deciding what needs attention and its priority. |
| **Working context** | The user's current work situation, including active projects, responsibilities and unresolved concerns. |
| **User preferences** | Preferences and local requirements that the user supplies, such as organisational standards or output preferences, for msgloom to apply across triage, analysis and reporting. |

## 4. Product features

**Personal priorities.** Identify which topics need attention using triage rules and working context, and propose priorities for topics the rules do not cover. The user's triage rules remain the deciding criteria.

**Topic analysis.** Explain developments and their implications using related information across sources and the user's local requirements. Investigate history, attachments and other work information when further analysis is useful.

**Scheduled reports.** Provide automatic reports on user-defined schedules for different priorities.

**Action support.** Recommend next steps, prepare replies, tasks and tickets, and carry out approved business actions.

**User customisation.** Take in the user's preferences and local requirements, and apply them across triage, analysis and reporting.

## 5. Report contract

Each report provides an overview and topic details. The overview covers every topic due for reporting, including its essential developments, required actions, deadlines and risks.

Topic details explain the assessment and provide supporting information and references back to the sources. They include references to every source message of the topic, including replies that arrive out of order and conversations that fork when two people reply at the same time. Missing information and uncertain conclusions are clearly identified.

The report makes each topic and its evidence clear and complete. It provides the summary and links to the original messages, so the user can read any original message when they want to, for example before approving or rejecting a request.

Reports are available through email and a local website, allowing the user to move from an overview to the detail needed for a decision.

## 6. Success

Success means that no work needing the user's response is missed, and that the user keeps up with important work with less reading. Judge it first by how much such work, or evidence that would change a decision, is missed; then by how well important information is understood. Measure both against examples the user has reviewed. The number of messages processed is not a measure of success.

This brief defines the final product. Phase scope and acceptance criteria are defined separately.

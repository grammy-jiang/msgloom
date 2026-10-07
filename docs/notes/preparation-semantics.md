# Preparation filtering and grouping semantics

**Scope:** deterministic Phase 1 A2 semantics over reviewed immutable
PreparedRecord values.

This lane is additive. It does not change prepared@1 or the Phase 1 persistence
schema. Integration registers the reviewed filter_result@1 and group_result@1
codecs in SemanticDataRegistry.phase1(). Both result kinds require semantic
data for accepted results. Filtering and grouping are pure synchronous
calculations: they perform no provider, database, filesystem, parser, AI, or
network work.

## Filtering contract

FilterConfig is frozen, strict, versioned by VersionRef, and rejects unknown
fields. It allows at most 256 rules. Each rule has a unique version reference
and at least one deterministic predicate. Populated predicate categories are
ANDed; values within sender, recipient, subject, source-type, or source-scope
categories are alternatives.

Address predicates compare exact prepared party identities. The configured
normalization policy is either exact or Unicode casefold. No trimming, domain
rewriting, plus-address handling, or address parsing is implicit. Configured
addresses with outer whitespace are rejected. Casefold collisions inside one
predicate are rejected at configuration validation.

Subject matching does not accept regular expressions. The supported operations
are exact, prefix, suffix, and contains. Each pattern is limited to 256
characters and each rule to 64 patterns. Evaluation therefore uses ordinary
linear string operations rather than an untrusted backtracking regex engine.

Time boundaries must be timezone-aware. not_before is inclusive and before is
exclusive. Python aware-datetime comparison supplies instant semantics across
different UTC offsets. Naive boundaries are invalid.

A source-scope predicate is an exact VersionRef with kind source_scope. The
later A1-to-preparation adapter must add a NativeRelationship whose kind is
source_scope and whose target is the scope reference when a scope is
available. The scope identity must already be stable and namespace-qualified;
this lane never parses or constructs provider IDs. A missing scope relationship
does not match a scoped rule.

Every rule is evaluated. Matches are saved in canonical rule-reference order,
so declaration order cannot settle a conflict. Include plus exclude is
conflict. Exclude alone is excluded; include alone is included. Guidance-only
matches are guidance. Guidance remains present in matched_rules even when
inclusion or exclusion also matches. No match is an explicit default included
result.

apply_filters does not update PreparedRecord.filtering. This is intentional:
the accepted prepared@1 shape has only one rule_ref and cannot losslessly carry
all matches. FilterResult references the exact prepared source version and
retains every matched versioned rule. Excluded prepared data therefore remains
unchanged and replayable. Excluded or conflicting records are held out of
semantic grouping and receive a one-member None grouping result.

## Grouping relationship conventions

Grouping never reads subject text. Equal or normalized subjects cannot create
a group. Input and output ordering is canonical by exact VersionRef so
replaying the same set in a different order returns the same result.

The later A1 adapter must preserve globally unambiguous, scope-qualified source
version identities. Every communication record that participates in native
grouping carries exactly one source_scope relationship whose target is a
VersionRef of kind source_scope. Native confirmation requires the source and
present target record to carry exactly the same scope reference. Missing,
multiple, invalid-kind, or conflicting scope evidence is explicit uncertainty;
same PreparedSourceType or VersionRef kind is never a substitute for account,
channel, or chat scope. Conversation candidates are partitioned by the same
declared scope, so even support-only candidates cannot merge independent
scopes. Contextual source types remain separate regardless of scope metadata.

Direct relationship targets are exact prepared source versions. A missing or
cross-kind target is not followed or guessed. Self-links and parent cycles are
invalid. Missing, ambiguous, invalid, or scope-incompatible ancestry is closed
through all descendants before any component union, so a child cannot become
confirmed through a parent that is later found uncertain. These cases preserve
every record as an explicit uncertain disposition rather than manufacturing a
component.

The supported relationship kinds are:

| Prepared source | Relationship kind | Phase 1 meaning |
| --- | --- | --- |
| Outlook email | in_reply_to | Exact present parent can confirm membership. |
| Outlook email | outlook_conversation | Candidate/support only. |
| Teams channel | teams_channel_reply_to | Exact root/parent can confirm. |
| Teams chat | teams_chat_reply_to | Explicit supported reply can confirm. |
| Any source | source_scope | Scope metadata only; never grouping evidence. |

For outlook_conversation, the target kind must also be outlook_conversation and
its identity must be scope-qualified by the adapter. One or more records
sharing that target produce Uncertain rather than Confirmed. Multiple
conversation targets on one record are visibly ambiguous.

For direct parent relations, more than one parent is ambiguous. A missing
parent is uncertain. A parent with a different source kind or declared source
scope is not joined. Confirmed groups are connected components of unambiguous
exact parent edges after ambiguity closure. The algorithm does not use a
conversation candidate to merge separate confirmed components.

Teams channel root/reply evidence may confirm a group. Teams chat messages stay
separate unless teams_chat_reply_to is explicitly present and resolvable. Chat
membership and time proximity are not grouping rules.

To Do, OneDrive, and Contacts are contextual inputs. They always receive
one-member None grouping results and cannot automatically form communication
groups, even if a generic relationship happens to be present. Source types are
partitioned before grouping, so no Phase 1 semantic cross-source join occurs.

## Result and codec boundary

FilterResult and GroupResult are strict frozen Pydantic models. GroupResult
carries Confirmed, Uncertain, or None status, exact canonical members, method,
exact relationship evidence, reason, and exactly one immutable filter result
for every member. None results are single-member and cannot claim grouping
evidence. Confirmed results require at least two members, method-consistent
parent evidence with exactly one spanning-tree edge per additional member, and
a connected evidence graph. Outlook conversation evidence is never Confirmed.
Excluded or conflicting filter outcomes cannot enter Confirmed or Uncertain
groups. These invariants are revalidated during encoding and decoding, so
validation-bypass copies or constructions cannot persist invented claims.

FilterResultCodec implements filter_result@1 with a 1 MiB canonical JSON
ceiling. GroupResultCodec implements group_result@1 with a 4 MiB ceiling. Both
satisfy the existing semantic registry codec protocol. The default registry
owns their registration. Encoding revalidates the complete model, including
instances made through validation-bypass APIs. Decoding rejects invalid or
noncanonical JSON.
The persistence registry remains responsible for digest, byte-count, schema,
and configured maximum-size enforcement when these codecs are later
registered.

No codec contains raw evidence bytes or mutates the prepared record. A later
stage must save its semantic result before a dependent claim is admitted,
following the reviewed awaited persistence lifecycle. Unsupported, ambiguous,
missing-parent, and conflicting-filter cases stay explicit rather than
becoming invented confirmed relationships or order-selected decisions.

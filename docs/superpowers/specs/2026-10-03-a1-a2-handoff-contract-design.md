# A1 to A2 durable handoff contract design

## Status

**Status:** Runtime implemented and qualified; Tasks 1–14 accepted by PRIMARY.
Task 15 documentation review and final independent acceptance remain pending.
See the [qualification record](../../notes/a1-closeout.md#handoff-qualification-record--2026-10-07).

**Design date:** 2026-10-03.

**A1 baseline:** 9e072eed17672f8380c709a9932ea56dbcbaff85.

This document defines the durable work-selection boundary between the completed
A1 Microsoft acquisition subsystem and A2 preparation. Kedro orchestration
remains downstream. This governing contract was originally design-only; later
user authorization approved its implementation. The requirements and readiness
amendments below remain in force. Runtime qualification does not claim final
Task 15 acceptance or installation of an external scheduler.

This design supersedes earlier conversational proposals that treated either one
CLI command or one Spider run_id as the universal A1-to-A2 batch. Neither
identity is a correct universal handoff unit.

## Intent

A1 stores historical acquisition state in one SQLite catalog. The catalog can
contain years of observations, evidence, current projections, provider
checkpoints, presence state, enrichment surfaces, failed-run residue, and
replayed captures.

A2 must never scan that catalog and guess which records belong to the current
scheduled processing cycle.

Instead:

1. A1 records exact downstream-relevant acquisition facts durably.
2. A1 commits a release group only after the group's semantic completion
   boundary is proven.
3. That committed group exposes immutable release entries as bounded downstream
   admission units.
4. A2 consumes only new immutable release entries after its own durable
   consumer cursor.
5. A2 freezes exact source selections before parsing.
6. Historical A1 data remains available as explicit supporting context without
   becoming primary work merely because it exists in SQLite.

The normal scheduled shape is:

    A1 collection
        |
        v
    durable acquisition facts
        |
        v
    committed release groups
        |
        v
    sequenced release entries
        |
        +------------------------------+
                                       |
                                       v
                                  A2 intake
                                       |
                                       v
                             immutable A2 workset
                                       |
                                       v
                                    Kedro

The package does not gain an internal scheduler or background queue. External
scheduling remains outside msgloom.

## Scope

This design covers the current A1 Microsoft acquisition surface:

- Outlook Mail discovery;
- Outlook Mail folder delta;
- Outlook Mail message delta and reconciliation;
- Outlook Mail Full-v1 enrichment;
- Outlook Calendar discovery;
- Outlook Calendar fixed-window reads;
- Outlook Calendar fixed-window delta;
- Outlook Calendar Full-v1 enrichment;
- Microsoft To Do discovery;
- Microsoft To Do authoritative snapshot sync;
- OneDrive discovery;
- OneDrive delta and 410 resync;
- OneDrive explicit content acquisition;
- Contacts discovery;
- Contacts authoritative snapshot sync;
- Contacts custom-folder delta;
- Microsoft profile acquisition as an explicit non-handoff exception.

The currently installed Scrapy project exposes 17 Microsoft Spiders. Teams is
not part of the current live A1 surface and therefore has no release mapping in
this design.

## Non-goals

This design does not:

- redesign Graph traversal;
- replace Scrapy Requests, callbacks, pipelines, extensions, or JOBDIR;
- introduce a generic workflow engine;
- move provider checkpoints out of their existing stores;
- make A1 import A2 preparation or source-reader models;
- make A2 mutate A1 rows as consumed;
- define Kedro nodes;
- define Calendar's final A2 semantic role;
- infer provider chronology from SQLite insertion order;
- treat provider folder/window absence as global deletion;
- retroactively invent exact event chronology for pre-ledger historical data;
- add automatic ledger pruning.

## 1. Existing boundaries that remain authoritative

### 1.1 Scrapy component ownership

Traversal stays in Spiders. Raw response/evidence persistence and domain
persistence stay in pipelines and domain stores. Provider checkpoint and
snapshot promotion stay in their existing lifecycle stores/extensions.
Commands remain intent mapping and user-level workflow composition.

The handoff feature must fit those boundaries. It must not become a second
crawler scheduler.

### 1.2 A1 and A2 remain dependency-separated

The current source reader is deliberately outside message_ingest. A1 does not
import msgloom.sources, msgloom.preparation, CollectedSelection, or A2 code.

That remains true.

A1 publishes acquisition provenance. A2 maps that provenance to VersionRef /
CollectedSelection and persists the resulting downstream snapshot.

### 1.3 Current mutable tables are not replay truth

Tables such as current Mail surfaces, attachments, Calendar surfaces, To Do
current records, Contacts current projections, and OneDrive current state
remain useful A1 operational state.

They are not the A1-to-A2 replay contract.

A failed or not-yet-released A1 operation may legitimately have updated some of
those tables. Reading them later cannot prove that a value belonged to an
already released downstream unit.

## 2. Terms

### Logical run

One logical Spider execution identified by the existing run_id.

A logical run may span more than one operating-system process when qualified
JOBDIR resume restores that run_id.

### Attempt

One concrete process/crawler attempt at a logical run.

A clean JOBDIR pause followed by resume is at least two attempts but one logical
run.

### Acquisition fact

An immutable A1 record that states one exact source-side fact obtained or
derived during acquisition.

A fact is not automatically eligible for A2.

### Release subject

The smallest semantic scope for which A1 can independently prove the requested
acquisition contract is complete enough to publish downstream effects.

Examples:

- one Mail discovery traversal scope;
- one Mail message Full-v1 target;
- one Calendar fixed window;
- one Calendar event Full-v1 target;
- one To Do authoritative snapshot scope;
- one OneDrive content item;
- one Contacts custom-folder delta scope.

The release subject owns the completion gate. It is not necessarily the unit
that A2 consumes.

### Release group

An immutable atomic publication declaring that one release subject passed its
completion or authority gate.

The group records coverage/profile/authority metadata shared by all effects
published by that completion decision.

A group may reference facts from more than one logical run only when the
current operation explicitly revalidates those older facts as the exact state
being released.

### Release entry

One immutable, independently pageable downstream effect within a committed
release group.

Examples include one changed Mail message, one Todo task, one Calendar event
membership transition, one OneDrive item/content impact, or one context update.

A large traversal/snapshot/delta group can therefore publish many release
entries atomically while A2 consumes those entries in bounded chunks.

### Stream

A durable acquisition family used for downstream cursors:

- outlook_mail;
- outlook_calendar;
- todo;
- onedrive;
- contacts.

Profile output is operational output, not an A2 stream.

### A2 consumer cursor

A2-owned durable progress for one A1 catalog, source_id, stream, stable
consumer identity combination.

The cursor belongs to A2. It is never a consumed flag in A1.

## 3. Hard invariants

The implementation must preserve all of the following.

### H1. No historical scan as incremental selection

A2 must not select scheduled work using provider timestamps or by listing all
current/historical source versions and guessing what is new.

### H2. No command-as-batch assumption

One CLI invocation can contain many Spider runs. A resumable logical run can
also span several CLI invocations.

A command invocation is therefore not the durable handoff identity.

### H3. No universal run-as-batch assumption

A single Full Spider can target several resources. One target can become
complete while another target fails.

run_id remains execution provenance, but release granularity is determined by
the release subject's semantic completion contract.

### H4. Facts and releases are different things

A durable fact can exist without being released.

Incomplete, stale, losing, paused, or failed release subjects may retain
facts for diagnostics, retries, or future revalidation without becoming A2
primary work. A run-level failure does not invalidate another subject in the
same run when that subject has its own independently proven release contract.

### H5. Downstream-visible state advancement must stage its fact atomically

Every downstream-relevant domain write that can make a new A1 source/component
state effective must stage the corresponding acquisition fact in the same
SQLite transaction.

This is required even for non-authoritative discovery/enrichment writes. If a
domain row could advance without its fact, a retry might later see only
current-equivalent state and have no durable proof that the new state was never
released.

A fact-insert failure therefore rolls back the state advancement it describes.

### H6. Authority cannot advance without recoverable downstream publication

When A1 advances an authoritative checkpoint, presence generation, or fixed
window state, the corresponding release/authority publication state must commit
in the same SQLite transaction.

A crash may not leave provider authority advanced with no recoverable
downstream release.

### H7. Positive observations and authority claims have different gates

A provider observation is not the same claim as authoritative absence,
membership reconciliation, or checkpoint advancement.

Derived absence and winning state transitions are publishable only at the
existing authority promotion boundary.

### H8. Canonical evidence provenance is independent of logical-run identity

HTTP-cache replay may make a current-run semantic item reference evidence
originally captured in an older run.

The contract must preserve both the logical acquisition run_id and the exact
canonical evidence_id.

It must not globally require evidence.run_id to equal run_id.

### H9. Provider time is not publication order

observed_at is provider/evidence provenance, not a downstream watermark.

Release order uses a local monotonic release sequence.

### H10. Release order is not provider semantic chronology

Concurrent runs can finish in a different order from provider freshness.

A release sequence orders durable admission. It does not replace provider
versions, CAS revisions, delta ordinals, page/entry ordering, or source times.

### H11. Stale writes cannot become newer primary state

Domain persistence must expose whether a fact advanced current state, was
current-equivalent/replayed, or was stale.

A stale fact remains audit/history data but cannot create a release claiming a
new effective primary source state.

### H12. Mutable current projections cannot reconstruct an old release

Every release must name immutable acquisition facts sufficient for A2 to
reconstruct the exact released source/component state without consulting future
mutable current rows.

### H13. A1 does not serialize CollectedSelection

CollectedSelection remains an A2-side snapshot. A1 stores provider-neutral
handoff provenance only.

### H14. Scoped removal stays scoped

Examples:

- Mail message removed from Folder F is not mailbox deletion.
- Calendar event removed from one fixed window is not global event deletion.
- snapshot-derived absence applies only to the exact authoritative source/scope.

The scope is part of the released transition identity.

### H15. Downstream progress is consumer-owned

A2 advances its release-entry cursor only in the same short A2 transaction
that durably saves the immutable intake workset selected by that cursor
advance. Expensive A1 evidence reads and selection materialization do not run
inside that write transaction.

### H16. No silent backup/restore skip

A2 must verify an anchor for its prior cursor. A restored or replaced A1
catalog that no longer contains the same cursor anchor fails closed and
requires explicit recovery/baseline selection.

### H17. Completion scope and consumer unit are separate

One completed release subject may affect an unbounded number of resources.

A1 therefore commits one release group for the completion/authority scope and
one or more sequenced release entries for individually consumable resource,
context, component-parent, or transition impacts.

A2 cursors advance over release entries, not over an indivisible scope-level
manifest.

### H18. Intake failure cannot poison the stream forever

A release entry that cannot currently be materialized within A2 limits or
because required evidence is unavailable must be durably admitted as held or
failed input with its exact A1 release reference.

Once that disposition and workset are durable, the cursor may advance. Repair
or replay is explicit; one bad entry must not permanently block every later
entry in the stream.

### H19. Release-time freshness is revalidated

An `advanced` fact means that state won when its domain transaction committed;
it does not grant a permanent right to publish later.

Before a non-authoritative release group creates a resource/component entry, it
must verify that the candidate source_state_key still represents the effective
A1 state for that resource/component, or that it is the exact
current-equivalent recovery of an unreleased advanced state.

A fact superseded by another concurrent run remains immutable history but does
not become a later primary entry merely because its run finishes later.

Authoritative paths obtain the equivalent protection from their existing
revision/generation/CAS promotion and create entries only for the winning
state.

### H20. Cursor admission and preparation completion are separate

Advancing the A2 release-entry cursor atomically creates an immutable intake
workset and a durable pending-work index entry.

Preparation/Kedro processing may fail after that cursor commit. A later
invocation must discover the pending workset directly and retry/replay its
already frozen inputs without rewinding the A1 cursor.

Only a separate short terminal update marks the pending workset completed.
Failed processing does not erase it and does not require recollection.

## 4. Why the rejected batch models fail

| Candidate | Result | Counterexample |
| --- | --- | --- |
| One public command = one handoff | rejected | Mail/Calendar sync run several crawlers; JOBDIR can resume one logical run in a later command |
| One run_id = one handoff | rejected | Full can target many resources; one target may complete while another fails |
| VersionRef list alone | rejected | derived absence, scoped removals, and component enrichment are not just new object versions |
| A1 writes CollectedSelection | rejected | reverses the existing A1/A2 dependency boundary |
| A2 scans provider tables by run_id | rejected | HTTP-cache canonicalization can produce a current run with no new observation row |
| raw journal row = immediately consumable | rejected | staged/losing/authority-pending facts must remain hidden until the correct semantic unit is eligible |
| one scope-level release = one A2 cursor step | rejected | snapshots/deltas/discovery can affect more records than one bounded A2 intake may admit |
| one global A2 cursor | rejected | one source ID can expose multiple streams and consumers may enable them independently |

## 5. Contract architecture

    Provider response or derived authority change
                         |
                         v
                 Domain persistence
                         |
                         v
              Immutable staged fact
                         |
                         v
             Subject completion gate
                    /           \
             incomplete        complete
                 |                |
                 v                v
          staged only       Release group
                                  |
                                  v
                         Release entries
                                  |
                       =======================
                                  |
                                  v
                              A2 intake
                                  |
                                  v
                      bounded entry-sequence cut
                                  |
                                  v
                       exact reconstruction
                                  |
                                  v
                     immutable A2 workset
                                  |
                                  v
                                Kedro

Every downstream-visible domain state advancement and its acquisition fact
share one transaction. A release group/entry publication is a separate
operation when the subject requires several facts or an end-of-scope proof.

For authoritative promotions, authority mutation plus the release group and
all entries produced by that authority decision share one transaction.

## 6. Acquisition fact contract

### 6.1 Required identity

A fact needs at least the following structural semantics:

    fact_id
    source_id
    stream

    run_id
    spider_name

    fact_kind
    resource_kind
    resource_identity

    parent_resource_kind      optional
    parent_resource_identity  optional

    scope_kind                optional
    scope_identity            optional

    component_kind            optional
    evidence_id               optional
    provider_observed_at

    storage_relation
    source_state_key          optional
    source_version_locator    optional
    authority_revision        optional
    provider_order            optional

The exact SQL schema is an implementation-plan decision, but these semantics
are required.

### 6.2 Fact kinds

The initial closed vocabulary is:

    resource_observation
    component_observation
    scoped_state_transition
    control_context

control_context covers durable source/context information such as a Mail folder,
Calendar inventory entry, To Do list, Contacts folder, or OneDrive drive record
when it is not itself an A2 primary communication record.

It is still downstream-readable context; it is not silently discarded.

### 6.3 Resource ownership

Component facts name their semantic parent.

Examples:

    Mail MIME                -> Mail message
    Mail attachment metadata -> Mail message
    Mail attachment bytes    -> Mail message

    Calendar attachment      -> Calendar event
    Calendar series topology -> Calendar event/series

    To Do checklist item     -> To Do task
    To Do linked resource    -> To Do task

    OneDrive content         -> OneDrive item

This prevents A2 from mistaking a component for an unrelated primary source.

### 6.4 Storage relation

The initial vocabulary is:

    advanced
    current_equivalent
    authority_staged
    stale

advanced means the write became the effective stored state for that
domain/resource/component.

current_equivalent means the acquisition is valid and exact but does not
advance semantic current state. Cache replay and idempotent re-observation can
produce this relation.

authority_staged means the provider observation is durable but is not yet
effective current state. Calendar/Contacts delta staging and OneDrive 410
resync observations use this relation. Such a fact can become downstream
eligible only through the winning authority promotion that applies it.

stale means a newer state already wins. A stale fact is retained but cannot
create a release claiming a newer effective primary source state.

Provider-specific stores may retain richer internal outcomes, but they must map
to these handoff semantics.

Release-entry eligibility follows these source-state rules:

- advanced facts are eligible once their release subject passes its gate;
- authority_staged facts are eligible only through the winning authority group
  that applies them;
- stale facts are never a new effective-source entry;
- current_equivalent facts do not create repetitive downstream work merely
  because a full snapshot observed the same state again;
- a current_equivalent observation may recover a previously staged advanced
  fact for the same source_state_key when that advanced fact has never belonged
  to a committed release entry and the current operation revalidates the same
  state.

source_state_key is an A1-owned canonical digest/identity of the retained source
or component state, excluding run/capture metadata. It exists to prove
equivalence and recovery; it is not an A2 parser/content hash.

The ledger also maintains a small mutable acquisition_effective_states index
keyed by source/stream/resource/component scope. It points to the fact and
source_state_key that currently win A1 freshness ordering.

The index is updated in the same transaction as the provider-domain write that
advances state. It is used only for storage-relation classification,
current-equivalent recovery, and release-time freshness checks. It is not an
immutable source version and A2 never reconstructs content from it.

This rule preserves failed-run recovery without sending every unchanged To Do
or Contacts snapshot row back to A2 on every schedule.

At release time, non-authoritative builders also revalidate that the selected
advanced/recovery state is still effective. `advanced` is a write-time
outcome, not a release-time freshness guarantee.

### 6.5 Exact source-version locator

A publishable resource/component fact carries a bounded A1-owned
source_version_locator when the exact provider representation must later become
an A2 source version.

The locator is independent of release-entry sequence. It identifies the exact
immutable representation using already durable A1 provenance such as an
observation key or canonical evidence plus resource/component identity.

A2 maps that locator to VersionRef. Releasing the same exact representation
again must not require inventing a different source version merely because the
downstream release entry is newer.

The locator is not an arbitrary path or provider payload.

### 6.6 Privacy and payload limits

The ledger does not duplicate arbitrary provider bodies or message content.

Source content remains in existing evidence files and domain/evidence stores.

A fact contains:

- stable provider/resource identifiers;
- bounded enum-like semantic metadata;
- exact evidence/provenance references;
- required scope/version/order metadata;
- small bounded transition reason data.

No access token, authorization header, preauthenticated download URL, message
body, attachment bytes, or arbitrary Graph object is copied into the handoff
ledger.

## 7. Release contract

### 7.1 Group granularity

A release group is the semantic completion/authority scope.

It can be traversal-scoped, authority-scoped, or one resource-profile target.
The group is committed atomically: A2 never sees half of one completion
decision.

A group is not required to fit in one A2 workset.

### 7.2 Group identity

A release group requires these semantics:

    release_group_id
    source_id
    stream

    release_kind
    subject_kind
    subject_identity

    scope_kind       optional
    scope_identity   optional
    profile          optional

    owner_run_id
    released_at
    coverage_kind

    authority_revision  optional
    group_digest

group_digest canonically binds the group identity, completion metadata, and the
ordered identities of the entries it publishes.

### 7.3 Release entries

Every downstream-consumable effect is represented by a release entry:

    release_entry_seq
    release_group_id

    entry_kind
    resource_kind
    resource_identity

    parent_resource_kind      optional
    parent_resource_identity  optional

    scope_kind                optional
    scope_identity            optional

    entry_digest

release_entry_seq is a monotonically increasing local publication sequence. It
orders downstream admission only; it is not provider time.

An entry names exact immutable fact IDs with bounded roles such as primary,
component, context, transition, or proof.

A large group can have many entries. All entries become visible atomically when
the group transaction commits, but A2 may consume the committed entries across
several bounded intake worksets.

### 7.4 Entry/member semantics

Component changes normally publish an entry for their semantic parent. For
example, new Mail MIME or attachment bytes produce a Mail-message impact rather
than an unrelated attachment work item.

A scoped transition can be its own entry when no readable source representation
exists, for example authoritative absence.

Multiple facts may belong to one entry. One fact can be referenced by later
groups only after the later release owner revalidates it as the exact state
satisfying that subject's contract.

### 7.5 Release kinds

The initial group families are:

    resource_set
    resource_profile
    authority_scope
    content_capture
    context_inventory

resource_profile is appropriate for Mail/Calendar Full-v1.

authority_scope is appropriate for snapshot/delta promotions.

content_capture is appropriate for explicit OneDrive content.

### 7.6 Release eligibility versus run outcome

A run may produce no groups, one group, or several groups.

A group may publish no entries when a completed authority round has no
downstream-relevant changes; the durable authority outcome can still be
recorded without forcing an empty A2 work item.

Subject-level completion status and declared terminal limitations are stored on
the release group, not collapsed into one run-wide completion flag.

A failed multi-target Full run may still contain a target whose profile was
independently proven terminal-complete. That target can receive its own group
and entry.

Conversely, a normally closing Spider is not enough to release a scope whose
completion contract was not established.

Run outcome remains diagnostics/control evidence, not the universal handoff
gate.

## 8. Authoritative promotion rule

For authority-bearing operations, the following structure is mandatory:

    BEGIN IMMEDIATE

    validate candidate/base revision
    apply winning provider state
    apply presence/window reconciliation
    advance provider checkpoint/generation
    write promotion-derived transition facts
    write one authority release group
    write all release entries for the winning authority state
    bind entries to exact staged/winning facts
    mark candidate committed

    COMMIT

Observation facts that were already staged earlier in the crawl are
referenced, not copied. Transition facts that exist only because promotion
established a new authority state are created in the promotion transaction.

The group and every entry belonging to that authority decision commit with the
provider checkpoint/generation. A2 can later page those already committed
entries without weakening the atomic provider decision.

If any required fact/release write fails, the provider authority mutation rolls
back.

This rule applies to:

- Outlook Mail message-delta lifecycle/cursor promotion;
- Outlook Mail folder-delta promotion;
- Outlook Calendar fixed-window delta promotion;
- To Do authoritative snapshot promotion;
- Contacts authoritative snapshot promotion;
- Contacts custom-folder delta promotion;
- OneDrive delta checkpoint/resync promotion.

No signal ordering assumption may substitute for this transaction.

## 9. Non-authoritative completion rule

Non-authoritative operations do not advance provider authority, but they still
need an explicit release completion contract.

If the process fails before release creation, domain/evidence rows and staged
facts may remain. They are not silently considered released.

Retry may:

- reacquire the source;
- reuse canonical cache evidence;
- discover that the domain state is current-equivalent;
- revalidate already staged exact facts;
- create the missing release idempotently.

This is why an unchanged/replayed acquisition must still be representable in
the fact ledger.

## 10. JOBDIR and logical-run identity

### 10.1 Supported resume identity

Qualified resumable paths must restore one logical run_id across process
attempts.

Currently established paths include:

- Outlook Mail delta;
- Outlook Calendar window;
- Outlook Calendar delta;
- Outlook Calendar full.

JOBDIR is execution state only. It does not replace the fact/release ledger or
provider checkpoints.

### 10.2 Mail discover/full prerequisite

Current Mail discover/full Requests are serializable, but the Spiders do not
restore run_id from JOBDIR. Reusing the same JOBDIR therefore creates a new
logical run identity around queued old work.

The handoff implementation must not bless that half-supported state.

The chosen correction is:

> Public Mail discover and Mail full must reject JOBDIR until a complete
> scope-bound logical-run resume contract is implemented and qualified.

Mail delta retains its existing qualified JOBDIR support.

This is intentionally fail-closed and smaller than inventing an unreviewed Mail
discover/full resume protocol during handoff work.

## 11. Run/attempt outcome ledger

A1 should retain bounded execution metadata separately from releases.

A logical-run/attempt row records execution-wide facts such as:

    execution outcome
    close/pause outcome
    coverage outcome
    authority outcome where the whole run owns one authority scope

It must not pretend that one run has a single resource-completion value when
the run can target several independent resources.

Per-subject semantic completion belongs to the release group. One Mail Full
run can therefore be failed overall while Message A has terminal-complete
Full-v1 and Message B remains incomplete.

For a single-scope authority run, the run outcome may additionally state that
the authority promotion committed, but the release group and its entries
remain the downstream contract.

Stats remain observability. Durable outcome rows may be populated from the same
validated facts but must not rely on parsing logs.

## 12. Seventeen-Spider release matrix

| Spider | Release subject | Release gate | Authority / coverage notes |
| --- | --- | --- | --- |
| microsoft_profile | none | none | Profile is one-shot command output plus evidence; not A2 primary work. |
| microsoft_todo_discover | one discovery traversal | complete traversal | Additive only; no absence inference; JOBDIR rejected. |
| microsoft_todo_sync | one source snapshot | snapshot promotion | Positive resources plus authoritative presence/absence; JOBDIR rejected. |
| microsoft_contacts_discover | one recursive discovery traversal | complete configured recursion | Additive folders/contacts; no absence authority; JOBDIR rejected. |
| microsoft_contacts_sync | one source snapshot | snapshot promotion | Authoritative presence/absence and shared generation ordering. |
| microsoft_contacts_delta | one custom-folder delta scope | winning folder delta promotion | Sparse/staged delta observations remain unreleased until promotion; the release exposes exact winning observations/transitions, not a mutable merged snapshot; internal Spider; JOBDIR rejected. |
| microsoft_onedrive_discover | one root inventory | drive + root pagination complete | Additive drive/root observations only; no recursive absence; JOBDIR rejected. |
| microsoft_onedrive_delta | one source delta scope | winning checkpoint/resync promotion | 410 reset publishes only the winning reset/materialized authority. |
| microsoft_onedrive_content | one item content target | exact content capture persisted and version-linked | Multi-item invocation can release successful items independently; JOBDIR rejected. |
| outlook_discover | one configured mailbox/folder traversal | completed or intentionally truncated configured traversal | Truncation is explicit coverage, never absence authority. Mail discover JOBDIR must be rejected by this phase. |
| outlook_folder_delta | one mailbox folder-delta scope | folder checkpoint promotion | Folder removal is control state, not message deletion; JOBDIR rejected. |
| outlook_delta | one mailbox message-delta/reconciliation scope | Mail lifecycle + cursor promotion | Rules-disabled promotes in crawler lifecycle; rules-enabled defers release/authority until workflow finalizer. Qualified JOBDIR retained. |
| outlook_full | one message target/profile | per-message Full-v1 completion | One run may release several messages independently. Rules workflow accepts declared terminal limitations. Mail full JOBDIR must be rejected by this phase. |
| outlook_calendar_discover | one calendar inventory | complete inventory | Context inventory; JOBDIR rejected. |
| outlook_calendar_window | one exact calendar/time window | finished configured pagination with exact scope | Pause does not release the window. Qualified JOBDIR retains one run ID. |
| outlook_calendar_delta | one exact fixed-window authority scope | winning checkpoint/state promotion | 410 rebaseline releases only winning materialized window state. |
| outlook_calendar_full | one event target/profile | per-event Full-v1 completion | One run may release several events independently; qualified scope-bound JOBDIR retained. |

## 13. Product-specific details

### 13.1 Outlook Mail discover

The release names:

- exact configured mailbox target;
- whole-mailbox or selected-folder scope;
- effective discovery policy metadata needed for interpretation;
- whether pagination exhausted normally or the explicit max-pages bound
  truncated traversal;
- all exact released message/context facts.

A truncated release is valid positive data but carries no completeness or
absence claim.

### 13.2 Outlook Mail folder delta

Explicit folder tombstones and resulting cursor state are released only with
the winning folder-delta checkpoint transaction.

Folder removal may invalidate message-delta cursors for that folder. It does
not create a global Mail-message deletion release.

### 13.3 Outlook Mail message delta

Message delta observations, folder removals, reconciliation sightings, and
candidate cursors can be staged during the crawl.

The release occurs only when Mail lifecycle and message delta cursors are
committed.

For rules-enabled sync:

    delta crawl validates
        |
        v
    delta authority remains deferred
        |
        v
    selected per-message Full releases complete
        |
        v
    workflow finalizer atomically promotes Mail lifecycle/cursors
        |
        v
    Mail authority release commits

Per-message Full release groups are independent subjects. The existing rules
workflow may continue to use its all-selected-target completion validator
as the authority gate for deferred delta promotion; per-message release
validation is an additional downstream publication decision, not a weakening of
that authority gate.

A later Mail authority-finalizer failure does not erase a Full target that was
independently proven complete.

### 13.4 Outlook Mail Full-v1

A Full Spider may target many messages.

Release is therefore per message, not per run.

For each message the release must bind the exact terminal Full-v1 component
facts required by the profile:

- detail;
- MIME;
- attachment inventory;
- required attachment raw/detail surfaces;
- explicit terminal limitation surfaces where the profile treats them as
  terminal.

Rules-enabled authoritative refresh requires current-attempt proof exactly as
the existing completion verifier does.

Explicit/enrich paths need an equivalent per-target release verifier in the
handoff implementation. A planner-no-work target can release only after A1
revalidates and binds the exact facts that already satisfy the requested
profile.

### 13.5 Outlook Calendar window

A window release identity includes:

- source;
- calendar identity/scope;
- exact start;
- exact end.

A clean JOBDIR pause is not window completion. The resumed attempt retains the
same logical run and ultimately creates at most one idempotent window release
for the completed scope.

### 13.6 Outlook Calendar delta

Ordered delta observations remain internal staging until the candidate wins
the existing CAS promotion.

The release binds:

- exact fixed-window scope;
- winning run/attempt;
- committed revision;
- effective window event state/transitions.

A removed event is absent from that fixed-window membership. No global event
deletion is inferred.

### 13.7 Outlook Calendar Full-v1

Release is per event target.

The handoff implementation must add a current-target Full-v1 completion proof
analogous in role to Mail's verifier, using Calendar's existing profile,
resource-version, attachment, and series-topology semantics.

A multi-target run can therefore release complete event A even if event B
fails.

### 13.8 To Do

Discovery release is additive.

Authoritative sync reuses the same traversal but releases the authoritative
snapshot only with snapshot promotion. The authority release contains the
winning presence state, including absence inferred from complete traversal.

Task lists, checklist entries, and linked resources retain their exact
hierarchical ownership. A2 may later classify them as context/components; A1
does not erase them.

### 13.9 Contacts

Discovery is one complete recursive additive traversal release.

Snapshot sync releases presence/absence only with the winning snapshot
promotion.

Custom-folder delta remains a folder-scoped authority release. Sparse delta
observations are staging input to the winning authority state. The release may
expose those exact winning observations and scoped transitions; it must not
pretend that a mutable merged ContactRecord is an immutable historical
provider response.

### 13.10 OneDrive

Discovery covers drive metadata and the complete configured root-child
inventory only.

Delta/resync release follows the winning checkpoint/promotion. A 410 reset's
partial enumeration never becomes authoritative merely because rows exist.
The released source side is the exact winning provider observations plus
authority transitions, not a later read of mutable OneDrive current rows.

Explicit content acquisition releases each successfully version-linked content
target independently.

OneDrive release metadata never persists preauthenticated download URLs.

## 14. Concurrency and ordering

### 14.1 Domain freshness

Two overlapping runs can observe the same resource.

The existing provider/domain freshness rules remain authoritative. The ledger
records each fact's storage relation.

A fact marked stale cannot produce a release that claims new effective state.

### 14.2 Current-equivalent replay

A current-equivalent observation can still be required for handoff recovery,
but it does not automatically create repetitive work.

Example:

1. Run A atomically writes a newly advanced provider state plus advanced fact,
   then fails before the completion subject is released.
2. Run B retries and observes the same source_state_key.
3. Domain persistence reports current_equivalent and stages that revalidation.
4. Run B successfully proves its completion subject.
5. The release builder sees that the earlier equivalent advanced fact has never
   belonged to a committed release entry and can publish that exact state once.

If the equivalent advanced state was already released, Run B creates no new
resource entry for that unchanged state.

This prevents both failed-run data loss and repeated full-snapshot churn.

### 14.3 Release-entry sequence

release_entry_seq orders committed downstream entries.

It does not decide:

- Graph delta ordering;
- source time;
- Calendar delta entry ordering;
- Contacts delta ordinal ordering;
- provider version freshness.

Those semantics remain in the fact/release metadata and existing provider
stores.

## 15. A2 intake contract

### 15.1 Cursor scope

A2 stores independent cursors by:

    A1 catalog identity
    source_id
    stream
    stable consumer_id

At minimum Mail and Calendar must not share one downstream cursor merely because
they share an Outlook source ID.

consumer_id is stable across ordinary parser/rule/configuration changes. Those
changes are recorded on worksets/results and use explicit replay/rerun policy;
they do not silently create a fresh source cursor and replay the entire feed.

The cursor position is:

    last_release_entry_seq
    last_release_entry_digest

not the release-group ID.

### 15.2 Bounded entry cut

For one source/stream, A2 chooses a finite entry range after its prior cursor:

    (last_release_entry_seq, cutoff_release_entry_seq]

The range is bounded by entry count and intake byte/query budgets before
downstream preparation begins.

A group with thousands of committed entries can therefore be drained over
multiple worksets. New A1 entries after the cutoff wait for a later intake.

### 15.3 Intake claim

Cursor admission is a separate durable work scope from processing an already
fixed preparation plan.

Phase 1 persistence must add a narrow PREPARE_INTAKE claim kind keyed by the A1
catalog identity, source_id, stream, and stable consumer_id.

The intake lease is finite and longer than its bounded materialization budget.

### 15.4 Materialization outside the final write transaction

A2 must not hold its SQLite write transaction while reading A1 evidence files
or constructing potentially large CollectedSelection values.

Under the intake claim it:

1. validates the prior cursor anchor;
2. reads a bounded committed release-entry cut from A1;
3. resolves exact entry facts;
4. constructs exact A2-side source selections/transition inputs;
5. persists immutable selection StageResults using claim-fenced, append-only
   writes;
6. records an explicit held/failure disposition for an entry that cannot be
   materialized safely.

These steps can use bounded awaited workers and short existing persistence
transactions.

### 15.5 Atomic workset/cursor finalization

After materialization, one short Phase 1 persistence transaction:

1. revalidates the current intake claim and unchanged prior cursor;
2. saves one immutable intake workset referencing the selected/held release
   entries and already durable selection results;
3. inserts the workset into the durable pending-preparation index;
4. advances the consumer cursor to the exact cutoff entry sequence/digest;
5. commits.

A crash before this transaction leaves the cursor unchanged. Previously saved
immutable selection results are harmless and may be reused by retry.

A crash after commit cannot lose work because the workset and its pending queue
entry are already durable.

### 15.6 Pending workset processing

Scheduled preparation first drains durable pending worksets independently of
whether the same invocation also admits newer release entries.

A pending workset references already frozen CollectedSelection/transition
inputs. Preparation uses those exact inputs and never rereads mutable LIVE A1
state.

After one workset reaches its accepted terminal preparation outcome, a short
claim-fenced transaction marks that workset terminal and records its result
references. A failed/cancelled preparation attempt leaves the workset pending
for later retry unless an explicit operator action records a terminal
disposition.

### 15.7 Held entries

A missing/corrupt evidence file, unsupported source type, configured byte
limit, or other per-entry materialization problem does not allow the intake to
silently drop that release.

The immutable workset records the exact release entry plus a bounded held/fail
reason. Once that durable disposition exists, the cursor may advance.

Explicit repair/replay can revisit the held entry later without rewinding
unrelated later stream progress.

### 15.8 Existing SavedSourceReader and preparation path

The current reader remains useful evidence for the exact-selection design:

- explicit VersionRef;
- exact evidence loading;
- CollectedSelection;
- replay after mutable current surfaces change.

However, list_versions() is not the scheduled handoff API.

A release-aware reader must enumerate release entries and reconstruct source
versions from release facts/source_version_locator values, never from future
mutable current projections.

It must also gain Calendar support before Calendar entries become
A2-processable.

After intake has persisted CollectedSelection results, scheduled preparation
should consume those exact saved selections through the existing replay/exact
selection path rather than call the LIVE reader again.

### 15.9 State-transition inputs

Not every release entry is a CollectedSelection.

A2 intake must also preserve typed scoped transitions such as:

- authoritative task/contact absence;
- Mail mailbox presence transition;
- Mail folder removal;
- Calendar fixed-window membership removal;
- OneDrive deletion/resync absence.

A2 policy may decide whether a transition triggers preparation, retirement,
reconciliation, or context refresh. A1 only supplies the exact scoped fact.

### 15.10 Historical context

A2 primary work comes only from the selected release-entry range.

While processing a primary record, A2 may read older A1 data as supporting
context, for example an In-Reply-To target.

That historical source is pinned to an exact selection and added to lineage. It
does not become primary work merely because it was read.

## 16. Scheduled execution

The external scheduler may run:

    A1 collection operation
        |
        | wait for requested operation outcome
        v
    A2 intake/preparation operation

or schedule A2 independently.

The handoff remains correct in either case because release state is durable.

No in-process queue connects A1 and A2, and no detached work survives a msgloom
invocation.

A chained operation may choose not to start A2 when its required A1 operation
fails. Independently completed release subjects from earlier work remain
durable and can be selected by a later explicit/scheduled A2 intake.

## 17. Historical bootstrap

Existing pre-ledger A1 history cannot be assigned a fabricated exact release
chronology.

The implementation must offer an explicit baseline choice.

### Baseline A: future-only

Create the ledger and start A2 from its genesis release-entry cursor.
Existing historical A1 rows remain context/replay data but are not automatically
admitted as new work.

Because pre-ledger current rows have no staged advanced acquisition fact,
post-ledger current-equivalent observations do not fabricate new work for those
old rows. Only a genuinely advanced post-ledger state, or explicit historical
baseline, admits them.

### Baseline B: explicit historical baseline

Run a dedicated bounded baseline operation that:

1. selects the operator-approved historical/current A1 scope;
2. captures exact A2-side selections;
3. saves one immutable baseline workset;
4. records the starting A1 release anchor;
5. uses the release stream for all future incremental intake.

The baseline must not guess its boundary from timestamps.

## 18. Backup, restore, and cursor anchors

A2 stores with every cursor:

    last_release_entry_seq
    last_release_entry_digest
    A1 catalog identity

Before advancing from a nonzero cursor, A2 verifies that the referenced release
entry still exists and has the same digest.

If it is missing or changed, A2 fails closed.

This catches:

- restore to an older A1 backup;
- replacement with another catalog;
- accidental ledger truncation;
- divergent copied state.

Automatic repair is out of scope. Recovery requires an explicit operator
baseline/reconciliation decision.

## 19. Additive schema shape

The implementation should add new tables rather than add handoff columns to
every provider table.

A candidate A1 shape is:

    acquisition_facts
    acquisition_effective_states
    acquisition_release_groups
    acquisition_release_entries
    acquisition_release_entry_facts
    acquisition_run_outcomes
    acquisition_ledger_metadata

acquisition_ledger_metadata owns a stable catalog identity and handoff-ledger
schema version. Existing catalogs receive that identity when the additive
ledger schema is first initialized; backups preserve it.

The exact DDL, indexes, uniqueness constraints, source-version locator encoding,
entry/group digest format, and sequence allocation are implementation-plan
work.

The A1 schema must support:

- append-only immutable released facts/groups/entries;
- one mutable effective-state index used only for freshness/equivalence gates;
- idempotent fact staging;
- idempotent group/entry publication;
- bounded lookup by source_id, stream, and release_entry_seq;
- lookup of unreleased facts by logical run/release subject;
- transactional inserts from provider stores/promotions;
- no arbitrary provider payload duplication.

The provider-neutral Phase 1 application database is different: it currently
uses explicit neutral schema version 3. Consumer cursors, intake worksets, and
their indexes therefore require an explicit reviewed v3-to-v4 migration rather
than implicit create_all behavior.

No automatic deletion/compaction is introduced in the first implementation.

## 20. Component ownership

### Spiders

Remain responsible for:

- provider traversal;
- request scope;
- pagination;
- callback parsing;
- provider-specific reset state;
- JOBDIR-serializable execution data where already qualified.

They do not own downstream consumer cursors.

### Item pipelines and domain stores

Own:

- awaited persistence;
- storage freshness outcome;
- source_state_key/source_version_locator derivation for persisted facts;
- atomic staging of each acquisition fact with the exact domain state
  advancement it describes.

One semantic item may still require several independent domain transactions
(for example Mail detail plus a surface row), but each individual advancement
must have its own atomic fact. A later release group binds all facts required
for subject completeness.

### Existing authority stores/extensions

Own the existing correctness proof and provider promotion.

They must be extended so authority release creation is inside the same
transaction as the promotion.

### Handoff release extension

For non-authoritative per-crawler scopes/targets, a narrow Scrapy extension may
finalize release groups/entries at natural spider_idle after request and item
pipeline work has drained and while the crawler CatalogService is still open.

It must be disabled for authority scopes whose existing checkpoint/snapshot
promotion owns publication. It must be idempotent and must not infer completion
from signal priority.

This keeps direct developer scrapy crawl execution and public Microsoft
commands on the same acquisition semantics.

### 20.1 A1 transaction insertion matrix

The following matrix is the implementation-readiness map for existing A1
persistence. Fact transaction names the transaction that must own the fact
write; no later pipeline may reconstruct it.

| Area | Existing persistence seam | Current outcome | Required handoff change | Release owner |
| --- | --- | --- | --- | --- |
| Mail message discovery/delta/detail | OutlookMailStore.record_message() | observation created/replay; current freshness implicit | Return structured storage relation, derive source_state_key, and stage exact message fact in the same session. Preserve immutable observation locator when one is created; cache replay can revalidate an older exact state. | discover scope / Mail authority / per-message Full |
| Mail positive presence | mark_message_present_in_session() inside record_message() | mutable presence update | No standalone primary entry. Bind presence facts/authority transitions only through the owning Mail release contract. | Mail authority |
| Mail folder membership removal | record_folder_removal() | append-only observation created/replay | Stage scoped message-in-folder transition fact in the same transaction; never map to global deletion. | Mail authority |
| Mail folder metadata | upsert_folder() | freshness decision implicit; no return | Return storage relation and stage control-context fact in the same transaction. | discover/folder-delta context |
| Mail folder tombstone | mark_folder_removed() | mutates folder presence and clears folder message cursors before final checkpoint | Stage exact folder transition/control facts in that transaction; keep them unreleased until winning folder-delta group commits. | folder-delta authority |
| Mail surface | set_surface() | mutable upsert; stale silently ignored; no run_id | Add logical-run provenance, return storage relation, and stage component fact atomically. | per-message Full |
| Mail attachment metadata | upsert_attachment() | mutable upsert; stale silently ignored | Add logical-run provenance, return storage relation, and stage component fact atomically. | per-message Full |
| Mail message-delta authority | promote_validated_mail_delta() + lifecycle/checkpoint session helpers | one writer_session() transaction | In that same transaction write promotion-derived presence transitions, one authority group, and all changed/recovery entries. Rules-enabled finalizer calls the same service after Full obligations pass. | existing immediate/deferred Mail authority owner |
| Mail folder-delta authority | OutlookFolderDeltaCheckpointStore.commit() | one Session.begin() transaction | Move/retain under strong writer transaction as needed; bind staged folder facts and publish one authority group + entries with checkpoint commit. | existing folder checkpoint extension |
| Calendar inventory/event | persist_calendar(), persist_event() | created/changed/unchanged/replay/stale | Stage resource/context facts in each existing transaction and map outcomes to ledger relations. | discover/window/per-event Full |
| Calendar surface | CalendarPlanningStore.set_event_surface() | mutable upsert; stale silently ignored; no outcome/run provenance | Add logical-run provenance, return storage relation, and stage component fact atomically. | per-event Full |
| Calendar attachment metadata/content | persist_attachment_metadata(), persist_attachment_content() | created/changed/unchanged/stale or acquired/replay | Stage parent-event component facts atomically; normalize outcomes to ledger relation. | per-event Full |
| Calendar series topology | persist_series_topology() | created/changed/unchanged/stale | Stage parent-event/series component fact atomically. | per-event Full |
| Calendar delta observation | persist_delta_observation() | append-only created/replay, not current | Stage authority_staged fact in the same transaction. | Calendar fixed-window authority |
| Calendar delta authority | CalendarDeltaCheckpointStore.commit() + apply_calendar_delta_state() | one explicit BEGIN IMMEDIATE connection transaction | Write derived fixed-window transitions plus group/entries inside this transaction; entries reference only the winning attempt's staged facts. | existing Calendar checkpoint extension |
| To Do resource | TodoStore._upsert() | created/changed/unchanged/stale | Stage resource/component facts atomically. Snapshot sighting remains separate proof; a sighting failure blocks authority release but does not erase the staged source fact. | discover or snapshot authority |
| To Do snapshot authority | TodoSnapshotStore.promote_snapshot() + reconcile-presence helper | one snapshot transaction; helper returns only counts | While reconciling, emit exact changed/recovery identity entries and absence/presence transition facts in-session; do not rescan mutable tables after commit. | existing To Do snapshot extension |
| Contacts folder/contact snapshot | persist_folder(), persist_contact() | created/changed/unchanged/stale | Stage facts in the existing writer_session() together with current state; retain sightings as authority proof. | discover or snapshot authority |
| Contacts delta observation | ContactsDeltaStore.persist_observation() | ordered staged observation only | Stage authority_staged contact fact in the same writer transaction. | Contacts folder-delta authority |
| Contacts snapshot authority | ContactsStore.promote_snapshot() | one writer transaction; helpers return counts | Emit exact folder/contact transition identities and group/entries in-session while presence is applied. | existing snapshot promotion extension |
| Contacts delta authority | ContactsDeltaStore.promote() | one writer transaction applying ordered observations + generation/CAS | Emit entry/transition facts as each winning observation is applied; skipped stale observations do not become primary entries. | existing Contacts delta extension |
| OneDrive drive/item | OneDriveStore._upsert_session() | created/changed/unchanged/stale | Stage resource/control fact in caller transaction. Delta-mode facts remain unreleased until winning checkpoint; discover facts use traversal release. | discover or OneDrive authority |
| OneDrive content | persist_content() + immutable OneDriveContentCapture | created/changed/unchanged/stale plus append-only capture | Stage exact item-content component fact in the same writer transaction; content release is per item. | per-item content |
| OneDrive 410 observation | persist_resync_observation() | ordered staged observation, not current | Stage authority_staged fact atomically with resync observation. | OneDrive authority |
| OneDrive delta/resync authority | promote_checkpoint() + apply_onedrive_resync_state() | one writer transaction; helper returns counts | Emit exact applied/skipped identities, derived absences, release group, and entries in-session. Normal delta references advanced facts from the run; reset references only winning reset observations. | existing OneDrive checkpoint extension |
| Profile | raw evidence pipeline only | one-shot command output | No A2 acquisition fact or release entry. | none |

The common A1 ledger writer must support caller-owned SQLAlchemy Session and
the Calendar Core Connection path without opening nested transactions. Store
methods remain the owners of domain semantics; the ledger helper owns canonical
fact/group/entry validation and idempotent inserts.

For a normal current-state write, the ledger helper stages the immutable fact
and updates acquisition_effective_states only when the provider store has
already decided the write is not stale. Matching source_state_key maps to
current_equivalent without replacing the effective fact; a new key maps to
advanced and atomically replaces the effective pointer. Authority-staged facts
do not update the effective pointer until the winning promotion applies them.

Candidate/checkpoint/control rows that exist only to prove lifecycle
completeness need not become downstream entries. They can be referenced by
bounded release-group proof metadata while resource/context/transition facts
remain the A2-facing payload.

### 20.2 Release-finalization matrix

| Operation class | Completion proof | Publication action |
| --- | --- | --- |
| Additive discovery/inventory | natural spider_idle, run integrity clean, provider-specific pagination/traversal proof | release extension commits one group and entries for unreleased effective facts in the exact configured scope |
| Explicitly truncated Mail discovery | natural idle + explicit max-pages termination | same as discovery, but coverage_kind=truncated; no absence authority |
| Calendar window | natural idle + exact scope + pagination exhausted; qualified JOBDIR preserves logical run | one window group; pause/interruption publishes nothing |
| Mail/Calendar Full | per-target profile verifier at natural idle or workflow phase gate | one group/entry per target proven terminal-complete; another failed target does not erase it |
| OneDrive explicit content | exact content capture + metadata-version association | one group/entry per successful item |
| Snapshot/delta authority | existing candidate/traversal proof + winning revision/generation/CAS | authority store writes group + entries in the promotion transaction |
| Rules-enabled Mail deferred authority | existing delta validation + all selected Full obligations | workflow finalizer invokes the same atomic Mail promotion/release service |

A generic spider_closed publisher is prohibited. Scrapy signal-handler order
does not establish catalog availability or semantic completion.

### 20.3 A2 persistence insertion matrix

The current provider-neutral Phase 1 database is explicit schema version 3 and
already owns short BEGIN IMMEDIATE transactions, claim fencing, immutable
StageResults, semantic-data codecs, and cancellation-safe async wrappers.

The handoff implementation extends that owner rather than creating a Kedro- or
reader-owned SQLite layer.

| Concern | Existing seam | Required change |
| --- | --- | --- |
| Intake ownership | ClaimKind, Phase1Store.acquire_claim() | add PREPARE_INTAKE; claim key binds A1 catalog identity + source + stream + stable consumer_id |
| Neutral schema | schema_store.py v3 explicit migration | reviewed v3 -> v4 migration adding intake cursor/workset tables and required indexes |
| Cursor | none | current cursor row keyed by catalog identity + source + stream + stable consumer_id; stores last entry seq/digest |
| Intake semantic payload | ResultSchemaRegistry, SemanticDataRegistry | register bounded preparation_intake_workset@1 codec containing entry references, exact collected-selection result refs, transition/held dispositions, and cutoff anchor |
| Selection persistence | existing collected_selection@1 StageResult + semantic data | reuse; release-aware reader produces the exact selection before cursor finalization |
| Final atomicity | Phase1Store._write_transaction() | new finalize_preparation_intake() validates live intake claim + prior cursor, appends workset result/data, inserts pending-workset state, advances cursor, and fences ownership in one short transaction |
| Retry | immutable StageResults + unchanged cursor on failed finalization | deterministic selection/result IDs allow harmless reuse; retry reads the same entry range |
| Pending processing | none | durable workset state indexes pending/terminal processing independently of source cursor progress |
| Processing | existing PreparationHandler replay path | scheduled handoff drains pending worksets using saved exact selections; it does not call LIVE selection after cursor advance |
| Bad entry | current Limitation/Failure contracts | intake workset records held disposition and exact release reference before cursor can pass it |
| Calendar | no current PreparedSourceType/reader adapter | add Calendar release-aware mapping before Calendar entries can become preparation selections |

PreparationHandler remains the finite parser/filter/group producer. Intake is
a preceding A2 admission step, not a Kedro node and not a replacement for the
existing PREPARE claim that protects an already fixed preparation plan.

### Command/workflow coordinator

Owns only gates that genuinely cross crawler phases, principally rules-enabled
deferred Mail authority. It does not become a generic queue or persistence
engine.

### A2 handoff reader/intake

Owns:

- PREPARE_INTAKE claim admission;
- per-consumer release-entry cursors;
- bounded release-entry enumeration;
- exact release reconstruction;
- CollectedSelection;
- held entry dispositions;
- immutable A2 intake worksets;
- historical supporting-context reads.

## 21. Implementation prerequisites

Before production handoff implementation is considered complete:

1. Mail discover must reject JOBDIR unless a full scope-bound resume contract is
   separately designed and qualified.
2. Mail full must reject JOBDIR unless a full scope-bound resume contract is
   separately designed and qualified.
3. Mail domain writes must expose advanced, current_equivalent, or stale
   handoff semantics rather than only observation-created/replay counters.
4. Mail and Calendar surface/component persistence must have explicit logical
   run provenance in the handoff facts; canonical evidence ownership cannot
   substitute for the current acquisition run.
5. Outlook Mail Full must have per-message release completeness.
6. Outlook Calendar Full must have per-event release completeness.
7. Authority promotion stores must atomically write release state.
8. A2 release intake must not use list_versions() as its incremental selector.
9. A2 must add a Calendar handoff/source adapter before claiming Calendar
   preparation support.
10. A1 must add a stable acquisition-ledger catalog identity and explicit
    release-group/release-entry sequence/digest contracts.
11. Release builders must publish bounded per-resource/transition entries under
    completion-scope groups so large snapshots/deltas are pageable by A2.
12. A2 Phase 1 persistence must implement an explicit neutral schema v3-to-v4
    migration for PREPARE_INTAKE claims, consumer cursors, immutable intake
    worksets, and pending-workset processing state.
13. The release-aware source reader must define stable exact source-version
    locators independent of release-entry sequence and must not reconstruct
    selections from mutable current tables.
14. A2 intake must durably represent held/unmaterializable entries before
    advancing their cursor range.
15. Non-authoritative release finalization must use a qualified natural-idle
    lifecycle boundary rather than spider_closed signal ordering.
16. Every provider/domain store that can advance downstream-visible state must
    stage its fact in that same transaction; post-pipeline fact insertion is not
    acceptable.
17. Each publishable resource/component family must define an A1
    source_state_key and exact source_version_locator so current-equivalent
    retry can recover unreleased advanced state without fabricating a new
    source version.
18. Non-authoritative release builders must revalidate source_state_key against
    current effective state in the release transaction so a delayed older run
    cannot publish after a newer concurrent run supersedes it.

19. A1 must maintain acquisition_effective_states transactionally with
    downstream-visible state advancement; the index is a freshness gate only
    and must never become A2 replay truth.
20. A2 cursor identity must use a stable consumer_id independent of ordinary
    configuration/code versions; version changes use explicit downstream
    replay/rerun semantics.
21. Cursor finalization must create durable pending-workset state in the same
    transaction so later preparation failure cannot orphan admitted work.

These are implementation tasks inside the frozen architecture, not alternate
architectures.

## 22. Acceptance requirements

### Ledger integrity

Tests must prove:

- domain write failure creates no successful fact/release;
- fact staging failure rolls back the state advancement it describes;
- no downstream-visible advanced state can commit without its staged fact;
- repeated exact staging is idempotent;
- HTTP-cache replay retains current logical run identity while referencing old
  canonical evidence;
- stale concurrent writes cannot create a newer primary release;
- a previously advanced fact that is superseded before its run completes does
  not create a later primary release entry;
- a current-equivalent retry releases a prior unreleased advanced state exactly
  once;
- an already released current-equivalent state does not create repetitive A2
  work;
- released facts, groups, and entries are immutable;
- one committed group can expose more entries than one A2 intake limit without
  requiring the group to be rereleased.

### Release correctness

Tests must prove:

- failed/incomplete traversal creates no traversal-scope release;
- configured Mail discovery truncation can release positive data only with
  explicit truncated coverage;
- clean Calendar window JOBDIR pause creates no window release;
- resumed Calendar window creates exactly one idempotent window release;
- one successful target in a multi-target Mail/Calendar Full run can release
  independently of another target failure;
- terminal Full-v1 limitations release only when the profile considers them
  complete;
- rules-enabled Mail delta creates no authority release before selected Full
  obligations pass;
- authority promotion and authority release roll back together.

### Provider-specific recovery

Tests must prove:

- Calendar 410 rebaseline releases only the winning attempt;
- OneDrive 410 resync releases only the winning materialized reset;
- stale Contacts snapshot/delta generation creates no winning release;
- incomplete To Do snapshot creates no authoritative absence release;
- Mail folder removal remains folder-scoped;
- Calendar removal remains fixed-window scoped.

### A2 intake

Tests must prove:

- historical A1 rows before the cursor are not newly admitted;
- two streams sharing a source ID advance independently;
- one large committed release group can be consumed over several bounded entry
  cuts without loss or duplication;
- a fixed release-entry cutoff excludes later concurrent entries;
- exact release reconstruction is unaffected by newer mutable A1 current state;
- evidence/selection materialization does not hold the final cursor write
  transaction open;
- workset save, pending-workset insertion, and cursor advance are atomic;
- crash before cursor commit safely replays the same entry range;
- crash/failure after cursor commit leaves a discoverable pending workset that
  can be retried without rewinding the A1 cursor;
- a materialization failure is durably held and cannot poison all later stream
  progress;
- cursor anchor mismatch after restore fails closed;
- historical context reads do not expand the primary workset.

### Framework lifecycle

Use real Scrapy lifecycle tests for:

- pipeline write/failure behavior;
- item concurrency;
- command/workflow completion;
- JOBDIR pause/resume;
- signal/close failures;
- cache replay.

Do not treat scrapy check alone as persistence evidence.

## 23. Evidence behind this design

The design was checked against the current A1 baseline and Scrapy 2.19.0.

The review included:

- all 17 installed Microsoft Spider entry points;
- all public Microsoft command dispatch paths;
- Mail/Calendar multi-phase workflows;
- rules-enabled deferred Mail promotion;
- Mail and Calendar Full-v1 profile semantics;
- To Do/Contacts snapshot promotion;
- Contacts delta generation ordering;
- OneDrive 410 staged resync;
- Calendar 410 fixed-window rebaseline;
- JOBDIR state and request serialization;
- HTTP-cache evidence canonicalization;
- current SavedSourceReader/CollectedSelection replay behavior.

Focused review suites covering those boundaries passed:

    138 passed
    29 passed

A scratch cache-replay probe additionally confirmed that a second logical Mail
run can reuse older canonical evidence without creating a second
message_observations row. A scratch JOBDIR probe confirmed that current Mail
discover/full do not preserve run_id across a reused JOBDIR.

Those probes are review evidence only and did not modify the repository.

## 24. Design exit criteria

This design is ready for implementation planning only when review agrees that:

- fact ledger + atomic release groups + sequenced release entries is the
  durable A1-to-A2 topology;
- completion granularity is semantic subject/scope while A2 consumption
  granularity is a bounded release entry, not universally command-level or
  run-level;
- authority release is transactionally coupled to provider authority promotion;
- A1 does not depend on A2 models;
- A2 owns cursors and immutable worksets;
- current provider tables are not handoff replay truth;
- all 17 current Spiders have an explicit release or non-release contract;
- the listed prerequisites are sufficient without redesigning existing Spider
  traversal.

Implementation should not begin by adding Kedro nodes. The first implementation
plan must start with the A1 ledger/release contract, its provider integration
matrix, and its failure/recovery tests.

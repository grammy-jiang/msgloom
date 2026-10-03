# A1 to A2 durable handoff contract design

## Status

**Status:** Draft for review.

**Design date:** 2026-10-03.

**A1 baseline:** 9e072eed17672f8380c709a9932ea56dbcbaff85.

This document defines the durable work-selection boundary between the completed
A1 Microsoft acquisition subsystem and the future A2/Kedro preparation
workflow. It is a design contract only. It does not authorize production code,
schema migration, A2 implementation, or scheduler changes.

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
2. A1 releases only facts covered by a proven semantic completion boundary.
3. A2 consumes only new immutable releases after its own durable consumer
   cursor.
4. A2 freezes exact source selections before parsing.
5. Historical A1 data remains available as explicit supporting context without
   becoming primary work merely because it exists in SQLite.

The normal scheduled shape is:

    A1 collection
        |
        v
    durable acquisition facts
        |
        v
    semantic release manifests
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

The smallest semantic unit for which A1 can independently prove that the
requested acquisition contract is complete enough for downstream use.

Examples:

- one Mail discovery traversal scope;
- one Mail message Full-v1 target;
- one Calendar fixed window;
- one Calendar event Full-v1 target;
- one To Do authoritative snapshot scope;
- one OneDrive content item;
- one Contacts custom-folder delta scope.

### Release manifest

An immutable record declaring that one release subject is downstream eligible
and naming the exact acquisition facts that establish that released state.

A release may reference facts from more than one logical run only when the
current operation explicitly revalidates those older facts as the exact state
being released.

### Stream

A durable acquisition family used for downstream cursors:

- outlook_mail;
- outlook_calendar;
- todo;
- onedrive;
- contacts.

Profile output is operational output, not an A2 stream.

### A2 consumer cursor

A2-owned durable progress for one A1 catalog, source_id, stream, consumer
combination.

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

### H5. Authority cannot advance without recoverable downstream publication

When A1 advances an authoritative checkpoint, presence generation, or fixed
window state, the corresponding release/authority publication state must commit
in the same SQLite transaction.

A crash may not leave provider authority advanced with no recoverable
downstream release.

### H6. Positive observations and authority claims have different gates

A provider observation is not the same claim as authoritative absence,
membership reconciliation, or checkpoint advancement.

Derived absence and winning state transitions are publishable only at the
existing authority promotion boundary.

### H7. Canonical evidence provenance is independent of logical-run identity

HTTP-cache replay may make a current-run semantic item reference evidence
originally captured in an older run.

The contract must preserve both the logical acquisition run_id and the exact
canonical evidence_id.

It must not globally require evidence.run_id to equal run_id.

### H8. Provider time is not publication order

observed_at is provider/evidence provenance, not a downstream watermark.

Release order uses a local monotonic release sequence.

### H9. Release order is not provider semantic chronology

Concurrent runs can finish in a different order from provider freshness.

A release sequence orders durable admission. It does not replace provider
versions, CAS revisions, delta ordinals, page/entry ordering, or source times.

### H10. Stale writes cannot become newer primary state

Domain persistence must expose whether a fact advanced current state, was
current-equivalent/replayed, or was stale.

A stale fact remains audit/history data but cannot create a release claiming a
new effective primary source state.

### H11. Mutable current projections cannot reconstruct an old release

Every release must name immutable acquisition facts sufficient for A2 to
reconstruct the exact released source/component state without consulting future
mutable current rows.

### H12. A1 does not serialize CollectedSelection

CollectedSelection remains an A2-side snapshot. A1 stores provider-neutral
handoff provenance only.

### H13. Scoped removal stays scoped

Examples:

- Mail message removed from Folder F is not mailbox deletion.
- Calendar event removed from one fixed window is not global event deletion.
- snapshot-derived absence applies only to the exact authoritative source/scope.

The scope is part of the released transition identity.

### H14. Downstream progress is consumer-owned

A2 advances its cursor only in the same A2 transaction that durably saves the
immutable workset and exact inputs selected by that cursor advance.

### H15. No silent backup/restore skip

A2 must verify an anchor for its prior cursor. A restored or replaced A1
catalog that no longer contains the same cursor anchor fails closed and
requires explicit recovery/baseline selection.

## 4. Why the rejected batch models fail

| Candidate | Result | Counterexample |
| --- | --- | --- |
| One public command = one handoff | rejected | Mail/Calendar sync run several crawlers; JOBDIR can resume one logical run in a later command |
| One run_id = one handoff | rejected | Full can target many resources; one target may complete while another fails |
| VersionRef list alone | rejected | derived absence, scoped removals, and component enrichment are not just new object versions |
| A1 writes CollectedSelection | rejected | reverses the existing A1/A2 dependency boundary |
| A2 scans provider tables by run_id | rejected | HTTP-cache canonicalization can produce a current run with no new observation row |
| raw journal row = immediately consumable | rejected | staged/losing/authority-pending facts must remain hidden until the correct semantic unit is eligible |
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
             Release-unit completion gate
                    /           \
             incomplete        complete
                 |                |
                 v                v
          staged only      Release manifest
                                  |
                       =======================
                                  |
                                  v
                              A2 intake
                                  |
                                  v
                        bounded release cut
                                  |
                                  v
                       exact reconstruction
                                  |
                                  v
                     immutable A2 workset
                                  |
                                  v
                                Kedro

For ordinary item persistence, facts and domain writes share the same
transaction where practical. A semantic release is a separate operation when
the release subject requires several facts or an end-of-scope proof.

For authoritative promotions, authority mutation and its release state share
one transaction.

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
    stale

advanced means the write became the effective stored state for that
domain/resource/component.

current_equivalent means the acquisition is valid and exact but does not
advance semantic current state. Cache replay and idempotent re-observation can
produce this relation.

stale means a newer state already wins. A stale fact is retained but cannot
create a release claiming a newer effective primary source state.

Provider-specific stores may retain richer internal outcomes, but they must map
to these handoff semantics.

### 6.5 Privacy and payload limits

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

### 7.1 Release granularity

A release is not universally run-scoped.

The release unit is the smallest semantic subject with an independently
provable completion contract.

This is required for multi-target Full/content spiders: one target must not be
held forever merely because another target in the same Spider run fails.

### 7.2 Release identity

A release requires these semantics:

    release_id
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
    release_digest

release_id is a monotonically increasing local publication sequence. It is an
admission order, not a provider timestamp.

release_digest canonically binds the release identity and member facts. It is
used as a cursor anchor and corruption/restore check.

### 7.3 Release members

A release manifest names its exact immutable fact IDs.

Conceptually:

    acquisition_release_facts
        release_id
        ordinal
        fact_id
        role

A release can reference facts from an earlier run only when the release owner
revalidates those facts as the exact state that satisfies the current release
contract. This supports idempotent retry/adoption without reading future
mutable state.

### 7.4 Release kinds

The initial release families are:

    resource_set
    resource_profile
    authority_scope
    content_capture
    context_inventory

resource_profile is appropriate for Mail/Calendar Full-v1.

authority_scope is appropriate for snapshot/delta promotions.

content_capture is appropriate for explicit OneDrive content.

### 7.5 Release eligibility versus run outcome

A run may have no releases, one release, or several releases.

Subject-level completion status and declared terminal limitations are stored on
the release subject/manifest, not collapsed into one run-wide completion flag.

A failed multi-target Full run may still contain a target whose profile was
independently proven terminal-complete. That target can receive its own
release.

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
    write authority release manifest referencing exact staged/winning facts
    mark candidate committed

    COMMIT

Observation facts that were already staged earlier in the crawl are referenced,
not copied. Transition facts that exist only because promotion established a
new authority state are created in the promotion transaction.

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

Per-subject semantic completion belongs to the release subject/manifest. One
Mail Full run can therefore be failed overall while Message A has
terminal-complete Full-v1 and Message B remains incomplete.

For a single-scope authority run, the run outcome may additionally state that
the authority promotion committed, but the release manifest remains the
downstream contract.

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

Per-message Full releases are independent release subjects. The existing
rules workflow may continue to use its all-selected-target completion validator
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

A current-equivalent observation can still be required for handoff recovery.

Example:

1. Run A writes a provider state but fails before release.
2. Run B retries the same provider state.
3. Domain persistence reports current-equivalent.
4. Run B successfully proves its release unit.
5. Run B can release the exact equivalent source facts.

This prevents failed earlier work from making a later successful acquisition
invisible.

### 14.3 Release sequence

release_id orders committed release manifests.

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
    consumer kind/version

At minimum Mail and Calendar must not share one downstream cursor merely because
they share an Outlook source ID.

### 15.2 Bounded cut

For one source/stream, A2 chooses a finite release range after its prior cursor:

    (last_release_id, cutoff_release_id]

The range is fixed before downstream parsing begins.

New A1 releases after the cutoff wait for the next intake.

### 15.3 Immutable workset

Within one A2 transaction:

1. validate the prior cursor anchor;
2. read the bounded release manifests;
3. resolve their exact release facts;
4. map eligible source releases to exact A2-side source selections;
5. save CollectedSelection snapshots and transition inputs;
6. save the immutable A2 workset;
7. advance the consumer cursor to the accepted cutoff;
8. commit.

Only after that transaction may Kedro start processing the workset.

### 15.4 Existing SavedSourceReader

The current reader remains useful evidence for the exact-selection design:

- explicit VersionRef;
- exact evidence loading;
- CollectedSelection;
- replay after mutable current surfaces change.

However, list_versions() is not the scheduled handoff API.

The A2 handoff reader must enumerate releases, not the historical source tables.

It must also gain Calendar support before Calendar releases become
A2-processable.

### 15.5 State-transition inputs

Not every release is a CollectedSelection.

A2 intake must also preserve typed scoped transitions such as:

- authoritative task/contact absence;
- Mail mailbox presence transition;
- Mail folder removal;
- Calendar fixed-window membership removal;
- OneDrive deletion/resync absence.

A2 policy may decide whether a transition triggers preparation, retirement,
reconciliation, or context refresh. A1 only supplies the exact scoped fact.

### 15.6 Historical context

A2 primary work comes only from the selected release range.

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

Create the ledger and start A2 from its genesis release cursor. Existing
historical A1 rows remain context/replay data but are not automatically admitted
as new work.

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

    last_release_id
    last_release_digest
    A1 catalog identity

Before advancing from a nonzero cursor, A2 verifies that the referenced release
still exists and has the same digest.

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

A candidate shape is:

    acquisition_facts
    acquisition_releases
    acquisition_release_facts
    acquisition_run_outcomes
    acquisition_ledger_metadata

The exact DDL, indexes, uniqueness constraints, and canonical digest format are
implementation-plan work.

The schema must support:

- append-only immutable released facts/manifests;
- idempotent fact staging;
- idempotent release creation;
- bounded lookup by source_id, stream, and release_id;
- lookup of unreleased facts by logical run/release subject;
- transactional inserts from provider stores/promotions;
- no arbitrary provider payload duplication.

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
- staging exact acquisition facts beside the domain write.

Where one semantic item currently requires several independent store
transactions, implementation may consolidate the transaction or stage enough
durable facts to make release recovery exact.

### Existing authority stores/extensions

Own the existing correctness proof and provider promotion.

They must be extended so authority release creation is inside the same
transaction as the promotion.

### Command/workflow coordinator

Owns only release gates that genuinely require post-crawler workflow knowledge,
for example rules-enabled deferred Mail authority or per-target workflow
completion validation.

It does not become a generic queue or persistence engine.

### A2 handoff reader/intake

Owns:

- per-consumer cursors;
- release enumeration;
- exact release reconstruction;
- CollectedSelection;
- immutable A2 worksets;
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

These are implementation tasks inside the frozen architecture, not alternate
architectures.

## 22. Acceptance requirements

### Ledger integrity

Tests must prove:

- domain write failure creates no successful fact/release;
- fact staging failure fails the owning persistence operation;
- repeated exact staging is idempotent;
- HTTP-cache replay retains current logical run identity while referencing old
  canonical evidence;
- stale concurrent writes cannot create a newer primary release;
- released facts are immutable.

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
- a fixed release cutoff excludes later concurrent releases;
- exact release reconstruction is unaffected by newer mutable A1 current state;
- workset save and cursor advance are atomic;
- crash before cursor commit safely replays the same release range;
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

- fact ledger + release manifest is the durable A1-to-A2 topology;
- release granularity is semantic-subject/scope completion, not universally
  command-level or run-level;
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

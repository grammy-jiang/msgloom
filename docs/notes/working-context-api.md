# Working-context capture API

**Scope:** immutable capture of explicitly selected local memory files only.

This lane owns msgloom.working_context. It does not discover memory, expose a
filesystem tool to AI, change interactive Claude/ChatGPT state, create
persistence schema, or launch AI.

## Configuration and selection

WorkingContextConfig is frozen, strict, and closed to unknown fields. The
caller supplies exact MemoryFileSelection values and explicit allowed_roots.
Selected paths must be absolute, traversal-free, unique, and lexically inside
an allowed root. An empty selected_files tuple means no memory was selected;
it is distinct from a selected empty file and from failed capture.

The configuration also fixes:

- IANA CaptureTimePolicy.timezone;
- StalePolicy.CAPTURE or StalePolicy.OMIT;
- stale age and future timestamp tolerance;
- maximum selected file count;
- per-file and total captured byte bounds; and
- maximum elapsed capture time.

capture(config, capture_time) revalidates the complete configuration before
filesystem work, including nested values that could have been created through
validation-bypass APIs. Boundary failures use a fixed opaque error rather than
Pydantic values or filesystem exception text. Numeric time bounds must be
finite. The function requires an aware capture_time whose timezone matches the
configured policy; the capture time is never inferred from the machine clock.

Stale and future decisions compare POSIX instants, not same-ZoneInfo wall-time
subtraction. This preserves actual elapsed seconds across daylight-saving folds
and jumps while retaining the caller's declared IANA timezone and local
timestamps in the snapshot.

No recursive home/session discovery, URI fetch, source credential read, or
arbitrary path lookup exists in this API.

## Filesystem and worker ownership

Capture uses one awaited file worker for the complete selection. For every
allowed root, the worker starts from the trusted filesystem root descriptor and
opens every absolute root component descriptor-relatively with O_NOFOLLOW. It
then walks selection-relative components the same way, opens the final object
without following a link, and verifies that descriptor is a regular file.
Thus a symlink in an allowed-root ancestor is rejected rather than trusted.
Replacing an already opened ancestor or final path cannot redirect its owned
descriptor. Directories, devices, FIFOs, and symlink escapes are rejected.

Actual reads are bounded. The reader requests at most the remaining per-file
and total budget plus one byte used only to detect overflow. It checks the
elapsed deadline between bounded chunks. A kernel-level regular-file read is
not forcibly interrupted mid-system-call. Metadata is checked before and after
the read; changed inode metadata causes the bytes to be discarded.

Opened-file fstat and read OSError outcomes become a fixed per-file unreadable
state; exception text is not exposed, the descriptor is closed, and later
selections continue. Cancellation does not abandon accepted worker work. The
coroutine shields and drains the owned worker through repeated cancellation,
closes descriptors in the worker, and only then re-raises CancelledError. Thus
no accepted capture continues after capture() returns, including when the
drained read finishes with an OSError.

The capture itself is read-only. Tests may mutate synthetic fixtures to prove
race handling, but production capture never writes source memory or settings.

## Snapshot states and integrity

Each selected file produces one CapturedMemoryFile. Visible states include
captured, empty, missing, stale, future timestamp, unreadable,
changed-during-read, malformed UTF-8, limit exceeded, unsafe path, non-regular
file, and timeout. An unavailable file has no text or content digest. A
selected empty file has exact empty text, a zero byte count, and an exact
content digest/reference.

Stale content is retained only under StalePolicy.CAPTURE; OMIT retains
metadata/state but no text. Future timestamps remain visible while their bytes
are captured if otherwise valid. UTF-8 decoding is strict. Content changed
during the read, malformed encoding, or overflow is never accepted as text.

Opaque limitations use fixed privacy-safe descriptions and never interpolate
absolute paths or exception text. Exact selected paths remain in the private
typed configuration/snapshot because replay requires them.

configuration_ref(config) hashes canonical meaning-bearing configuration,
including exact selections, roots, timezone/stale policy, and bounds. A
snapshot records that configuration reference, exact capture time/timezone,
ordered per-file outcomes, timestamps, content digests/references, exact
bounded text, and limitations. snapshot_sha256 hashes all of those snapshot
fields except itself. snapshot_ref(snapshot) returns the corresponding
VersionRef.

Capture time is deliberately meaning-bearing. Repeating capture at a different
time creates a different snapshot version even when file bytes are unchanged.
It may also cross a stale/future boundary and change a file state or whether
stale text is retained. Exact replay with the same configuration, capture time,
file metadata, and bytes produces the same snapshot/version.

## Persistence and AI-consumer handoff

WorkingContextCodec is a canonical, size-bounded validating semantic codec
with kind working_context and schema_version 1. Encoding revalidates complete
model semantics rather than trusting an existing Pydantic instance or its
integrity hash. CAPTURED/EMPTY content requirements, selected identity/path
uniqueness, selection-reference binding to the configuration version, declared
timezone consistency, and content references are checked on encode and decode.
The codec does not query persistence to reconstruct configuration authority.

The default Phase 1 registries register working_context@1 as a result schema
that requires semantic data. SemanticDataRegistry composes this codec with
the reviewed preparation codecs. Capture does not mutate either registry.

The later handler sequence is:

1. build and validate WorkingContextConfig from trusted application
   configuration;
2. supply the explicit aware capture time and await capture();
3. build the semantic integrity reference through the composed persistence
   registry;
4. create a working_context@1 stage result whose semantic reference points to
   this exact snapshot;
5. await the atomic semantic-data/result persistence call;
6. reload/validate the saved reference when required by the handler; and only
   then
7. launch semantic AI with the saved prepared inputs and saved working-context
   reference.

The triage stage's working_context_version should use snapshot_ref(snapshot),
binding the assessment to the exact capture. A failure, cancellation, or
unavailable selected file remains visible rather than becoming empty memory.

Paths are replay metadata, not an instruction to give the AI filesystem
access. The AI consumer should receive only the declared saved semantic input
needed by its prompt contract. It must not receive a general local-file tool,
source credentials, interactive session storage, or permission to discover
additional memory. Persistence remains the existing manager-owned Phase 1
SQLAlchemy/SQLite boundary; this package adds no database or handler.

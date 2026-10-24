# A2 v2 independent golden corpus

This corpus is the oracle for tasks T0-01, T0-02, T0-03,
T0-04, T0-05, T0-06, T0-07, T0-08, T0-09 and T0-10 of the A2 Kedro v2 programme. It
lives in `tests/a2_kedro/golden/`. The execution manifest names `tests/a2_kedro/gold/`.
The supervisor changed the path to `golden/`.

## Coverage

| File | Topic | Positive | Negative |
| --- | --- | --- | --- |
| `t0_01.json` | A1 fixed behavior: 20 Spiders, 7 streams, Task 15 rules | 6 | 5 |
| `t0_02.json` | Mail multi-MIME, inline quote, duplicate Message-ID, transfer encodings, nested message, truncated multipart | 9 | 8 |
| `t0_03.json` | Teams chat, channel, component-only, scope refresh, edited and deleted messages, truncated record | 8 | 9 |
| `t0_04.json` | Calendar (cancelled, all-day, recurrence, removed marker), To Do, OneDrive, Contacts stay contextual | 8 | 7 |
| `t0_05.json` | PDF, Word, Excel, malformed, large, partial | 7 | 7 |
| `t0_06.json` | Held, intake-held, transition-only: one terminal per item | 11 | 20 |
| `t0_07.json` | Crash, restart, late write, cancel: accepted prefix, replay | 10 | 7 |
| `t0_08.json` | Historical prepared@1 reader, prepared@2 mapping, no lossy projection | 13 | 38 |
| `t0_09.json` | Prefect lost, duplicate hint, partial A1 finish | 6 | 8 |
| `t0_10.json` | Node.run logger, PII canary, telemetry, illegal paths, token and URL redaction, loopback allowance, network observable | 7 | 17 |

Cases T0-02-P06 to P09, N07, N08, T0-03-P06 to P08, N07 to N09 and
T0-04-P06 to P08, N06, N07 were added after the T0-11 review (finding M2).
A language model wrote them by hand from the cited A1 notes. No program
produced any value. Six of them carry a `policy_status` marker because the
A1 text is silent.

Cases T0-10-P06, P07 and N14 to N17 were added after the T0-11 review
(finding M3). A language model wrote them by hand. All six carry a
`policy_status` marker. N14 and N15 use the fake canaries `FAKE-TOKEN-0000`
and `FAKE-TOKEN-0001`. T0-10-P07 states how a consuming test observes "0
outbound connections, 0 DNS lookups": recording guards on
`socket.create_connection`, `socket.getaddrinfo` and `socket.socket.connect`,
installed before the run, with a self-check call before the run.

## Independence rules

1. A language model (a Claude Sonnet 5.5 worker) annotated each expected
   value by hand-reading the A2 blueprint and the accepted A1 notes and
   fixtures. No program may generate an expected value. One disclosed
   exception exists: the pinned digests (SHA-256 and byte count) in
   T0-08-P01 and T0-08-P02 were computed with `json` and `hashlib` from the
   base payload in the file and compared with the A1 v1 codec output. No human
   has reviewed the corpus. The 35 cases that carry a `policy_status` marker
   need owner sign-off (see `a2-v2-golden-decisions.md`). Do not describe the
   corpus as human-annotated or human-reviewed.
2. The author reads only A1 code names, A1 docs, the A1 spec and A1 tests. The
   `provenance.sources` field of each file lists what was read.
3. Nobody runs or imports `msgloom.a2_kedro` or other A2 code to get an
   expected value. A reviewer must reject a case that looks copied from output.
4. A2 authors must not change an expected value to make a test pass. A change
   needs a new reviewer and a new line in the manifest.
5. A2 authors must not rewrite A1 acceptance rules. T0-01 fixes those rules.
6. All data is synthetic. Hosts must be reserved names from RFC 2606 and
   RFC 6761: `example.com`, `example.net`, `example.org` (and subdomains), or a
   name that ends in `.example`, `.invalid`, `.test` or `.localhost`. The
   corpus uses `example.invalid` and `example.test`. The test rejects any other
   host, such as `foo.internal`. It exempts only an exact allowlist of file
   names (`NON_HOST_TOKENS`), never a file suffix, and never after `//` or `@`.
   The canary string `CANARY-PII-7731-ZQ` marks data that must never reach a
   log, a status record or a stored artifact.

## File format

Each file has `schema`, `task_id`, `title`, `annotator`,
`independence_statement`, `provenance` and `cases`. Each case has `case_id`,
`polarity` (`positive` or `negative`), `title`, `input` and `expected`.
Some cases add `rationale`. A positive case shows required behavior. A
negative case shows behavior that must not happen, or a trap.

T0-05 uses these status words: `complete`, `partial`, `unsupported`, `failed`.
A parse error must never give `complete`. The words map to A1 behavior so:

| Oracle status | A1 behavior |
| --- | --- |
| `failed` | The parser raises (for PDF: `PdfParseError`) or the boundary rejects the input before extraction. Cases: encrypted PDF, malformed PDF or DOCX, wrong detected format, ZIP byte limit, PDF output limit, worker crash. |
| `unsupported` | The parser returns output whose only content is an unsupported limitation for the whole input. Case: legacy `.doc`. |
| `partial` | The parser returns output with a content-loss limitation (scanned, partial, unsupported part). Other content may remain. |
| `complete` | The parser returns content with no content-loss limitation. |

Disclosure-only limitations that every successful parse carries do not count
as content loss. Examples are the PDF reading-order, layout and table notes
and the Word `word-feature-coverage` limitation. Complete cases therefore use
the field `content_loss_limitations`. Sources: `parser-pdf.md` ("Lifecycle
and failures"), `parser-word.md`, `parser-excel.md`.

### Field names `content_loss_limitations` and `limitations`

Both fields exist only in `t0_05.json`. Both hold the expected set of
content-loss limitation kinds. They differ in name for this reason:

- `content_loss_limitations` appears in `complete` cases. The value is `[]`.
  The name tells the reader that only content-loss limitations must be absent.
  Disclosure-only limitations may still be present in a `complete` result.
- `limitations` appears in `partial` and `unsupported` cases. The value lists
  the content-loss kinds that must be present, for example `["scanned"]`.
  Disclosure-only limitations are not listed there.

A consuming test must treat both names as the same set: the content-loss
subset of the reported limitations. It must compare that subset only, and
ignore disclosure-only limitations. The names stay different so that the
manifest digest and the reviewed text of `t0_05.json` do not change. Merging
them is a safe future change if the corpus has no other consumer. It needs a
reviewer and a new manifest line.

## Decisions that are not from A1

`a2-v2-golden-decisions.md` is the authoritative list. It gives the status
and the `policy_status` marker of each case. The summary below is older text.

These expected values are not derived from A1 docs. Each needs owner sign-off.
The cases name the status in their provenance or rationale.

- **T0-10 Dataset paths (PROPOSED POLICY).** No cited A1 or master document
  defines a Dataset path rule. The accept and reject verdicts and the reason
  words in P01, P05 and N01 to N10 are the plain security answer. Each of
  those cases carries a `provenance` field that says so. A2 authors must not
  cite them as A1 requirements.
- **T0-09 N08 (PROPOSED POLICY).** The handoff spec (H6, H18) does not say how
  A2 reacts when A1 authority advanced with no release. N04 fixes only what
  the rules decide: no work, no cursor move, no invented release. N08 proposes
  a visible failure.
- **T0-04 Calendar (task-goal decision).** `preparation-semantics.md` names
  only To Do, OneDrive and Contacts as contextual inputs. The handoff spec
  leaves Calendar's final A2 role open. T0-04 P04, P05 and N03 treat Calendar
  as contextual with a one-member None group because the task goal says so.
- **T0-02 reply text split (A2-level).** The contributed text and quoted text
  split and the oldest-first ancestor order are task-level annotations. The
  cited A1 docs do not define them.
- **T0-02 P01.** This case follows A1 only. `parser-mime-html.md` says MIME
  alternatives are extracted independently and that equivalence is not
  inferred. The case does not count the HTML alternative as the same
  contribution. How A2 merges the two texts is open.

## Integrity

`MANIFEST.sha256` lists a SHA-256 digest for each `t0_*.json` file. It uses the
`sha256sum` format. A reviewer updates it after a reviewed change:

    cd tests/a2_kedro/golden && sha256sum t0_*.json > MANIFEST.sha256

`tests/a2_kedro/test_gold_corpus.py` checks structure and the manifest only. It
checks strict JSON (duplicate keys fail), required fields, unique case IDs,
both polarities per file, positive cases before negative cases, non-empty
provenance and independence text, and reserved synthetic hosts only. It also
rejects token-like strings (bearer values, secret query parameters, JSON Web
Tokens, GUIDs, long opaque runs) unless they are on an exact allowlist of
fake canaries (`CANARY-PII-7731-ZQ`, `FAKE-TOKEN-0000`, `FAKE-TOKEN-0001`)
or the three pinned T0-08 digests. It does not check behavior.

## How implementation tests consume the oracle

Future A2 tests load a golden file with the strict loader. They run the A2
code on each `input`. They compare the result with `expected`. Rules:

- Compare only the fields present in `expected`. Extra output fields are fine.
- Read `input` descriptions of documents as a recipe for a synthetic builder.
  The builder lives in the implementation test, not in the corpus.
- Treat `<tmp>` in T0-10 as the pytest `tmp_path`. Create the symlink case in
  that directory. Skip no case silently.
- Run every `negative` case. A negative case passes when the forbidden
  behavior is absent.
- Keep the manifest test in CI so an unreviewed edit fails.

## Limits

The expected values are a language model's hand reading of written A1 rules
and the A2 blueprint. No human has reviewed them. They are not proof of live
provider behavior. Some terms in T0-05 and T0-10 (for example the
reason words) are oracle vocabulary. The implementation may map them to its own
enum names in the consuming test.

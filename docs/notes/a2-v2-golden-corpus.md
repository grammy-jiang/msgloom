# A2 v2 independent golden corpus

This corpus is the hand-annotated oracle for tasks T0-01, T0-02, T0-03,
T0-04, T0-05, T0-09 and T0-10 of the A2 Kedro v2 programme. It lives in
`tests/a2_kedro/golden/`. The execution manifest names `tests/a2_kedro/gold/`.
The supervisor changed the path to `golden/`.

## Coverage

| File | Topic | Positive | Negative |
| --- | --- | --- | --- |
| `t0_01.json` | A1 fixed behavior: 20 Spiders, 7 streams, Task 15 rules | 6 | 5 |
| `t0_02.json` | Mail multi-MIME, inline quote, duplicate Message-ID | 5 | 6 |
| `t0_03.json` | Teams chat, channel, component-only, scope refresh | 5 | 6 |
| `t0_04.json` | Calendar, To Do, OneDrive, Contacts stay contextual | 5 | 5 |
| `t0_05.json` | PDF, Word, Excel, malformed, large, partial | 7 | 7 |
| `t0_09.json` | Prefect lost, duplicate hint, partial A1 finish | 6 | 7 |
| `t0_10.json` | Node.run logger, PII canary, telemetry, illegal paths | 5 | 13 |

T0-06, T0-07 and T0-08 are outside this corpus. They depend on contract tasks.

## Independence rules

1. A person writes each expected value by hand. No program may generate it.
2. The author reads only A1 code names, A1 docs, the A1 spec and A1 tests. The
   `provenance.sources` field of each file lists what was read.
3. Nobody runs or imports `msgloom.a2_kedro` or other A2 code to get an
   expected value. A reviewer must reject a case that looks copied from output.
4. A2 authors must not change an expected value to make a test pass. A change
   needs a new reviewer and a new line in the manifest.
5. A2 authors must not rewrite A1 acceptance rules. T0-01 fixes those rules.
6. All data is synthetic. Domains end in `example.invalid` or `example.test`.
   The canary string `CANARY-PII-7731-ZQ` marks data that must never reach a
   log, a status record or a stored artifact.

## File format

Each file has `schema`, `task_id`, `title`, `annotator`,
`independence_statement`, `provenance` and `cases`. Each case has `case_id`,
`polarity` (`positive` or `negative`), `title`, `input` and `expected`.
Some cases add `rationale`. A positive case shows required behavior. A
negative case shows behavior that must not happen, or a trap.

T0-05 uses these status words: `complete`, `partial`, `unsupported`, `failed`.
A parse error must never give `complete`.

## Integrity

`MANIFEST.sha256` lists a SHA-256 digest for each `t0_*.json` file. It uses the
`sha256sum` format. A human updates it after a reviewed change:

    cd tests/a2_kedro/golden && sha256sum t0_*.json > MANIFEST.sha256

`tests/a2_kedro/test_gold_corpus.py` checks structure and the manifest only. It
checks strict JSON (duplicate keys fail), required fields, unique case IDs,
both polarities per file, non-empty provenance and independence text, and
synthetic domains. It does not check behavior.

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

The expected values are a human reading of written A1 rules. They are not
proof of live provider behavior. Some terms in T0-05 and T0-10 (for example the
reason words) are oracle vocabulary. The implementation may map them to its own
enum names in the consuming test.

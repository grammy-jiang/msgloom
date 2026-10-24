# A2 v2 golden oracle T0-08: the historical reader keeps prepared@1 and maps prepared@2

This note describes `tests/a2_kedro/golden/t0_08.json`. The oracle covers the
rule "an old prepared@1 stays readable and a new prepared@2 maps correctly".
A person wrote every expected decision by hand from the A2 Kedro v2
blueprint, the frozen v1 contract and the A1 fixtures. No A2 v2 code produced
any value.

The execution manifest names `tests/a2_kedro/gold/t0_08.json`. The file lives
in `golden/`, as in decision 5 of `a2-v2-golden-decisions.md`.

## Model

Each case has a stored record and one operation.

| Part | Meaning |
| --- | --- |
| Stored record | A label (`kind`, `schema_version`) and a payload. The payload is a named base plus ordered edits (`set`, `delete`, `copy`). |
| `read` | The reader routes by the exact label. `prepared` with `1` uses the historical v1 reader. `prepared` with `2` uses the v2 reader. Any other label gives `unknown_version`. |
| `force_v1_codec` | The v1 codec reads the payload, whatever the label says. |
| `project_to_v1` | Ask for a v1 record made from a v2 record. |
| `bind_triage_input` | Bind the record ref into `triage_input@1` or `triage_input@2`. |

An accepted read has a view: the exact text, the ordered limitation codes,
the preserved, dropped and invented field names, and the A3 line. A rejected
case has one reason code. The vocabulary is in the `model` object of the
file.

## Rules used

| Rule | Source |
| --- | --- |
| The allowlist is closed over `(prepared, 1)` and `(prepared, 2)`. Labels compare as exact JSON values. | Blueprint 4.1; plan C0-12a, C0-17b |
| A v1 record is read as before. Nothing is migrated, re-encoded or upgraded. The reader adds no v2 field. | Blueprint 4.1 |
| The v1 model has 14 required fields, extra fields are forbidden, and the codec rejects bytes that are not canonical. | v1 contract (records and codec modules) |
| A prepared@2 record cannot be decoded by the v1 codec. A v2 label does not upgrade a v1 payload. | Blueprint 2, 8.1 |
| The reader never drops zones, relations, lineage, attachments or limitations. | Blueprint 4, 8.1 |
| Any limitation, at record, attachment or parsed content level, gives INCOMPLETE. COMPLETE has none. | Blueprint 4.2 |
| A projection from v2 to v1 is not allowed by default, even when the record looks simple. | Blueprint 8.1; plan C0-17c |
| triage_input@1 takes refs of version 1. triage_input@2 takes refs of version 2. | v1 A3 codec; blueprint 8.1 |

## Cases

| Case | Topic | Title |
| --- | --- | --- |
| T0-08-P01 | historical_v1 | A full old prepared@1 record is read unchanged by the historical reader |
| T0-08-P02 | historical_v1 | A prepared@1 record with old fields only (chat, no attachment, no parsed content) stays readable |
| T0-08-P03 | historical_v1 | An old To Do record with an excluded filtering decision and a rule ref keeps that decision |
| T0-08-P04 | limitations | An old record keeps an attachment limitation after the record limitation, in stored order |
| T0-08-P05 | historical_v1 | Subject and body text come back exactly as stored (spaces, tab, non-ASCII, empty text) |
| T0-08-P06 | historical_unchanged | The v1 codec still decodes the same v1 bytes to the same view after the v2 reader exists |
| T0-08-P07 | v2_mapping | A minimal prepared@2 record maps to a COMPLETE v2 view on the triage_input@2 line |
| T0-08-P08 | limitations | A full prepared@2 record keeps every limitation in order, without sort or merge, and every zone and relation |
| T0-08-P09 | v2_mapping | Role, selection ordinal, an unknown zone and an unknown relation are kept, not guessed |
| T0-08-P10 | limitations | A limitation that only an attachment reports still keeps the record INCOMPLETE and visible |
| T0-08-P11 | limitations | A limitation that only the parsed content reports still keeps the record INCOMPLETE and visible |
| T0-08-P12 | binding | A prepared@1 ref binds into the historical triage_input@1 line |
| T0-08-P13 | binding | A prepared@2 ref binds into the new triage_input@2 line |
| T0-08-N01 | version_rejection | A future version 3 label is rejected even when the payload looks like prepared@2 |
| T0-08-N02 | version_rejection | Version 0 is rejected even when the payload looks like prepared@1 |
| T0-08-N03 | version_rejection | The label 02 is rejected; versions are exact strings |
| T0-08-N04 | version_rejection | The JSON number 2 is rejected; the version is a string |
| T0-08-N05 | version_rejection | The kind Prepared with a capital letter is rejected |
| T0-08-N06 | version_rejection | A null version is rejected |
| T0-08-N07 | version_rejection | A filter_result@2 label is not read by the prepared reader |
| T0-08-N08 | tamper | A prepared@2 payload forced through the v1 codec is rejected |
| T0-08-N09 | tamper | An old v1 payload relabeled prepared@2 is not accepted as a v2 record |
| T0-08-N10 | tamper | A v2 payload labeled prepared@1 is rejected, not read with the new fields ignored |
| T0-08-N11 | tamper | A prepared@1 record with one added v2 field (zones) is rejected |
| T0-08-N12 | missing_field | A prepared@1 record without its body key is rejected |
| T0-08-N13 | tamper | A prepared@1 record that omits a defaulted key (display_name) is not canonical |
| T0-08-N14 | tamper | A prepared@1 source time without a time zone is rejected |
| T0-08-N15 | tamper | A prepared@1 record with an unknown source type is rejected |
| T0-08-N16 | tamper | A pending filtering decision that names a rule is rejected |
| T0-08-N17 | tamper | An attachment whose parsed content ref is not in parsed_contents is rejected |
| T0-08-N18 | tamper | Two parsed contents with the same reference are rejected |
| T0-08-N19 | tamper | A source mapping range that is not increasing is rejected |
| T0-08-N20 | tamper | A sender with a blank identity is rejected |
| T0-08-N21 | tamper | A limitation with an empty code is rejected |
| T0-08-N22 | missing_field | A prepared@2 record without lineage is rejected |
| T0-08-N23 | missing_field | A prepared@2 record without selection is rejected |
| T0-08-N24 | limitations | A record that says COMPLETE while an attachment reports a limitation is rejected |
| T0-08-N25 | limitations | A record that says INCOMPLETE without any limitation is rejected |
| T0-08-N26 | tamper | A lineage ref that names zones@2 instead of zones@1 is rejected |
| T0-08-N27 | tamper | A zone kind outside the closed set is rejected |
| T0-08-N28 | tamper | A zone that ends after the body is rejected |
| T0-08-N29 | tamper | A quote zone that carries an author attribution is rejected |
| T0-08-N30 | tamper | A role outside primary, component, context and transition is rejected |
| T0-08-N31 | tamper | A negative selection ordinal is rejected |
| T0-08-N32 | tamper | A v2 limitation with an empty detail is rejected |
| T0-08-N33 | missing_field | A lineage block that lacks the zones stage ref is rejected |
| T0-08-N34 | lossy_projection | A full prepared@2 record is never projected to a prepared@1 record |
| T0-08-N35 | lossy_projection | A prepared@2 record with no zone, relation or limitation worth keeping is still not projected |
| T0-08-N36 | binding | A prepared@2 ref cannot enter the historical triage_input@1 line |
| T0-08-N37 | binding | A prepared@1 ref does not enter the new triage_input@2 line |
| T0-08-N38 | version_rejection | A future version 3 ref is rejected by the bind operation before the line is compared |

## Pinned digests

P01 and P02 pin the SHA-256 and the byte count of the canonical JSON of the
two v1 bases. This pins the historical bytes. The author computed the digests
with the standard `json` and `hashlib` modules from the base in the file. The
author then compared them once with the output of the v1 codec. The author
also decoded every v1 case with the real v1 codec to check that accept and
reject agree. All agree, except N37, where the v1 codec accepts the record
and the rejection comes from the A3 line (`triage_input@2`). No A2 v2 code
was used.

## Limits

- The prepared@2 field names are oracle names built from the blueprint list in
  section 4. C0-07 freezes the wire names. A consuming test maps the names.
  The decisions do not depend on the names.
- The parsed output of a content is outside this oracle, except for its
  limitations. The v1 bases use an empty block list.
- The v1 reader rules come from the frozen v1 model. The oracle covers a
  subset of those rules: one case per rule.
- The answer for N37 (triage_input@2 refuses prepared@1) follows the closed
  version-2 allowlist of C0-17b. The blueprint does not say it in one
  sentence.
- The reference reader in the test is a consistency check. It is not a
  conformance proof for the future A3 adapter.
- `policy_status` is not set on any T0-08 case. Each decision comes from the
  blueprint or the frozen v1 contract.

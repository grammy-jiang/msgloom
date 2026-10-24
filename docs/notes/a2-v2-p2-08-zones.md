# A2 v2 P2-08: content zones (PROVISIONAL)

Code: `msgloom/a2_kedro/zones.py`.
Tests: `tests/a2_kedro/test_p2_08.py` (behavior, invariants, mutations),
`tests/a2_kedro/test_p2_08_hostile.py` (1 MB inputs).

All names and bounds are PROVISIONAL. The module builds the C0-05
`ContentZones` and proves it with the contract checks `validate_against`
and `verify_bytes`. It reuses the contract types and adds no wire field.

## Entry point

`build_zones(raw, source, *, part_id, author, max_zones=1024)` returns a
`ZoneResult(zones, content, unknown, limitations)`.

- `source` is the P2-07 `NormalizedContent` (code points). The module
  converts it to the contract `NormalizedContent` (UTF-8 bytes) and returns
  it as `content`.
- `author` is required. No quote is attributed to it.
- `zones` is `None` when the text has no zone.

## Contract gaps (open questions)

1. The contract has no `unknown` zone kind. Unknown text stays unzoned and
   is listed in `ZoneResult.unknown`. Zones plus `unknown` tile the text.
2. The contract has no kind for a forwarded body. The body is a depth 1
   `quote` zone right after a `forward_header` zone.
3. `ContentZones` needs 1 to 1024 zones. An empty or all-unknown text has
   no `ContentZones`, so `zones` is `None`.
4. The contract has no attribution field except `quote_author_sha256`. Its
   digest basis is open in C0-05. This module hashes the casefolded claim
   with single spaces (`On ... wrote:` middle, `From:` value, or the marker
   line one level up). `None` means no claim or the claim names the author.
5. The mime_html `QuotedRegion` model is not in this base. Zones are
   found from the normalized text only. A later step can use the regions.

## Rules and limits

See the module docstring. In short: `>` prefix is a quote (depth up to 16);
the exact RFC 3676 delimiter line (dash, dash, space) is a signature (at most 12 lines); `On ... wrote:`
needs a depth 1 `>` line at once; an Outlook `From/Sent/To/[Cc]/Subject`
block starts a forward. Anything ambiguous makes the marker line and the
rest of the text unknown. Quoted text is never `authored`.

Known limits: the author test is a substring test and drops a claim on a
false hit. Text after an unknown marker is unknown to the end. A forwarded
body is one flat quote zone; inner quoting is not parsed. Marker lines over
512 characters are plain text.

## Cost

One forward pass. Lookahead is at most 8 header lines, one marker line or
one signature region that is then consumed. No regular expression. The
1 MB hostile tests run in under 1 s each on a Raspberry Pi 5 (identity map).
The zone cap gives the `zone_limit` limitation and an unknown tail.

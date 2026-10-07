# Security probes

Runnable checks that **measure** a security claim instead of citing one.

Each probe exists because a review made a claim about a library's behaviour and
the claim needed testing before it went into a design document. A requirement
based on a library's reputation is the kind of thing that is wrong two versions
later.

Run one with its dependencies and nothing else:

```bash
uv run --with lxml --with defusedxml python research/security-probes/xxe_probe.py
```

---

## `xxe_probe.py` — XML external entities

**Why it exists.** `msgloom-security-review.md` F5 stated that lxml resolves
external entities by default, that the Word path (python-docx → lxml) was
therefore exposed while the Excel path (openpyxl + defusedxml) was protected,
and that the fix was to add defusedxml to the Word path.

**Measured 2026-09-17 on lxml 6.1.0 / libxml2 2.14.6. The claim is wrong in
three ways, and the corrections matter more than the original.**

| Parser configuration | Reads a local file? | Makes a network request? |
| --- | --- | --- |
| **Default** | **No — refuses, raises `XMLSyntaxError`** | No |
| `XMLParser()` | No — same refusal | No |
| `resolve_entities=False` | No | No |
| **`resolve_entities=True`, `no_network=True`** | **YES** | No |
| `resolve_entities=True`, `no_network=False` | No | No |

### Correction 1 — the default is safe here

lxml 6.1.0 refuses an external entity outright. The review's premise does not
hold on this version, so "the Word path is exposed by default" is not true
today.

**It is still a real risk class.** The default is this version's behaviour, not
a promise.

### Correction 2 — `no_network=True` is not protection

This is the finding worth keeping. A developer who turns entity resolution on
for some legitimate reason and sets `no_network=True` will reasonably believe
they are safe.

**They are not.** `no_network` blocks the network and does nothing about
`file://`. A `.docx` carrying a local-file entity reads that file into the
extracted text, and the extracted text goes to the model.

### Correction 3 — the recommended fix is being removed

`defusedxml.lxml` emits `DeprecationWarning: defusedxml.lxml is no longer
supported and will be removed in a future release.` Recommending it for the
lxml path would be adopting something on its way out.

`defusedxml.ElementTree` still refuses the same bytes with
`EntitiesForbidden`, so defusedxml remains the right answer for
stdlib-ElementTree paths — which is what the openpyxl row uses it for.

## The requirement, as corrected

Replaces F5's original wording in `msgloom-security-review.md`.

> **Never set `resolve_entities=True`** on any parser that touches source
> bytes. If a format genuinely needs entity expansion, that is a decision with
> a recorded reason, not a default.
>
> **`no_network=True` is not a substitute.** It does not stop local file
> disclosure.
>
> **Verify the behaviour on every dependency upgrade** by running this probe.
> The current default is safe; that is an observation about lxml 6.1.0, not a
> guarantee from lxml.

**This is `R-D`, restated.** The original said "disable external entities in
every parser and verify". The verification half was always the important half,
and the measurement shows why: the thing to guard against is not a bad default
— it is a well-meant override.

## What the probe does not cover

- **python-docx and openpyxl themselves are not installed here**, so the probe
  tests lxml directly rather than through them. A real regression test in the
  implementation should feed a genuine `.docx` and `.xlsx` through the actual
  parser path.
- Billion-laughs and quadratic-blowup expansion are **not** tested. They are a
  different risk — resource exhaustion, which `R-E` covers — and they belong in
  the malicious-fixture suite rather than here.
- It probes one lxml version on one machine. That is the point: **run it
  again** when the version changes.

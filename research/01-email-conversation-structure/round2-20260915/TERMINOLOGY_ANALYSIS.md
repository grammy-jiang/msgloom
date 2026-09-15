# Topic 01 Round 2 — academic terminology analysis

## Scope

Round 2 is intentionally narrow. It does not redo generic email threading, ordinary conversation clustering, zoning, summarization, or semantic response-scope research. It targets only:

- **R2-A** incomplete/incremental email reconstruction;
- **R2-B** robust quotation-occurrence to source-span alignment.

## Round 1 seed-term audit

| Round 1 term | Round 2 status | Reason |
| --- | --- | --- |
| `email thread reconstruction` | retain but narrow | too broad by itself; must combine with missing/incomplete/incremental phenomena |
| `reply-to prediction` | conditional | useful only if it treats unavailable/multiple/late parents or uncertainty |
| `conversation disentanglement` | demote | chat/forum clustering was already covered and is not direct email reconstruction |
| `email quotation extraction` | retain but refine | detection alone is insufficient; need occurrence-to-source provenance/alignment |
| `quoted text detection` | demote | identifies quote vs new text but usually does not identify exact source span |
| `inline replies` | retain | relevant when paired with alignment/provenance/interleaving |

## Promoted R2-A terminology — incomplete / incremental reconstruction

- `hidden email reconstruction`
- `hidden message reconstruction`
- `missing message recovery`
- `missing parent` / `unavailable parent`
- `orphaned quotation`
- `partial email history` / `incomplete email history`
- `partial export`
- `precedence graph`
- `partial-order reconstruction`
- `late arrival` / `out-of-order email`
- `incremental thread reconstruction`
- `thread reconciliation`
- `reply graph reconstruction`
- `multiple parents` / `multiple reply targets`
- `relation correction` / `reconciliation after late evidence`

The Carenini/Ng/Zhou hidden-email line is a strong direct-email terminology anchor. It explicitly treats originals absent from the folder, quoted fragments, partial recovery, precedence graphs, and partial ordering.

## Promoted R2-B terminology — quotation/source alignment

- `quoted fragment matching`
- `quotation source identification`
- `quote provenance`
- `quotation provenance`
- `quote-source alignment`
- `source-span alignment`
- `edited quotation alignment`
- `partial quotation matching`
- `approximate quote matching`
- `fragment overlap`
- `fragment splitting`
- `markerless quotation`
- `inline reply alignment`
- `interleaved reply alignment`
- `nested quotation alignment`

Important distinction:

`quote detection` != `quote occurrence -> exact source message/span` != `semantic response scope`.

The last item is Topic 04 and is excluded from this round.

## Primary search families

### Q-A1 hidden / missing email

- `"hidden email" reconstruction`
- `"hidden emails" quoted fragments`
- `"missing email" reconstruction quotation`
- `"orphaned quotation" email`
- `email "missing parent" thread`
- `email "partial history" reconstruction`

### Q-A2 incremental reconciliation

- `email incremental thread reconstruction`
- `email out-of-order threading reconstruction`
- `email late parent reconstruction`
- `email reply graph incremental`
- `email multiple parents reply graph`
- `email thread reconciliation missing messages`

### Q-B1 quote provenance / source-span alignment

- `email quotation source identification`
- `email quote provenance`
- `email quoted fragment matching`
- `email edited quotation alignment`
- `email partial quotation matching`
- `email quote source span`

### Q-B2 inline/interleaved structure

- `email inline reply alignment quotation`
- `email interleaved reply extraction source`
- `email nested quote alignment`
- `HTML email quotation alignment`
- `markerless quote email detection alignment`

### Q-C recent methods

Cross only the validated R2-A/R2-B task terms with:

- `2024`, `2025`, `2026`
- `large language model`, `LLM`
- `incremental`, `reconciliation`

LLM is a method family, not a research target. A paper is excluded if the LLM merely summarizes/replies to email without reconstructing missing/late relations or aligning quotes to source spans.

## Discovery pass 1 findings

### Strong direct primary line

1. **Discovery and Regeneration of Hidden Emails** (Carenini, Ng, Zhou, Zwart; SAC 2005)
   - reconstructs absent originals from embedded quotations;
   - represents fragment precedence and partial ordering;
   - explicitly acknowledges that unquoted parts may be unrecoverable and ordering may remain uncertain;
   - direct fit: R2-A and R2-B.

2. **Scalable Discovery of Hidden Emails from Large Folders** (Carenini, Ng, Zhou; KDD 2005)
   - extends hidden-email discovery/reconstruction to robustness and scalability on Enron;
   - direct fit: R2-A and R2-B.

These are related papers from one research line, not independent replications. Both may be retained because SAC emphasizes the reconstruction/partial-order model while KDD evaluates robustness/scalability on real folders.

### Structural/behavioural candidates requiring stricter screening

- **Construction of Deliberation Structure in E-Mail Communication**: direct email, multi-topic deliberation trees. Hold until a clean attributable full text is available and structural fit to quote/source alignment is demonstrated. Semantic agreement scope is Topic 04.
- **The Use of Quoting to Preserve Context in Electronic Mail Dialogues**: useful behavioral evidence on selective quoting, but likely not an alignment algorithm. Hold unless it materially changes R2-B assumptions; do not admit solely for historical completeness.

### Explicit exclusions from first pass

- help-desk response automation / multi-sentence answer scope -> Topic 04;
- generic recent email reply assistance -> Topic 04 unless reconstruction/alignment is evaluated;
- generic dialogue/thread disentanglement already covered in Round 1 -> exclude unless it addresses incomplete/late evidence directly;
- generic summarization and zoning -> exclude;
- `THREAD`-named software/papers unrelated to email threading -> exclude.

## Recent-literature search status

Initial targeted searches for 2024–2026 direct email reconstruction, missing-parent reconciliation, and quote-source alignment did **not** surface a clear task-matched academic paper. This is only a discovery result for the queries tried. It is not a claim that such literature does not exist. Continue citation-led and terminology-refined discovery before corpus freeze.

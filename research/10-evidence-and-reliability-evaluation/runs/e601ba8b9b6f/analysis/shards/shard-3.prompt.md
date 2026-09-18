You are one worker inside an automated literature-review pipeline.
A script, not a person, reads your reply. Follow these rules exactly:
- Do the task completely in this single reply. Do not ask questions and do not
  wait for confirmation.
- Reply with the requested artifact block(s) only: no preamble, no commentary
  outside the blocks. Each block starts with a line `===BEGIN <name>===` and
  ends with a line `===END <name>===`; the content between those lines is
  written to a file verbatim.
- Never invent papers, identifiers, numbers, or quotes. Leave unknown fields
  out or mark them as unknown.
- Do not use your code tool, canvas, or connectors; plain text is enough.

# Task: read and analyze 5 paper(s)

Research topic: **evidence attribution, factuality, completeness and reliability evaluation for workplace communication systems: what exact evidence supports each decision-relevant statement, whether it is current and correctly attributed, what was omitted, and when the system should abstain**

For each paper below, open it with your web tool. Prefer the `html` URL
(arXiv HTML full text); fall back to `abs` (abstract only) or `pdf` when
the HTML page is unavailable. Then write ONE analysis object per paper in
your own words. Do not copy long passages; a `quote` may hold at most one
sentence.

Papers:
- paper_id `doi-10-1017-s1351324909005051` — Formal and functional assessment of the pyramid method for summary content evaluation (Rebecca J. Passonneau; 2010)
- paper_id `2606.00093` — Agreement Metrics for LLM-as-Judge Evaluation: What to Report and Why (Delip Rao, Chris Callison-Burch; 2026)
    html: https://arxiv.org/html/2606.00093
    abs: https://arxiv.org/abs/2606.00093
    pdf: https://arxiv.org/pdf/2606.00093
- paper_id `2605.16354` — Augmenting Human Evaluation with LLM Judges: How Many Human Reviews Do You Need? (Jane Paik Kim; 2026)
    html: https://arxiv.org/html/2605.16354
    abs: https://arxiv.org/abs/2605.16354
    pdf: https://arxiv.org/pdf/2605.16354
- paper_id `2111.09525` — SummaC: Re-Visiting NLI-based Models for Inconsistency Detection in Summarization (Philippe Laban, Tobias Schnabel, Paul N. Bennett et al.; 2022)
    html: https://arxiv.org/html/2111.09525
    abs: https://arxiv.org/abs/2111.09525
    pdf: https://arxiv.org/pdf/2111.09525
- paper_id `2305.14627` — Enabling Large Language Models to Generate Text with Citations (Tianyu Gao, Howard Yen, Jiatong Yu et al.; 2023)
    html: https://arxiv.org/html/2305.14627
    abs: https://arxiv.org/abs/2305.14627
    pdf: https://arxiv.org/pdf/2305.14627

Analysis object (every field required unless noted):
- paper_id: exactly as listed above
- title
- research_question: one sentence
- methodology: 2-5 sentences
- key_findings: 3-8 items {finding, evidence_type, section} where evidence_type is
  supported, unsupported, or contradicted
- limitations: list of strings
- reproducibility: {code_available, dataset_available, metrics_reported} booleans
- confidence_scores: map short finding label -> float in [0, 1]
- raw_claims: 5-15 short one-sentence claims, in your words if verbatim is not possible
- source_url: the URL you actually read
- access: "full_text" or "abstract_only"

JSON schema of one analysis object:
{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "title": "PaperAnalysis",
 "description": "Schema for per-paper analysis output produced by the paper-analyzer sub-agent.",
 "type": "object",
 "required": [
  "paper_id",
  "title",
  "research_question",
  "methodology",
  "key_findings",
  "limitations",
  "reproducibility",
  "confidence_scores",
  "raw_claims"
 ],
 "properties": {
  "paper_id": {
   "type": "string",
   "minLength": 1,
   "description": "arXiv ID or other unique paper identifier"
  },
  "title": {
   "type": "string",
   "minLength": 1
  },
  "research_question": {
   "type": "string",
   "minLength": 1,
   "description": "Single-sentence statement of the paper's primary research question"
  },
  "methodology": {
   "type": "string",
   "minLength": 1,
   "description": "Description of the research methodology used"
  },
  "key_findings": {
   "type": "array",
   "minItems": 1,
   "items": {
    "type": "object",
    "required": [
     "finding",
     "evidence_type"
    ],
    "properties": {
     "finding": {
      "type": "string",
      "minLength": 1
     },
     "evidence_type": {
      "type": "string",
      "enum": [
       "supported",
       "unsupported",
       "contradicted"
      ]
     },
     "section": {
      "type": "string"
     },
     "quote": {
      "type": "string"
     }
    }
   }
  },
  "limitations": {
   "type": "array",
   "items": {
    "type": "string"
   }
  },
  "reproducibility": {
   "type": "object",
   "properties": {
    "code_available": {
     "type": "boolean"
    },
    "dataset_available": {
     "type": "boolean"
    },
    "metrics_reported": {
     "type": "boolean"
    }
   }
  },
  "confidence_scores": {
   "type": "object",
   "description": "Map of finding summary → confidence in [0, 1]",
   "additionalProperties": {
    "type": "number",
    "minimum": 0.0,
    "maximum": 1.0
   }
  },
  "raw_claims": {
   "type": "array",
   "items": {
    "type": "string"
   },
   "description": "Atomic sentences extracted verbatim from the paper"
  }
 },
 "additionalProperties": true
}

If a paper cannot be opened at all, do not write an analysis for it; list
it under `skipped` with a reason instead.

Reply format (one block containing one JSON object):
===BEGIN shard-3.result.json===
{"analyses": [<analysis objects>],
 "skipped": [{"paper_id": "...", "reason": "..."}]}
===END shard-3.result.json===

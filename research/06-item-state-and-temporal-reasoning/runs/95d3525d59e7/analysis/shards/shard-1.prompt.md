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

Research topic: **Natural-language longitudinal work-item revision in workplace and operational communication: distinguishing supersession, correction, supplementation, contradiction, reopening, unresolved conflict, and claimed versus independently confirmed completion.**

For each paper below, open it with your web tool. Prefer the `html` URL
(arXiv HTML full text); fall back to `abs` (abstract only) or `pdf` when
the HTML page is unavailable. Then write ONE analysis object per paper in
your own words. Do not copy long passages; a `quote` may hold at most one
sentence.

Papers:
- paper_id `manual-2362cbe877` — ProPara-CRTS: Canonical Referent Tracking for Reliable Evaluation of Entity State Tracking in Process Narratives (Bingyang Ye, Timothy Obiso, Jingxuan Tu et al.; 2025)
- paper_id `1805.06975` — Tracking State Changes in Procedural Text: A Challenge Dataset and Models for Process Paragraph Comprehension (Bhavana Dalvi Mishra, Lifu Huang, Niket Tandon et al.; 2018)
    html: https://arxiv.org/html/1805.06975
    abs: https://arxiv.org/abs/1805.06975
    pdf: https://arxiv.org/pdf/1805.06975
- paper_id `2608.20116` — When Text and Numbers Disagree: Evidence Arbitration in Large Language Models (Mattia Carletti, Edward Phillips, Fredrik K. Gustafsson et al.; 2026)
    html: https://arxiv.org/html/2608.20116
    abs: https://arxiv.org/abs/2608.20116
    pdf: https://arxiv.org/pdf/2608.20116
- paper_id `2406.00197` — Re3: A Holistic Framework and Dataset for Modeling Collaborative Document Revision (Qian Ruan, Ilia Kuznetsov, Iryna Gurevych; 2024)
    html: https://arxiv.org/html/2406.00197
    abs: https://arxiv.org/abs/2406.00197
    pdf: https://arxiv.org/pdf/2406.00197
- paper_id `doi-10-1016-0004-3702-86-90080-9` — An assumption-based TMS (Johan de Kleer; 1986)

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
===BEGIN shard-1.result.json===
{"analyses": [<analysis objects>],
 "skipped": [{"paper_id": "...", "reason": "..."}]}
===END shard-1.result.json===

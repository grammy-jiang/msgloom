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

Research topic: **Direct empirical methods for cross-version multimodal document element lineage and hierarchical provenance, with special attention to revised workbook provenance and message referring-expression grounding into versioned pages, regions, and cells.**

For each paper below, open it with your web tool. Prefer the `html` URL
(arXiv HTML full text); fall back to `abs` (abstract only) or `pdf` when
the HTML page is unavailable. Then write ONE analysis object per paper in
your own words. Do not copy long passages; a `quote` may hold at most one
sentence.

Papers:
- paper_id `2410.05243` — Navigating the Digital World as Humans Do: Universal Visual Grounding for GUI Agents (Boyu Gou, Ruohan Wang, Boyuan Zheng et al.; 2024)
    html: https://arxiv.org/html/2410.05243
    abs: https://arxiv.org/abs/2410.05243
    pdf: https://arxiv.org/pdf/2410.05243
- paper_id `2604.13731` — Doc-V*: Coarse-to-Fine Interactive Visual Reasoning for Multi-Page Document VQA (Yuanlei Zheng, Pei Fu, Hang Li et al.; 2026)
    html: https://arxiv.org/html/2604.13731
    abs: https://arxiv.org/abs/2604.13731
    pdf: https://arxiv.org/pdf/2604.13731
- paper_id `doi-10-1145-2950290-2950359` — Detecting table clones and smells in spreadsheets (Wensheng Dou, Shing-Chi Cheung, Chushu Gao et al.; 2016)
- paper_id `doi-10-3390-app152312430` — Document Image Verification Based on Paragraph Alignment and Subtle Change Detection (Daoquan Li, Weifei Jia, Quanlin Yu et al.; 2025)
- paper_id `2506.21055` — Class-Agnostic Region-of-Interest Matching in Document Images (Demin Zhang, Jiahao Lyu, Zhijie Shen et al.; 2025)
    html: https://arxiv.org/html/2506.21055
    abs: https://arxiv.org/abs/2506.21055
    pdf: https://arxiv.org/pdf/2506.21055

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

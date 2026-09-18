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

Research topic: **email, image, table and attachment understanding in workplace communication: preserving multimodal and document structure, and grounding evidence back to precise source locations such as a cell, region, page or attachment version**

For each paper below, open it with your web tool. Prefer the `html` URL
(arXiv HTML full text); fall back to `abs` (abstract only) or `pdf` when
the HTML page is unavailable. Then write ONE analysis object per paper in
your own words. Do not copy long passages; a `quote` may hold at most one
sentence.

Papers:
- paper_id `1911.10683` — Image-based table recognition: data, model, and evaluation (Xu Zhong, Elaheh ShafieiBavani, Antonio Jimeno Yepes; 2020)
    html: https://arxiv.org/html/1911.10683
    abs: https://arxiv.org/abs/1911.10683
    pdf: https://arxiv.org/pdf/1911.10683
- paper_id `doi-10-1007-s00521-022-06948-5` — Reading order detection on handwritten documents (Lorenzo Quirós, Enrique Vidal; 2022)
- paper_id `2010.12537` — TUTA: Tree-based Transformers for Generally Structured Table Pre-training (Zhiruo Wang, Haoyu Dong, Ran Jia et al.; 2021)
    html: https://arxiv.org/html/2010.12537
    abs: https://arxiv.org/abs/2010.12537
    pdf: https://arxiv.org/pdf/2010.12537
- paper_id `2006.14806` — TURL: Table Understanding through Representation Learning (Xiang Deng, Huan Sun, Alyssa Lees et al.; 2020)
    html: https://arxiv.org/html/2006.14806
    abs: https://arxiv.org/abs/2006.14806
    pdf: https://arxiv.org/pdf/2006.14806
- paper_id `2111.07129` — Visual Understanding of Complex Table Structures from Document Images (Sachin Raja, Ajoy Mondal, C. V. Jawahar; 2022)
    html: https://arxiv.org/html/2111.07129
    abs: https://arxiv.org/abs/2111.07129
    pdf: https://arxiv.org/pdf/2111.07129

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

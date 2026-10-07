# Topic 01 rendering inputs

The installed tool_report supports `custom_template` plus explicit `synthesis_path`. The parent will use that supported interface to render analysis/synthesis.json with templates/topic01.md.j2, then submit the genuine ToolResult to the runner. No installed renderer will be edited. The custom template is hash-recorded and the independent reviewer reads the exact rendered draft and synthesis. All normal reviewer, strict validation, publication and completion gates remain required.

The synthesis retains the exact installed CrossPaperSynthesisRecord schema. Additional per-corpus string fields used by the template:

paper_id, title, authors (string), year (string), venue, url, domain (DIRECT_EMAIL or TRANSFER), evidence_role, publication_type, data_summary, reproducibility, read_scope.

`evidence_strength_map` must contain explicit RQ1–RQ8 answers. Each finding_id begins with its RQ ID and a short descriptive title. Each finding contains an answer, supporting_papers, evidence_ids, confidence, interpretation_notes, and limitations that state residual gaps. This is schema-compatible. The template renders every field relevant to the answer.

`recurring_patterns` holds 4–6 substantive executive takeaways. Taxonomy, assumptions, contradictions/tensions, operational implications, production readiness, mechanisms, design implications, research gaps and risk register use their standard schema fields. No empty filler sections. Every finding needs real paper support, and claims confined to engineering documentation must remain identified as engineering facts.

`evidence_matrix` uses string fields paper_id, methods, assumptions, results (include exact task/dataset/unit/verified metric/locator), limitations. `traceability_appendix` rows use item_id, item_type, papers, evidence_ids (human-readable page/section/analysis finding locators), confidence.

Use accurate qualified wording for incomplete bibliographic and dataset-license information. URLs in References do not imply they were fetched in this run. E14 is a dissertation; E15 is the local MSR technical report version. All appendix file links resolve from the published report in the namespace root, not report/draft.md's intermediate directory.

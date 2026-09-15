# Synthetic case catalogue

Frozen engineering-validation cases. These are adversarial coverage cases, not a model of production frequency.

| Case | Family | Messages | Quotes | Relations | Tags | Purpose |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `late-parent-arrival` | `late_parent` | 2 | 1 | 1 | E1, E2, E3 | Reply and quotation arrive before the referenced original. |
| `sibling-branches` | `branching` | 3 | 2 | 2 | E1, E3 | Independent sibling replies share a parent but do not imply sibling visibility. |
| `multiple-parents` | `multiple_parent` | 3 | 2 | 1 | E1, E3 | A message can carry more than one parent identifier; the benchmark does not collapse it to a tree. |
| `boilerplate-collision` | `ambiguous_source` | 3 | 1 | 0 | E1, E2, E4 | Identical boilerplate in unrelated sources must remain an alternative-source set. |
| `short-edited-quote` | `edited_quote` | 2 | 1 | 0 | E1, E2, E4 | A short edited quote must not be silently normalized back to the source wording. |
| `markerless-copy` | `markerless_quote` | 2 | 1 | 0 | E1, E2 | Copied source text without a quotation marker exposes detector recall limits. |
| `html-table-nested` | `html_table` | 2 | 1 | 0 | E1, E2 | HTML blockquote containing a table must preserve decision-bearing cell text and structure. |
| `mime-alternative-preservation` | `mime_alternative` | 1 | 0 | 0 | E1, E2 | Multipart alternative fixture checks decision-bearing text survives the selected representation. |
| `duplicate-message-id` | `duplicate_id` | 3 | 1 | 1 | E1, E3, duplicate-id | Two distinct observed messages share one Message-ID; a later reference cannot justify a unique parent from the identifier alone. |
| `headerless-source-and-missing-parent` | `missing_identifier` | 2 | 1 | 1 | E1, E3, missing-id | Quoted content can align to an observed source even when reply-parent metadata points to an unavailable identifier. |
| `header-vs-quote-source-conflict` | `evidence_conflict` | 3 | 1 | 1 | E1, E3, conflicting-evidence | Reply-parent metadata and quotation provenance point to different messages and must remain separate relation types. |
| `same-subject-unrelated` | `subject_false_friend` | 2 | 0 | 0 | E1 | Two messages share a subject but have no ancestry evidence. |
| `changed-subject-reply` | `subject_change` | 2 | 1 | 1 | E1, E3 | Explicit ancestry remains evidence even when the subject changes completely. |
| `interleaved-inline-reply` | `interleaved_reply` | 2 | 2 | 1 | E1, E2, E3 | Two separated quote occurrences from one source are interleaved with distinct new reply text. |
| `forwarded-message-block` | `forwarded_block` | 2 | 1 | 0 | E1, E2, forward | Forwarded content remains evidence even without RFC-style quote markers; the simple structural quote detector is expected to miss it. |
| `truncated-references` | `truncated_references` | 3 | 2 | 3 | E1, E3, references | A truncated References chain must not replace explicit In-Reply-To direct-parent evidence. |
| `boilerplate-reuse-not-quotation` | `reuse_negative_control` | 2 | 0 | 0 | E1, E2, negative-control | Exact repeated boilerplate is a negative control for reuse-augmented quote detection. |
| `format-flowed` | `format_flowed` | 1 | 1 | 0 | E1, E2 | Flowed quoted lines exercise quote-depth-aware normalization and space-stuffing behavior. |

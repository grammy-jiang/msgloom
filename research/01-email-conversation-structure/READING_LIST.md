# Topic 01 reading list status

**The academic reading list is incomplete.** The runner could not obtain a nonempty candidate corpus. No paper was screened, shortlisted, read in full, or read at abstract level. Assigning paper priorities from this run would imply evidence that the run did not obtain.

The following verified primary engineering documents are useful preparation. They are standards and product documentation, not academic papers. The supervising assistant saved their public source texts and access records in [supporting/engineering/](supporting/engineering/NOTES.md).

| Priority | Primary source | Why read it |
| --- | --- | --- |
| 1 | [RFC 5322 §3.6.4: Identification fields](https://www.rfc-editor.org/rfc/rfc5322.html#section-3.6.4) | Defines message identifiers, reply relationships, and the multiple-parent limitation of References construction. Establishes the metadata vocabulary for RQ1/RQ3. |
| 2 | [RFC 5256 §3: IMAP THREAD REFERENCES](https://www.rfc-editor.org/rfc/rfc5256.html#section-3) | Defines a named deterministic baseline, including missing identifiers, dummy nodes, cycles, and subject-based grouping. Read §6 for misleading-tree limitations. |
| 3 | [RFC 3676 §§4.1–4.5: format=flowed text](https://www.rfc-editor.org/rfc/rfc3676.html#section-4.1) | Specifies quote depth, space stuffing, flowed lines, and signature separators. Useful for plain-text preservation fixtures under RQ2. |
| 4 | [Microsoft Graph message resource](https://learn.microsoft.com/en-us/graph/api/resources/message?view=graph-rest-1.0) | Clarifies conversationId, conversationIndex, replyTo, internetMessageHeaders, internetMessageId, uniqueBody, and version fields. |
| 5 | [Microsoft Graph immutable Outlook identifiers](https://learn.microsoft.com/en-us/graph/outlook-immutable-id) | Clarifies folder-move stability and export/re-import limits when defining synthetic identity cases. |

After the search blocker is resolved, prioritize foundational direct-email thread-reassembly and quotation/signature work. Then assess recent reply prediction and conversation-disentanglement papers as transfer candidates. This is a search order, not a screened paper shortlist. See [RUN_STATUS.md](RUN_STATUS.md) for the missing stages and actual search coverage.

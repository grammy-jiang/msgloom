# Official engineering evidence for Topic 01

These are standards and product documentation. They are not academic papers and do not count toward the research corpus or full-text paper counts. The supervising assistant fetched these public sources on 2026-09-14. Exact UTC timestamps, URLs, response status, file sizes, and SHA-256 values are in [source_access.json](source_access.json). No mailbox was accessed.

## ENG-01: Internet message relationships

[RFC 5322, §3.6.4](https://www.rfc-editor.org/rfc/rfc5322.html#section-3.6.4), pp. 25–27; saved [rfc5322.txt](rfc5322.txt), lines 1351–1483.

`Message-ID` identifies a message version. Adding transport headers does not necessarily create a new message identity. Reply headers are recommended, so their absence is possible. `In-Reply-To` can contain identifiers for multiple parents. The specification discourages constructing `References` for multiple parents and does not define that construction. Distinguish the recipient-address field `Reply-To` (§3.6.2) from ancestry evidence.

**Research implication (inference):** Preserve message-level references and their provenance before reducing them to any tree. A common ancestor does not establish that the authors of sibling replies read each other's messages.

## ENG-02: A reproducible threading baseline

[RFC 5256, §3, THREAD/REFERENCES](https://www.rfc-editor.org/rfc/rfc5256.html#section-3), pp. 7–13; saved [rfc5256.txt](rfc5256.txt), lines 382–653. See §6, lines 846–854, for misleading-tree limitations.

REFERENCES normalizes identifiers. It uses `References`, then the first valid `In-Reply-To` identifier as a fallback. It assigns replacement identifiers to missing or duplicate identifiers, creates dummy nodes for missing messages, and prevents cycles. Its later steps prune dummy nodes and combine threads by base subject. The specification warns that false reference headers and subject normalization can mislead threading. It also explains that adjacent identifiers in a truncated `References` field need not identify a direct parent and child.

**Research implication (proposal):** Evaluate this algorithm as a named baseline. Preserve raw identifiers, conflicts, and missing-ancestor evidence separately from its display tree. Its result does not establish Topic identity or participant knowledge.

## ENG-03: Plain-text quotation semantics

[RFC 3676, §§4.1–4.5](https://www.rfc-editor.org/rfc/rfc3676.html#section-4.1), pp. 6–11; saved [rfc3676.txt](rfc3676.txt), lines 287–595.

For `text/plain; format=flowed`, quote depth is determined before space unstuffing and line-flow processing. `DelSp` controls treatment of the trailing soft-break space. The signature separator the signature separator consisting of two hyphens followed by a space is a special case. Quote-depth changes end paragraphs, including recovery from malformed flowed input.

**Research implication (proposal):** Preserve raw bytes and mappings when normalizing flowed text. Include stuffed literal quotation markers and quote-depth changes in synthetic tests. These rules do not specify general HTML quotation boundaries, arbitrary disclaimers, or semantic response scope.

## ENG-04: Microsoft Graph message fields

[Message resource, Properties](https://learn.microsoft.com/en-us/graph/api/resources/message?view=graph-rest-1.0); saved [graph-message.html](graph-message.html). Locate the table rows by exact property name.

`conversationId` identifies a conversation; `conversationIndex` indicates position within it. `replyTo` contains recipient addresses. `internetMessageHeaders` requires `$select`. `internetMessageId` exposes the Internet message identifier. `uniqueBody` also requires selection and can contain HTML or text. `bodyPreview` contains only the first 255 body characters. `changeKey` represents the message version. The default Graph `id` can change on a folder move. `hasAttachments` excludes inline-only attachments.

**Research implication (inference):** The field descriptions do not establish a measured guarantee that `uniqueBody` preserves every inline reply. Evaluate it against preserved bodies. Do not infer a reply parent from `replyTo`, or a Topic from `conversationId`.

## ENG-05: Graph identity limits

[Obtain immutable identifiers, How it works / Lifetime of immutable IDs](https://learn.microsoft.com/en-us/graph/outlook-immutable-id); saved [graph-immutable-id.html](graph-immutable-id.html).

`Prefer: IdType="ImmutableId"` applies to each request that includes it. The identifier remains stable across folder moves within a mailbox. It changes when the item moves to an archive mailbox or is exported and re-imported. Graph identifiers are case-sensitive.

**Research implication (proposal):** Investigate separate fields for the source item, observation version, Internet message identifier, and acquired bytes. This is a proposed experiment boundary, not an approved msgloom architecture change.

## Access limitations

All five saved sources returned HTTP 200. Microsoft Learn includes a generic authorization notice in page chrome, but the property and identity documentation was publicly readable in the returned pages. These accesses validate documented semantics only. They do not test a tenant, client implementation, malformed message, or preservation accuracy.

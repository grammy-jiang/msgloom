# Topic 02 academic terminology analysis

Status: started. This document precedes academic-paper acquisition and will be refined from actual literature terminology.

## Product problem

msgloom must identify concrete work matters inside message content. One supplied group may produce several Topics. Within one message, evidence for a Topic may be non-contiguous, and the same span may be relevant to more than one Topic. Segmentation must preserve conditions, evidence, exceptions and reply scope.

## Seed keyword audit

| BRIEF seed | Initial academic interpretation | Initial fit | Main risk |
| --- | --- | --- | --- |
| `topic segmentation` | Partition a document/dialogue into topically coherent contiguous segments | Strong for boundary/segment literature | Usually assumes contiguous, single segmentation |
| `dialogue topic segmentation` | Detect topic boundaries/segments in dialogue or multiparty conversation | Strong transfer family; possibly direct for Teams-like dialogue | Dialogue utterances and shared visibility differ from email/body spans |
| `span classification` | Classify a candidate text span | Useful method family | Too broad; often NER/IE and not topic segmentation |
| `multi-label text classification` | Assign multiple labels to a whole text/document | Secondary only | Message-level labels do not identify supporting spans |
| `hierarchical text classification` | Predict labels from a hierarchical taxonomy | Weak/conditional | Label hierarchy is not the msgloom Topic problem |

## Academic task families to validate

### F1 — Topical / dialogue segmentation

Candidate terminology: `topic segmentation`, `topical segmentation`, `dialogue topic segmentation`, `topic boundary detection`, `topic shift detection`, `conversation segmentation`, `topically coherent segment`.

Target evidence: annotation units, boundary metrics, local/global context, multi-party dialogue, failure modes.

### F2 — Joint segmentation and topic labeling

Candidate terminology: `topic segmentation and labeling`, `joint topic segmentation and classification`, `segment-level topic classification`, `topic identification`, `topic affiliation`.

Target evidence: whether segments are merely detected or also assigned a semantic topic identity; assumptions about one label per segment.

### F3 — Span-level multi-assignment methods

Candidate terminology: `span classification`, `span-based classification`, `multi-label span classification`, `overlapping span classification`, `overlapping span extraction`, `multi-span extraction`.

Target evidence: multiple labels per span and exact supporting-span identification. Likely transfer-method literature.

### F4 — Discontinuous / non-contiguous span representation

Candidate terminology: `discontinuous span extraction`, `discontiguous span extraction`, `non-contiguous span extraction`, `discontinuous sequence labeling`, `discontinuous mention recognition`.

Target evidence: representing one semantic object with multiple separated spans. Likely transfer-method literature.

### F5 — Discourse-unit segmentation

Candidate terminology: `discourse segmentation`, `discourse unit segmentation`, `elementary discourse unit segmentation`, `EDU segmentation`, `clause segmentation`, `discourse parsing`.

Target evidence: whether sentence, clause, EDU or arbitrary span is the right candidate unit before Topic assignment.

### F6 — Whole-message multi-topic classification

Candidate terminology: `multi-topic document classification`, `multi-label document classification`, `multi-label email classification`, `multi-label dialogue classification`.

Target evidence: whether a message can be assigned to multiple matters. This family cannot by itself support span-level or non-contiguous assignment claims.

## Capability distinctions that must remain separate

1. topic-boundary detection;
2. contiguous topic segmentation;
3. topic labeling of a segment;
4. whole-message multi-label classification;
5. exact span assignment;
6. overlapping span assignment;
7. non-contiguous assignment to one Topic;
8. preservation of decision-bearing conditions/evidence/scope.

A reported score for one capability must never be presented as a score for another.

## Initial query families

### Q1 topical/dialogue segmentation

- `"dialogue topic segmentation"`
- `"topic segmentation" dialogue`
- `"topical segmentation" dialogue`
- `"topic boundary detection" dialogue`
- `"topic shift detection" conversation`
- `"topic segmentation and labeling" dialogue`

### Q2 multi-topic / segment labeling

- `"multi-topic" dialogue segmentation`
- `"multiple topics" dialogue segmentation`
- `"segment-level topic classification"`
- `"topic affiliation" utterance`
- `"topic identification" utterance dialogue`

### Q3 span overlap / multi-assignment

- `"multi-label span classification" NLP`
- `"overlapping span classification" NLP`
- `"overlapping span extraction" NLP`
- `"multi-span extraction" NLP`
- `"multi-label sequence labeling" NLP`

### Q4 discontinuous spans

- `"discontinuous span extraction" NLP`
- `"discontiguous span" NLP`
- `"non-contiguous span extraction" NLP`
- `"discontinuous sequence labeling" NLP`

### Q5 discourse units

- `"discourse segmentation" NLP`
- `"elementary discourse unit" segmentation`
- `"EDU segmentation"`
- `"discourse unit segmentation" dialogue`
- `"clause segmentation" discourse`

### Q6 direct email/work communication cross-queries

Cross the strongest validated task terms with: `email`, `e-mail`, `business email`, `workplace communication`, `enterprise communication`, `work chat`, `multiparty dialogue`.

## Exclusion / downgrading rules

- Pure hierarchical taxonomy classification is secondary unless it contributes a needed representation/evaluation mechanism.
- Whole-document multi-label results do not count as span-level evidence.
- Generic NER/IE discontinuous-span work is TRANSFER_METHOD unless it directly evaluates Topic-like assignment.
- Meeting/chat/dialogue results are TRANSFER unless the object and annotation closely match asynchronous message bodies.
- Summarization, intent classification, or discourse parsing results support only the exact measured subtask.

## Next action

Run manual discovery using the query families above. Use high-quality seed papers to revise the terminology before bulk PDF acquisition.

## Discovery pass 1 — terminology corrections

The first manual search materially changes the priority order. Direct email/asynchronous-conversation literature exists and uses **topic segmentation of email conversations**, **topic segmentation and labeling in asynchronous conversations**, **topical clusters**, and sentence-pair **same/different topic** relations. This is more directly aligned with msgloom than the generic BRIEF terms suggested.

### Promoted terms

- `topic segmentation of email conversations` — PRIMARY DIRECT family.
- `topic segmentation and labeling in asynchronous conversations` — PRIMARY DIRECT family.
- `topical clusters` / `topical clustering of sentences` — useful direct-email terminology.
- `same-topic sentence pair classification` / graph partitioning — direct-email modeling terminology.
- `fine-grained conversation structure` / `fragment quotation graph` — direct-email structure terms to track because asynchronous topics can interleave.
- `joint document segmentation and segment labeling` — strong TRANSFER family for joint boundary+label learning.
- `topic affiliation` — useful recent DTS term, still TRANSFER unless email/work-message evidence appears.

### Demoted terms

- `hierarchical text classification` — no longer a core search family; use only if a concrete paper solves a relevant representation/evaluation subproblem.
- generic `multi-label text classification` — SECONDARY; whole-message labeling does not establish topic-support spans.

### Direct-email structural observation to test in full text

The Joty/Carenini/Murray/Ng email line explicitly treats asynchronous email topics as potentially non-sequential/intersecting. That makes direct email topic segmentation especially relevant to the BRIEF requirement for non-contiguous content. Full-text analysis must determine exactly how their annotations/models represent these intersections and whether a single topic may own separated sentences/fragments.

### New search queries

- `"topic segmentation" email conversations`
- `"topic segmentation" emails topical clusters`
- `"topic segmentation and labeling" asynchronous conversations`
- `"topical clusters" email conversations`
- `"same topic" sentence pair email segmentation`
- `"fragment quotation graph" topic segmentation`
- `"joint document segmentation" "segment labeling"`

## Direct-email discovery finding: multi-topic sentence annotation

The D01 seed paper's corpus-design section is unusually well aligned with the Topic 02 brief: annotators first identified conversation topics, then assigned each sentence to the most appropriate topic, **and could assign all relevant topics when a sentence covered more than one topic**. The research object is therefore better described as sentence-to-topical-cluster assignment with possible multi-membership than as ordinary contiguous boundary segmentation. This finding promotes the following search terms:

- `topic assignment` + email conversation
- `sentence topic assignment` + email
- `topical clustering` + email sentences
- `multi-topic sentence` + conversation
- `topic cluster` + asynchronous conversation

This is a discovery-stage observation. Formal claim extraction, metrics, and limitations remain for the later full-text Research Pipeline worker.

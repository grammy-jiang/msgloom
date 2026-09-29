"""Prepared-source evidence grounding regressions."""

from __future__ import annotations

from dataclasses import replace

import pytest

from msgloom.preparation import (
    BlockRole,
    CellLocation,
    DocumentLocation,
    MimePartLocation,
    PageLocation,
    PreparedAttachment,
    SourceMapping,
    TextBlock,
)
from msgloom.preparation.filtering import (
    AddressNormalization,
    FilterConfig,
    apply_filters,
)
from msgloom.triage import (
    Development,
    EvidenceKind,
    TriageCandidate,
    TriageEvidence,
    TriageReconciliationError,
    TriageRuleConfig,
    evaluate_rule_set,
    reconcile_triage,
)
from tests.prepared_contract_fixtures import prepared_record

from .helpers import allocation, prepared, ref, topic


def _inputs(record):
    filter_config = FilterConfig(
        reference=ref("filter-config", "synthetic"),
        address_normalization=AddressNormalization.EXACT,
        rules=(),
    )
    rule_config = TriageRuleConfig(version=ref("rule-set", "v1"), rules=())
    return {
        "filter_config": filter_config,
        "filter_results": (apply_filters(record, filter_config),),
        "rule_evaluation": evaluate_rule_set((record,), rule_config),
    }


def _reconcile_evidence(record, item: TriageEvidence):
    candidate_topic = topic("a", (record.source,)).model_copy(
        update={
            "developments": (
                Development(
                    text="Synthetic evidence development",
                    evidence=(item,),
                ),
            )
        }
    )
    return reconcile_triage(
        TriageCandidate(topics=(candidate_topic,), dispositions=()),
        selected_records=(record,),
        topic_allocations=(allocation("a", "topic-a", "assessment-a"),),
        **_inputs(record),
    )


def test_body_statement_must_occur_inside_exact_mapped_range() -> None:
    """A retained body mapping cannot authenticate text outside its range."""
    record = prepared(
        "source-a",
        body="Only this genuine synthetic source text exists.",
    )
    mapping = SourceMapping(
        source=record.source,
        field="body",
        location=DocumentLocation("message-body", 0),
        start=0,
        end=9,
    )
    record = record.model_copy(update={"source_mappings": (mapping,)})

    grounded = TriageEvidence(
        kind=EvidenceKind.SOURCE_STATEMENT,
        source_ref=record.source,
        statement="Only this",
        mapping=mapping,
    )
    _reconcile_evidence(record, grounded)

    invented = grounded.model_copy(
        update={"statement": "INVENTED SOURCE STATEMENT ABSENT FROM ALL CONTENT"}
    )
    with pytest.raises(
        TriageReconciliationError,
        match="ungrounded-source-statement",
    ):
        _reconcile_evidence(record, invented)

    outside_range = grounded.model_copy(update={"statement": "genuine"})
    with pytest.raises(
        TriageReconciliationError,
        match="ungrounded-source-statement",
    ):
        _reconcile_evidence(record, outside_range)


def test_metadata_only_attachment_cannot_support_source_statement() -> None:
    """Attachment identity without saved parsed text is not factual evidence."""
    record = prepared("source-a")
    attachment_ref = ref("attachment", "synthetic-missing")
    mapping = SourceMapping(
        source=attachment_ref,
        field="attachments[0]",
        location=DocumentLocation("attachment", 0),
    )
    record = record.model_copy(
        update={
            "attachments": (PreparedAttachment(reference=attachment_ref),),
            "source_mappings": (mapping,),
        }
    )
    item = TriageEvidence(
        kind=EvidenceKind.SOURCE_STATEMENT,
        source_ref=record.source,
        statement="Invented statement from unavailable attachment",
        mapping=mapping,
    )
    with pytest.raises(
        TriageReconciliationError,
        match="unresolvable-evidence-mapping",
    ):
        _reconcile_evidence(record, item)


def test_parsed_attachment_block_and_table_cell_statements_are_grounded() -> None:
    """Exact retained parser block and cell locations remain expressible."""
    record = prepared_record()
    attachment_ref = record.attachments[0].reference
    text_mapping = SourceMapping(
        source=attachment_ref,
        field="parsed_contents[0].blocks[0]",
        location=DocumentLocation("workbook", 0),
    )
    cell_mapping = record.source_mappings[1]
    record = record.model_copy(
        update={"source_mappings": record.source_mappings + (text_mapping,)}
    )

    for statement, mapping in (
        ("Attachment heading", text_mapping),
        ("42", cell_mapping),
    ):
        item = TriageEvidence(
            kind=EvidenceKind.SOURCE_STATEMENT,
            source_ref=record.source,
            statement=statement,
            mapping=mapping,
        )
        data = _reconcile_evidence(record, item)
        retained = data.topics[0].developments[0].evidence[0]
        if retained.mapping != mapping:
            pytest.fail("exact parsed attachment evidence mapping was not retained")


@pytest.mark.parametrize(
    "location",
    (
        MimePartLocation("1.2"),
        PageLocation(3),
        DocumentLocation("document", 4),
    ),
)
def test_mime_pdf_and_word_text_block_locations_resolve(location) -> None:
    """Parser-native text locations resolve only to their exact retained block."""
    record = prepared_record()
    parsed = record.parsed_contents[0]
    output = replace(
        parsed.output,
        blocks=(
            TextBlock(
                order=0,
                role=BlockRole.TEXT,
                text="Exact retained parser text",
                location=location,
            ),
        ),
    )
    parsed = parsed.model_copy(update={"output": output})
    mapping = SourceMapping(
        source=record.attachments[0].reference,
        field="parsed_contents[0].blocks[0]",
        location=location,
    )
    record = record.model_copy(
        update={
            "parsed_contents": (parsed,),
            "source_mappings": (mapping,),
        }
    )
    item = TriageEvidence(
        kind=EvidenceKind.SOURCE_STATEMENT,
        source_ref=record.source,
        statement="retained parser text",
        mapping=mapping,
    )
    _reconcile_evidence(record, item)


@pytest.mark.parametrize(
    ("field", "location"),
    (
        (
            "parsed_contents[0].blocks[1]",
            CellLocation("Budget", 8, 2, "B8"),
        ),
        (
            "parsed_contents[0].blocks[2]",
            PageLocation(2),
        ),
        (
            "parsed_contents[0].blocks[0]",
            DocumentLocation("workbook", 99),
        ),
    ),
)
def test_forged_parsed_locations_fail_even_when_mapping_is_retained(
    field: str,
    location,
) -> None:
    """Mapping membership cannot forge a parser cell, page, or block location."""
    record = prepared_record()
    mapping = SourceMapping(
        source=record.attachments[0].reference,
        field=field,
        location=location,
    )
    record = record.model_copy(
        update={"source_mappings": record.source_mappings + (mapping,)}
    )
    item = TriageEvidence(
        kind=EvidenceKind.SOURCE_STATEMENT,
        source_ref=record.source,
        statement="Synthetic forged statement",
        mapping=mapping,
    )
    with pytest.raises(
        TriageReconciliationError,
        match="unresolvable-evidence-mapping",
    ):
        _reconcile_evidence(record, item)


def test_interpretation_requires_available_mapping_but_is_not_literal_match() -> None:
    """Structural grounding does not pretend to validate semantic judgment."""
    record = prepared_record()
    mapping = record.source_mappings[1]
    item = TriageEvidence(
        kind=EvidenceKind.INTERPRETATION,
        source_ref=record.source,
        statement="The value may require review.",
        mapping=mapping,
    )
    _reconcile_evidence(record, item)


def test_invented_evidence_source_fails_with_opaque_code() -> None:
    """Rejected source identities are not reproduced by the public error."""
    record = prepared("source-a")
    secret = "PRIVATE-INVENTED-EVIDENCE-MUST-NOT-ECHO"
    invalid_evidence = TriageEvidence(
        kind=EvidenceKind.SOURCE_STATEMENT,
        source_ref=ref("source", secret),
        statement="Synthetic statement",
    )
    invalid_topic = topic("a", (record.source,)).model_copy(
        update={
            "developments": (
                Development(
                    text="Synthetic invalid evidence",
                    evidence=(invalid_evidence,),
                ),
            )
        }
    )
    with pytest.raises(TriageReconciliationError) as caught:
        reconcile_triage(
            TriageCandidate(topics=(invalid_topic,), dispositions=()),
            selected_records=(record,),
            topic_allocations=(allocation("a", "topic-a", "assessment-a"),),
            **_inputs(record),
        )
    if secret in str(caught.value):
        pytest.fail("invented evidence source leaked through reconciliation error")

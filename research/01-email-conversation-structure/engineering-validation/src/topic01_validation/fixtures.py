"""Deterministic adversarial fixture construction for E1-E4."""
from __future__ import annotations

from dataclasses import dataclass
from email.utils import formatdate
from pathlib import Path
from typing import Iterable

from .models import (
    BenchmarkCase,
    LabeledSpan,
    MessageFixture,
    QuoteGold,
    RelationGold,
    SourceSpan,
    find_span,
    validate_cases,
)


def _raw_plain(
    *,
    message_id: str | None,
    subject: str,
    body: str,
    in_reply_to: tuple[str, ...] = (),
    references: tuple[str, ...] = (),
    content_type: str = "text/plain; charset=utf-8",
) -> bytes:
    headers = [
        "From: synthetic@example.invalid",
        "To: user@example.invalid",
        f"Subject: {subject}",
        "Date: Tue, 15 Sep 2026 00:00:00 +0000",
        "MIME-Version: 1.0",
        f"Content-Type: {content_type}",
        "Content-Transfer-Encoding: 8bit",
    ]
    if message_id is not None:
        headers.insert(3, f"Message-ID: {message_id}")
    if in_reply_to:
        headers.append("In-Reply-To: " + " ".join(in_reply_to))
    if references:
        headers.append("References: " + " ".join(references))
    return ("\r\n".join(headers) + "\r\n\r\n" + body.replace("\n", "\r\n")).encode("utf-8")


def _raw_multipart(*, message_id: str, subject: str, plain: str, html: str, boundary: str) -> bytes:
    headers = [
        "From: synthetic@example.invalid",
        "To: user@example.invalid",
        f"Subject: {subject}",
        f"Message-ID: {message_id}",
        "Date: Tue, 15 Sep 2026 00:00:00 +0000",
        "MIME-Version: 1.0",
        f'Content-Type: multipart/alternative; boundary="{boundary}"',
    ]
    body = (
        f"--{boundary}\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n"
        + plain.replace("\n", "\r\n")
        + f"\r\n--{boundary}\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"
        + html.replace("\n", "\r\n")
        + f"\r\n--{boundary}--\r\n"
    )
    return ("\r\n".join(headers) + "\r\n\r\n" + body).encode("utf-8")


def _message(
    key: str,
    *,
    body: str,
    subject: str,
    rank: int,
    in_reply_to: tuple[str, ...] = (),
    references: tuple[str, ...] = (),
    content_type: str = "text/plain; charset=utf-8",
    expected_text: str | None = None,
    notes: str = "",
) -> MessageFixture:
    internet_id = f"<{key}@synthetic.invalid>"
    raw = _raw_plain(
        message_id=internet_id,
        subject=subject,
        body=body,
        in_reply_to=in_reply_to,
        references=references,
        content_type=content_type,
    )
    authored_text = body.replace("\r\n", "\n").rstrip("\n") if expected_text is None else expected_text
    return MessageFixture(
        message_id=key,
        raw_rfc822=raw,
        expected_text=authored_text,
        arrival_rank=rank,
        internet_message_id=internet_id,
        subject=subject,
        content_kind=content_type.split(";", 1)[0].strip().lower(),
        notes=notes,
    )


def _message_custom_id(
    key: str,
    *,
    internet_id: str,
    raw_message_id: str | None,
    body: str,
    subject: str,
    rank: int,
    in_reply_to: tuple[str, ...] = (),
    references: tuple[str, ...] = (),
    notes: str = "",
) -> MessageFixture:
    raw = _raw_plain(
        message_id=raw_message_id,
        subject=subject,
        body=body,
        in_reply_to=in_reply_to,
        references=references,
    )
    authored_text = body.replace("\r\n", "\n").rstrip("\n")
    return MessageFixture(
        message_id=key,
        raw_rfc822=raw,
        expected_text=authored_text,
        arrival_rank=rank,
        internet_message_id=internet_id,
        subject=subject,
        content_kind="text/plain",
        notes=notes,
    )


def _html_message(
    key: str, *, html: str, expected_text: str, subject: str, rank: int, notes: str = ""
) -> MessageFixture:
    internet_id = f"<{key}@synthetic.invalid>"
    raw = _raw_plain(
        message_id=internet_id,
        subject=subject,
        body=html,
        content_type="text/html; charset=utf-8",
    )
    return MessageFixture(key, raw, expected_text, rank, internet_id, subject, "text/html", notes)


def _multipart_message(key: str, *, plain: str, html: str, subject: str, rank: int) -> MessageFixture:
    internet_id = f"<{key}@synthetic.invalid>"
    raw = _raw_multipart(
        message_id=internet_id,
        subject=subject,
        plain=plain,
        html=html,
        boundary=f"topic01-{key}-boundary",
    )
    # The fixture contract explicitly selects the authored text/plain alternative.
    expected_text = plain.replace("\r\n", "\n").rstrip("\n")
    return MessageFixture(key, raw, expected_text, rank, internet_id, subject, "text/plain")


def canonical_cases() -> tuple[BenchmarkCase, ...]:
    cases: list[BenchmarkCase] = []

    # E3 anchor: the parent exists historically but arrives after the reply.
    p_body = "Approve Project Atlas budget.\nCondition: Legal must sign off.\nDeadline: Friday."
    p = _message("late-parent", body=p_body, subject="Atlas", rank=2)
    r_body = "> Approve Project Atlas budget.\n> Condition: Legal must sign off.\n\nAgreed, subject to that condition."
    r = _message(
        "late-reply",
        body=r_body,
        subject="Re: Atlas",
        rank=1,
        in_reply_to=(p.internet_message_id,),
        references=(p.internet_message_id,),
    )
    q_text = "> Approve Project Atlas budget.\n> Condition: Legal must sign off."
    src_text = "Approve Project Atlas budget.\nCondition: Legal must sign off."
    cases.append(
        BenchmarkCase(
            case_id="late-parent-arrival",
            description="Reply and quotation arrive before the referenced original.",
            family="late_parent",
            messages=(r, p),
            relations=(RelationGold("late-reply", "reply_parent", target_ids=("late-parent",)),),
            quotes=(
                QuoteGold(
                    "late-q1",
                    "late-reply",
                    find_span(r.expected_text, q_text),
                    (SourceSpan("late-parent", find_span(p.expected_text, src_text)),),
                    marker_style="plain_gt",
                ),
            ),
            spans=(
                LabeledSpan(
                    "late-decision",
                    "late-parent",
                    find_span(p.expected_text, "Condition: Legal must sign off."),
                    "decision_bearing",
                    "Condition: Legal must sign off.",
                ),
                LabeledSpan(
                    "late-deadline",
                    "late-parent",
                    find_span(p.expected_text, "Deadline: Friday."),
                    "deadline",
                    "Deadline: Friday.",
                ),
                LabeledSpan(
                    "late-new",
                    "late-reply",
                    find_span(r.expected_text, "Agreed, subject to that condition."),
                    "new_content",
                    "Agreed, subject to that condition.",
                ),
            ),
            replay_orders=(("late-reply", "late-parent"), ("late-parent", "late-reply")),
            tags=("E1", "E2", "E3"),
        )
    )

    # Two sibling replies to the same parent; no sibling edge is gold.
    root = _message("branch-root", body="Choose supplier A.\nBudget cap is AUD 20,000.", subject="Supplier", rank=1)
    left = _message(
        "branch-left",
        body="> Choose supplier A.\n\nI support supplier A.",
        subject="Re: Supplier",
        rank=2,
        in_reply_to=(root.internet_message_id,),
        references=(root.internet_message_id,),
    )
    right = _message(
        "branch-right",
        body="> Budget cap is AUD 20,000.\n\nPlease confirm the cap.",
        subject="Re: Supplier",
        rank=3,
        in_reply_to=(root.internet_message_id,),
        references=(root.internet_message_id,),
    )
    cases.append(
        BenchmarkCase(
            "sibling-branches",
            "Independent sibling replies share a parent but do not imply sibling visibility.",
            "branching",
            (root, left, right),
            relations=(
                RelationGold("branch-left", "reply_parent", target_ids=("branch-root",)),
                RelationGold("branch-right", "reply_parent", target_ids=("branch-root",)),
            ),
            quotes=(
                QuoteGold("branch-q1", "branch-left", find_span(left.expected_text, "> Choose supplier A."), (SourceSpan("branch-root", find_span(root.expected_text, "Choose supplier A.")),)),
                QuoteGold("branch-q2", "branch-right", find_span(right.expected_text, "> Budget cap is AUD 20,000."), (SourceSpan("branch-root", find_span(root.expected_text, "Budget cap is AUD 20,000.")),)),
            ),
            replay_orders=(("root", "left", "right"),) if False else (("branch-root", "branch-left", "branch-right"), ("branch-root", "branch-right", "branch-left")),
            tags=("E1", "E3"),
        )
    )

    # Multiple parents in In-Reply-To are retained as a set.
    m1 = _message("multi-a", body="Question A: approve red?", subject="Two approvals", rank=1)
    m2 = _message("multi-b", body="Question B: approve blue?", subject="Two approvals", rank=2)
    m3 = _message(
        "multi-reply",
        body="> Question A: approve red?\n> Question B: approve blue?\n\nBoth approved.",
        subject="Re: Two approvals",
        rank=3,
        in_reply_to=(m1.internet_message_id, m2.internet_message_id),
        references=(m1.internet_message_id, m2.internet_message_id),
    )
    cases.append(
        BenchmarkCase(
            "multiple-parents",
            "A message can carry more than one parent identifier; the benchmark does not collapse it to a tree.",
            "multiple_parent",
            (m1, m2, m3),
            relations=(RelationGold("multi-reply", "reply_parent", target_ids=("multi-a", "multi-b")),),
            quotes=(
                QuoteGold(
                    "multi-q-a", "multi-reply", find_span(m3.expected_text, "> Question A: approve red?"),
                    (SourceSpan("multi-a", find_span(m1.expected_text, "Question A: approve red?")),),
                    source_semantics="alternatives", marker_style="plain_gt",
                    notes="First occurrence in a composite displayed block; requires source A."
                ),
                QuoteGold(
                    "multi-q-b", "multi-reply", find_span(m3.expected_text, "> Question B: approve blue?"),
                    (SourceSpan("multi-b", find_span(m2.expected_text, "Question B: approve blue?")),),
                    source_semantics="alternatives", marker_style="plain_gt",
                    notes="Second occurrence in a composite displayed block; requires source B."
                ),
            ),
            replay_orders=(("multi-a", "multi-b", "multi-reply"), ("multi-reply", "multi-b", "multi-a")),
            tags=("E1", "E3"),
        )
    )

    # Boilerplate collision: quote alone cannot establish unique provenance.
    b1 = _message("boiler-a", body="Please review the attached proposal.\nDecision: approve Alpha.", subject="Proposal", rank=1)
    b2 = _message("boiler-b", body="Please review the attached proposal.\nDecision: reject Beta.", subject="Proposal", rank=2)
    br = _message("boiler-reply", body="> Please review the attached proposal.\n\nWhich one?", subject="Re: Proposal", rank=3)
    shared = "Please review the attached proposal."
    cases.append(
        BenchmarkCase(
            "boilerplate-collision",
            "Identical boilerplate in unrelated sources must remain an alternative-source set.",
            "ambiguous_source",
            (b1, b2, br),
            quotes=(
                QuoteGold(
                    "boiler-q1",
                    "boiler-reply",
                    find_span(br.expected_text, "> Please review the attached proposal."),
                    (
                        SourceSpan("boiler-a", find_span(b1.expected_text, shared)),
                        SourceSpan("boiler-b", find_span(b2.expected_text, shared)),
                    ),
                    notes="Unique source attribution is unsupported.",
                ),
            ),
            spans=(
                LabeledSpan("boiler-a-decision", "boiler-a", find_span(b1.expected_text, "Decision: approve Alpha."), "decision_bearing", "Decision: approve Alpha."),
                LabeledSpan("boiler-b-decision", "boiler-b", find_span(b2.expected_text, "Decision: reject Beta."), "decision_bearing", "Decision: reject Beta."),
            ),
            replay_orders=(("boiler-a", "boiler-b", "boiler-reply"),),
            tags=("E1", "E2", "E4"),
        )
    )

    # Edited short quotation.
    es = _message("edit-source", body="Ship 10 units Monday.", subject="Shipment", rank=1)
    er = _message("edit-reply", body="> Ship 12 units Monday.\n\nPlease use the revised quantity.", subject="Re: Shipment", rank=2)
    cases.append(
        BenchmarkCase(
            "short-edited-quote",
            "A short edited quote must not be silently normalized back to the source wording.",
            "edited_quote",
            (es, er),
            quotes=(
                QuoteGold("edit-q1", "edit-reply", find_span(er.expected_text, "> Ship 12 units Monday."), (SourceSpan("edit-source", find_span(es.expected_text, "Ship 10 units Monday.")),), marker_style="plain_gt", notes="Fuzzy structural source relation; quoted text itself differs and must be preserved."),
            ),
            spans=(
                LabeledSpan("edit-decision-source", "edit-source", find_span(es.expected_text, "10"), "decision_bearing", "10"),
                LabeledSpan("edit-decision-reply", "edit-reply", find_span(er.expected_text, "12"), "decision_bearing", "12"),
            ),
            replay_orders=(("edit-source", "edit-reply"),),
            tags=("E1", "E2", "E4"),
        )
    )

    # Markerless copy: gold quotation, baseline structural detector should miss it.
    ms = _message("markerless-source", body="Escalate incident INC-42 before 17:00.", subject="Incident", rank=1)
    mr = _message("markerless-reply", body="Escalate incident INC-42 before 17:00.\nI will handle it.", subject="Re: Incident", rank=2)
    cases.append(
        BenchmarkCase(
            "markerless-copy",
            "Copied source text without a quotation marker exposes detector recall limits.",
            "markerless_quote",
            (ms, mr),
            quotes=(
                QuoteGold("markerless-q1", "markerless-reply", find_span(mr.expected_text, "Escalate incident INC-42 before 17:00."), (SourceSpan("markerless-source", find_span(ms.expected_text, "Escalate incident INC-42 before 17:00.")),), marker_style="markerless"),
            ),
            spans=(LabeledSpan("markerless-decision", "markerless-source", find_span(ms.expected_text, "before 17:00"), "decision_bearing", "before 17:00"),),
            replay_orders=(("markerless-source", "markerless-reply"),),
            tags=("E1", "E2"),
        )
    )

    # HTML blockquote/table fixture. Quote occurrence text is structurally explicit.
    hs_html = "<html><body><p>Approval limit:</p><table><tr><th>Region</th><th>Limit</th></tr><tr><td>AU</td><td>AUD 50,000</td></tr></table></body></html>"
    hr_html = "<html><body><blockquote><p>Approval limit:</p><table><tr><th>Region</th><th>Limit</th></tr><tr><td>AU</td><td>AUD 50,000</td></tr></table></blockquote><p>Keep the AU limit unchanged.</p></body></html>"
    visible = "Approval limit:\nRegion | Limit\nAU | AUD 50,000"
    hs = _html_message("html-source", html=hs_html, expected_text=visible, subject="Limits", rank=1)
    hr = _html_message(
        "html-reply", html=hr_html, expected_text=visible + "\nKeep the AU limit unchanged.",
        subject="Re: Limits", rank=2
    )
    # Choose the visible source segment common to both; the blockquote detector range
    # can be broader than this gold semantic quotation span.
    cases.append(
        BenchmarkCase(
            "html-table-nested",
            "HTML blockquote containing a table must preserve decision-bearing cell text and structure.",
            "html_table",
            (hs, hr),
            quotes=(
                QuoteGold("html-q1", "html-reply", find_span(hr.expected_text, visible), (SourceSpan("html-source", find_span(hs.expected_text, visible)),), marker_style="html_blockquote"),
            ),
            spans=(
                LabeledSpan("html-source-limit", "html-source", find_span(hs.expected_text, "AUD 50,000"), "decision_bearing", "AUD 50,000"),
                LabeledSpan("html-reply-limit", "html-reply", find_span(hr.expected_text, "AUD 50,000"), "decision_bearing", "AUD 50,000"),
            ),
            replay_orders=(("html-source", "html-reply"),),
            tags=("E1", "E2"),
        )
    )

    # Multipart/alternative: current research baseline intentionally prefers text/plain.
    plain = "Limit is AUD 75,000.\nCondition: CFO approval required."
    html = "<p>Limit is <b>AUD 75,000</b>.</p><p>Condition: CFO approval required.</p>"
    mm = _multipart_message("mime-alternative", plain=plain, html=html, subject="Limit", rank=1)
    cases.append(
        BenchmarkCase(
            "mime-alternative-preservation",
            "Multipart alternative fixture checks decision-bearing text survives the selected representation.",
            "mime_alternative",
            (mm,),
            spans=(
                LabeledSpan("mime-limit", "mime-alternative", find_span(mm.expected_text, "AUD 75,000"), "decision_bearing", "AUD 75,000"),
                LabeledSpan("mime-condition", "mime-alternative", find_span(mm.expected_text, "Condition: CFO approval required."), "condition", "Condition: CFO approval required."),
            ),
            replay_orders=(("mime-alternative",),),
            tags=("E1", "E2"),
        )
    )

    # Duplicate Message-ID: the header identifier cannot uniquely select one source.
    dup_id = "<duplicate@synthetic.invalid>"
    d1 = _message_custom_id(
        "dup-a", internet_id=dup_id, raw_message_id=dup_id,
        body="Alpha decision is approved.", subject="Duplicate", rank=1,
    )
    d2 = _message_custom_id(
        "dup-b", internet_id=dup_id, raw_message_id=dup_id,
        body="Beta decision is rejected.", subject="Duplicate", rank=2,
    )
    dr = _message(
        "dup-reply", body="> Alpha decision is approved.\n\nNoted.", subject="Re: Duplicate", rank=3,
        in_reply_to=(dup_id,), references=(dup_id,),
    )
    cases.append(BenchmarkCase(
        "duplicate-message-id",
        "Two distinct observed messages share one Message-ID; a later reference cannot justify a unique parent from the identifier alone.",
        "duplicate_id",
        (d1, d2, dr),
        relations=(RelationGold("dup-reply", "reply_parent", target_ids=("dup-a", "dup-b"), ambiguous=True, notes="Identifier collision; do not force a unique parent."),),
        quotes=(QuoteGold("dup-q1", "dup-reply", find_span(dr.expected_text, "> Alpha decision is approved."), (SourceSpan("dup-a", find_span(d1.expected_text, "Alpha decision is approved.")),), marker_style="plain_gt"),),
        replay_orders=(("dup-a", "dup-b", "dup-reply"), ("dup-b", "dup-a", "dup-reply"), ("dup-reply", "dup-a", "dup-b")),
        tags=("E1", "E3", "duplicate-id"),
    ))

    # Headerless historical source plus an unresolved external parent reference.
    hsource = _message_custom_id(
        "headerless-source", internet_id="", raw_message_id=None,
        body="Retain clause 9 unchanged.", subject="Clause 9", rank=1,
        notes="Raw source deliberately lacks Message-ID.",
    )
    href = "<unknown-parent@synthetic.invalid>"
    hreply = _message(
        "headerless-reply", body="> Retain clause 9 unchanged.\n\nAcknowledged.", subject="Re: Clause 9", rank=2,
        in_reply_to=(href,), references=(href,),
    )
    cases.append(BenchmarkCase(
        "headerless-source-and-missing-parent",
        "Quoted content can align to an observed source even when reply-parent metadata points to an unavailable identifier.",
        "missing_identifier",
        (hsource, hreply),
        relations=(RelationGold("headerless-reply", "reply_parent", target_ids=(), missing_target_ids=(href,), notes="Do not substitute content similarity for the missing header parent."),),
        quotes=(QuoteGold("headerless-q1", "headerless-reply", find_span(hreply.expected_text, "> Retain clause 9 unchanged."), (SourceSpan("headerless-source", find_span(hsource.expected_text, "Retain clause 9 unchanged.")),), marker_style="plain_gt"),),
        replay_orders=(("headerless-source", "headerless-reply"), ("headerless-reply", "headerless-source")),
        tags=("E1", "E3", "missing-id"),
    ))

    # Metadata parent and quoted source are deliberately different relations.
    ca = _message("conflict-parent", body="Parent metadata message only.", subject="Conflict", rank=1)
    cb = _message("conflict-quoted", body="Quoted evidence belongs here.", subject="Conflict", rank=2)
    cr = _message(
        "conflict-reply", body="> Quoted evidence belongs here.\n\nReply text.", subject="Re: Conflict", rank=3,
        in_reply_to=(ca.internet_message_id,), references=(ca.internet_message_id,),
    )
    cases.append(BenchmarkCase(
        "header-vs-quote-source-conflict",
        "Reply-parent metadata and quotation provenance point to different messages and must remain separate relation types.",
        "evidence_conflict",
        (ca, cb, cr),
        relations=(RelationGold("conflict-reply", "reply_parent", target_ids=("conflict-parent",)),),
        quotes=(QuoteGold("conflict-q1", "conflict-reply", find_span(cr.expected_text, "> Quoted evidence belongs here."), (SourceSpan("conflict-quoted", find_span(cb.expected_text, "Quoted evidence belongs here.")),), marker_style="plain_gt"),),
        replay_orders=(("conflict-parent", "conflict-quoted", "conflict-reply"), ("conflict-reply", "conflict-parent", "conflict-quoted")),
        tags=("E1", "E3", "conflicting-evidence"),
    ))

    # Same subject is not ancestry evidence by itself.
    su1 = _message("same-subject-a", body="Unrelated Alpha matter.", subject="Weekly update", rank=1)
    su2 = _message("same-subject-b", body="Unrelated Beta matter.", subject="Weekly update", rank=2)
    cases.append(BenchmarkCase(
        "same-subject-unrelated",
        "Two messages share a subject but have no ancestry evidence.",
        "subject_false_friend",
        (su1, su2),
        relations=(), quotes=(), replay_orders=(("same-subject-a", "same-subject-b"),), tags=("E1",),
    ))

    # Subject changes do not erase explicit reply metadata.
    cs = _message("changed-subject-root", body="Original matter remains active.", subject="Old subject", rank=1)
    csr = _message(
        "changed-subject-reply", body="> Original matter remains active.\n\nNew framing, same reply relation.",
        subject="Completely new subject text", rank=2,
        in_reply_to=(cs.internet_message_id,), references=(cs.internet_message_id,),
    )
    cases.append(BenchmarkCase(
        "changed-subject-reply",
        "Explicit ancestry remains evidence even when the subject changes completely.",
        "subject_change",
        (cs, csr),
        relations=(RelationGold("changed-subject-reply", "reply_parent", target_ids=("changed-subject-root",)),),
        quotes=(QuoteGold("changed-subject-q1", "changed-subject-reply", find_span(csr.expected_text, "> Original matter remains active."), (SourceSpan("changed-subject-root", find_span(cs.expected_text, "Original matter remains active.")),), marker_style="plain_gt"),),
        replay_orders=(("changed-subject-root", "changed-subject-reply"),), tags=("E1", "E3"),
    ))

    # Interleaved replies create multiple occurrence spans against one source.
    irs = _message(
        "inline-source",
        body="Question one: approve Alpha?\nQuestion two: approve Beta?",
        subject="Inline", rank=1,
    )
    irr = _message(
        "inline-reply",
        body="> Question one: approve Alpha?\nYes for Alpha.\n\n> Question two: approve Beta?\nNo for Beta.",
        subject="Re: Inline", rank=2,
        in_reply_to=(irs.internet_message_id,), references=(irs.internet_message_id,),
    )
    cases.append(BenchmarkCase(
        "interleaved-inline-reply",
        "Two separated quote occurrences from one source are interleaved with distinct new reply text.",
        "interleaved_reply",
        (irs, irr),
        relations=(RelationGold("inline-reply", "reply_parent", target_ids=("inline-source",)),),
        quotes=(
            QuoteGold("inline-q1", "inline-reply", find_span(irr.expected_text, "> Question one: approve Alpha?"), (SourceSpan("inline-source", find_span(irs.expected_text, "Question one: approve Alpha?")),), marker_style="plain_gt"),
            QuoteGold("inline-q2", "inline-reply", find_span(irr.expected_text, "> Question two: approve Beta?"), (SourceSpan("inline-source", find_span(irs.expected_text, "Question two: approve Beta?")),), marker_style="plain_gt"),
        ),
        spans=(
            LabeledSpan("inline-new-a", "inline-reply", find_span(irr.expected_text, "Yes for Alpha."), "new_content", "Yes for Alpha."),
            LabeledSpan("inline-new-b", "inline-reply", find_span(irr.expected_text, "No for Beta."), "new_content", "No for Beta."),
        ),
        replay_orders=(("inline-source", "inline-reply"),), tags=("E1", "E2", "E3"),
    ))

    # Forwarded block: structural `>` detector intentionally does not treat this as a quote.
    fs = _message("forward-source", body="Decision: approve Gamma rollout.", subject="Gamma", rank=1)
    fwd_text = "Decision: approve Gamma rollout."
    fr = _message(
        "forward-wrapper",
        body="FYI\n\n---------- Forwarded message ----------\nFrom: synthetic@example.invalid\nSubject: Gamma\n\nDecision: approve Gamma rollout.",
        subject="Fwd: Gamma", rank=2,
    )
    cases.append(BenchmarkCase(
        "forwarded-message-block",
        "Forwarded content remains evidence even without RFC-style quote markers; the simple structural quote detector is expected to miss it.",
        "forwarded_block",
        (fs, fr),
        quotes=(QuoteGold("forward-q1", "forward-wrapper", find_span(fr.expected_text, fwd_text), (SourceSpan("forward-source", find_span(fs.expected_text, fwd_text)),), marker_style="forwarded_block"),),
        spans=(LabeledSpan("forward-decision", "forward-wrapper", find_span(fr.expected_text, fwd_text), "decision_bearing", fwd_text),),
        replay_orders=(("forward-source", "forward-wrapper"),),
        tags=("E1", "E2", "forward"),
    ))

    # Truncated References: explicit In-Reply-To remains the direct-parent evidence.
    tr_root = _message("tr-root", body="Root statement.", subject="References", rank=1)
    tr_mid = _message(
        "tr-mid", body="> Root statement.\n\nMiddle reply.", subject="Re: References", rank=2,
        in_reply_to=(tr_root.internet_message_id,), references=(tr_root.internet_message_id,),
    )
    tr_reply = _message(
        "tr-reply", body="> Middle reply.\n\nFinal reply.", subject="Re: References", rank=3,
        in_reply_to=(tr_mid.internet_message_id,),
        # Deliberately truncated/misaligned References contains only the root.
        references=(tr_root.internet_message_id,),
    )
    cases.append(BenchmarkCase(
        "truncated-references",
        "A truncated References chain must not replace explicit In-Reply-To direct-parent evidence.",
        "truncated_references",
        (tr_root, tr_mid, tr_reply),
        relations=(
            RelationGold("tr-mid", "reply_parent", target_ids=("tr-root",)),
            RelationGold("tr-reply", "reply_parent", target_ids=("tr-mid",)),
            RelationGold("tr-reply", "ancestry", target_ids=("tr-root",), notes="Ancestry is distinct from direct parent."),
        ),
        quotes=(
            QuoteGold("tr-q1", "tr-mid", find_span(tr_mid.expected_text, "> Root statement."), (SourceSpan("tr-root", find_span(tr_root.expected_text, "Root statement.")),), marker_style="plain_gt"),
            QuoteGold("tr-q2", "tr-reply", find_span(tr_reply.expected_text, "> Middle reply."), (SourceSpan("tr-mid", find_span(tr_mid.expected_text, "Middle reply.")),), marker_style="plain_gt"),
        ),
        replay_orders=(("tr-root", "tr-mid", "tr-reply"), ("tr-reply", "tr-root", "tr-mid")),
        tags=("E1", "E3", "references"),
    ))

    # Exact text reuse can be boilerplate without being a quotation.
    nb1 = _message("reuse-boiler-source", body="Please review the attached proposal.\nAlpha context.", subject="Boilerplate", rank=1)
    nb2 = _message("reuse-boiler-new", body="Please review the attached proposal.\nThis is independently written new content.", subject="Different matter", rank=2)
    cases.append(BenchmarkCase(
        "boilerplate-reuse-not-quotation",
        "Exact repeated boilerplate is a negative control for reuse-augmented quote detection.",
        "reuse_negative_control",
        (nb1, nb2),
        relations=(), quotes=(),
        spans=(LabeledSpan("reuse-new", "reuse-boiler-new", find_span(nb2.expected_text, "This is independently written new content."), "new_content", "This is independently written new content."),),
        replay_orders=(("reuse-boiler-source", "reuse-boiler-new"),),
        tags=("E1", "E2", "negative-control"),
    ))

    # format=flowed / space-stuffing fixture.
    ff = _message(
        "flowed",
        body="> quoted line one \n> continues here\n -- not a signature separator after unstuffing",
        subject="Flowed",
        rank=1,
        content_type='text/plain; charset=utf-8; format=flowed; delsp=yes',
        expected_text="> quoted line onecontinues here\n-- not a signature separator after unstuffing",
        notes="Exercises a small RFC3676-oriented baseline; not a full conformance suite.",
    )
    cases.append(
        BenchmarkCase(
            "format-flowed",
            "Flowed quoted lines exercise quote-depth-aware normalization and space-stuffing behavior.",
            "format_flowed",
            (ff,),
            quotes=(
                QuoteGold(
                    "flowed-q1",
                    "flowed",
                    find_span(ff.expected_text, "> quoted line onecontinues here"),
                    source_candidates=(),
                    source_missing=True,
                    marker_style="plain_gt",
                    notes="The quoted source is intentionally unavailable in this fixture.",
                ),
            ),
            spans=(),
            replay_orders=(("flowed",),),
            tags=("E1", "E2"),
        )
    )

    validate_cases(cases)
    return tuple(cases)


def write_fixture_corpus(directory: Path) -> None:
    import hashlib
    import json

    directory.mkdir(parents=True, exist_ok=True)
    cases = canonical_cases()
    manifest: dict[str, object] = {"schema_version": "topic01-engineering-v1", "cases": []}
    for case in cases:
        cdir = directory / case.case_id
        cdir.mkdir(exist_ok=True)
        (cdir / "gold.json").write_text(json.dumps(case.to_dict(), ensure_ascii=False, indent=2) + "\n")
        msg_entries = []
        for message in case.messages:
            path = cdir / f"{message.message_id}.eml"
            path.write_bytes(message.raw_rfc822)
            msg_entries.append({
                "message_id": message.message_id,
                "path": str(path.relative_to(directory.parent)),
                "sha256": hashlib.sha256(message.raw_rfc822).hexdigest(),
                "bytes": len(message.raw_rfc822),
            })
        manifest["cases"].append({"case_id": case.case_id, "family": case.family, "messages": msg_entries})
    (directory / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

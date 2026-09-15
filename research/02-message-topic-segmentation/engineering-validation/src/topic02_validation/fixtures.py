"""Independently authored synthetic/adversarial fixtures for Topic 02.

Gold text and labels are authored here; no unit segmenter, assignment baseline,
or representation component is called to create expected answers.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json

from .models import (
    BenchmarkCase, ContextStepGold, EvidenceSpan, MembershipGold, Span,
    TopicDefinition, TopicObjectGold, validate_cases,
)


def _nth_span(text: str, needle: str, nth: int = 0) -> Span:
    start = -1
    cursor = 0
    for _ in range(nth + 1):
        start = text.find(needle, cursor)
        if start < 0:
            raise ValueError(f"substring not found: {needle!r} occurrence {nth}")
        cursor = start + 1
    return Span(start, start + len(needle))


def S(text: str, sid: str, needle: str, *, kind: str = "topic_evidence", origin: str = "authored", nth: int = 0) -> EvidenceSpan:
    return EvidenceSpan(sid, _nth_span(text, needle, nth), needle, origin, kind)


def M(sid: str, *topics: str, notes: str = "") -> MembershipGold:
    return MembershipGold(sid, required_topics=tuple(topics), notes=notes)


def A(sid: str, *alternative_sets: tuple[str, ...], notes: str = "") -> MembershipGold:
    return MembershipGold(sid, alternative_topic_sets=tuple(tuple(x) for x in alternative_sets), abstention_allowed=True, notes=notes)


def T(tid: str, description: str, *terms: str) -> TopicDefinition:
    return TopicDefinition(tid, description, tuple(terms))


def O(tid: str, *span_ids: str) -> TopicObjectGold:
    return TopicObjectGold(tid, tuple(span_ids))


def canonical_cases() -> tuple[BenchmarkCase, ...]:
    cases: list[BenchmarkCase] = []

    # 1. Single matter + deadline.
    text = "Please approve the Atlas budget by Friday."
    spans = (
        S(text, "s1", "Please approve the Atlas budget by Friday."),
        S(text, "d1", "Friday", kind="deadline"),
        S(text, "a1", "approve the Atlas budget", kind="decision"),
    )
    cases.append(BenchmarkCase(
        "single-topic-deadline", "Single work matter with a decision and deadline.", text,
        (T("ATLAS", "Atlas budget approval", "atlas", "budget", "approve"),), spans,
        (M("s1", "ATLAS"), M("d1", "ATLAS"), M("a1", "ATLAS")),
        (O("ATLAS", "s1"),), tags=("EV1", "EV2", "EV4"),
    ))

    # 2. Two contiguous matters.
    text = "Atlas budget is approved. Beta release moves to Tuesday."
    spans = (S(text, "a", "Atlas budget is approved."), S(text, "b", "Beta release moves to Tuesday."), S(text, "bd", "Tuesday", kind="deadline"))
    cases.append(BenchmarkCase(
        "two-topics-contiguous", "Two independent contiguous work matters.", text,
        (T("ATLAS", "Atlas budget", "atlas", "budget"), T("BETA", "Beta release schedule", "beta", "release")), spans,
        (M("a", "ATLAS"), M("b", "BETA"), M("bd", "BETA")), (O("ATLAS", "a"), O("BETA", "b")), tags=("EV1", "EV2", "EV3"),
    ))

    # 3. A-B-A non-contiguous recurrence in one message.
    text = "Atlas budget needs Legal sign-off. Beta release is Tuesday. Atlas vendor quote expires Friday."
    spans = (
        S(text, "a1", "Atlas budget needs Legal sign-off."),
        S(text, "b1", "Beta release is Tuesday."),
        S(text, "a2", "Atlas vendor quote expires Friday."),
        S(text, "a-cond", "Legal sign-off", kind="condition"),
        S(text, "a-dead", "Friday", kind="deadline"),
    )
    cases.append(BenchmarkCase(
        "noncontiguous-aba", "Atlas evidence recurs after an intervening Beta matter.", text,
        (T("ATLAS", "Atlas budget/vendor approval", "atlas", "budget", "vendor"), T("BETA", "Beta release", "beta", "release")), spans,
        (M("a1", "ATLAS"), M("b1", "BETA"), M("a2", "ATLAS"), M("a-cond", "ATLAS"), M("a-dead", "ATLAS")),
        (O("ATLAS", "a1", "a2"), O("BETA", "b1")), tags=("EV1", "EV2", "EV3", "noncontiguous"),
    ))

    # 4. One span jointly belongs to two matters.
    text = "The security review blocks both Atlas deployment and Beta release."
    spans = (S(text, "shared", text, kind="supporting_evidence"),)
    cases.append(BenchmarkCase(
        "overlap-shared-span", "One evidence span simultaneously belongs to two work matters.", text,
        (T("ATLAS", "Atlas deployment", "atlas", "deployment", "security"), T("BETA", "Beta release", "beta", "release", "security")), spans,
        (M("shared", "ATLAS", "BETA", notes="Joint membership, not ambiguity."),),
        (O("ATLAS", "shared"), O("BETA", "shared")), tags=("EV1", "EV3", "overlap"),
    ))

    # 5. Two matters inside one sentence / clause boundary.
    text = "Approve Atlas if Legal signs off, but postpone Beta until QA passes."
    spans = (
        S(text, "atlas-clause", "Approve Atlas if Legal signs off"),
        S(text, "beta-clause", "postpone Beta until QA passes"),
        S(text, "legal-cond", "Legal signs off", kind="condition"),
        S(text, "qa-cond", "QA passes", kind="condition"),
    )
    cases.append(BenchmarkCase(
        "clause-split-two-matters", "One sentence contains two work matters with separate conditions.", text,
        (T("ATLAS", "Atlas approval", "atlas", "legal"), T("BETA", "Beta release postponement", "beta", "qa")), spans,
        (M("atlas-clause", "ATLAS"), M("beta-clause", "BETA"), M("legal-cond", "ATLAS"), M("qa-cond", "BETA")),
        (O("ATLAS", "atlas-clause"), O("BETA", "beta-clause")), tags=("EV2", "EV4", "clause"),
    ))

    # 6. Condition scope must not leak to Beta.
    text = "Atlas is approved only if Finance confirms funding. Beta is already funded."
    spans = (
        S(text, "atlas", "Atlas is approved only if Finance confirms funding."),
        S(text, "beta", "Beta is already funded."),
        S(text, "fund-cond", "only if Finance confirms funding", kind="condition"),
    )
    cases.append(BenchmarkCase(
        "condition-scope", "A condition narrows Atlas only, not neighboring Beta.", text,
        (T("ATLAS", "Atlas approval", "atlas", "finance"), T("BETA", "Beta funding", "beta", "funded")), spans,
        (M("atlas", "ATLAS"), M("beta", "BETA"), M("fund-cond", "ATLAS")), (O("ATLAS", "atlas"), O("BETA", "beta")), tags=("EV4",),
    ))

    # 7. Exception scope.
    text = "Approve Atlas except the EU rollout; Beta approval is unchanged."
    spans = (
        S(text, "atlas", "Approve Atlas except the EU rollout"),
        S(text, "beta", "Beta approval is unchanged."),
        S(text, "exception", "except the EU rollout", kind="exception"),
    )
    cases.append(BenchmarkCase(
        "exception-scope", "An exception belongs only to Atlas.", text,
        (T("ATLAS", "Atlas approval", "atlas", "eu"), T("BETA", "Beta approval", "beta")), spans,
        (M("atlas", "ATLAS"), M("beta", "BETA"), M("exception", "ATLAS")), (O("ATLAS", "atlas"), O("BETA", "beta")), tags=("EV4",),
    ))

    # 8. Shared supporting evidence.
    text = "The same vendor certificate supports Atlas and Beta compliance."
    spans = (S(text, "shared-evidence", text, kind="supporting_evidence"),)
    cases.append(BenchmarkCase(
        "shared-supporting-evidence", "One evidence item supports two matters.", text,
        (T("ATLAS", "Atlas compliance", "atlas", "compliance"), T("BETA", "Beta compliance", "beta", "compliance")), spans,
        (M("shared-evidence", "ATLAS", "BETA"),), (O("ATLAS", "shared-evidence"), O("BETA", "shared-evidence")), tags=("EV3", "EV4"),
    ))

    # 9. Heading plus list items.
    text = "Atlas rollout:\n- Legal approval pending.\n- Vendor quote due Friday.\nBeta release:\n- QA complete."
    spans = (
        S(text, "ah", "Atlas rollout:", kind="heading"),
        S(text, "a1", "Legal approval pending."),
        S(text, "a2", "Vendor quote due Friday."),
        S(text, "ad", "Friday", kind="deadline"),
        S(text, "bh", "Beta release:", kind="heading"),
        S(text, "b1", "QA complete."),
    )
    cases.append(BenchmarkCase(
        "heading-list-scope", "Headings govern following list items without becoming separate matters.", text,
        (T("ATLAS", "Atlas rollout", "atlas", "rollout", "legal", "vendor"), T("BETA", "Beta release", "beta", "release", "qa")), spans,
        (M("ah", "ATLAS"), M("a1", "ATLAS"), M("a2", "ATLAS"), M("ad", "ATLAS"), M("bh", "BETA"), M("b1", "BETA")),
        (O("ATLAS", "ah", "a1", "a2"), O("BETA", "bh", "b1")), tags=("EV2", "EV4", "list"),
    ))

    # 10. Table-like rows.
    text = "Matter | Owner | Deadline\nAtlas | Ana | Friday\nBeta | Ben | Tuesday"
    spans = (
        S(text, "arow", "Atlas | Ana | Friday"), S(text, "brow", "Beta | Ben | Tuesday"),
        S(text, "ad", "Friday", kind="deadline"), S(text, "bd", "Tuesday", kind="deadline"),
    )
    cases.append(BenchmarkCase(
        "table-rows", "Different table rows belong to different matters.", text,
        (T("ATLAS", "Atlas owner/deadline", "atlas", "ana", "friday"), T("BETA", "Beta owner/deadline", "beta", "ben", "tuesday")), spans,
        (M("arow", "ATLAS"), M("brow", "BETA"), M("ad", "ATLAS"), M("bd", "BETA")),
        (O("ATLAS", "arow"), O("BETA", "brow")), tags=("EV2", "EV4", "table"),
    ))

    # 11. Genuine ambiguity; later context resolves it.
    text = "This change needs approval before Friday."
    spans = (S(text, "amb", text), S(text, "deadline", "Friday", kind="deadline"))
    cases.append(BenchmarkCase(
        "ambiguous-reference", "The current message alone does not identify which matter 'this change' refers to.", text,
        (T("ATLAS", "Atlas budget change", "atlas", "budget"), T("BETA", "Beta release change", "beta", "release")), spans,
        (A("amb", ("ATLAS",), ("BETA",), notes="Either matter is possible from current text; abstention is valid."), A("deadline", ("ATLAS",), ("BETA",))),
        (),
        context_texts=(("ctx-atlas", "Earlier context: this change is the Atlas budget revision."),),
        context_steps=(
            ContextStepGold("without-context", (), (), ("amb", "deadline"), "Must abstain without antecedent context."),
            ContextStepGold("with-atlas-context", ("ctx-atlas",), (("amb", ("ATLAS",)), ("deadline", ("ATLAS",))), (), "Context resolves the matter."),
        ), tags=("EV5", "EV6", "ambiguity"),
    ))

    # 12. Quoted history vs authored content.
    text = "> Atlas budget requires CFO approval.\nNew: Beta release is Tuesday."
    spans = (
        S(text, "quoted-atlas", "> Atlas budget requires CFO approval.", origin="quoted"),
        S(text, "authored-beta", "New: Beta release is Tuesday.", origin="authored"),
        S(text, "cfo", "CFO approval", kind="approval_constraint", origin="quoted"),
    )
    cases.append(BenchmarkCase(
        "quoted-vs-authored", "Quoted Topic evidence and newly authored Topic evidence remain distinguishable.", text,
        (T("ATLAS", "Atlas budget", "atlas", "budget", "cfo"), T("BETA", "Beta release", "beta", "release")), spans,
        (M("quoted-atlas", "ATLAS"), M("authored-beta", "BETA"), M("cfo", "ATLAS")),
        (O("ATLAS", "quoted-atlas"), O("BETA", "authored-beta")), tags=("EV1", "EV4", "origin"),
    ))

    # 13. Shared span plus matter-specific scope.
    text = "Atlas and Beta share the security exception, but only Atlas needs Legal approval."
    spans = (
        S(text, "shared", "Atlas and Beta share the security exception"),
        S(text, "atlas-only", "only Atlas needs Legal approval"),
        S(text, "legal", "Legal approval", kind="approval_constraint"),
    )
    cases.append(BenchmarkCase(
        "shared-plus-specific", "Shared evidence coexists with a matter-specific approval constraint.", text,
        (T("ATLAS", "Atlas security/approval", "atlas", "security", "legal"), T("BETA", "Beta security", "beta", "security")), spans,
        (M("shared", "ATLAS", "BETA"), M("atlas-only", "ATLAS"), M("legal", "ATLAS")),
        (O("ATLAS", "shared", "atlas-only"), O("BETA", "shared")), tags=("EV3", "EV4"),
    ))

    # 14. Same lexical token, different concrete matters.
    text = "Atlas budget for Project North is approved. Atlas vendor issue for Project South remains open."
    spans = (S(text, "north", "Atlas budget for Project North is approved."), S(text, "south", "Atlas vendor issue for Project South remains open."))
    cases.append(BenchmarkCase(
        "same-term-different-matters", "Shared lexical token Atlas does not make two concrete work matters identical.", text,
        (T("NORTH", "Project North Atlas budget", "north", "budget"), T("SOUTH", "Project South Atlas vendor issue", "south", "vendor")), spans,
        (M("north", "NORTH"), M("south", "SOUTH")), (O("NORTH", "north"), O("SOUTH", "south")), tags=("EV3", "lexical-collision"),
    ))

    # 15. Context correction/retraction A -> B with an unaffected neighboring matter.
    text = "Use the same approval limit as before. North audit remains open."
    spans = (
        S(text, "ref", "Use the same approval limit as before.", kind="context_reference"),
        S(text, "neighbor", "North audit remains open."),
    )
    cases.append(BenchmarkCase(
        "context-correction", "Later context corrects one ambiguous interpretation without changing a neighboring explicit matter.", text,
        (
            T("ATLAS", "Atlas approval limit", "atlas", "approval", "limit"),
            T("BETA", "Beta approval limit", "beta", "approval", "limit"),
            T("NORTH", "North audit", "north", "audit"),
        ), spans,
        (
            A("ref", ("ATLAS",), ("BETA",), notes="Message text alone is ambiguous."),
            M("neighbor", "NORTH", notes="Control span must remain NORTH through correction."),
        ), (O("NORTH", "neighbor"),),
        context_texts=(
            ("ctx1", "Earlier note: the approval limit discussion concerned Atlas."),
            ("ctx2", "Correction: 'same approval limit' in this message refers to Beta, not Atlas."),
        ),
        context_steps=(
            ContextStepGold("no-context", (), (("neighbor", ("NORTH",)),), ("ref",)),
            ContextStepGold("initial-context", ("ctx1",), (("ref", ("ATLAS",)), ("neighbor", ("NORTH",))), ()),
            ContextStepGold("corrected-context", ("ctx1", "ctx2"), (("ref", ("BETA",)), ("neighbor", ("NORTH",))), (), "Later explicit correction supersedes only the ambiguous reference; neighboring explicit matter stays unchanged."),
        ), tags=("EV5", "correction"),
    ))

    # 16. Irrelevant chatter should yield no Topic evidence.
    text = "Thanks everyone, have a good evening."
    cases.append(BenchmarkCase(
        "irrelevant-chatter", "No work matter should be invented for social chatter.", text,
        (T("ATLAS", "Atlas budget", "atlas", "budget"),), (), (), (), tags=("EV3", "negative-control"),
    ))

    # 17. Evidence shared, decision only one matter.
    text = "The audit report concerns Atlas and Beta. Approve Atlas now; Beta remains under review."
    spans = (
        S(text, "evidence", "The audit report concerns Atlas and Beta.", kind="supporting_evidence"),
        S(text, "adec", "Approve Atlas now", kind="decision"),
        S(text, "bstate", "Beta remains under review."),
    )
    cases.append(BenchmarkCase(
        "shared-evidence-separate-decision", "Shared evidence must not broaden an Atlas-only decision into Beta.", text,
        (T("ATLAS", "Atlas audit approval", "atlas", "audit", "approve"), T("BETA", "Beta audit review", "beta", "audit", "review")), spans,
        (M("evidence", "ATLAS", "BETA"), M("adec", "ATLAS"), M("bstate", "BETA")),
        (O("ATLAS", "evidence", "adec"), O("BETA", "evidence", "bstate")), tags=("EV3", "EV4", "scope"),
    ))

    # 18. Non-contiguous Topic with an overlapping shared middle span.
    text = "Atlas budget opens Monday. Shared security review applies to Atlas and Beta. Atlas approval closes Friday."
    spans = (
        S(text, "a1", "Atlas budget opens Monday."),
        S(text, "shared", "Shared security review applies to Atlas and Beta.", kind="supporting_evidence"),
        S(text, "a2", "Atlas approval closes Friday."),
        S(text, "fri", "Friday", kind="deadline"),
    )
    cases.append(BenchmarkCase(
        "noncontiguous-with-overlap", "Atlas has separated evidence and shares a middle span with Beta.", text,
        (T("ATLAS", "Atlas budget/approval", "atlas", "budget", "approval"), T("BETA", "Beta security review", "beta", "security")), spans,
        (M("a1", "ATLAS"), M("shared", "ATLAS", "BETA"), M("a2", "ATLAS"), M("fri", "ATLAS")),
        (O("ATLAS", "a1", "shared", "a2"), O("BETA", "shared")), tags=("EV1", "EV3", "noncontiguous", "overlap"),
    ))

    validate_cases(cases)
    return tuple(cases)


def write_fixture_corpus(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    cases = canonical_cases()
    rows = []
    for case in cases:
        path = root / f"{case.case_id}.gold.json"
        payload = json.dumps(case.to_dict(), ensure_ascii=False, indent=2) + "\n"
        path.write_text(payload)
        rows.append({"case_id": case.case_id, "path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    manifest = {
        "schema_version": "topic02-engineering-fixture-manifest-v1",
        "case_count": len(cases),
        "cases": rows,
        "gold_independence": "Authored literal message text and explicit span/topic annotations; no tested unit/assignment/representation component generates gold.",
    }
    (root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest

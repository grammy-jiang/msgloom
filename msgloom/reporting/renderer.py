"""Strict bounded Jinja rendering and structural coverage validation."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from pydantic import BaseModel, ConfigDict, Field, model_validator

from msgloom.contracts import Limitation, VersionRef

from .build import ReportBuildError
from .models import (
    PendingAssessmentWarning,
    ReportOverviewItem,
    ReportPart,
    ReportTopic,
)

_TEMPLATE_DIR = Path(__file__).with_name("templates")
RENDERER_VERSION = "jinja-report@2"
_ALLOWED_TAGS = {
    "a",
    "article",
    "body",
    "br",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "html",
    "li",
    "p",
    "strong",
    "ul",
}


class RendererConfig(BaseModel):
    """Trusted finite output limits for one report build."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    max_part_bytes: Annotated[int, Field(ge=1_024, le=4 * 1024 * 1024)]
    max_total_bytes: Annotated[int, Field(ge=2_048, le=8 * 1024 * 1024)]
    max_parts: Annotated[int, Field(ge=1, le=128)]

    @model_validator(mode="after")
    def _coherent(self) -> RendererConfig:
        if self.max_total_bytes < self.max_part_bytes:
            raise ValueError("total output bound must allow one full part")
        return self


class _OutputOverflow(Exception):
    """Stop streaming before a configured output byte ceiling is crossed."""


class _HTMLAudit(HTMLParser):
    """Collect visible article text while rejecting unsafe saved markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.article: str | None = None
        self.article_depth = 0
        self.article_text: dict[str, list[str]] = {}
        self.all_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _ALLOWED_TAGS:
            raise ReportBuildError("saved report HTML contains an unsafe tag")
        values = dict(attrs)
        if any(name.lower().startswith("on") for name, _value in attrs):
            raise ReportBuildError("saved report HTML contains an unsafe attribute")
        if tag == "a":
            if set(values) != {"href"} or not _safe_url(values.get("href")):
                raise ReportBuildError("saved report HTML contains an unsafe link")
        elif set(values) - {"data-topic"}:
            raise ReportBuildError("saved report HTML contains an unexpected attribute")
        if tag == "article":
            identity = values.get("data-topic")
            if not identity or identity in self.article_text:
                raise ReportBuildError("saved report HTML has invalid topic structure")
            self.article = identity
            self.article_depth = 1
            self.article_text[identity] = []
        elif self.article is not None:
            self.article_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self.article is None:
            return
        self.article_depth -= 1
        if tag == "article" and self.article_depth == 0:
            self.article = None

    def handle_data(self, data: str) -> None:
        self.all_text.append(data)
        if self.article is not None:
            self.article_text[self.article].append(data)


def render_report(
    report_ref: VersionRef,
    overview: tuple[ReportOverviewItem, ...],
    topics: tuple[ReportTopic, ...],
    warnings: tuple[PendingAssessmentWarning, ...],
    config: RendererConfig,
    limitations: tuple[Limitation, ...] = (),
) -> tuple[ReportPart, ...]:
    """Render finite parts without accumulating output beyond configured bounds."""
    config = RendererConfig.model_validate(config.model_dump(), strict=True)
    html_env, text_env = _environments()
    try:
        rendered = _render_groups(
            report_ref,
            overview,
            [topics],
            warnings,
            limitations,
            html_env,
            text_env,
            config,
        )
    except _OutputOverflow:
        groups = [(topic,) for topic in topics]
        if len(groups) > config.max_parts:
            raise ReportBuildError("report requires more output parts than configured")
        try:
            rendered = _render_groups(
                report_ref,
                overview,
                groups,
                warnings,
                limitations,
                html_env,
                text_env,
                config,
            )
        except _OutputOverflow:
            raise ReportBuildError(
                "one or more complete report topics exceed output bounds"
            ) from None
    parts = tuple(
        ReportPart(
            part_number=index,
            topic_refs=tuple(topic.topic_ref for topic in group),
            plain_text=plain,
            html=html,
        )
        for index, (group, plain, html) in enumerate(rendered, 1)
    )
    validate_rendered_coverage(topics, parts, overview, warnings, limitations)
    return parts


def validate_rendered_coverage(
    topics: tuple[ReportTopic, ...],
    parts: tuple[ReportPart, ...],
    overview: tuple[ReportOverviewItem, ...] | None = None,
    warnings: tuple[PendingAssessmentWarning, ...] = (),
    limitations: tuple[Limitation, ...] = (),
) -> None:
    """Require section-local identities/content and safe saved HTML."""
    mapped = [ref for part in parts for ref in part.topic_refs]
    if len(mapped) != len(set(mapped)) or set(mapped) != {x.topic_ref for x in topics}:
        raise ReportBuildError("rendered topic-to-part identity coverage failed")
    audits: dict[int, _HTMLAudit] = {}
    for part in parts:
        audit = _HTMLAudit()
        audit.feed(part.html)
        audit.close()
        audits[part.part_number] = audit
    first = min(parts, key=lambda item: item.part_number)
    overview_text = _between(first.plain_text, "OVERVIEW", "DETAILS")
    html_all = " ".join(audits[first.part_number].all_text)
    expected_overview = overview or tuple(
        ReportOverviewItem(
            topic_ref=t.topic_ref,
            assessment_ref=t.assessment_ref,
            title=t.title,
            priority=t.priority,
            developments=tuple(x.text for x in t.developments),
            actions=tuple(x.text for x in t.actions),
            deadlines=tuple(x.original_wording for x in t.deadlines),
            risks=tuple(x.text for x in t.risks),
        )
        for t in topics
    )
    overview_items_text = overview_text.split("PENDING WORK", 1)[0]
    overview_items_text = overview_items_text.split("REPORT LIMITATIONS", 1)[0]
    for item in expected_overview:
        if overview_items_text.count(_ref(item.topic_ref)) != 1:
            raise ReportBuildError("rendered overview identity is duplicated")
        values = (
            _ref(item.topic_ref),
            _ref(item.assessment_ref),
            item.title,
            item.priority.value,
            *item.developments,
            *item.actions,
            *item.deadlines,
            *item.risks,
        )
        _require_values(values, overview_text, html_all, "overview")
    for warning in warnings:
        _require_values(
            (
                _ref(warning.topic_ref),
                _ref(warning.selected_assessment_ref),
                _ref(warning.pending_ref),
                warning.detail,
            ),
            overview_text,
            html_all,
            "pending warning",
        )
    for limitation in limitations:
        _require_values(
            (limitation.code, limitation.detail),
            overview_text,
            html_all,
            "report limitation",
        )
    by_ref = {ref: part for part in parts for ref in part.topic_refs}
    for topic in topics:
        part = by_ref[topic.topic_ref]
        plain = _topic_plain(part.plain_text, topic.topic_ref)
        article = " ".join(
            audits[part.part_number].article_text.get(_ref(topic.topic_ref), ())
        )
        if not article:
            raise ReportBuildError("rendered HTML topic detail is missing")
        required = [
            _ref(topic.assessment_ref),
            topic.title,
            topic.priority.value,
            topic.reason,
            *[x.text for x in topic.developments],
            *[x.text for x in topic.risks],
            *[_ref(x) for x in topic.source_refs],
        ]
        for action in topic.actions:
            required.extend((action.text, action.owner.state.value))
            if action.owner.value is not None:
                required.append(action.owner.value)
        for deadline in topic.deadlines:
            required.extend(
                (deadline.original_wording, f"ambiguous={deadline.ambiguous}")
            )
            if deadline.interpreted_at is None:
                required.append("not interpreted")
            else:
                required.extend(
                    (
                        deadline.interpreted_at.isoformat(),
                        f"timezone basis={deadline.timezone_basis}",
                    )
                )
        for evidence in topic.evidence:
            required.extend(
                (evidence.kind.value, _ref(evidence.source_ref), evidence.statement)
            )
        for link in topic.source_links:
            required.append(link.url)
        for limitation in topic.limitations:
            required.extend((limitation.code, limitation.detail))
        _require_values(tuple(required), plain, article, "topic detail")


def _render_groups(
    report_ref: VersionRef,
    overview: tuple[ReportOverviewItem, ...],
    groups: list[tuple[ReportTopic, ...]],
    warnings: tuple[PendingAssessmentWarning, ...],
    limitations: tuple[Limitation, ...],
    html_env: Environment,
    text_env: Environment,
    config: RendererConfig,
) -> list[tuple[tuple[ReportTopic, ...], str, str]]:
    values = []
    total = 0
    for number, group in enumerate(groups, 1):
        context = {
            "report_ref": report_ref,
            "part_number": number,
            "part_count": len(groups),
            "show_overview": number == 1,
            "overview": overview,
            "topics": group,
            "warnings": warnings,
            "limitations": limitations,
        }
        plain = _bounded_template(
            text_env.get_template("report.txt.j2"), context, config.max_part_bytes
        )
        plain_bytes = len(plain.encode("utf-8"))
        html = _bounded_template(
            html_env.get_template("report.html.j2"),
            context,
            config.max_part_bytes - plain_bytes,
        )
        size = plain_bytes + len(html.encode("utf-8"))
        total += size
        if total > config.max_total_bytes or number > config.max_parts:
            raise _OutputOverflow
        values.append((group, plain, html))
    return values


def _bounded_template(template: object, context: dict[str, object], limit: int) -> str:
    if limit < 1:
        raise _OutputOverflow
    chunks: list[str] = []
    size = 0
    for chunk in template.generate(**context):  # type: ignore[attr-defined]
        size += len(chunk.encode("utf-8"))
        if size > limit:
            raise _OutputOverflow
        chunks.append(chunk)
    return "".join(chunks)


def _environments() -> tuple[Environment, Environment]:
    html_env = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        undefined=StrictUndefined,
        autoescape=select_autoescape(enabled_extensions=("html",), default=True),
    )
    text_env = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        undefined=StrictUndefined,
        autoescape=False,
    )
    for env in (html_env, text_env):
        env.filters["ref"] = _ref
    return html_env, text_env


def _between(value: str, start: str, end: str) -> str:
    if start not in value or end not in value:
        raise ReportBuildError("rendered report section is missing")
    return value.split(start, 1)[1].split(end, 1)[0]


def _topic_plain(value: str, ref: VersionRef) -> str:
    marker = f"TOPIC {_ref(ref)}"
    if value.count(marker) != 1:
        raise ReportBuildError("rendered topic detail identity coverage failed")
    tail = value.split(marker, 1)[1]
    return tail.split("\nTOPIC ", 1)[0]


def _require_values(values: tuple[str, ...], plain: str, html: str, label: str) -> None:
    for value in values:
        if value not in plain or value not in html:
            raise ReportBuildError(f"rendered {label} coverage failed")


def _safe_url(value: str | None) -> bool:
    if value is None:
        return False
    parsed = urlsplit(value)
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
        and parsed.username is None
        and parsed.password is None
    )


def _ref(value: VersionRef) -> str:
    return f"{value.kind}:{value.identity}@{value.version}"

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
RENDERER_VERSION = "jinja-report@3"
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
_VOID_TAGS = {"br"}


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
    """Validate saved markup structure and collect exact article/link bindings."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.article: str | None = None
        self.article_text: dict[str, list[str]] = {}
        self.links: list[tuple[str | None, str]] = []
        self._seen_doctype = False

    def handle_decl(self, decl: str) -> None:
        if self._seen_doctype or decl.lower() != "doctype html" or self.stack:
            raise ReportBuildError("saved report HTML has invalid declaration")
        self._seen_doctype = True

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _ALLOWED_TAGS:
            raise ReportBuildError("saved report HTML contains an unsafe tag")
        names = [name for name, _value in attrs]
        if len(names) != len(set(names)):
            raise ReportBuildError("saved report HTML has duplicate attributes")
        if any(name.lower().startswith("on") for name in names):
            raise ReportBuildError("saved report HTML contains an unsafe attribute")
        values = dict(attrs)
        if tag == "a":
            if set(values) != {"href"} or not _safe_url(values.get("href")):
                raise ReportBuildError("saved report HTML contains an unsafe link")
            href = values["href"]
            if href is None:
                raise ReportBuildError("saved report HTML contains an unsafe link")
            self.links.append((self.article, href))
        elif tag in {"article", "li"}:
            if set(values) - {"data-topic"}:
                raise ReportBuildError(
                    "saved report HTML contains an unexpected attribute"
                )
        elif values:
            raise ReportBuildError("saved report HTML contains an unexpected attribute")
        if tag == "article":
            identity = values.get("data-topic")
            if (
                not identity
                or self.article is not None
                or identity in self.article_text
            ):
                raise ReportBuildError("saved report HTML has invalid article boundary")
            self.article = identity
            self.article_text[identity] = []
        if tag not in _VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _VOID_TAGS:
            raise ReportBuildError("saved report HTML has invalid self-closing tag")
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID_TAGS or not self.stack or self.stack[-1] != tag:
            raise ReportBuildError("saved report HTML has malformed tag boundaries")
        self.stack.pop()
        if tag == "article":
            if self.article is None:
                raise ReportBuildError("saved report HTML has invalid article boundary")
            self.article = None

    def handle_data(self, data: str) -> None:
        if self.article is not None:
            self.article_text[self.article].append(data)

    def finish(self) -> None:
        if self.stack or self.article is not None or not self._seen_doctype:
            raise ReportBuildError("saved report HTML is structurally incomplete")


def render_report(
    report_ref: VersionRef,
    overview: tuple[ReportOverviewItem, ...],
    topics: tuple[ReportTopic, ...],
    warnings: tuple[PendingAssessmentWarning, ...],
    config: RendererConfig,
    limitations: tuple[Limitation, ...] = (),
) -> tuple[ReportPart, ...]:
    """Render finite parts without accumulating output beyond configured bounds."""
    config = RendererConfig.model_validate_json(
        config.model_dump_json(warnings="error"), strict=True
    )
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
    validate_rendered_coverage(
        topics, parts, overview, warnings, limitations, report_ref=report_ref
    )
    return parts


def validate_rendered_coverage(
    topics: tuple[ReportTopic, ...],
    parts: tuple[ReportPart, ...],
    overview: tuple[ReportOverviewItem, ...] | None = None,
    warnings: tuple[PendingAssessmentWarning, ...] = (),
    limitations: tuple[Limitation, ...] = (),
    *,
    report_ref: VersionRef | None = None,
) -> None:
    """Require exact independent plain/HTML structure and topic-to-part coverage."""
    if not parts:
        raise ReportBuildError("rendered report has no parts")
    numbers = tuple(part.part_number for part in parts)
    if numbers != tuple(range(1, len(parts) + 1)):
        raise ReportBuildError("rendered report part numbering is not consecutive")
    mapped = tuple(ref for part in parts for ref in part.topic_refs)
    expected_refs = tuple(topic.topic_ref for topic in topics)
    if mapped != expected_refs:
        raise ReportBuildError("rendered topic-to-part identity coverage failed")
    if report_ref is None:
        raise ReportBuildError("rendered report identity is required")
    expected_overview = overview or _overview_from_topics(topics)
    by_ref = {topic.topic_ref: topic for topic in topics}
    html_env, text_env = _environments()
    for part in parts:
        group = tuple(by_ref[ref] for ref in part.topic_refs)
        context = _context(
            report_ref,
            part.part_number,
            len(parts),
            expected_overview,
            group,
            warnings,
            limitations,
        )
        expected_plain = text_env.get_template("report.txt.j2").render(**context)
        expected_html = html_env.get_template("report.html.j2").render(**context)
        if part.plain_text != expected_plain:
            raise ReportBuildError("rendered plain section coverage failed")
        if part.html != expected_html:
            raise ReportBuildError("rendered HTML section coverage failed")
        audit = _HTMLAudit()
        audit.feed(part.html)
        audit.close()
        audit.finish()
        expected_articles = tuple(_ref(topic.topic_ref) for topic in group)
        if tuple(audit.article_text) != expected_articles:
            raise ReportBuildError("rendered HTML article mapping is invalid")
        expected_links = [
            (_ref(topic.topic_ref), link.url)
            for topic in group
            for link in topic.source_links
        ]
        if audit.links != expected_links:
            raise ReportBuildError("rendered HTML source link binding is invalid")


def _overview_from_topics(
    topics: tuple[ReportTopic, ...],
) -> tuple[ReportOverviewItem, ...]:
    return tuple(
        ReportOverviewItem(
            topic_ref=topic.topic_ref,
            assessment_ref=topic.assessment_ref,
            title=topic.title,
            priority=topic.priority,
            developments=tuple(x.text for x in topic.developments),
            actions=tuple(x.text for x in topic.actions),
            deadlines=tuple(x.original_wording for x in topic.deadlines),
            risks=tuple(x.text for x in topic.risks),
        )
        for topic in topics
    )


def _context(
    report_ref: VersionRef,
    number: int,
    count: int,
    overview: tuple[ReportOverviewItem, ...],
    topics: tuple[ReportTopic, ...],
    warnings: tuple[PendingAssessmentWarning, ...],
    limitations: tuple[Limitation, ...],
) -> dict[str, object]:
    return {
        "report_ref": report_ref,
        "part_number": number,
        "part_count": count,
        "show_overview": number == 1,
        "overview": overview,
        "topics": topics,
        "warnings": warnings,
        "limitations": limitations,
    }


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
        context = _context(
            report_ref,
            number,
            len(groups),
            overview,
            group,
            warnings,
            limitations,
        )
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

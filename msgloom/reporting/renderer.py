"""Strict Jinja rendering and post-render identity/content coverage checks."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Annotated

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from pydantic import BaseModel, ConfigDict, Field, model_validator

from msgloom.contracts import VersionRef

from .build import ReportBuildError
from .models import (
    PendingAssessmentWarning,
    ReportOverviewItem,
    ReportPart,
    ReportTopic,
)

_TEMPLATE_DIR = Path(__file__).with_name("templates")
RENDERER_VERSION = "jinja-report@1"


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


def render_report(
    report_ref: VersionRef,
    overview: tuple[ReportOverviewItem, ...],
    topics: tuple[ReportTopic, ...],
    warnings: tuple[PendingAssessmentWarning, ...],
    config: RendererConfig,
) -> tuple[ReportPart, ...]:
    """Render exact finite parts; never truncate a topic to satisfy bounds."""
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

    groups: list[tuple[ReportTopic, ...]] = [topics]
    rendered = _render_groups(
        report_ref, overview, groups, warnings, html_env, text_env
    )
    if not _within(rendered, config):
        groups = [(topic,) for topic in topics]
        if len(groups) > config.max_parts:
            raise ReportBuildError("report requires more output parts than configured")
        rendered = _render_groups(
            report_ref, overview, groups, warnings, html_env, text_env
        )
    if not _within(rendered, config):
        raise ReportBuildError(
            "one or more complete report topics exceed output bounds"
        )
    parts = tuple(
        ReportPart(
            part_number=index,
            topic_refs=tuple(topic.topic_ref for topic in group),
            plain_text=plain,
            html=html,
        )
        for index, (group, plain, html) in enumerate(rendered, 1)
    )
    validate_rendered_coverage(topics, parts)
    return parts


def validate_rendered_coverage(
    topics: tuple[ReportTopic, ...],
    parts: tuple[ReportPart, ...],
) -> None:
    """Require exact topic mapping and every essential field in saved output."""
    mapped = [ref for part in parts for ref in part.topic_refs]
    if len(mapped) != len(set(mapped)) or set(mapped) != {x.topic_ref for x in topics}:
        raise ReportBuildError("rendered topic-to-part identity coverage failed")
    by_ref = {ref: part for part in parts for ref in part.topic_refs}
    for topic in topics:
        part = by_ref[topic.topic_ref]
        plain = part.plain_text
        html = part.html
        required = [
            topic.title,
            topic.reason,
            topic.priority.value,
            *[x.text for x in topic.developments],
            *[x.text for x in topic.actions],
            *[x.original_wording for x in topic.deadlines],
            *[x.text for x in topic.risks],
            *[_ref(x) for x in topic.source_refs],
        ]
        for value in required:
            if value not in plain or escape(value, quote=True) not in html:
                raise ReportBuildError("rendered essential topic coverage failed")
        for evidence in topic.evidence:
            label = evidence.kind.value
            if evidence.statement not in plain or label not in plain:
                raise ReportBuildError("rendered evidence coverage failed")
            if escape(evidence.statement, quote=True) not in html:
                raise ReportBuildError("rendered HTML evidence coverage failed")


def _render_groups(
    report_ref: VersionRef,
    overview: tuple[ReportOverviewItem, ...],
    groups: list[tuple[ReportTopic, ...]],
    warnings: tuple[PendingAssessmentWarning, ...],
    html_env: Environment,
    text_env: Environment,
) -> list[tuple[tuple[ReportTopic, ...], str, str]]:
    values = []
    for number, group in enumerate(groups, 1):
        context = {
            "report_ref": report_ref,
            "part_number": number,
            "part_count": len(groups),
            "overview": overview,
            "topics": group,
            "warnings": warnings,
        }
        plain = text_env.get_template("report.txt.j2").render(**context)
        html = html_env.get_template("report.html.j2").render(**context)
        values.append((group, plain, html))
    return values


def _within(
    rendered: list[tuple[tuple[ReportTopic, ...], str, str]],
    config: RendererConfig,
) -> bool:
    if len(rendered) > config.max_parts:
        return False
    sizes = [
        len(plain.encode("utf-8")) + len(html.encode("utf-8"))
        for _group, plain, html in rendered
    ]
    return (
        all(size <= config.max_part_bytes for size in sizes)
        and sum(sizes) <= config.max_total_bytes
    )


def _ref(value: VersionRef) -> str:
    return f"{value.kind}:{value.identity}@{value.version}"

"""Shared synthetic composition helpers for A2 producer tests."""

from __future__ import annotations

from pathlib import Path

from msgloom.contracts import ResultSchemaRegistry, VersionRef
from msgloom.persistence import Phase1Persistence, SemanticDataRegistry
from msgloom.preparation import (
    DocumentFormat,
    ParserConfig,
    ParserIdentity,
    ParserLimits,
)
from msgloom.preparation.codec import PreparedDataCodec
from msgloom.preparation.filtering import (
    AddressNormalization,
    FilterConfig,
    FilterResultCodec,
)
from msgloom.preparation.grouping import GroupResultCodec
from msgloom.preparation_pipeline import (
    DerivedByteArtifactCodec,
    ParserProfile,
    PreparationMode,
    PreparationPlan,
    SelectionPlan,
)
from msgloom.sources import CollectedSelectionCodec
from tests.prepared_contract_fixtures import phase1_url

_LIMITS = ParserLimits(
    wall_time_seconds=10.0,
    memory_bytes=512 * 1024 * 1024,
    decompressed_bytes=16 * 1024 * 1024,
    output_bytes=8 * 1024 * 1024,
    container_members=2048,
)
_MIME = ParserIdentity("msgloom.mime-html", "1", "stdlib-email+selectolax-0.4.12")
_EXCEL = ParserIdentity("msgloom.excel", "1", "python-calamine-0.8.2+openpyxl-3.1.5")
_PDF = ParserIdentity("msgloom.pdf", "1", "pypdfium2-5.13.0")
_WORD = ParserIdentity("msgloom.word", "1", "python-docx-1.2.0+lxml-6.1.3")


def profiles(*formats: DocumentFormat) -> tuple[ParserProfile, ...]:
    """Return reviewed production identities for selected parser formats."""
    values: list[ParserProfile] = []
    for format_ in formats:
        if format_ in {
            DocumentFormat.MIME,
            DocumentFormat.HTML,
            DocumentFormat.TEXT,
            DocumentFormat.JSON,
        }:
            parser, profile = _MIME, "mime-html-v1"
        elif format_ in {
            DocumentFormat.XLSX,
            DocumentFormat.XLSM,
            DocumentFormat.XLS,
            DocumentFormat.XLSB,
            DocumentFormat.ODS,
        }:
            parser, profile = _EXCEL, "excel-primary-v1"
        elif format_ is DocumentFormat.PDF:
            parser, profile = _PDF, "pdf-primary-v1"
        else:
            parser, profile = _WORD, "word-native-v1"
        values.append(
            ParserProfile(
                format=format_,
                parser=parser,
                config=ParserConfig(profile),
                limits=_LIMITS,
            )
        )
    return tuple(values)


def filter_config(version: str = "filter-v1") -> FilterConfig:
    """Return a no-rule deterministic include configuration."""
    return FilterConfig(
        reference=VersionRef("filter_config", "phase1", version),
        address_normalization=AddressNormalization.EXACT,
    )


def plan(
    source: VersionRef,
    *,
    attempt,
    mode: PreparationMode = PreparationMode.LIVE,
    replay_result=None,
    replay_selection=None,
    parser_profiles: tuple[ParserProfile, ...],
    timeout: float = 30.0,
) -> PreparationPlan:
    """Build one finite plan with a lease longer than its execution budget."""
    return PreparationPlan(
        mode=mode,
        attempt=attempt,
        selections=(
            SelectionPlan(
                source=source,
                replay_result=replay_result,
                replay_selection=replay_selection,
            ),
        ),
        filter_config=filter_config(),
        parser_profiles=parser_profiles,
        configuration_version="prepare-config-v1",
        code_version="test-build-v1",
        execution_timeout_seconds=timeout,
        claim_lease_seconds=timeout + 5.0,
    )


async def open_store(path: Path) -> Phase1Persistence:
    """Open persistence with explicit manager-composable A2 registrations."""
    result_registry = ResultSchemaRegistry.phase1().with_schema(
        "derived_bytes", "1", semantic_data_required=True
    )
    semantic_registry = SemanticDataRegistry(
        (
            CollectedSelectionCodec(),
            DerivedByteArtifactCodec(),
            PreparedDataCodec(),
            FilterResultCodec(),
            GroupResultCodec(),
        )
    )
    return await Phase1Persistence.open(
        phase1_url(path),
        registry=result_registry,
        semantic_registry=semantic_registry,
    )

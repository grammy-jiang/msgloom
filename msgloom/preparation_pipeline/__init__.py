"""Finite A2 preparation producer composition surface."""

from typing import TYPE_CHECKING

from msgloom.preparation_pipeline.codec import (
    DERIVED_BYTES_KIND,
    DERIVED_BYTES_SCHEMA_VERSION,
    DerivedByteArtifact,
    DerivedByteArtifactCodec,
)
from msgloom.preparation_pipeline.models import (
    ParserProfile,
    PreparationMode,
    PreparationPlan,
    SelectionPlan,
)

if TYPE_CHECKING:
    from msgloom.preparation_pipeline.handler import PreparationHandler
    from msgloom.preparation_pipeline.intake import PreparationIntakeService


def __getattr__(name: str):
    """Load the handler lazily so codec registration cannot create import cycles."""
    if name == "PreparationIntakeService":
        from msgloom.preparation_pipeline.intake import PreparationIntakeService

        return PreparationIntakeService
    if name == "PreparationHandler":
        from msgloom.preparation_pipeline.handler import PreparationHandler

        return PreparationHandler
    raise AttributeError(name)


__all__ = [
    "DERIVED_BYTES_KIND",
    "DERIVED_BYTES_SCHEMA_VERSION",
    "DerivedByteArtifact",
    "DerivedByteArtifactCodec",
    "ParserProfile",
    "PreparationHandler",
    "PreparationIntakeService",
    "PreparationMode",
    "PreparationPlan",
    "SelectionPlan",
]

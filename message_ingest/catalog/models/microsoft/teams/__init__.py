"""Dedicated Microsoft Teams catalog model registration."""

from .content import (
    TeamsHostedContentObservation,
    TeamsReferenceResolutionCurrent,
    TeamsReferenceResolutionObservation,
)
from .coverage import TeamsCoverageCurrent, TeamsCoverageObservation
from .message import (
    TeamsMessageAttachmentObservation,
    TeamsMessageCurrent,
    TeamsMessageDeletionObservation,
    TeamsMessageObservation,
)
from .topology import TeamsTopologyCurrent, TeamsTopologyObservation

__all__ = [
    "TeamsCoverageCurrent",
    "TeamsCoverageObservation",
    "TeamsHostedContentObservation",
    "TeamsMessageAttachmentObservation",
    "TeamsMessageCurrent",
    "TeamsMessageDeletionObservation",
    "TeamsMessageObservation",
    "TeamsReferenceResolutionCurrent",
    "TeamsReferenceResolutionObservation",
    "TeamsTopologyCurrent",
    "TeamsTopologyObservation",
]

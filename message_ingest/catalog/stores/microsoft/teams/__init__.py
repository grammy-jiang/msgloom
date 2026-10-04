"""Microsoft Teams dedicated catalog stores."""

from .content import TeamsContentStore
from .coverage import TeamsCoverageStore
from .message import TeamsMessageStore
from .topology import TeamsTopologyStore

__all__ = [
    "TeamsContentStore",
    "TeamsCoverageStore",
    "TeamsMessageStore",
    "TeamsTopologyStore",
]

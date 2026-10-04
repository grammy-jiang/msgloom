"""Microsoft acquisition spiders."""

from . import outlook, teams
from .profile import MicrosoftProfileSpider

__all__ = ["MicrosoftProfileSpider", "outlook", "teams"]

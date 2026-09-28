"""Microsoft acquisition spiders."""

from . import outlook
from .profile import MicrosoftProfileSpider

__all__ = ["MicrosoftProfileSpider", "outlook"]

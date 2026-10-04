"""Evidence-first delegated Teams application spiders."""

from .channel import MicrosoftTeamsChannelDiscoverSpider
from .chat import MicrosoftTeamsChatDiscoverSpider

__all__ = ["MicrosoftTeamsChannelDiscoverSpider", "MicrosoftTeamsChatDiscoverSpider"]

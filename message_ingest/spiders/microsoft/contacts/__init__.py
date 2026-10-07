"""Personal Contacts discovery, snapshot sync, and custom-folder delta."""

from .delta import MicrosoftContactsDeltaSpider
from .snapshot import MicrosoftContactsDiscoverSpider, MicrosoftContactsSyncSpider

__all__ = [
    "MicrosoftContactsDeltaSpider",
    "MicrosoftContactsDiscoverSpider",
    "MicrosoftContactsSyncSpider",
]

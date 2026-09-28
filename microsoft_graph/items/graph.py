"""Optional provider-only default items compatible with Scrapy item adapters."""

from dataclasses import dataclass
from typing import Any


@dataclass
class GraphResourceItem:
    """Retain one unmodified Graph resource and its response URL."""

    resource: dict[str, Any]
    url: str


__all__ = ["GraphResourceItem"]

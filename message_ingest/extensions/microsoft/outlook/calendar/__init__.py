"""Outlook Calendar Scrapy lifecycle extensions."""

from .checkpoint import CalendarDeltaCheckpointExtension, CalendarDeltaSpiderState

__all__ = ["CalendarDeltaCheckpointExtension", "CalendarDeltaSpiderState"]

"""Outlook item-persistence pipelines."""

from .calendar import OutlookCalendarPipeline
from .email import OutlookMailPipeline

__all__ = ["OutlookCalendarPipeline", "OutlookMailPipeline"]

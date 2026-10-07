"""Outlook catalog stores."""

from .calendar import OutlookCalendarStore
from .email import OutlookMailStore

__all__ = ["OutlookCalendarStore", "OutlookMailStore"]

"""Shared Outlook mailbox target path and delegated-scope contract."""

from __future__ import annotations

from typing import ClassVar
from urllib.parse import quote

from scrapy.settings import BaseSettings

from microsoft_graph.spiders.graph import MicrosoftGraphSpider


class OutlookMailboxSpider(MicrosoftGraphSpider):
    """Target the signed-in mailbox or one explicitly delegated mailbox."""

    target_mailbox_setting = "MS_GRAPH_TARGET_MAILBOX"
    shared_graph_permissions: ClassVar[tuple[str, ...]] = ()

    @classmethod
    def required_graph_permissions(cls, settings: BaseSettings) -> tuple[str, ...]:
        mailbox = cls._target_mailbox_from_settings(settings)
        return cls.shared_graph_permissions if mailbox else cls.graph_permissions

    @classmethod
    def _target_mailbox_from_settings(cls, settings: BaseSettings) -> str:
        value = settings.get(cls.target_mailbox_setting, "") or ""
        if not isinstance(value, str):
            raise TypeError(f"{cls.target_mailbox_setting} must be a string")
        if value != value.strip():
            raise ValueError(
                f"{cls.target_mailbox_setting} must not contain surrounding whitespace"
            )
        return value

    @property
    def target_mailbox(self) -> str:
        return self._target_mailbox_from_settings(self.crawler.settings)

    def _mailbox_path(self) -> str:
        """Return `/me` or one encoded `/users/{locator}` Graph path prefix."""
        if not self.target_mailbox:
            return "/me"
        return f"/users/{quote(self.target_mailbox, safe='')}"

    def _mailbox_url(self, suffix: str) -> str:
        if suffix and not suffix.startswith("/"):
            raise ValueError("mailbox URL suffix must start with '/'")
        return f"{self.graph_root}{self._mailbox_path()}{suffix}"


__all__ = ["OutlookMailboxSpider"]

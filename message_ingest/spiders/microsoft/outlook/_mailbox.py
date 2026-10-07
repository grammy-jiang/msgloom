"""Bind reusable Outlook mailbox targeting to msgloom source settings."""

from abc import ABC
from typing import ClassVar

from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider
from microsoft_graph.spiders.outlook.mailbox import OutlookMailboxSpider as GraphMailbox


class OutlookMailboxSpider(GraphMailbox, MicrosoftGraphSpider, ABC):
    """Keep the legacy mailbox setting and source-target identity marker."""

    target_mailbox_setting = "MSGLOOM_TARGET_MAILBOX"
    mailbox_targeted: ClassVar[bool] = True


__all__ = ["OutlookMailboxSpider"]

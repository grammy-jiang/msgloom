"""Summarize acquisition items without exposing acquired private content."""

from microsoft_graph.logformatter import MicrosoftGraphLogFormatter

from .item_summary import summarize_item


class MessageIngestLogFormatter(MicrosoftGraphLogFormatter):
    """Keep application item summaries and the existing global privacy scope."""

    _item_summary = staticmethod(summarize_item)

    def _redact(self, spider) -> bool:
        """Apply safe formatting to all application acquisition records."""
        return True


__all__ = ["MessageIngestLogFormatter"]

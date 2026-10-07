"""Microsoft Teams chat v1.0 paths and provider query constraints."""

from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import quote, urlencode

from microsoft_graph.spiders.graph import MicrosoftGraphSpider


class MicrosoftTeamsChatSpider(MicrosoftGraphSpider):
    """
    Supply chat paths without traversal, parsing, or application state.

    IDs are opaque provider path segments and are encoded exactly once here.
    Consumers own callbacks, evidence ordering, continuation traversal, and
    semantic persistence. Consumers also select permissions and page sizes;
    collection helpers validate provider bounds without selecting a profile.
    """

    @staticmethod
    def _segment(value: str, *, name: str) -> str:
        """Validate one opaque provider ID and encode it as one path segment."""
        if not isinstance(value, str) or not value:
            raise ValueError(f"{name} must be a non-empty string")
        return quote(value, safe="")

    @staticmethod
    def _page_size(value: int) -> int:
        """Require the Graph chat/message page-size range of 1 through 50."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("page_size must be an integer")
        if not 1 <= value <= 50:
            raise ValueError("page_size must be between 1 and 50")
        return value

    @staticmethod
    def _utc_boundary(value: str, *, name: str) -> tuple[str, datetime]:
        """Validate one exact ISO-8601 UTC boundary without rewriting it."""
        if not isinstance(value, str):
            raise TypeError(f"{name} must be a string")
        if not value or value != value.strip():
            raise ValueError(f"{name} must be a non-empty ISO-8601 datetime")
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be a valid ISO-8601 datetime") from exc
        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            raise ValueError(f"{name} must be UTC")
        return value, parsed

    @classmethod
    def _modified_window(cls, lower: str, upper: str) -> tuple[str, str]:
        """Require an increasing UTC last-modified window."""
        lower_text, lower_value = cls._utc_boundary(lower, name="modified_after")
        upper_text, upper_value = cls._utc_boundary(upper, name="modified_before")
        if lower_value >= upper_value:
            raise ValueError("modified_after must be earlier than modified_before")
        return lower_text, upper_text

    @staticmethod
    def _query_path(path: str, query: list[tuple[str, str | int]]) -> str:
        """Append a newly constructed query while preserving option order."""
        return f"{path}?{urlencode(query)}" if query else path

    def chats_path(self, *, page_size: int | None = None) -> str:
        """List the signed-in user's chats with an optional caller page size."""
        query: list[tuple[str, str | int]] = []
        if page_size is not None:
            query.append(("$top", self._page_size(page_size)))
        return self._query_path("/me/chats", query)

    def chat_path(self, chat_id: str) -> str:
        """Address one chat by its opaque provider ID."""
        chat = self._segment(chat_id, name="chat_id")
        return f"/chats/{chat}"

    def chat_members_path(self, chat_id: str) -> str:
        """List explicit chat members without the capped inline expansion."""
        return f"{self.chat_path(chat_id)}/members"

    def chat_messages_path(
        self,
        chat_id: str,
        *,
        page_size: int | None = None,
        modified_after: str | None = None,
        modified_before: str | None = None,
    ) -> str:
        """
        List chat messages with an optional strict UTC modified-time window.

        A bounded window always uses descending lastModifiedDateTime order and
        matching strict gt/lt predicates, as required by Graph.
        """
        query: list[tuple[str, str | int]] = []
        if page_size is not None:
            query.append(("$top", self._page_size(page_size)))
        if (modified_after is None) != (modified_before is None):
            raise ValueError(
                "modified_after and modified_before must be supplied together"
            )
        if modified_after is not None and modified_before is not None:
            lower, upper = self._modified_window(modified_after, modified_before)
            filter_value = (
                f"lastModifiedDateTime gt {lower} and lastModifiedDateTime lt {upper}"
            )
            query.extend(
                [
                    ("$orderby", "lastModifiedDateTime desc"),
                    ("$filter", filter_value),
                ]
            )
        return self._query_path(
            f"{self.chat_path(chat_id)}/messages",
            query,
        )

    def chat_message_path(self, chat_id: str, message_id: str) -> str:
        """Address one chat message by chat-scoped opaque identity."""
        message = self._segment(message_id, name="message_id")
        return f"{self.chat_path(chat_id)}/messages/{message}"

    def chat_pins_path(self, chat_id: str) -> str:
        """List pin relations separately from message observations."""
        return f"{self.chat_path(chat_id)}/pinnedMessages"

    def hosted_contents_path(self, chat_id: str, message_id: str) -> str:
        """List hosted-content metadata for one chat message."""
        return f"{self.chat_message_path(chat_id, message_id)}/hostedContents"

    def hosted_content_path(
        self,
        chat_id: str,
        message_id: str,
        hosted_content_id: str,
    ) -> str:
        """Address one hosted-content metadata item by opaque ID."""
        hosted = self._segment(hosted_content_id, name="hosted_content_id")
        return f"{self.hosted_contents_path(chat_id, message_id)}/{hosted}"

    def hosted_content_bytes_path(
        self,
        chat_id: str,
        message_id: str,
        hosted_content_id: str,
    ) -> str:
        """
        Address current hosted bytes without implying message-version binding.

        The provider API offers no historical-version selector for this value.
        Consumers own uncached request representation and evidence linkage.
        """
        return (
            f"{self.hosted_content_path(chat_id, message_id, hosted_content_id)}/$value"
        )


__all__ = ["MicrosoftTeamsChatSpider"]

"""Reusable Outlook Mail scopes, paths, and representation."""

from collections.abc import Sequence
from typing import ClassVar
from urllib.parse import quote, urlencode

from .mailbox import OutlookMailboxSpider


class OutlookMailSpider(OutlookMailboxSpider):
    """Acquire Mail with immutable IDs and own/shared read permissions."""

    graph_prefer = 'IdType="ImmutableId"'
    graph_permissions: ClassVar[tuple[str, ...]] = ("Mail.Read",)
    shared_graph_permissions: ClassVar[tuple[str, ...]] = ("Mail.Read.Shared",)

    def messages_path(
        self,
        *,
        folder_id: str = "",
        fields: Sequence[str] = (),
        order_by: str | None = None,
        page_size: int | None = None,
    ) -> str:
        """Build a mailbox or folder collection path with provider query fields."""
        path = self._mailbox_path()
        if folder_id:
            path += f"/mailFolders/{quote(folder_id, safe='')}"
        query: dict[str, str | int] = {}
        if fields:
            query["$select"] = ",".join(fields)
        if order_by is not None:
            query["$orderby"] = order_by
        if page_size is not None:
            query["$top"] = page_size
        return _query_path(f"{path}/messages", query)

    def message_path(
        self,
        message_id: str,
        *,
        fields: Sequence[str] = (),
        expand: str | None = None,
    ) -> str:
        """Encode one message ID once with optional select/expand query fields."""
        path = f"{self._mailbox_path()}/messages/{quote(message_id, safe='')}"
        query: dict[str, str | int] = {}
        if fields:
            query["$select"] = ",".join(fields)
        if expand is not None:
            query["$expand"] = expand
        return _query_path(path, query)

    def message_mime_path(self, message_id: str) -> str:
        """Return the MIME endpoint independently of Accept/cache policy."""
        return f"{self.message_path(message_id)}/$value"

    def mail_folders_path(
        self,
        *,
        parent_folder_id: str = "",
        include_hidden: bool | None = None,
        page_size: int | None = None,
    ) -> str:
        """Build a root or childFolders inventory without traversal state."""
        path = f"{self._mailbox_path()}/mailFolders"
        if parent_folder_id:
            path += f"/{quote(parent_folder_id, safe='')}/childFolders"
        query: dict[str, str | int] = {}
        if include_hidden is not None:
            query["includeHiddenFolders"] = str(include_hidden).lower()
        if page_size is not None:
            query["$top"] = page_size
        return _query_path(path, query)

    def message_delta_path(self, folder_id: str, *, fields: Sequence[str] = ()) -> str:
        """Build a folder's initial delta path; continuations remain opaque."""
        path = (
            f"{self._mailbox_path()}/mailFolders/"
            f"{quote(folder_id, safe='')}/messages/delta"
        )
        return _query_path(path, {"$select": ",".join(fields)} if fields else {})

    def mail_folder_delta_path(self, *, fields: Sequence[str] = ()) -> str:
        """Build initial mailFolder delta without choosing a cursor policy."""
        return _query_path(
            f"{self._mailbox_path()}/mailFolders/delta",
            {"$select": ",".join(fields)} if fields else {},
        )


def _query_path(path: str, query: dict[str, str | int]) -> str:
    """Encode new-query values in insertion order; never rebuild provider links."""
    return f"{path}?{urlencode(query)}" if query else path

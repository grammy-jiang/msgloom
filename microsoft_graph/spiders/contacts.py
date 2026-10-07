"""Microsoft personal Contacts read scope and v1.0 provider paths."""

from collections.abc import Iterable
from typing import ClassVar
from urllib.parse import quote, urlencode

from .graph import MicrosoftGraphSpider


class MicrosoftContactsSpider(MicrosoftGraphSpider):
    """Supply read-only Contacts paths; consumers own traversal and storage."""

    graph_permissions: ClassVar[tuple[str, ...]] = ("Contacts.Read",)
    folder_select_fields: ClassVar[tuple[str, ...]] = (
        "id",
        "displayName",
        "parentFolderId",
    )
    # personalNotes is intentionally absent pending explicit privacy acceptance.
    contact_select_fields: ClassVar[tuple[str, ...]] = (
        "id",
        "displayName",
        "givenName",
        "surname",
        "initials",
        "nickName",
        "title",
        "companyName",
        "department",
        "jobTitle",
        "emailAddresses",
        "businessPhones",
        "homePhones",
        "mobilePhone",
        "birthday",
        "parentFolderId",
        "lastModifiedDateTime",
    )

    @staticmethod
    def _folder_id(folder_id: str) -> str:
        """Validate a concrete raw folder ID before one-time path encoding."""
        if not isinstance(folder_id, str) or not folder_id.strip():
            raise ValueError("Contacts folder ID must be a non-empty string")
        return quote(folder_id, safe="")

    @staticmethod
    def _collection_path(
        path: str,
        *,
        page_size: int | None = None,
        select: Iterable[str] | None = None,
    ) -> str:
        """Append only caller-selected OData projection and page-size options."""
        query: list[tuple[str, object]] = []
        if select is not None:
            fields = tuple(select)
            if fields:
                query.append(("$select", ",".join(fields)))
        if page_size is not None:
            query.append(("$top", page_size))
        return f"{path}?{urlencode(query)}" if query else path

    def default_contacts_path(
        self, *, page_size: int | None = None, select: Iterable[str] | None = None
    ) -> str:
        """List the signed-in user's default Contacts collection."""
        return self._collection_path("/me/contacts", page_size=page_size, select=select)

    def contact_folders_path(
        self, *, page_size: int | None = None, select: Iterable[str] | None = None
    ) -> str:
        """List custom contact folders below the default Contacts folder."""
        return self._collection_path(
            "/me/contactFolders", page_size=page_size, select=select
        )

    def child_folders_path(
        self,
        folder_id: str,
        *,
        page_size: int | None = None,
        select: Iterable[str] | None = None,
    ) -> str:
        """List children of one concrete folder with its raw ID encoded once."""
        path = f"/me/contactFolders/{self._folder_id(folder_id)}/childFolders"
        return self._collection_path(path, page_size=page_size, select=select)

    def folder_contacts_path(
        self,
        folder_id: str,
        *,
        page_size: int | None = None,
        select: Iterable[str] | None = None,
    ) -> str:
        """List contacts in one concrete custom contact folder."""
        path = f"/me/contactFolders/{self._folder_id(folder_id)}/contacts"
        return self._collection_path(path, page_size=page_size, select=select)

    def contacts_delta_path(
        self, folder_id: str, *, select: Iterable[str] | None = None
    ) -> str:
        """Start delta only for a validated concrete custom-folder identity."""
        path = f"/me/contactFolders/{self._folder_id(folder_id)}/contacts/delta"
        return self._collection_path(path, select=select)


__all__ = ["MicrosoftContactsSpider"]

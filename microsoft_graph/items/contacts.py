"""Provider-only personal Contacts projections with unchanged raw JSON."""

from dataclasses import dataclass, field
from typing import Any, Self

from microsoft_graph.protocol import graph_object


def _resource(resource: dict[str, Any], context: str) -> dict[str, Any]:
    """Validate only provider object identity, not optional contact content."""
    raw = graph_object(resource, context=context)
    resource_id = raw.get("id")
    if not isinstance(resource_id, str) or not resource_id:
        raise ValueError(f"{context} requires a non-empty id")
    return raw


@dataclass(slots=True)
class ContactFolderItem:
    """Contact-folder identity and hierarchy without application provenance."""

    folder_id: str
    raw: dict[str, Any]
    display_name: str | None = field(init=False)
    parent_folder_id: str | None = field(init=False)

    def __post_init__(self) -> None:
        """Project optional values without truth-value coercion."""
        self.display_name = self.raw.get("displayName")
        self.parent_folder_id = self.raw.get("parentFolderId")

    @classmethod
    def from_graph(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Map one provider folder while retaining the original dictionary."""
        raw = _resource(resource, "Contacts folder")
        return cls(folder_id=raw["id"], raw=raw, **kwargs)


@dataclass(slots=True)
class ContactItem:
    """Personal contact projection for default or concrete custom-folder scope."""

    folder_id: str | None
    is_default_scope: bool
    contact_id: str
    raw: dict[str, Any]
    display_name: str | None = field(init=False)
    given_name: str | None = field(init=False)
    surname: str | None = field(init=False)
    initials: str | None = field(init=False)
    nick_name: str | None = field(init=False)
    title: str | None = field(init=False)
    company_name: str | None = field(init=False)
    department: str | None = field(init=False)
    job_title: str | None = field(init=False)
    email_addresses: list[dict[str, Any]] | None = field(init=False)
    business_phones: list[str] | None = field(init=False)
    home_phones: list[str] | None = field(init=False)
    mobile_phone: str | None = field(init=False)
    birthday: str | None = field(init=False)
    parent_folder_id: str | None = field(init=False)
    last_modified_date_time: str | None = field(init=False)
    removed: dict[str, Any] | None = field(init=False)

    def __post_init__(self) -> None:
        """Preserve nested and falsey provider values exactly as supplied."""
        if self.is_default_scope:
            if self.folder_id is not None:
                raise ValueError("Default Contacts scope must not invent a folder ID")
        elif not isinstance(self.folder_id, str) or not self.folder_id.strip():
            raise ValueError("Custom Contacts scope requires a concrete folder ID")
        mapping = {
            "display_name": "displayName",
            "given_name": "givenName",
            "surname": "surname",
            "initials": "initials",
            "nick_name": "nickName",
            "title": "title",
            "company_name": "companyName",
            "department": "department",
            "job_title": "jobTitle",
            "email_addresses": "emailAddresses",
            "business_phones": "businessPhones",
            "home_phones": "homePhones",
            "mobile_phone": "mobilePhone",
            "birthday": "birthday",
            "parent_folder_id": "parentFolderId",
            "last_modified_date_time": "lastModifiedDateTime",
            "removed": "@removed",
        }
        for attribute, provider_name in mapping.items():
            setattr(self, attribute, self.raw.get(provider_name))

    @classmethod
    def from_graph(
        cls,
        resource: dict[str, Any],
        *,
        folder_id: str | None,
        is_default_scope: bool,
        **kwargs: Any,
    ) -> Self:
        """Map a contact without interpreting identity or removal semantics."""
        raw = _resource(resource, "Contact")
        return cls(
            folder_id=folder_id,
            is_default_scope=is_default_scope,
            contact_id=raw["id"],
            raw=raw,
            **kwargs,
        )


__all__ = ["ContactFolderItem", "ContactItem"]

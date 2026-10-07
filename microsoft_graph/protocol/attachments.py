"""
Outlook attachment type and endpoint mechanics without completion policy.

Paths are the reusable attachment contract. Pass them to the consumer's
request factory so callbacks, errbacks, representation headers, and traversal
context keep their normal ownership and Scrapy serialization behavior.
"""

from collections.abc import Sequence
from urllib.parse import quote, urlencode


def attachment_type_name(attachment_type: str | None) -> str:
    """Normalize Graph namespace spellings while keeping unknown types visible."""
    return (
        (attachment_type or "unknown")
        .removeprefix("#microsoft.graph.")
        .removeprefix("microsoft.graph.")
    )


def attachment_list_path(
    parent_path: str,
    *,
    page_size: int | None = None,
    fields: Sequence[str] = (),
) -> str:
    """List attachments with optional caller-selected fields and page size."""
    query: dict[str, str | int] = {}
    if page_size is not None:
        query["$top"] = page_size
    if fields:
        query["$select"] = ",".join(fields)
    path = f"{parent_path}/attachments"
    return f"{path}?{urlencode(query)}" if query else path


def attachment_path(parent_path: str, attachment_id: str) -> str:
    """Encode an attachment ID once under an already encoded resource path."""
    return f"{parent_path}/attachments/{quote(attachment_id, safe='')}"


def attachment_raw_path(parent_path: str, attachment_id: str) -> str:
    """Return the Graph raw-content endpoint for a file or item attachment."""
    return f"{attachment_path(parent_path, attachment_id)}/$value"


def item_attachment_path(parent_path: str, attachment_id: str) -> str:
    """Expand the embedded item without combining it with raw-content fetches."""
    query = urlencode({"$expand": "microsoft.graph.itemattachment/item"})
    return f"{attachment_path(parent_path, attachment_id)}?{query}"

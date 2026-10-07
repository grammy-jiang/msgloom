"""Selected attachment inventory fields shared by Outlook acquisition profiles."""

# Inventory excludes embedded bytes; full acquisition fetches them separately.
ATTACHMENT_METADATA_FIELDS = (
    "id",
    "name",
    "contentType",
    "size",
    "isInline",
    "lastModifiedDateTime",
)

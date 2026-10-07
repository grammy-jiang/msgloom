"""Selected personal Contacts fields and application privacy policy."""

FOLDER_SELECT_FIELDS = (
    "id",
    "displayName",
    "parentFolderId",
)
# personalNotes is intentionally absent pending explicit privacy acceptance.
CONTACT_SELECT_FIELDS = (
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

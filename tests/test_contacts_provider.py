"""Pin personal Contacts read paths, privacy projection, and delta parsing."""

import subprocess
import sys

import pytest
from scrapy.settings import Settings

from microsoft_graph.items.contacts import ContactFolderItem, ContactItem
from microsoft_graph.spiders.contacts import MicrosoftContactsSpider


def test_contacts_paths_encode_raw_ids_once_and_use_read_scope_only():
    spider = MicrosoftContactsSpider(name="provider")
    folder_id = "A/B+=%2F ?é"
    encoded = "A%2FB%2B%3D%252F%20%3F%C3%A9"
    cases = [
        (spider.default_contacts_path(), "/me/contacts"),
        (spider.contact_folders_path(), "/me/contactFolders"),
        (
            spider.child_folders_path(folder_id),
            f"/me/contactFolders/{encoded}/childFolders",
        ),
        (
            spider.folder_contacts_path(folder_id),
            f"/me/contactFolders/{encoded}/contacts",
        ),
        (
            spider.contacts_delta_path(folder_id),
            f"/me/contactFolders/{encoded}/contacts/delta",
        ),
    ]
    for actual, expected in cases:
        if actual != expected:
            pytest.fail(f"Contacts path changed: {actual!r} != {expected!r}")
    settings = Settings()
    spider.update_settings(settings)
    if spider.required_graph_permissions(settings) != ("Contacts.Read",):
        pytest.fail("Contacts must require Contacts.Read only")
    if settings.getlist("MS_GRAPH_SCOPES") != ["Contacts.Read"]:
        pytest.fail("Contacts must never request Contacts.ReadWrite")


def test_contacts_projection_excludes_personal_notes_and_preserves_falsey_values():
    spider = MicrosoftContactsSpider(name="provider")
    path = spider.default_contacts_path(
        page_size=25, select=spider.contact_select_fields
    )
    if "personalNotes" in path or "personalNotes" in spider.contact_select_fields:
        pytest.fail("Selected Contacts projection must exclude personalNotes")
    raw = {
        "id": "contact",
        "displayName": "",
        "givenName": "",
        "surname": "",
        "initials": "",
        "nickName": "",
        "title": "",
        "companyName": "",
        "department": "",
        "jobTitle": "",
        "emailAddresses": [],
        "businessPhones": [],
        "homePhones": [],
        "mobilePhone": "",
        "birthday": None,
        "parentFolderId": "",
        "lastModifiedDateTime": "",
        "personalNotes": "provider-private-note",
        "future": {"nested": [False, 0, ""]},
    }
    item = ContactItem.from_graph(raw, folder_id=None, is_default_scope=True)
    if item.raw is not raw:
        pytest.fail("Raw provider JSON must remain unchanged evidence projection")
    if (
        item.email_addresses is not raw["emailAddresses"]
        or item.business_phones is not raw["businessPhones"]
    ):
        pytest.fail("Nested provider values must retain identity")
    if (item.display_name, item.mobile_phone, item.parent_folder_id) != ("", "", ""):
        pytest.fail("Falsey provider fields were normalized")
    if hasattr(item, "personal_notes"):
        pytest.fail("personalNotes must not become a semantic projection")


def test_folder_projection_preserves_parent_and_falsey_name():
    raw = {"id": "folder", "displayName": "", "parentFolderId": "parent", "future": 0}
    item = ContactFolderItem.from_graph(raw)
    if (item.folder_id, item.display_name, item.parent_folder_id, item.raw) != (
        "folder",
        "",
        "parent",
        raw,
    ):
        pytest.fail("Contact folder provider projection changed values")


@pytest.mark.parametrize("folder_id", ["", " ", None, False])
def test_custom_folder_paths_require_concrete_identity(folder_id):
    spider = MicrosoftContactsSpider(name="provider")
    for operation in (
        spider.child_folders_path,
        spider.folder_contacts_path,
        spider.contacts_delta_path,
    ):
        with pytest.raises((TypeError, ValueError)):
            operation(folder_id)


def test_contacts_framework_imports_without_application_or_sqlalchemy():
    code = r"""
import importlib.abc
import sys
class Forbid(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"message_ingest", "sqlalchemy"}:
            raise ImportError(f"Forbidden dependency: {fullname}")
sys.meta_path.insert(0, Forbid())
from microsoft_graph.items.contacts import ContactFolderItem, ContactItem
from microsoft_graph.spiders.contacts import MicrosoftContactsSpider
spider = MicrosoftContactsSpider(name="standalone")
spider.graph_request(spider.default_contacts_path())
spider.graph_request(spider.contacts_delta_path("folder"))
ContactFolderItem.from_graph({"id": "folder"})
ContactItem.from_graph({"id": "contact"}, folder_id="folder", is_default_scope=False)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode:
        pytest.fail(result.stderr)

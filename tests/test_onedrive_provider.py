"""Keep OneDrive provider paths read-only and projections lossless."""

import subprocess
import sys
from dataclasses import fields, make_dataclass

import pytest
from itemadapter import ItemAdapter
from scrapy.settings import Settings

from microsoft_graph.items.onedrive import OneDriveDriveItem, OneDriveItem
from microsoft_graph.spiders.onedrive import MicrosoftOneDriveSpider


def test_onedrive_paths_encode_raw_ids_once_and_require_read_only_scope():
    spider = MicrosoftOneDriveSpider(name="provider")
    item_id = "A/B+=%2F ?é#"
    item_path = "/me/drive/items/A%2FB%2B%3D%252F%20%3F%C3%A9%23"
    cases = [
        (spider.drive_path(), "/me/drive"),
        (spider.root_children_path(), "/me/drive/root/children"),
        (
            spider.root_children_path(page_size=37),
            "/me/drive/root/children?%24top=37",
        ),
        (spider.item_children_path(item_id), item_path + "/children"),
        (
            spider.item_children_path(item_id, page_size=37),
            item_path + "/children?%24top=37",
        ),
        (spider.delta_path(), "/me/drive/root/delta"),
        (spider.delta_path(page_size=37), "/me/drive/root/delta?%24top=37"),
        (spider.content_path(item_id), item_path + "/content"),
    ]
    for actual, expected in cases:
        if actual != expected:
            pytest.fail(f"OneDrive path bytes changed: {actual!r} != {expected!r}")
        request = spider.graph_request(actual)
        if request.method != "GET" or request.body:
            pytest.fail("OneDrive provider paths must produce read requests")
    settings = Settings()
    spider.update_settings(settings)
    if spider.required_graph_permissions(settings) != ("Files.Read",):
        pytest.fail("OneDrive requires Files.Read only")
    if settings.getlist("MS_GRAPH_SCOPES") != ["Files.Read"]:
        pytest.fail("OneDrive must not request write permissions")


@pytest.mark.parametrize("provider", [OneDriveDriveItem, OneDriveItem])
def test_provider_items_are_slotted_and_keep_raw_identity_without_provenance(provider):
    raw = {"id": "resource", "future": {"flags": [0, False, ""]}}
    item = provider.from_graph(raw)
    if item.raw is not raw or item.id != "resource":
        pytest.fail("Provider identity or the original object was changed")
    if hasattr(item, "__dict__") or ItemAdapter(item).asdict()["raw"] != raw:
        pytest.fail("OneDrive items must be slotted adapter-compatible dataclasses")
    forbidden = {"observed_at", "evidence_id", "run_id", "source_id"}
    if forbidden.intersection(field.name for field in fields(provider)):
        pytest.fail("Application provenance leaked into the provider")
    for field in fields(provider):
        if field.name not in {"id", "raw"} and getattr(item, field.name) is not None:
            pytest.fail(f"Missing optional field {field.name} must remain None")


@pytest.mark.parametrize("provider", [OneDriveDriveItem, OneDriveItem])
@pytest.mark.parametrize("raw", [None, [], "object", {}, {"id": ""}, {"id": False}])
def test_provider_items_reject_unstable_object_identity(provider, raw):
    with pytest.raises((TypeError, ValueError)):
        provider.from_graph(raw)


def test_drive_metadata_preserves_falsey_and_nested_values():
    raw = {
        "id": "drive",
        "driveType": "personal",
        "name": "",
        "webUrl": "",
        "owner": {"user": {"displayName": "", "id": "owner"}},
        "quota": {"deleted": 0, "remaining": 0, "state": "normal"},
        "createdDateTime": "created",
        "lastModifiedDateTime": "",
    }
    item = OneDriveDriveItem.from_graph(raw)
    mapping = {
        "drive_type": "driveType",
        "name": "name",
        "web_url": "webUrl",
        "owner": "owner",
        "quota": "quota",
        "created_date_time": "createdDateTime",
        "last_modified_date_time": "lastModifiedDateTime",
    }
    for field, key in mapping.items():
        if getattr(item, field) is not raw[key]:
            pytest.fail(f"Drive field {key} was transformed or copied")


def test_drive_item_preserves_every_projection_including_empty_facets():
    raw = {
        "id": "item",
        "name": "",
        "size": 0,
        "createdDateTime": "created",
        "lastModifiedDateTime": "",
        "webUrl": "",
        "eTag": "",
        "cTag": "",
        "parentReference": {"driveId": "drive", "id": "parent"},
        "file": {"mimeType": "application/octet-stream", "hashes": {}},
        "folder": {"childCount": 0},
        "deleted": {},
        "package": {},
        "remoteItem": {"id": "remote", "file": {}},
        "fileSystemInfo": {},
        "specialFolder": {"name": "documents"},
    }
    item = OneDriveItem.from_graph(raw)
    mapping = {
        "name": "name",
        "size": "size",
        "created_date_time": "createdDateTime",
        "last_modified_date_time": "lastModifiedDateTime",
        "web_url": "webUrl",
        "e_tag": "eTag",
        "c_tag": "cTag",
        "parent_reference": "parentReference",
        "file": "file",
        "folder": "folder",
        "deleted": "deleted",
        "package": "package",
        "remote_item": "remoteItem",
        "file_system_info": "fileSystemInfo",
        "special_folder": "specialFolder",
    }
    for field, key in mapping.items():
        if getattr(item, field) is not raw[key]:
            pytest.fail(f"DriveItem field {key} was transformed or copied")


@pytest.mark.parametrize("provider", [OneDriveDriveItem, OneDriveItem])
def test_provider_only_validates_identity_and_accepts_consumer_subclass_fields(
    provider,
):
    consumer = make_dataclass(
        "ObservedResource",
        [("observed_at", str), ("evidence_id", str), ("run_id", str)],
        bases=(provider,),
        slots=True,
    )
    raw = {"id": "resource", "name": False, "future": [None]}
    item = consumer.from_graph(
        raw, observed_at="observed", evidence_id="evidence", run_id="run"
    )
    if item.name is not False or item.raw is not raw:
        pytest.fail("Optional provider values must not be schema-validated")
    if (item.observed_at, item.evidence_id, item.run_id) != (
        "observed",
        "evidence",
        "run",
    ):
        pytest.fail("Consumer subclass arguments were not forwarded")


def test_onedrive_import_and_use_without_consumer_or_sqlalchemy():
    code = """
import importlib.abc
import sys
class ForbidConsumer(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"message_ingest", "sqlalchemy"}:
            raise ImportError(f"Forbidden dependency: {fullname}")
sys.meta_path.insert(0, ForbidConsumer())
from microsoft_graph.spiders.onedrive import MicrosoftOneDriveSpider
from microsoft_graph.items.onedrive import OneDriveDriveItem, OneDriveItem
spider = MicrosoftOneDriveSpider(name="standalone")
spider.graph_request(spider.drive_path())
spider.graph_request(spider.content_path("item"))
OneDriveDriveItem.from_graph({"id": "drive"})
OneDriveItem.from_graph({"id": "item", "deleted": {}})
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

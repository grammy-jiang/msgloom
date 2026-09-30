"""Keep Mail acquisition-policy ownership on collection spiders only."""

import pytest

from message_ingest.spiders.microsoft.outlook.email import _base
from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)
from message_ingest.spiders.microsoft.outlook.email.folder_delta import (
    OutlookFolderDeltaSpider,
)
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider


def test_mail_collection_boundary_excludes_folder_and_full_spiders() -> None:
    collection = getattr(_base, "OutlookMailCollectionSpider", None)
    if collection is None:
        pytest.fail("Outlook Mail collection spiders need an explicit shared base")

    if not issubclass(OutlookDiscoverSpider, collection):
        pytest.fail("Outlook discovery must be a Mail collection spider")
    if not issubclass(OutlookDeltaSpider, collection):
        pytest.fail("Outlook delta must be a Mail collection spider")
    if issubclass(OutlookFolderDeltaSpider, collection):
        pytest.fail("Folder delta must not load Mail message acquisition policy")
    if issubclass(OutlookFullSpider, collection):
        pytest.fail("Full acquisition must not re-evaluate Mail acquisition policy")

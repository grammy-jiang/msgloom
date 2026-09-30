"""Keep Mail acquisition-policy ownership on collection spiders only."""

import pytest
from scrapy.settings import Settings

from message_ingest import settings as project_settings
from message_ingest.spidermiddlewares.microsoft.outlook.email import (
    OUTLOOK_MAIL_RULE_MIDDLEWARE_PRIORITY,
    OutlookMailAcquisitionRuleMiddleware,
)
from message_ingest.spiders.microsoft.contacts.snapshot import (
    MicrosoftContactsDiscoverSpider,
)
from message_ingest.spiders.microsoft.onedrive.discover import (
    MicrosoftOneDriveDiscoverSpider,
)
from message_ingest.spiders.microsoft.outlook.calendar.discover import (
    OutlookCalendarDiscoverSpider,
)
from message_ingest.spiders.microsoft.outlook.email import _base
from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)
from message_ingest.spiders.microsoft.outlook.email.folder_delta import (
    OutlookFolderDeltaSpider,
)
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider
from message_ingest.spiders.microsoft.profile import MicrosoftProfileSpider
from message_ingest.spiders.microsoft.todo.discover import MicrosoftTodoDiscoverSpider


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


@pytest.mark.parametrize(
    ("spider_cls", "expected"),
    [
        (OutlookDiscoverSpider, True),
        (OutlookDeltaSpider, True),
        (OutlookFolderDeltaSpider, False),
        (OutlookFullSpider, False),
        (OutlookCalendarDiscoverSpider, False),
        (MicrosoftTodoDiscoverSpider, False),
        (MicrosoftOneDriveDiscoverSpider, False),
        (MicrosoftContactsDiscoverSpider, False),
        (MicrosoftProfileSpider, False),
    ],
)
def test_rule_middleware_effective_activation_matrix(
    spider_cls, expected: bool
) -> None:
    settings = Settings()
    spider_cls.update_settings(settings)
    entries = settings.getdict("SPIDER_MIDDLEWARES")
    actual = entries.get(OutlookMailAcquisitionRuleMiddleware)

    if expected and actual != OUTLOOK_MAIL_RULE_MIDDLEWARE_PRIORITY:
        pytest.fail(
            f"{spider_cls.__name__} must register Mail rule middleware at "
            f"{OUTLOOK_MAIL_RULE_MIDDLEWARE_PRIORITY}, got {actual!r}"
        )
    if not expected and actual is not None:
        pytest.fail(f"{spider_cls.__name__} must not register Mail rule middleware")


def test_rule_middleware_is_not_globally_configured() -> None:
    entries = getattr(project_settings, "SPIDER_MIDDLEWARES", {})
    if any(
        key is OutlookMailAcquisitionRuleMiddleware
        or key
        == "message_ingest.spidermiddlewares.microsoft.outlook.email.OutlookMailAcquisitionRuleMiddleware"
        for key in entries
    ):
        pytest.fail("Mail rule middleware must not be configured globally")

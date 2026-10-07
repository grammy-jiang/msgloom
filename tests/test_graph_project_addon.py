"""Build the consumer stack through the native Scrapy add-on manager."""

from types import SimpleNamespace

import pytest
from scrapy.core.downloader.middleware import DownloaderMiddlewareManager
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.settings import Settings
from scrapy.utils.misc import load_object
from scrapy.utils.test import get_crawler, get_reactor_settings

from message_ingest import settings as project
from message_ingest.extensions.microsoft_graph.privacy import (
    MicrosoftGraphLogPrivacyExtension as AppPrivacy,
)
from message_ingest.fingerprints.microsoft_graph import (
    RepresentationAwareRequestFingerprinter,
)
from message_ingest.observability.formatter import MessageIngestLogFormatter
from message_ingest.spiders.microsoft.onedrive.content import (
    MicrosoftOneDriveContentSpider,
)
from message_ingest.spiders.microsoft.outlook.calendar.discover import (
    OutlookCalendarDiscoverSpider,
)
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)
from message_ingest.spiders.microsoft.todo.discover import MicrosoftTodoDiscoverSpider
from microsoft_graph.addon import MicrosoftGraphAddon
from microsoft_graph.auth.session import MicrosoftGraphAuthSession
from microsoft_graph.extensions.privacy import MicrosoftGraphLogPrivacyExtension
from microsoft_graph.middlewares import (
    MicrosoftGraphDeviceCodeAuthMiddleware,
    MicrosoftGraphDiagnosticsMiddleware,
    MicrosoftGraphErrorMiddleware,
    MicrosoftGraphInteractiveAuthMiddleware,
    PrivacySafeRetryMiddleware,
)


@pytest.mark.parametrize(
    "spider_class,kwargs",
    [
        (MicrosoftOneDriveContentSpider, {"item_ids": '["id"]'}),
        (OutlookCalendarDiscoverSpider, {}),
        (OutlookDiscoverSpider, {}),
        (MicrosoftTodoDiscoverSpider, {}),
    ],
)
@pytest.mark.parametrize("auth_method", ["device_code", "interactive"])
def test_project_addon_builds_one_stack_and_keeps_consumer_policy(
    spider_class, kwargs, auth_method, tmp_path, monkeypatch
):
    settings = Settings()
    settings.setmodule(project, priority="project")
    settings.setdict(
        {
            "MS_GRAPH_AUTH_METHOD": auth_method,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        },
        priority="cmdline",
    )
    session = SimpleNamespace(auth_method=auth_method, scopes=[], account_binding=None)
    monkeypatch.setattr(
        MicrosoftGraphAuthSession, "from_crawler", lambda crawler: session
    )
    crawler = get_crawler(
        spider_class,
        # Passing global defaults as project settings would falsely make the
        # native middleware base an explicit consumer override.
        settings_dict={
            **{
                key: value
                for key, value in settings.items()
                if settings.getpriority(key)
            },
            **get_reactor_settings(),
        },
    )
    crawler.spider = spider_class.from_crawler(crawler, **kwargs)
    if [type(addon) for addon in crawler.addons.addons] != [MicrosoftGraphAddon]:
        pytest.fail("Project must load the Graph add-on through Scrapy")
    stack = DownloaderMiddlewareManager.from_crawler(crawler).middlewares
    types = [type(component) for component in stack]
    for cls in (
        PrivacySafeRetryMiddleware,
        MicrosoftGraphErrorMiddleware,
        MicrosoftGraphDiagnosticsMiddleware,
    ):
        if types.count(cls) != 1:
            pytest.fail(f"Effective stack must contain exactly one {cls.__name__}")
    if RetryMiddleware in types:
        pytest.fail("Native RetryMiddleware must not duplicate privacy-safe retry")
    expected_auth = (
        MicrosoftGraphDeviceCodeAuthMiddleware
        if auth_method == "device_code"
        else MicrosoftGraphInteractiveAuthMiddleware
    )
    actual_auth = [
        cls
        for cls in types
        if cls
        in (
            MicrosoftGraphDeviceCodeAuthMiddleware,
            MicrosoftGraphInteractiveAuthMiddleware,
        )
    ]
    if actual_auth != [expected_auth]:
        pytest.fail("App auth selection changed after add-on configuration")
    priorities = {
        load_object(key): value
        for key, value in crawler.settings.get_component_priority_dict_with_base(
            "DOWNLOADER_MIDDLEWARES"
        ).items()
    }
    if [
        priorities[cls]
        for cls in (
            PrivacySafeRetryMiddleware,
            MicrosoftGraphErrorMiddleware,
            MicrosoftGraphDeviceCodeAuthMiddleware,
            MicrosoftGraphInteractiveAuthMiddleware,
            MicrosoftGraphDiagnosticsMiddleware,
        )
    ] != [550, 555, 950, 951, 960]:
        pytest.fail("Graph request/response component ordering changed")
    if crawler.extensions is None:
        pytest.fail("Native extension manager did not initialize")
    privacy = [
        type(extension)
        for extension in crawler.extensions.middlewares
        if isinstance(extension, MicrosoftGraphLogPrivacyExtension)
    ]
    if privacy != [AppPrivacy]:
        pytest.fail("Consumer privacy subclass must replace the framework default")
    if not isinstance(
        crawler.request_fingerprinter, RepresentationAwareRequestFingerprinter
    ):
        pytest.fail("Add-on replaced the app's representation identity")
    if not isinstance(crawler.logformatter, MessageIngestLogFormatter):
        pytest.fail("Add-on replaced the app's log formatter")
    if crawler.settings.get("MS_GRAPH_STATS_PREFIX") != "msgloom":
        pytest.fail("Add-on changed the consumer stats namespace")
    if crawler.settings.getlist("MS_GRAPH_ERROR_RETRY_HTTP_CODES") != [429, 503, 509]:
        pytest.fail("Add-on changed the consumer retry policy")

"""Keep Mail acquisition-policy ownership on collection spiders only."""

import pytest
from scrapy.crawler import Crawler
from scrapy.exceptions import NotConfigured
from scrapy.settings import Settings
from scrapy.utils.project import get_project_settings
from scrapy.utils.test import get_crawler

from message_ingest import settings as project_settings
from message_ingest.acquisition.microsoft.outlook.email import (
    MAIL_RULE_POLICY_FAMILY,
    mail_rule_observation_from_item,
)
from message_ingest.acquisition.microsoft.outlook.email.policy_context import (
    OutlookMailPolicyContextExtension,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_config import (
    effective_mail_policy_digest,
    parse_mail_rule_policy,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_engine import (
    DeterministicMailRuleEvaluator,
)
from message_ingest.items.microsoft.outlook.email import OutlookMailItem
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


def _policy(*, enabled: bool, private: str = "approval"):
    raw: dict[str, object] = {"enabled": enabled}
    if enabled:
        raw.update(
            {
                "default_profile": "discovery",
                "rules": [
                    {
                        "id": "finance-01",
                        "sequence": 10,
                        "profile": "full",
                        "conditions": {"subject_contains": [private]},
                    }
                ],
            }
        )
    return parse_mail_rule_policy(raw, source_label="explicit")


def _collection_spider(policy):
    crawler = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={"MSGLOOM_SOURCE_IDENTITY_REQUIRED": False},
    )
    spider = OutlookDiscoverSpider.from_crawler(
        crawler,
        _mail_rule_policy=policy,
    )
    crawler.spider = spider
    return crawler, spider


def test_disabled_policy_keeps_real_middleware_silently_not_configured() -> None:
    crawler, spider = _collection_spider(_policy(enabled=False))

    if spider.mail_rule_evaluator is not None:
        pytest.fail("Disabled policy constructed a RuleEngine")
    with pytest.raises(NotConfigured):
        OutlookMailAcquisitionRuleMiddleware.from_crawler(crawler)


def test_enabled_policy_constructs_real_evaluator_and_safe_policy_metadata() -> None:
    policy = _policy(enabled=True)
    _crawler, spider = _collection_spider(policy)

    if not isinstance(spider.mail_rule_evaluator, DeterministicMailRuleEvaluator):
        pytest.fail("Enabled policy did not construct the deterministic RuleEngine")
    if spider.mail_rule_policy_enabled is not True:
        pytest.fail("Spider lost safe enabled-policy state")
    if spider.mail_rule_policy_family != MAIL_RULE_POLICY_FAMILY:
        pytest.fail("Spider policy-family metadata changed")
    if spider.mail_rule_policy_digest != effective_mail_policy_digest(policy):
        pytest.fail("Spider private policy digest changed")


def test_private_policy_is_not_forwarded_into_scrapy_state_or_settings() -> None:
    private = "PRIVATE_POLICY_VALUE_889"
    policy = _policy(enabled=True, private=private)
    crawler, spider = _collection_spider(policy)

    exposed = "\n".join(
        (
            repr(spider),
            repr(getattr(spider, "state", {})),
            repr(crawler.settings),
            repr(crawler.stats.get_stats()),
            repr(spider.__dict__.get("_mail_rule_policy", None)),
        )
    )
    if private in exposed:
        pytest.fail("Raw Mail policy escaped into ordinary Scrapy runtime surfaces")
    if "_mail_rule_policy" in spider.__dict__:
        pytest.fail("Raw policy kwarg was retained as a generic Spider attribute")


def test_probe_request_never_contains_raw_policy_or_private_digest() -> None:
    private = "PRIVATE_POLICY_VALUE_440"
    policy = _policy(enabled=True, private=private)
    _crawler, spider = _collection_spider(policy)
    item = OutlookMailItem.from_graph(
        {"id": "message-1", "changeKey": "change-1", "bodyPreview": "preview"},
        source_response_url="https://example.test/messages",
        observed_at="2026-10-01T00:00:00Z",
        observation_kind="delta",
        evidence_id="evidence-1",
        run_id="run-1",
    )
    observation = mail_rule_observation_from_item(item)
    evaluator = spider.mail_rule_evaluator
    if evaluator is None:
        pytest.fail("Enabled policy unexpectedly lost its evaluator")
    evaluation = evaluator.evaluate(observation)
    request = spider.mail_rule_probe_request(observation, evaluation.required_data)

    exposed = repr((request.meta, request.cb_kwargs, request.to_dict(spider=spider)))
    if private in exposed or spider.mail_rule_policy_digest in exposed:
        pytest.fail("Rule probe request serialized raw policy/private digest")
    if "_mail_rule_policy" in request.meta or "_mail_rule_policy" in request.cb_kwargs:
        pytest.fail("Private policy was copied into Request state")


def test_direct_crawl_without_private_policy_uses_xdg_default_once(
    tmp_path,
    monkeypatch,
) -> None:
    config_home = tmp_path / "xdg"
    config = config_home / "msgloom" / "msgloom.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        """[acquisition.microsoft.outlook.mail]
enabled = true
[[acquisition.microsoft.outlook.mail.rules]]
id = "r1"
sequence = 1
profile = "full"
[acquisition.microsoft.outlook.mail.rules.conditions]
subject_contains = ["approval"]
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    crawler = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={"MSGLOOM_SOURCE_IDENTITY_REQUIRED": False},
    )

    spider = OutlookDiscoverSpider.from_crawler(crawler)

    if not isinstance(spider.mail_rule_evaluator, DeterministicMailRuleEvaluator):
        pytest.fail("Direct crawl did not resolve the XDG Mail policy")


def test_rule_components_survive_scrapy_existing_crawler_runner_settings_merge() -> (
    None
):
    """Spider-priority components must survive Scrapy 2.19's Crawler re-merge."""
    settings = get_project_settings()
    crawler = Crawler(OutlookDeltaSpider, settings)

    before_middlewares = crawler.settings.getdict("SPIDER_MIDDLEWARES")
    before_extensions = crawler.settings.getdict("EXTENSIONS")
    if before_middlewares.get(OutlookMailAcquisitionRuleMiddleware) != (
        OUTLOOK_MAIL_RULE_MIDDLEWARE_PRIORITY
    ):
        pytest.fail("Mail rule middleware missing before runner settings merge")
    if before_extensions.get(OutlookMailPolicyContextExtension) != 60:
        pytest.fail("Mail policy extension missing before runner settings merge")

    # Scrapy 2.19 create_crawler(existing_crawler) applies runner settings again.
    crawler.settings.update(settings)

    after_middlewares = crawler.settings.getdict("SPIDER_MIDDLEWARES")
    after_extensions = crawler.settings.getdict("EXTENSIONS")
    if after_middlewares.get(OutlookMailAcquisitionRuleMiddleware) != (
        OUTLOOK_MAIL_RULE_MIDDLEWARE_PRIORITY
    ):
        pytest.fail("Runner settings merge erased Spider Mail rule middleware")
    if after_extensions.get(OutlookMailPolicyContextExtension) != 60:
        pytest.fail("Runner settings merge erased Spider Mail policy extension")

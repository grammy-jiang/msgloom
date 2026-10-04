"""Keep delegated Teams discovery below the public Microsoft command."""

import argparse

import pytest
from scrapy.exceptions import UsageError
from scrapy.settings import Settings

from message_ingest.commands.microsoft import Command


def _options(arguments):
    command = Command()
    command.settings = Settings()
    parser = argparse.ArgumentParser()
    command.add_options(parser)
    try:
        opts = parser.parse_args(["teams", *arguments])
    except SystemExit:
        pytest.fail("The Microsoft command did not accept the Teams namespace")
    return command, opts


@pytest.mark.parametrize(
    "resource,spider",
    [
        ("chat", "microsoft_teams_chat_discover"),
        ("channel", "microsoft_teams_channel_discover"),
    ],
)
def test_teams_discovery_maps_only_the_requested_resource(
    monkeypatch, resource, spider
):
    """Reject crossed chat/channel dispatch and hidden acquisition arguments."""
    from message_ingest.commands import _common

    calls = []
    monkeypatch.setattr(
        _common, "run_graph", lambda command, name, args: calls.append((name, args))
    )
    command, opts = _options([resource, "discover"])
    command.run([], opts)
    if calls != [(spider, {})]:
        pytest.fail("Teams discovery selected the wrong acquisition intent")


@pytest.mark.parametrize("resource", ["chat", "channel"])
def test_teams_command_preserves_explicit_source_settings(resource, monkeypatch):
    """Keep native command-line settings priority above the Teams default."""
    from message_ingest.commands import _common

    seen = []
    monkeypatch.setattr(
        _common,
        "run_graph",
        lambda command, name, args: seen.append(
            command.settings.get("MSGLOOM_TEAMS_SOURCE_ID")
        ),
    )
    command, opts = _options(
        [resource, "discover", "-s", "MSGLOOM_TEAMS_SOURCE_ID=selected-source"]
    )
    command.process_options([], opts)
    command.run([], opts)
    if seen != ["selected-source"]:
        pytest.fail("Teams command discarded explicit source selection")


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["chat"],
        ["chat", "sync"],
        ["channel", "delta"],
        ["context", "discover"],
        ["meeting", "discover"],
        ["chat", "discover", "chat-id"],
        ["channel", "discover", "team-id", "channel-id"],
        ["chat", "discover", "--page-size", "25"],
        ["chat", "discover", "--folder", "folder"],
        ["channel", "discover", "--max-pages", "0"],
        ["chat", "discover", "--reconcile"],
        ["channel", "discover", "--no-reconcile"],
        ["chat", "discover", "--operation", "refresh"],
        ["channel", "discover", "--max-enrich", "0"],
        ["chat", "discover", "--start", "2026-10-01T00:00:00Z"],
        ["channel", "discover", "--end", "2026-10-02T00:00:00Z"],
        ["chat", "discover", "--calendar", "calendar"],
        ["channel", "discover", "--json"],
        ["chat", "discover", "--yes"],
        ["channel", "discover", "--acquisition-profile", "outlook-mail-full-v1"],
    ],
)
def test_teams_rejects_unsupported_intent_before_any_crawl(arguments, monkeypatch):
    """Do not convert unsupported flags into a successful full crawl."""
    from message_ingest.commands import _common

    calls = []
    monkeypatch.setattr(_common, "run_graph", lambda *args: calls.append(args))
    command, opts = _options(arguments)
    with pytest.raises(UsageError):
        command.run([], opts)
    if calls:
        pytest.fail("Invalid Teams intent started a crawl")


@pytest.mark.parametrize("resource", ["chat", "channel"])
def test_teams_rejects_jobdir_before_crawler_creation(resource, monkeypatch):
    """An existing scheduler directory cannot imply qualified Teams resume."""
    from message_ingest.commands import _common

    calls = []
    monkeypatch.setattr(_common, "run_graph", lambda *args: calls.append(args))
    command, opts = _options([resource, "discover", "-s", "JOBDIR=prior-run"])
    command.process_options([], opts)
    with pytest.raises(UsageError, match="JOBDIR"):
        command.run([], opts)
    if calls:
        pytest.fail("Unsupported Teams resume started a crawler")

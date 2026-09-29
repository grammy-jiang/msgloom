"""Keep Contacts discovery/sync in the unified Microsoft command hierarchy."""

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
    return command, parser.parse_args(["contacts", *arguments])


@pytest.mark.parametrize(
    "action,spider",
    [("discover", "microsoft_contacts_discover"), ("sync", "microsoft_contacts_sync")],
)
def test_contacts_command_dispatches_snapshot_modes(monkeypatch, action, spider):
    from message_ingest.commands.microsoft import contacts

    calls = []
    monkeypatch.setattr(
        contacts, "run_graph", lambda command, name, args: calls.append((name, args))
    )
    command, opts = _options([action, "--page-size", "25"])
    command.run([], opts)
    if calls != [(spider, {"page_size": "25"})]:
        pytest.fail("Contacts command did not dispatch the requested snapshot mode")


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["delta"],
        ["discover", "folder-id"],
        ["sync", "folder-id"],
        ["sync", "--mailbox", "mailbox"],
        ["sync", "--folder", "folder"],
        ["sync", "--calendar", "calendar"],
        ["sync", "--max-pages", "0"],
        ["sync", "--max-enrich", "0"],
        ["sync", "--reconcile"],
        ["sync", "--no-reconcile"],
        ["sync", "--operation", "refresh"],
        ["sync", "--json"],
        ["sync", "--yes"],
        ["sync", "--start", "2026-09-29T00:00:00Z"],
        ["sync", "--end", "2026-10-01T00:00:00Z"],
    ],
)
def test_contacts_rejects_unrelated_actions_identifiers_and_options(arguments):
    command, opts = _options(arguments)
    with pytest.raises(UsageError):
        command.run([], opts)

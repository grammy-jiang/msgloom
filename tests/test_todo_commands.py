"""Keep To Do discovery inside the existing Microsoft command namespace."""

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
    return command, parser.parse_args(["todo", *arguments])


@pytest.mark.parametrize("options,size", [([], "100"), (["--page-size", "25"], "25")])
def test_todo_command_dispatches_one_discovery_spider(monkeypatch, options, size):
    from message_ingest.commands.microsoft import todo

    calls = []
    monkeypatch.setattr(
        todo, "run_graph", lambda command, name, args: calls.append((name, args))
    )
    command, opts = _options(["discover", *options])
    command.run([], opts)
    if calls != [("microsoft_todo_discover", {"page_size": size})]:
        pytest.fail("To Do must dispatch one normal Scrapy discovery crawl")


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["sync"],
        ["delta"],
        ["full"],
        ["complete"],
        ["discover", "list-id"],
        ["discover", "list-id", "task-id"],
        ["discover", "--mailbox", "mailbox"],
        ["discover", "--folder", ""],
        ["discover", "--folder", "folder"],
        ["discover", "--calendar", "calendar"],
        ["discover", "--start", "2026-09-29T00:00:00Z"],
        ["discover", "--end", "2026-10-01T00:00:00Z"],
        ["discover", "--max-pages", "0"],
        ["discover", "--max-enrich", "0"],
        ["discover", "--reconcile"],
        ["discover", "--no-reconcile"],
        ["discover", "--operation", "refresh"],
        ["discover", "--json"],
        ["discover", "--yes"],
        ["discover", "--acquisition-profile", "outlook-mail-full-v1"],
    ],
)
def test_todo_rejects_other_actions_identifiers_and_options(arguments):
    command, opts = _options(arguments)
    with pytest.raises(UsageError):
        command.run([], opts)


@pytest.mark.parametrize("size", ["0", "1001", "bad"])
def test_todo_cli_validates_page_size(size):
    with pytest.raises(SystemExit):
        _options(["discover", "--page-size", size])

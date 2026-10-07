"""Keep To Do read actions inside the existing Microsoft command namespace."""

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


@pytest.mark.parametrize(
    "action,spider,options,size",
    [
        ("discover", "microsoft_todo_discover", [], "100"),
        ("discover", "microsoft_todo_discover", ["--page-size", "25"], "25"),
        ("sync", "microsoft_todo_sync", [], "100"),
        ("sync", "microsoft_todo_sync", ["--page-size", "25"], "25"),
    ],
)
def test_todo_command_dispatches_one_read_spider(
    monkeypatch, action, spider, options, size
):
    from message_ingest.commands.microsoft import todo

    calls = []
    monkeypatch.setattr(
        todo, "run_graph", lambda command, name, args: calls.append((name, args))
    )
    command, opts = _options([action, *options])
    command.run([], opts)
    if calls != [(spider, {"page_size": size})]:
        pytest.fail("To Do command did not dispatch the expected read crawl")


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["delta"],
        ["full"],
        ["complete"],
        ["discover", "list-id"],
        ["sync", "list-id"],
        ["discover", "list-id", "task-id"],
        ["sync", "list-id", "task-id"],
        ["discover", "--mailbox", "mailbox"],
        ["sync", "--folder", "folder"],
        ["discover", "--calendar", "calendar"],
        ["sync", "--start", "2026-09-29T00:00:00Z"],
        ["discover", "--end", "2026-10-01T00:00:00Z"],
        ["sync", "--max-pages", "0"],
        ["discover", "--max-enrich", "0"],
        ["sync", "--reconcile"],
        ["discover", "--no-reconcile"],
        ["sync", "--operation", "refresh"],
        ["discover", "--json"],
        ["sync", "--yes"],
        ["discover", "--acquisition-profile", "outlook-mail-full-v1"],
    ],
)
def test_todo_rejects_other_actions_identifiers_and_options(arguments):
    command, opts = _options(arguments)
    with pytest.raises(UsageError):
        command.run([], opts)


@pytest.mark.parametrize("action", ["discover", "sync"])
def test_todo_command_rejects_jobdir(action):
    command, opts = _options([action])
    if command.settings is None:
        pytest.fail("Command settings were not initialized")
    command.settings.set("JOBDIR", "/tmp/unsupported", priority="cmdline")
    with pytest.raises(UsageError, match="JOBDIR"):
        command.run([], opts)


@pytest.mark.parametrize("action", ["discover", "sync"])
@pytest.mark.parametrize("size", ["0", "1001", "bad"])
def test_todo_cli_validates_page_size(action, size):
    with pytest.raises(SystemExit):
        _options([action, "--page-size", size])

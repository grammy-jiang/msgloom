"""Reject invalid channel collection shape and scope, including empty pages."""

from typing import Any

import pytest

from microsoft_graph.protocol import GraphObjectTypeError
from microsoft_graph.spiders.teams.channel_composition import (
    parse_channel_replies,
    parse_channel_root_messages,
)


@pytest.mark.parametrize("resources", [{}, (), "", {"value": []}])
@pytest.mark.parametrize("reply", [False, True])
def test_collection_shape_is_validated_before_iteration(resources, reply):
    parser = parse_channel_replies if reply else parse_channel_root_messages
    kwargs: dict[str, Any] = {"root_message_id": "root"} if reply else {}
    with pytest.raises(GraphObjectTypeError):
        parser(resources, host_team_id="host", channel_id="channel", **kwargs)


@pytest.mark.parametrize("reply", [False, True])
@pytest.mark.parametrize("field", ["host_team_id", "channel_id"])
def test_empty_collection_still_requires_channel_scope(reply, field):
    parser = parse_channel_replies if reply else parse_channel_root_messages
    kwargs: dict[str, Any] = {"host_team_id": "host", "channel_id": "channel"}
    kwargs[field] = ""
    if reply:
        kwargs["root_message_id"] = "root"
    with pytest.raises(ValueError):
        parser([], **kwargs)


def test_empty_reply_collection_still_requires_root_scope():
    with pytest.raises(ValueError):
        parse_channel_replies(
            [], host_team_id="host", channel_id="channel", root_message_id=""
        )

"""Synthetic SDK option and message-boundary tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any, ClassVar

import pytest
from claude_agent_sdk._internal.transport.subprocess_cli import (
    SubprocessCLITransport,
)
from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock

from msgloom.ai.sdk_worker import build_options, execute


def _payload() -> dict[str, Any]:
    return {
        "system_prompt": "trusted prompt",
        "user_prompt": '{"declared_input":"synthetic"}',
        "schema": {
            "type": "object",
            "properties": {"priority": {"type": "string"}},
            "required": ["priority"],
            "additionalProperties": False,
        },
        "model": "synthetic-qualified-model",
        "max_turns": 2,
        "max_tokens": 700,
        "cli_path": "/synthetic/claude",
    }


def test_options_disable_tools_settings_plugins_mcp_and_resume() -> None:
    """The effective pinned-SDK argv keeps every extension surface closed."""
    options = build_options(_payload())
    if options.tools != [] or options.allowed_tools != []:
        pytest.fail("both base tools and allowed tools must be empty")
    if options.setting_sources != [] or options.skills != []:
        pytest.fail("settings sources and skills must be explicitly empty")
    if options.plugins != [] or options.mcp_servers != {}:
        pytest.fail("plugins and MCP servers must be empty")
    if not options.strict_mcp_config:
        pytest.fail("strict MCP configuration must be enabled")
    if options.resume is not None or options.continue_conversation:
        pytest.fail("fresh attempts must not resume sessions")
    if options.hooks is not None or options.agents is not None:
        pytest.fail("hooks and agents must remain absent")
    transport = SubprocessCLITransport(prompt="", options=options)
    transport._cli_path = "/synthetic/claude"
    argv = transport._build_command()
    tools_index = argv.index("--tools")
    if argv[tools_index + 1] != "":
        pytest.fail("pinned SDK must emit an empty --tools value")
    required = {
        "--strict-mcp-config",
        "--setting-sources=",
        "--permission-mode",
        "dontAsk",
        "--task-budget",
        "700",
    }
    if not required <= set(argv):
        pytest.fail(f"effective argv is missing controls: {required - set(argv)}")
    forbidden = {"--continue", "--resume", "--plugin-dir", "--mcp-config"}
    if forbidden & set(argv):
        pytest.fail("effective argv contains a forbidden extension/session flag")


class _FakeClient:
    """Minimal fresh SDK client double."""

    instances: ClassVar[list[_FakeClient]] = []

    def __init__(self, options: object) -> None:
        self.options = options
        self.connected: str | None = None
        self.disconnected = False
        self.instances.append(self)

    async def connect(self, prompt: str) -> None:
        self.connected = prompt

    async def receive_response(self) -> AsyncIterator[object]:
        yield AssistantMessage(
            content=[TextBlock("synthetic exposed text")],
            model="synthetic-qualified-model",
        )
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="synthetic-session",
            structured_output={"priority": "Normal"},
        )

    async def disconnect(self) -> None:
        self.disconnected = True


def test_execute_uses_fresh_client_and_exposes_closed_events() -> None:
    """Each execution creates and closes a new SDK client."""
    _FakeClient.instances.clear()
    first: list[dict[str, object]] = []
    second: list[dict[str, object]] = []
    asyncio.run(execute(_payload(), first.append, _FakeClient))
    asyncio.run(execute(_payload(), second.append, _FakeClient))
    if len(_FakeClient.instances) != 2:
        pytest.fail("each attempt must construct a fresh SDK client")
    if not all(client.disconnected for client in _FakeClient.instances):
        pytest.fail("all fresh SDK clients must be disconnected")
    if first[-1].get("structured_output") != {"priority": "Normal"}:
        pytest.fail("structured output was not exposed")
    if {event["type"] for event in first} != {"trace", "final"}:
        pytest.fail("worker emitted an event outside the closed protocol")


class _IncompleteClient(_FakeClient):
    async def receive_response(self):
        yield AssistantMessage(
            content=[TextBlock("partial only")],
            model="synthetic-qualified-model",
        )


def test_incomplete_stream_is_failed_not_semantic_fallback() -> None:
    """A missing SDK result remains an explicit failed transport result."""
    events: list[dict[str, object]] = []
    asyncio.run(execute(_payload(), events.append, _IncompleteClient))
    if events[-1].get("ok") is not False:
        pytest.fail("incomplete SDK stream must fail")
    if events[-1].get("code") != "incomplete-sdk-stream":
        pytest.fail("incomplete SDK stream has the wrong failure code")


class _EvidenceClient(_FakeClient):
    async def receive_response(self):
        from claude_agent_sdk.types import SystemMessage, ThinkingBlock

        yield SystemMessage(
            subtype="init",
            data={"session_id": "synthetic-session", "tools": []},
        )
        yield AssistantMessage(
            content=[
                ThinkingBlock("synthetic exposed thinking", "synthetic-signature"),
                TextBlock("synthetic exposed text"),
            ],
            model="synthetic-qualified-model",
            error=None,
            usage={"input_tokens": 3, "output_tokens": 4},
            message_id="synthetic-message",
            stop_reason="end_turn",
            session_id="synthetic-session",
            uuid="synthetic-uuid",
        )
        yield ResultMessage(
            subtype="success",
            duration_ms=11,
            duration_api_ms=7,
            is_error=False,
            num_turns=1,
            session_id="synthetic-session",
            stop_reason="end_turn",
            total_cost_usd=0.01,
            usage={"input_tokens": 3, "output_tokens": 4},
            result="synthetic result",
            structured_output={"priority": "Normal"},
            model_usage={
                "synthetic-model": {
                    "inputTokens": 3,
                    "outputTokens": 4,
                    "cacheReadInputTokens": 0,
                    "cacheCreationInputTokens": 0,
                    "webSearchRequests": 0,
                    "costUSD": 0.01,
                    "contextWindow": 1000,
                    "maxOutputTokens": 100,
                }
            },
            permission_denials=[{"tool_name": "Read"}],
            errors=[],
            api_error_status=None,
            uuid="synthetic-result-uuid",
            terminal_reason="completed",
            origin={"kind": "human"},
        )


def test_full_exposed_sdk_evidence_is_preserved_before_final() -> None:
    """Public SDK fields remain closed structured evidence in stream order."""
    events: list[dict[str, object]] = []
    asyncio.run(execute(_payload(), events.append, _EvidenceClient))
    kinds = [event.get("kind") for event in events if event["type"] == "trace"]
    if kinds != ["system", "assistant_thinking", "assistant_text", "result"]:
        pytest.fail("exposed SDK evidence order or variants were lost")
    system = events[0]["data"]
    if not isinstance(system, dict) or system["data"]["tools"] != []:
        pytest.fail("SystemMessage.data was not preserved")
    thinking = events[1]["data"]
    if not isinstance(thinking, dict) or thinking["signature"] != "synthetic-signature":
        pytest.fail("ThinkingBlock evidence was not preserved")
    result = events[3]["data"]
    if not isinstance(result, dict):
        pytest.fail("ResultMessage evidence is not structured")
    expected = {
        "duration_ms": 11,
        "duration_api_ms": 7,
        "session_id": "synthetic-session",
        "total_cost_usd": 0.01,
        "terminal_reason": "completed",
    }
    if any(result.get(key) != value for key, value in expected.items()):
        pytest.fail("ResultMessage timing/session/cost metadata was lost")
    if result.get("structured_output") != {"priority": "Normal"}:
        pytest.fail("ResultMessage structured output evidence was lost")
    if result.get("model_usage") is None or result.get("usage") is None:
        pytest.fail("ResultMessage usage evidence was lost")


class _ToolClient(_FakeClient):
    async def receive_response(self):
        from claude_agent_sdk.types import ToolUseBlock

        yield AssistantMessage(
            content=[ToolUseBlock("tool-1", "Read", {"path": "/synthetic"})],
            model="synthetic-qualified-model",
        )
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="synthetic-session",
            structured_output={"priority": "Normal"},
        )


def test_unexpected_tool_event_is_visible_and_fails_closed() -> None:
    """Disabled-tool evidence is retained but cannot produce eligible output."""
    events: list[dict[str, object]] = []
    asyncio.run(execute(_payload(), events.append, _ToolClient))
    tool_events = [event for event in events if event.get("kind") == "tool_use"]
    if len(tool_events) != 1:
        pytest.fail("unexpected tool event was not exposed")
    tool_data = tool_events[0]["data"]
    if not isinstance(tool_data, dict) or tool_data.get("tool_name") != "Read":
        pytest.fail("unexpected tool identity was not retained")
    final = events[-1]
    if final.get("ok") is not False or final.get("code") != "disabled-tool-event":
        pytest.fail("disabled tool event did not fail the SDK attempt")

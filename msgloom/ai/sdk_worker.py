"""Isolated child entry point for the pinned Claude Agent SDK."""

from __future__ import annotations

import asyncio
import json
import math
import sys
from collections.abc import Callable, Mapping
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    ServerToolResultBlock,
    ServerToolUseBlock,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)


def build_options(payload: dict[str, Any]) -> ClaudeAgentOptions:
    """Build the closed effective SDK options for one fresh session."""
    return ClaudeAgentOptions(
        tools=[],
        allowed_tools=[],
        system_prompt=payload["system_prompt"],
        mcp_servers={},
        strict_mcp_config=True,
        permission_mode="dontAsk",
        continue_conversation=False,
        resume=None,
        session_id=None,
        max_turns=payload["max_turns"],
        model=payload["model"],
        fallback_model=None,
        cwd="/work",
        cli_path=payload["cli_path"],
        settings="{}",
        add_dirs=[],
        env={},
        extra_args={},
        hooks=None,
        agents=None,
        setting_sources=[],
        skills=[],
        plugins=[],
        output_format={"type": "json_schema", "schema": payload["schema"]},
        enable_file_checkpointing=False,
        task_budget={"total": payload["max_tokens"]},
    )


def _json_data(value: object, *, depth: int = 0) -> object:
    """Accept only finite JSON values already exposed by the public SDK."""
    if depth > 16:
        raise ValueError("SDK evidence nesting exceeded")
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("SDK evidence contains a non-finite number")
        return value
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("SDK evidence object key is not text")
            result[key] = _json_data(item, depth=depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        return [_json_data(item, depth=depth + 1) for item in value]
    raise TypeError("SDK exposed an unsupported evidence value")


def _assistant_meta(message: AssistantMessage, index: int) -> dict[str, object]:
    return {
        "block_index": index,
        "model": message.model,
        "parent_tool_use_id": message.parent_tool_use_id,
        "error": message.error,
        "usage": _json_data(message.usage),
        "message_id": message.message_id,
        "stop_reason": message.stop_reason,
        "session_id": message.session_id,
        "uuid": message.uuid,
    }


def _trace(
    kind: str,
    name: str,
    text: str,
    data: dict[str, object],
) -> dict[str, object]:
    return {
        "type": "trace",
        "kind": kind,
        "name": name,
        "text": text,
        "data": data,
    }


def _assistant_events(
    message: AssistantMessage,
) -> tuple[list[dict[str, object]], bool]:
    events: list[dict[str, object]] = []
    forbidden_tool = False
    for index, block in enumerate(message.content):
        data = _assistant_meta(message, index)
        if isinstance(block, TextBlock):
            data["text"] = block.text
            events.append(_trace("assistant_text", message.model, block.text, data))
            continue
        if isinstance(block, ThinkingBlock):
            data.update({"thinking": block.thinking, "signature": block.signature})
            events.append(
                _trace(
                    "assistant_thinking",
                    message.model,
                    block.thinking,
                    data,
                )
            )
            continue
        if isinstance(block, ToolUseBlock):
            data.update(
                {
                    "tool_use_id": block.id,
                    "tool_name": block.name,
                    "input": _json_data(block.input),
                    "server_side": False,
                }
            )
            events.append(_trace("tool_use", block.name, "", data))
            forbidden_tool = True
            continue
        if isinstance(block, ToolResultBlock):
            data.update(
                {
                    "tool_use_id": block.tool_use_id,
                    "content": _json_data(block.content),
                    "is_error": block.is_error,
                    "server_side": False,
                }
            )
            events.append(_trace("tool_result", block.tool_use_id, "", data))
            forbidden_tool = True
            continue
        if isinstance(block, ServerToolUseBlock):
            data.update(
                {
                    "tool_use_id": block.id,
                    "tool_name": block.name,
                    "input": _json_data(block.input),
                    "server_side": True,
                }
            )
            events.append(_trace("tool_use", block.name, "", data))
            forbidden_tool = True
            continue
        if isinstance(block, ServerToolResultBlock):
            data.update(
                {
                    "tool_use_id": block.tool_use_id,
                    "content": _json_data(block.content),
                    "server_side": True,
                }
            )
            events.append(_trace("tool_result", block.tool_use_id, "", data))
            forbidden_tool = True
            continue
        raise TypeError("SDK exposed an unsupported assistant content block")
    return events, forbidden_tool


def _result_data(message: ResultMessage) -> dict[str, object]:
    deferred = message.deferred_tool_use
    deferred_data: object = None
    if deferred is not None:
        deferred_data = {
            "id": deferred.id,
            "name": deferred.name,
            "input": _json_data(deferred.input),
        }
    return {
        "subtype": message.subtype,
        "duration_ms": message.duration_ms,
        "duration_api_ms": message.duration_api_ms,
        "is_error": message.is_error,
        "num_turns": message.num_turns,
        "session_id": message.session_id,
        "stop_reason": message.stop_reason,
        "total_cost_usd": message.total_cost_usd,
        "usage": _json_data(message.usage),
        "result": message.result,
        "structured_output": _json_data(message.structured_output),
        "model_usage": _json_data(message.model_usage),
        "permission_denials": _json_data(message.permission_denials),
        "deferred_tool_use": deferred_data,
        "errors": _json_data(message.errors),
        "api_error_status": message.api_error_status,
        "uuid": message.uuid,
        "terminal_reason": message.terminal_reason,
        "origin": _json_data(message.origin),
    }


def _result_final(message: ResultMessage) -> dict[str, object]:
    if message.is_error:
        return {
            "type": "final",
            "ok": False,
            "code": "sdk-result-error",
            "detail": message.terminal_reason or message.subtype,
        }
    if not isinstance(message.structured_output, dict):
        return {
            "type": "final",
            "ok": False,
            "code": "missing-structured-output",
            "detail": "SDK result did not contain a structured object",
        }
    return {
        "type": "final",
        "ok": True,
        "structured_output": _json_data(message.structured_output),
    }


async def execute(
    payload: dict[str, Any],
    emit: Callable[[dict[str, object]], None],
    client_factory: Callable[[ClaudeAgentOptions], Any] = ClaudeSDKClient,
) -> None:
    """Execute one fresh SDK session and emit normalized protocol events."""
    options = build_options(payload)
    final: dict[str, object] | None = None
    forbidden_tool = False
    client = client_factory(options)
    try:
        await client.connect(payload["user_prompt"])
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                events, saw_tool = _assistant_events(message)
                forbidden_tool = forbidden_tool or saw_tool
                for event in events:
                    emit(event)
                continue
            if isinstance(message, SystemMessage):
                emit(
                    _trace(
                        "system",
                        message.subtype,
                        message.subtype,
                        {
                            "subtype": message.subtype,
                            "data": _json_data(message.data),
                        },
                    )
                )
                continue
            if isinstance(message, ResultMessage):
                if final is not None:
                    raise ValueError("SDK emitted duplicate result messages")
                data = _result_data(message)
                emit(
                    _trace(
                        "result",
                        message.subtype,
                        message.terminal_reason or message.subtype,
                        data,
                    )
                )
                final = _result_final(message)
                continue
            raise TypeError("SDK emitted an unsupported message variant")
    finally:
        await client.disconnect()
    if forbidden_tool:
        final = {
            "type": "final",
            "ok": False,
            "code": "disabled-tool-event",
            "detail": "SDK exposed a tool event while tools were disabled",
        }
    if final is None:
        final = {
            "type": "final",
            "ok": False,
            "code": "incomplete-sdk-stream",
            "detail": "SDK stream ended without a result message",
        }
    emit(final)


def _stdout_emit(event: dict[str, object]) -> None:
    sys.stdout.write(
        json.dumps(
            event,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    sys.stdout.write("\n")
    sys.stdout.flush()


def main() -> None:
    """Read one parent request and run it."""
    try:
        payload = json.loads(
            sys.stdin.read(),
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite worker input")
            ),
        )
        if not isinstance(payload, dict):
            raise TypeError("worker payload must be an object")
        asyncio.run(execute(payload, _stdout_emit))
    except Exception as exc:  # noqa: BLE001 - safe child boundary
        _stdout_emit(
            {
                "type": "final",
                "ok": False,
                "code": "worker-failure",
                "detail": type(exc).__name__,
            }
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

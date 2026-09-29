"""Trusted request construction for the isolated SDK worker."""

from __future__ import annotations

import json
from pathlib import Path

from msgloom.ai.models import AnalysisAttempt


def build_worker_payload(
    attempt: AnalysisAttempt,
    schema: dict[str, object],
    model: str,
    cli_path: Path,
) -> dict[str, object]:
    """Build the exact child request from trusted application values."""
    user_prompt = json.dumps(
        {
            "declared_input": attempt.input_text,
            "working_context": attempt.context_text,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return {
        "system_prompt": attempt.prompt_text,
        "user_prompt": user_prompt,
        "schema": schema,
        "model": model,
        "max_turns": attempt.limits.max_turns,
        "max_tokens": attempt.limits.max_tokens,
        "cli_path": str(cli_path),
    }

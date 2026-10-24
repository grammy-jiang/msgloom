"""Re-run the isolated Q0 Kedro probe matrix without modifying msgloom.

Requires disposable Kedro 1.7.0 environments at <sandbox-root>/env-py312,
env-py313 and env-py314. Results are written *only* inside sandbox-root.
Run from the msgloom Q0 research worktree:
    python3 -I scripts/research/q0_kedro_matrix.py

This does NOT install any package or exercise msgloom's production data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

REQUIRED_SCENARIOS = 20
REQUIRED_INTERPRETERS = ("312", "313", "314")
TIMEOUT_PER_RUN_S = 20


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sandbox-root",
        type=Path,
        default=Path("/tmp/msgloom-a2-q0-20261023"),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
    )
    args = parser.parse_args()
    sandbox = args.sandbox_root.resolve(strict=True)
    root = args.repo_root.resolve(strict=True)
    code = (root / "scripts/research/q0_kedro_runtime_probe.py").resolve(strict=True)
    if not code.is_relative_to(root):
        raise ValueError("Q0 code escaped the explicit research root")

    results: dict[str, dict[str, Any]] = {}
    failed: list[str] = []
    for tag in REQUIRED_INTERPRETERS:
        interpreter = sandbox / f"env-py{tag}/bin/python"
        if not interpreter.exists():
            raise FileNotFoundError(f"Missing disposable runtime: py{tag}")
        for optimized in (False, True):
            name = f"py{tag}" + ("-O" if optimized else "")
            command = [
                str(interpreter),
                *(["-O"] if optimized else []),
                "-I",
                str(code),
            ]
            environment = os.environ.copy()
            environment.update(
                {
                    "DO_NOT_TRACK": "1",
                    "KEDRO_DISABLE_TELEMETRY": "1",
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
            )
            try:
                process = subprocess.run(
                    command,
                    cwd=root,
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=TIMEOUT_PER_RUN_S,
                )
                record: dict[str, Any] = {
                    "returncode": process.returncode,
                    "stderr": process.stderr,
                    "stdout_sha256": hashlib.sha256(
                        process.stdout.encode("utf-8")
                    ).hexdigest(),
                    "stdout_bytes": len(process.stdout.encode("utf-8")),
                }
                try:
                    record["result"] = json.loads(process.stdout)
                except json.JSONDecodeError:
                    record["error"] = "probe did not emit exactly one JSON record"
            except subprocess.TimeoutExpired:
                record = {"returncode": "TIMEOUT", "error": "20s hard stop"}

            result = record.get("result", {})
            if (
                record.get("returncode") != 0
                or record.get("stderr")
                or not isinstance(result, dict)
                or result.get("scenarios_passed") != REQUIRED_SCENARIOS
                or len(result.get("scenarios", [])) != REQUIRED_SCENARIOS
                or len(set(result.get("scenarios", []))) != REQUIRED_SCENARIOS
                or result.get("socket_connection_attempts_during_runtime") != 0
                or result.get("socket_control_interceptions") != 1
                or result.get("postcommit_cancel_observed_accepted") != 1
                or result.get("claims_changed_at_runtime") != 1
                or result.get("heartbeat_ticks_during_cpu", 0) < 5
                or result.get("heartbeat_max_gap_s", 1) >= 0.08
                or result.get("positive_node_log_chars", 0) <= 0
                or result.get("redacted_node_log_chars", 0) <= 0
            ):
                failed.append(name)
            results[name] = record
            print(
                f"{name}: exit={record['returncode']} "
                f"scenarios={result.get('scenarios_passed')} "
                f"json={isinstance(result, dict) and bool(result)}"
            )

    output = sandbox / "results/q0-r2-matrix.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.resolve().is_relative_to(sandbox):
        raise ValueError("matrix output escaped isolated sandbox")
    evidence = {
        "schema": "q0-r2-matrix@1",
        "probe_sha256": hashlib.sha256(code.read_bytes()).hexdigest(),
        "platform": "Raspberry Pi 5 Linux aarch64",
        "all_passed": not failed,
        "failed_variants": failed,
        "runs": results,
    }
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(f"Matrix evidence: {output}")
    if failed:
        raise SystemExit("Q0 failed variants: " + ", ".join(failed))


if __name__ == "__main__":
    main()

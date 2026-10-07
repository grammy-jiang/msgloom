"""Exercise discovery release with canonical cache bytes and enabled policy."""

import json
import subprocess
import sys

import pytest
from handoff_full_crawl_helpers import snapshot
from test_outlook_crawls import ROOT, RUN_COMMAND, graph_server

__all__ = ["graph_server"]


@pytest.mark.parametrize("policy_enabled", [False, True])
def test_native_mail_cache_release_retains_effective_policy(
    tmp_path, graph_server, policy_enabled
):
    """A replay must release old evidence under the actual discovery policy.

    The first public command stores unreleased bytes. The second public
    command enables release only in its subprocess, then uses native cache
    replay. An enabled discovery-only policy must survive into release scope.
    """
    config = tmp_path / "policy.toml"
    config.write_text(
        "[acquisition.microsoft.outlook.mail]\n"
        f"enabled = {str(policy_enabled).lower()}\n"
        'default_profile = "discovery"\n'
        "rules = []\n"
    )
    settings = {
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.db'}",
        "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
        "MSGLOOM_SOURCE_ID": "source",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
        "MSGLOOM_CATALOG_ENABLED": "True",
        "MSGLOOM_RAW_EVIDENCE_ENABLED": "True",
        "HTTPCACHE_ENABLED": "True",
        "HTTPCACHE_DIR": str(tmp_path / "cache"),
        "AUTOTHROTTLE_ENABLED": "False",
        "LOG_LEVEL": "INFO",
    }
    command = [
        "microsoft",
        "outlook",
        "mail",
        "discover",
        "--config",
        str(config),
    ]
    for key, value in settings.items():
        command.extend(["-s", f"{key}={value}"])
    before = None
    for enabled in (False, True):
        extension = "message_ingest.extensions.handoff.HandoffReleaseExtension"
        runner = RUN_COMMAND.replace(
            'execute(["scrapy",',
            "import message_ingest.settings as settings\n"
            f'settings.EXTENSIONS[{extension!r}] = None\nexecute(["scrapy",',
        )
        if enabled:
            runner = runner.replace(
                f"settings.EXTENSIONS[{extension!r}] = None",
                f"settings.EXTENSIONS[{extension!r}] = 70",
            )
        result = subprocess.run(
            [sys.executable, "-c", runner, graph_server, *command],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode or "Traceback (most recent call last)" in result.stderr:
            pytest.fail(result.stderr)
        state = snapshot(tmp_path, "mail")
        if not enabled:
            before = state
            if not state["facts"] or state["groups"]:
                pytest.fail("Seed must persist unpublished discovery facts")
            continue
        if before is None:
            pytest.fail("Cache replay has no baseline capture")
        if "httpcache/hit" not in result.stderr:
            pytest.fail("Second discovery did not exercise native cache replay")
        if state["evidence"] != before["evidence"]:
            pytest.fail("Cached discovery replaced canonical raw captures")
        if len(state["groups"]) != 1:
            pytest.fail("Cached discovery did not publish one release group")
        resources = [
            json.loads(row["payload"])
            for row in state["entries"]
            if json.loads(row["payload"])["entry_kind"] == "resource"
        ]
        if len(resources) != 2:
            pytest.fail("Cache-backed discovery lost positive message entries")
        group = state["groups"][0]
        scope = json.loads(group["scope_identity"])
        if scope["policy_enabled"] is not policy_enabled or not scope["policy_digest"]:
            pytest.fail("Discovery release lost the effective acquisition policy")
        if group["coverage_kind"] != "complete" or group["authority_revision"]:
            pytest.fail("Cached discovery changed coverage or absence authority")
        capture_runs = {
            json.loads(value)["run_id"] for value in before["facts"].values()
        }
        if group["owner_run_id"] in capture_runs:
            pytest.fail("Cache release confused logical-run and capture ownership")

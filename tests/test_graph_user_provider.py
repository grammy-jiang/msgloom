"""Exercise the user provider without application or persistence imports."""

import subprocess
import sys

import pytest


def test_user_provider_is_standalone_and_preserves_scope_override():
    code = """
import importlib.abc
import sys

class ForbidConsumer(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"message_ingest", "msgloom", "sqlalchemy"}:
            raise ImportError(f"Forbidden dependency: {fullname}")

sys.meta_path.insert(0, ForbidConsumer())
from scrapy.settings import Settings
from microsoft_graph.spiders.user import MicrosoftGraphUserSpider

spider = MicrosoftGraphUserSpider(name="user")
settings = Settings()
spider.update_settings(settings)
if settings.getlist("MS_GRAPH_SCOPES") != ["User.Read"]:
    raise RuntimeError("User provider lost its read-only scope")
if spider.user_path() != "/me":
    raise RuntimeError("User provider lost the signed-in-user endpoint")
request = spider.graph_request(spider.user_path())
if request.url != "https://graph.microsoft.com/v1.0/me":
    raise RuntimeError("User request changed its endpoint")
if request.method != "GET" or request.body or "Prefer" in request.headers:
    raise RuntimeError("User provider changed its read representation")
settings.set("MS_GRAPH_SCOPES", ["consumer"], priority="cmdline")
spider.update_settings(settings)
if settings.getlist("MS_GRAPH_SCOPES") != ["consumer"]:
    raise RuntimeError("Explicit scopes must take precedence")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode:
        pytest.fail(result.stderr)

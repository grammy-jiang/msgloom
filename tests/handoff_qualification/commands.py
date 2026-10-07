"""Subprocess command fixtures keep the actual Scrapy lifecycle intact."""

import subprocess
import sys
from pathlib import Path

from tests import test_contacts_crawl as contacts
from tests.handoff_qualification.server import END, START

ROOT = Path(__file__).resolve().parents[2]


def contacts_args(root, origin, *, delta=False, folder="folder-delta"):
    """Build the existing public snapshot or internal delta crawl command."""
    args = (
        ["crawl", "microsoft_contacts_delta", "-a", f"folder_id={folder}"]
        if delta
        else ["microsoft", "contacts", "sync"]
    )
    command = [sys.executable, "-m", "scrapy", *args]
    for key, value in contacts._settings(root, origin).items():
        command.extend(["-s", f"{key}={value}"])
    return command


def calendar(root, origin, *, end=END):
    """Invoke the public Calendar command using an explicit local root."""
    script = (
        "import sys\n"
        "from scrapy.cmdline import execute\n"
        "from message_ingest.spiders.microsoft.outlook.calendar.delta "
        "import OutlookCalendarDeltaSpider\n"
        "OutlookCalendarDeltaSpider.graph_root = sys.argv[1] + '/v1.0'\n"
        "OutlookCalendarDeltaSpider.allowed_domains = ['127.0.0.1']\n"
        "execute(['scrapy', 'microsoft', 'outlook', 'calendar', "
        "'delta', *sys.argv[2:]])\n"
    )
    settings = {
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": "False",
        "MSGLOOM_SOURCE_ID": "calendar-qualification",
        "MSGLOOM_DATABASE_URL": f"sqlite:///{root / 'catalog.sqlite3'}",
        "MSGLOOM_RAW_EVIDENCE_DIR": str(root / "raw"),
        "MSGLOOM_CATALOG_ENABLED": "True",
        "MSGLOOM_RAW_EVIDENCE_ENABLED": "True",
        "HTTPCACHE_ENABLED": "False",
        "AUTOTHROTTLE_ENABLED": "False",
        "RETRY_TIMES": "0",
        "LOG_LEVEL": "INFO",
    }
    args = [sys.executable, "-c", script, origin, "--start", START, "--end", end]
    for key, value in settings.items():
        args.extend(["-s", f"{key}={value}"])
    return subprocess.run(
        args, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False
    )


def contacts_crawl(root, origin, *, delta=False, folder="folder-delta"):
    """
    Wait for one real Contacts command using the repository fixture limit.
    """
    return subprocess.run(
        contacts_args(root, origin, delta=delta, folder=folder),
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

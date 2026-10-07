"""
Bounded local Graph fixture for Calendar reset, Contacts race and Profile.
"""

import json
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
from urllib.parse import parse_qs, urlsplit

START = "2026-09-27T00:00:00+00:00"
END = "2026-10-04T00:00:00+00:00"
OTHER_END = "2026-10-05T00:00:00+00:00"
DOWNLOAD_PATH = "/qualification/onedrive/preauthenticated-never-requested"
DOWNLOAD_SENTINEL = "task10-r2-downloadurl-sentinel-5d6c0f"


def onedrive_download_url(origin: str) -> str:
    """Return the distinctive preauthenticated URL supplied by this fixture."""
    return f"{origin}{DOWNLOAD_PATH}?token={DOWNLOAD_SENTINEL}"


@contextmanager
def local_graph():
    """Serve only synthetic data, with an explicit held delta continuation."""
    state = {"calendar": "baseline"}
    reached = Event()
    release = Event()
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            """Keep synthetic transport logs out of test output."""

        def do_GET(self):
            """Route fixture data without contacting any provider."""
            seen.append(self.path)
            split = urlsplit(self.path)
            query = parse_qs(split.query)
            status, payload = 200, {"value": []}
            if split.path == "/v1.0/me":
                payload = {"id": "profile-local", "displayName": "fixture-only"}
            elif split.path == "/v1.0/me/drive/root/delta":
                payload = {
                    "value": [
                        {
                            "id": "kept",
                            "name": "kept",
                            "eTag": "v1",
                            "file": {},
                            "@microsoft.graph.downloadUrl": onedrive_download_url(
                                origin
                            ),
                        },
                        {"id": "absent", "name": "absent", "eTag": "a1", "file": {}},
                    ],
                    "@odata.deltaLink": origin + "/v1.0/me/drive/root/delta?round=2",
                }
            elif split.path.endswith("/calendarView/delta"):
                end = query.get("endDateTime", [END])[0]
                other = end == OTHER_END
                values = [
                    {"id": "kept", "changeKey": "v1"},
                    {"id": "absent", "changeKey": "v1"},
                ]
                if state["calendar"] != "baseline" and not other:
                    values = [
                        {"id": "kept", "changeKey": "v2"},
                        {"id": "new", "changeKey": "v1"},
                    ]
                payload = {
                    "value": values,
                    "@odata.deltaLink": origin
                    + ("/calendar-other" if other else "/calendar-cursor"),
                }
            elif split.path == "/calendar-cursor":
                if state["calendar"] == "unchanged":
                    payload = {
                        "value": [
                            {"id": "kept", "changeKey": "v2"},
                            {"id": "new", "changeKey": "v1"},
                        ],
                        "@odata.deltaLink": origin + "/calendar-cursor",
                    }
                else:
                    payload = {
                        "value": [{"id": "ghost", "changeKey": "discard"}],
                        "@odata.nextLink": origin + "/calendar-expired",
                    }
            elif split.path == "/calendar-expired":
                status = 410
                payload = {"error": {"code": "SyncStateNotFound"}}
            elif split.path.endswith("/contacts/delta"):
                payload = {
                    "value": [{"id": "racing", "jobTitle": "old"}],
                    "@odata.nextLink": origin + "/held-terminal",
                }
            elif split.path == "/held-terminal":
                reached.set()
                if not release.wait(20):
                    status = 500
                    payload = {"error": {"code": "FixtureBarrierTimeout"}}
                else:
                    payload = {"value": [], "@odata.deltaLink": origin + "/done"}
            elif split.path == "/v1.0/me/contactFolders":
                payload = {"value": [{"id": "folder-race"}]}
            elif split.path.endswith("/contactFolders/folder-race/contacts"):
                payload = {"value": [{"id": "racing", "jobTitle": "winner"}]}
            elif split.path == "/v1.0/me/contacts" or split.path.endswith(
                "/childFolders"
            ):
                payload = {"value": []}
            else:
                status = 404
                payload = {"error": {"code": "UnexpectedFixtureRoute"}}
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    origin = f"http://127.0.0.1:{server.server_port}"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield origin, state, reached, release, seen
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

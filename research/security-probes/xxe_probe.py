"""Does lxml actually resolve external entities by default?

The security review asserts it does, and that the Word path (python-docx →
lxml) has no protection while the Excel path (openpyxl + defusedxml) does.

**Check the claim before writing it into a design document.** A requirement
based on a library's reputation rather than its behaviour is the kind of thing
that is wrong two versions later.

Two things are probed separately, because they are different risks:
  1. local file disclosure — does an entity pointing at a file get expanded?
  2. network egress    — does an entity pointing at a URL cause a request?
"""

import http.server
import pathlib
import socket
import tempfile
import threading

import lxml.etree as ET

SECRET = "CANARY-a7f3e9-local-file-was-read"

hits: list[str] = []


class Listener(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        hits.append(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"<!ENTITY x 'pwned'>")

    def log_message(self, *args: object) -> None:
        pass


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def probe(label: str, xml: bytes, parser: ET.XMLParser | None) -> None:
    hits.clear()
    try:
        root = ET.fromstring(xml, parser)
        text = (root.text or "") + "".join(
            (e.text or "") for e in root.iter()
        )
    except Exception as exc:  # noqa: BLE001 — a refusal is a valid outcome
        print(f"  {label:34} raised {type(exc).__name__}")
        print(f"  {'':34} file read: no · network: {'YES' if hits else 'no'}")
        return
    leaked = SECRET in text
    print(f"  {label:34} parsed")
    print(
        f"  {'':34} file read: {'**YES**' if leaked else 'no'} · "
        f"network: {'**YES**' if hits else 'no'}"
    )


def main() -> None:
    tmp = pathlib.Path(tempfile.mkdtemp())
    secret_file = tmp / "secret.txt"
    secret_file.write_text(SECRET, encoding="utf-8")

    port = free_port()
    server = http.server.HTTPServer(("127.0.0.1", port), Listener)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    local = f"""<?xml version="1.0"?>
<!DOCTYPE d [ <!ENTITY xxe SYSTEM "file://{secret_file}"> ]>
<d>&xxe;</d>""".encode()

    remote = f"""<?xml version="1.0"?>
<!DOCTYPE d [ <!ENTITY xxe SYSTEM "http://127.0.0.1:{port}/leak"> ]>
<d>&xxe;</d>""".encode()

    print(f"lxml {ET.LXML_VERSION}, libxml2 {ET.LIBXML_VERSION}\n")

    print("A local-file entity, the way a .docx would carry one")
    probe("default parser", local, None)
    probe("XMLParser()", local, ET.XMLParser())
    probe("resolve_entities=False", local, ET.XMLParser(resolve_entities=False))
    probe(
        "no_network=True (default)",
        local,
        ET.XMLParser(resolve_entities=True, no_network=True),
    )

    print("\nA remote entity — does the machine make a request?")
    probe("default parser", remote, None)
    probe("XMLParser()", remote, ET.XMLParser())
    probe(
        "no_network=False, entities on",
        remote,
        ET.XMLParser(resolve_entities=True, no_network=False),
    )
    probe("resolve_entities=False", remote, ET.XMLParser(resolve_entities=False))

    print("\nWhat defusedxml does with the same bytes")
    try:
        from defusedxml.lxml import fromstring as defused  # type: ignore

        try:
            defused(local)
            print("  defusedxml.lxml                    parsed — unexpected")
        except Exception as exc:  # noqa: BLE001
            print(f"  defusedxml.lxml                    refused: {type(exc).__name__}")
    except ImportError as exc:
        print(f"  defusedxml.lxml unavailable: {exc}")

    from defusedxml.ElementTree import fromstring as defused_et

    try:
        defused_et(local)
        print("  defusedxml.ElementTree             parsed — unexpected")
    except Exception as exc:  # noqa: BLE001
        print(f"  defusedxml.ElementTree             refused: {type(exc).__name__}")

    server.shutdown()


if __name__ == "__main__":
    main()

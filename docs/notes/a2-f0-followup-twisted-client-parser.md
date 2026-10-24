# A2 F0 follow-up: Twisted client parser and GHSA-q7qq-6mhp-9rc4

Date: 2026-10-24. Base: PR74 SHA `d2adcc9`. Host: Raspberry Pi 5, Linux
aarch64. Interpreter for reads: project `.venv`, CPython 3.13.5, used read
only with `python -B`.

This note is research evidence. It is not a risk acceptance. It does not
change the Twisted pin, `pyproject.toml` or `uv.lock`.

## Result

- Yes. A Scrapy 2.19.0 download uses Twisted 26.4.0
  `twisted.web._newclient.HTTPClientParser`. Scrapy swaps in its own
  subclass, `_LenientHTTPClientParser`, after Twisted builds the parser.
- The advisory names a different class: the server-side
  `twisted.web.http.HTTPChannel`. A Scrapy download never builds it.
- The advisory text makes no statement about the client parser. This work
  found no source or advisory evidence that the client parser is exploitable
  through this advisory. It also did not prove the opposite. See UNKNOWN.

## What the advisory says

Source: `gh api /advisories/GHSA-q7qq-6mhp-9rc4`, fetched 2026-10-24 and
read as data only. Published 2026-10-23. Severity: medium. CVE-2026-115877.
Vulnerable range: `<= 26.4.0`. First patched version: `26.10.0rc1`.

Quoted from the text:

- Summary: "An incomplete header-value validation (CWE-444) in the Twisted
  HTTP server lets a bare carriage return or line feed in a header value
  hide a following header from the parser."
- Mechanism: "`twisted.web.http.HTTPChannel.headerReceived` rejects a NUL
  byte in a header value but not a bare CR or LF".
- Precondition: "Because the channel splits requests only on CRLF, a value
  carrying a bare LF and a second header arrives as one line".
- Scope: "Affected product: Twisted, `twisted.web.http.HTTPChannel`".
- Impact: "Twisted is the strict endpoint that frames the request without a
  body, so it is realized only behind such a proxy, and there is no code
  execution."

Every statement is about parsing a request on the server side.

## Source evidence (installed Scrapy 2.19.0, Twisted 26.4.0)

Paths are relative to `site-packages`.

| Fact | Location |
| --- | --- |
| Scrapy imports `Agent`, `HTTPConnectionPool`, `HTTP11ClientProtocol` and `HTTPClientParser` | `scrapy/core/downloader/handlers/http11.py:20` to `:28` |
| The handler sets the pool factory to `_LenientHTTP11ClientFactory` | `http11.py:111` |
| `_LenientHTTPClientParser` extends `HTTPClientParser` and overrides `lineReceived` | `http11.py:785` to `:829` |
| `_LenientHTTP11ClientProtocol.request` calls Twisted `request`, then sets `self._parser.__class__ = _LenientHTTPClientParser` | `http11.py:832` to `:845` |
| Twisted `HTTP11ClientProtocol.request` builds `HTTPClientParser(request, self._finishResponse)` | `twisted/web/_newclient.py:1553` |
| `HTTPParser.delimiter = b"\n"` (client side) | `_newclient.py:224` |
| `HTTPChannel` extends `basic.LineReceiver`, whose delimiter is `b"\r\n"` | `twisted/web/http.py:2213`, `twisted/protocols/basic.py:421` |
| `HTTPClientParser` docstring: "An HTTP parser which only handles HTTP responses." | `_newclient.py:340` |
| No `HTTPChannel` reference in the handler | tested by `test_installed_sources_keep_the_claimed_structure` |

## Loopback fixture

`scripts/research/a2_f0_twisted_client_probe.py` starts a raw TCP server on
`127.0.0.1` with an ephemeral port. It runs a real Scrapy crawl. It patches
`HTTPClientParser.__init__`, `HTTPClientParser.dataReceived` and
`HTTPChannel.__init__` to count calls. No external host. No Graph.

`tests/research/test_a2_f0_twisted_client_parser.py` runs the probe in a
fresh interpreter for each mode and checks the facts. The tests are
host-portable and are collected by default.

Observed (both modes, exit 0):

| Fact | Value |
| --- | --- |
| Handler for the `http` scheme | `HTTP11DownloadHandler` |
| `HTTPClientParser` built | 1 |
| Class that received response bytes | `_LenientHTTPClientParser` |
| `HTTPChannel` built | 0 |
| Status and body | 200, `ok` |

Mode `bare-lf` sends the response header line `X-Fold: a\nX-Hidden: b`.
The crawl returned two separate headers, `X-Fold: a` and `X-Hidden: b`. The
client parser splits lines on LF. The advisory mechanism needs a split on
CRLF only. This is an observation about one input. It is not a proof of
safety.

## UNKNOWN

- UNKNOWN: whether the client parser, or Scrapy's subclass, has any
  weakness of its own. The advisory does not cover it. This work tested one
  input shape only (bare LF in a header value).
- UNKNOWN: whether other bare-CR inputs behave differently. Only bare LF was
  driven.
- UNKNOWN: client-side impact of header-value differences between a proxy
  and the client. msgloom reaches Graph over HTTPS. No proxy setting was
  examined here.
- UNKNOWN: behavior on CPython 3.12 and 3.14, and with Twisted
  `26.10.0rc1`. The prerelease was not evaluated.
- Not examined: `scrapy bench`, which starts a server-side `Site`. The
  earlier note `a2-f0-controls-20261024.md` covers it.

## Commands

| Command | Exit |
| --- | --- |
| probe, `--mode plain` and `--mode bare-lf` | 0 and 0 |
| `pytest tests/research/test_a2_f0_twisted_client_parser.py` | 0 (7 passed) |

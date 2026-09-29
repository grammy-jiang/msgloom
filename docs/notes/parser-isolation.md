# Parser isolation boundary

## Caller contract

The public preparation boundary is:

    async parse_isolated(
        request: ParserRequest, content: bytes
    ) -> ParserOutput

The caller supplies bytes already saved by the collection/evidence path and a
reviewed ParserRequest. Before process launch, the boundary verifies the exact
saved byte count and SHA-256 digest, the closed parser identity for the
detected format, the input-size ceiling, and format signatures or container
structure. The parent never selects executable code from a request field.

The caller must await the coroutine. A successful return means only that the
isolated parser output passed strict wire decoding and exact provenance
validation. The caller still owns stage admission, persistence, completion,
retry policy, and any later dependency gate. This boundary performs no
database writes and cannot mark preparation complete.

The production registry is closed to these reviewed identities:

- MIME, HTML, TEXT, JSON: msgloom.mime-html@1,
  stdlib-email+selectolax-0.4.12.
- XLSX, XLSM, XLS, XLSB, ODS: msgloom.excel@1,
  python-calamine-0.8.2+openpyxl-3.1.5.
- PDF: msgloom.pdf@1, pypdfium2-5.13.0.
- DOCX, DOC: msgloom.word@1, python-docx-1.2.0+lxml-6.1.3.

Tests use a separate TrustedRegistry containing one explicit synthetic fixture
module. The public API has no registry or module argument, so production
callers cannot turn the boundary into an arbitrary plugin runner.

## Isolation and lifecycle

Linux execution uses /usr/bin/bwrap with explicit user, PID, IPC, network, and
UTS namespaces. User-namespace creation is mandatory rather than best effort.
The worker gets a new /proc, /dev, bounded tmpfs, one read-only input file,
read-only /usr, the msgloom package, qualified site packages, and one fixed
writable result file inside an otherwise read-only output mount. System Python
runs directly from read-only /usr. A qualified non-system interpreter is
resolved from the current ``sys.executable``/``sys.base_prefix`` and only that
runtime base is mounted read-only at /runtime; its containing home directory is
not mounted. The worker does not receive the host home, checkout root, /etc,
source credentials, token caches, or a shared network namespace.

The environment is cleared and rebuilt with only runtime values for PATH,
HOME=/nonexistent, PWD=/tmp, LC_CTYPE=C.UTF-8, PYTHONPATH, and Python
no-cache/no-user-site settings.
Worker stdout and stderr are discarded. Parser/library exception text
therefore cannot echo input through IPC. The only accepted return channel is
the pre-created ``result.json`` bind, which must remain a regular, non-symlink,
single-link file no larger than ``ParserLimits.output_bytes``. The parser
cannot create sibling files in that read-only output mount. Writable scratch is
only the bounded /tmp tmpfs; ``RLIMIT_FSIZE`` is a per-file ceiling and is not
claimed as an aggregate directory quota.

The worker applies address-space, CPU, output-file, open-file, process-count,
and core-dump limits before importing the selected parser. ZIP-family inputs
are checked for member count, unsafe names, symlinks, encryption, required
container members, declared expansion, and actual streamed expansion before
native parser import. PDF and legacy Office inputs require their expected
signatures.

Wall time starts before preflight/file preparation and covers sandbox launch,
stdin IPC, parsing/process wait, and bounded result reading. Required cleanup
runs after that deadline rather than being abandoned by it. On timeout or
cancellation, the parent snapshots sandbox descendants with Linux pidfds,
sends SIGKILL through those race-resistant handles, kills and awaits the
bubblewrap child, and waits for every captured descendant pidfd to report exit
before returning. Accepted thread work, process spawn/reap, result reading, and
temporary-storage removal are drained through cancellation; repeated
cancellation cannot hand their ownership back early.

## Wire and provenance validation

Requests and outputs use UTF-8 JSON with a 64 KiB request ceiling. Decoding
rejects duplicate keys, unknown fields, non-finite numbers, type coercion, and
unknown union tags. Output bytes are bounded before JSON decoding. Every
parsed location and block is reconstructed through the prepared immutable
contracts.

The returned ParserProvenance must equal
ParserProvenance.from_request(request) exactly. A structurally valid result
with a substituted source, parser, format, profile, or parser settings is
rejected.

## Measured validation and limitations

On 2026-09-29 this lane was exercised on Linux
6.18.50+rpt-rpi-2712, Python 3.13.5, and bubblewrap 0.12.0. Synthetic tests
demonstrated event-loop progress while a synchronous fixture parser slept,
network-route and host-path isolation, environment clearing, opaque parser
failures, wall timeout, caller cancellation, descendant cleanup, output-size
rejection, unsafe output-file rejection, strict malformed-output rejection,
exact provenance rejection, and format/container preflight.

The boundary is Linux-specific and fails closed if bubblewrap, the current
trusted interpreter runtime, qualified site packages, or a registered parser
module is missing. Bubblewrap namespaces and POSIX resource limits are defence
in depth, not a proof that native parser libraries are vulnerability-free.
RLIMIT_AS and RLIMIT_CPU apply per process; RLIMIT_NPROC bounds descendant
count and the wall timer bounds the sandbox lifetime, but this lane does not
add a cgroup aggregate memory/CPU quota or a seccomp filter. /usr, qualified
site packages, the msgloom package, and (for uv-managed Python) the single
current runtime base are visible read-only because Python/native libraries
require them. Aggregate writable scratch is limited by the /tmp tmpfs size;
the host exposes no writable output directory, only the fixed result-file bind.

For manager matrix qualification, use the already-qualified uv-managed
interpreters without installing runtimes:

    UV_PROJECT_ENVIRONMENT=/tmp/msgloom-isolation-py312 \
      uv sync --frozen --python \
      /home/grammy-jiang/.local/share/uv/python/cpython-3.12-linux-aarch64-gnu/bin/python3.12
    /tmp/msgloom-isolation-py312/bin/python -m pytest -q tests/parser_isolation

    UV_PROJECT_ENVIRONMENT=/tmp/msgloom-isolation-py314 \
      uv sync --frozen --python \
      /home/grammy-jiang/.local/share/uv/python/cpython-3.14-linux-aarch64-gnu/bin/python3.14
    /tmp/msgloom-isolation-py314/bin/python -m pytest -q tests/parser_isolation

Those commands create isolated project environments from the existing frozen
lock; they do not install or select a different Python runtime. The manager
still owns dependency qualification and the native-format matrix.

"""Check claim-test synchronization with deterministic elapsed time."""

from queue import Empty
from types import SimpleNamespace

import pytest

from tests.phase1_foundation import test_persistence as target


class Clock:
    """Advance only when a simulated queue delivers or times out."""

    now = 0.0

    def monotonic(self):
        return self.now


class Queue:
    """Deliver scheduled messages within the caller's real wait budget."""

    def __init__(self, clock, messages):
        self.clock = clock
        self.messages = iter(messages)
        self.closed = False

    def get(self, timeout):
        at, value = next(self.messages, (1000, None))
        if at > self.clock.now + timeout:
            self.clock.now += timeout
            raise Empty
        self.clock.now = max(self.clock.now, at)
        return value

    def cancel_join_thread(self):
        pass

    def close(self):
        self.closed = True


class Process:
    """Retain exit and cleanup state for the parent orchestration."""

    def __init__(self, pid, exitcode):
        self.pid = pid
        self.exitcode = None
        self.final_exitcode = exitcode
        self.started = False

    def start(self):
        self.started = True

    def join(self, timeout):
        self.exitcode = self.final_exitcode

    def is_alive(self):
        return self.started and self.exitcode is None

    def terminate(self):
        self.exitcode = -15

    def kill(self):
        self.exitcode = -9


@pytest.fixture
def harness(monkeypatch):
    """Replace elapsed startup and IPC, keeping parent control flow real."""
    clock = Clock()
    monkeypatch.setattr(target, "time", clock)

    def build(ready, results, exitcode=0):
        queues = [Queue(clock, results), Queue(clock, ready)]
        processes = [Process(101, exitcode), Process(102, 0)]
        released = []
        context = SimpleNamespace(
            Event=lambda: SimpleNamespace(set=lambda: released.append(clock.now)),
            Queue=iter(queues).__next__,
            Process=lambda **kwargs: next(pending),
        )
        pending = iter(processes)
        monkeypatch.setattr(target.multiprocessing, "get_context", lambda _: context)
        return clock, queues, processes, released

    return build


def test_slow_peer_startup_keeps_fresh_contention_budget(tmp_path, harness):
    clock, queues, processes, released = harness(
        [(9.63, 101), (12, 102)], [(20, "acquired"), (21, "blocked")]
    )
    target.test_duplicate_claim_is_excluded_across_processes(tmp_path)
    if released != [12] or clock.now != 21:
        pytest.fail("Both workers must be ready before contention starts")
    if any(p.exitcode != 0 for p in processes) or not all(q.closed for q in queues):
        pytest.fail("Successful contention did not reap workers and close queues")


@pytest.mark.parametrize(
    ("ready", "results", "exitcode", "message"),
    [
        ([(1000, 101)], [], 0, "startup timed out"),
        ([(0, 101), (0, 101)], [], 0, "invalid readiness"),
        (
            [(0, 101), (0, 102)],
            [(8, "acquired"), (16, "blocked")],
            0,
            "result delivery timed out",
        ),
        ([(0, 101), (0, 102)], [(0, "acquired"), (0, "blocked")], 7, "exited with 7"),
        (
            [(0, 101), (0, 102)],
            [(0, "acquired"), (0, "acquired")],
            0,
            "Expected one durable claim winner",
        ),
    ],
)
def test_failure_is_bounded_and_cleans_up(
    tmp_path, harness, ready, results, exitcode, message
):
    clock, queues, processes, _ = harness(ready, results, exitcode)
    with pytest.raises(pytest.fail.Exception, match=message):
        target.test_duplicate_claim_is_excluded_across_processes(tmp_path)
    if clock.now > 60 or any(p.is_alive() for p in processes):
        pytest.fail("Failed orchestration exceeded its bound or leaked workers")
    if not all(q.closed for q in queues):
        pytest.fail("Failed orchestration leaked IPC queues")


@pytest.mark.parametrize("release", [True, False])
def test_worker_uses_remaining_startup_budget(tmp_path, monkeypatch, release):
    """A ready child can wait for a slow peer; an absent gate still fails."""
    clock = Clock()
    monkeypatch.setattr(target, "time", clock)
    results = []

    def announce(pid):
        clock.now = 11

    def wait(timeout):
        if timeout > 49:
            pytest.fail("Child reset the shared startup deadline")
        return release and timeout >= 12

    args = (
        target._url(tmp_path / "worker.sqlite3"),
        SimpleNamespace(wait=wait),
        SimpleNamespace(put=results.append),
        SimpleNamespace(put=announce),
        60,
    )
    if not release:
        with pytest.raises(TimeoutError, match="start barrier expired"):
            target._claim_process(*args)
        if results:
            pytest.fail("Worker contended before the gate was released")
        return
    target._claim_process(*args)
    if results != ["acquired"]:
        pytest.fail("Ready worker did not contend after the slow peer arrived")

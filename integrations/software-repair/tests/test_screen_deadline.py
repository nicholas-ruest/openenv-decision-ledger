import importlib.util
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import signal
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

spec = importlib.util.spec_from_file_location("deadline_fixture", Path(__file__).parents[1] / "scripts/screen_deadline.py")
deadline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deadline)


def finished(until, code):
    assert until > time.monotonic()
    return code


def hangs(until, partial):
    with Path(partial).open("x") as stream:
        stream.write("partial archive\n")
        stream.flush()
        os.fsync(stream.fileno())
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(time.sleep, [30] * 4))


def fails(until):
    raise RuntimeError("synthetic detail that must not be serialized")


def disappears(until):
    os._exit(0)


def parent_loss_worker(until, connection, partial):
    with Path(partial).open("x") as stream:
        stream.write("observed before parent loss\n")
        stream.flush()
        os.fsync(stream.fileno())
    ready = threading.Barrier(5)
    def blocked():
        ready.wait(timeout=2)
        time.sleep(30)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(blocked) for _ in range(4)]
        ready.wait(timeout=2)
        connection.send(os.getpid())
        connection.close()
        for future in futures:
            future.result()


def parent_loss_supervisor(connection, root):
    deadline.run_bounded(parent_loss_worker, (connection, root / "partial"), 30, root / "receipt")


def parent_loss_harness(result_connection, root):
    # Isolate Linux subreaper state inside a fixture process, not the test host.
    # It adopts and reaps the worker after its owned supervisor is killed.
    assert deadline.ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0
    context = deadline.multiprocessing.get_context("fork")
    receiver, sender = context.Pipe(duplex=False)
    supervisor = context.Process(target=parent_loss_supervisor, args=(sender, root))
    supervisor.start()
    sender.close()
    worker = None
    reaped = False
    try:
        assert receiver.poll(3), "fixture worker did not start"
        worker = receiver.recv()
        supervisor.kill()
        supervisor.join(timeout=1)
        until = time.monotonic() + 3
        while time.monotonic() < until:
            pid, status = os.waitpid(worker, os.WNOHANG)
            if pid == worker:
                reaped = True
                result_connection.send({"signal": os.WTERMSIG(status), "reaped": True,
                                        "supervisor_exit": supervisor.exitcode})
                return
            time.sleep(.01)
        raise AssertionError("worker survived supervisor death")
    finally:
        if supervisor.is_alive():
            supervisor.kill()
            supervisor.join(timeout=1)
        if worker is not None and not reaped:
            # This is our adopted, unreaped child; its PID cannot be reused.
            os.kill(worker, signal.SIGKILL)
            os.waitpid(worker, 0)
        receiver.close()
        result_connection.close()


def test_actual_supervisor_sigkill_stops_and_reaps_worker_threads(tmp_path):
    context = deadline.multiprocessing.get_context("fork")
    receiver, sender = context.Pipe(duplex=False)
    harness = context.Process(target=parent_loss_harness, args=(sender, tmp_path))
    harness.start()
    sender.close()
    try:
        assert receiver.poll(6), "parent-loss fixture failed to report"
        result = receiver.recv()
        harness.join(timeout=1)
        assert harness.exitcode == 0
        assert result == {"signal": signal.SIGKILL, "reaped": True, "supervisor_exit": -signal.SIGKILL}
        assert (tmp_path / "partial").read_text() == "observed before parent loss\n"
        events = [json.loads(line) for line in (tmp_path / "receipt").read_text().splitlines()]
        assert all(e["event"] != "terminal" for e in events)
    finally:
        if harness.is_alive():
            harness.kill()
        harness.join(timeout=1)
        receiver.close()


def test_parent_change_race_and_guard_failure_refuse_target(monkeypatch):
    class FailedLib:
        def prctl(self, *args):
            return -1
    monkeypatch.setattr(deadline.ctypes, "CDLL", lambda *a, **kw: FailedLib())
    with pytest.raises(OSError, match="cannot arm"):
        deadline.arm_parent_death(os.getppid())
    class GoodLib:
        def prctl(self, *args):
            assert args[:2] == (1, signal.SIGKILL)
            return 0
    monkeypatch.setattr(deadline.ctypes, "CDLL", lambda *a, **kw: GoodLib())
    killed = []
    monkeypatch.setattr(deadline.os, "kill", lambda pid, sig: killed.append((pid, sig)))
    with pytest.raises(RuntimeError, match="parent changed"):
        deadline.arm_parent_death(-1)
    assert killed == [(os.getpid(), signal.SIGKILL)]


def test_worker_never_enters_target_when_parent_guard_cannot_arm(monkeypatch):
    def fail_guard(parent):
        raise OSError("private guard detail")
    monkeypatch.setattr(deadline, "arm_parent_death", fail_guard)
    class Connection:
        def __init__(self):
            self.events = []
            self.closed = False
        def send(self, event):
            self.events.append(event)
        def close(self):
            self.closed = True
    connection = Connection()
    with pytest.raises(SystemExit) as stopped:
        deadline._entry(connection, lambda *a: pytest.fail("unprotected target entered"), (),
                        time.monotonic() + 1, os.getpid())
    assert stopped.value.code == 1 and connection.closed
    assert connection.events[0]["exception_type"] == "OSError"
    assert "private guard detail" not in json.dumps(connection.events)


class BlockingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        time.sleep(30)
    def log_message(self, *args):
        pass


def serve_blocking(connection):
    server = HTTPServer(("127.0.0.1", 0), BlockingHandler)
    connection.send(server.server_port)
    connection.close()
    server.serve_forever()


def http_hangs(until, port):
    def request(_):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        connection.request("GET", "/")
        connection.getresponse()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(request, range(4)))


def test_actual_child_and_http_threads_stop_at_wall_bound_preserving_partial_archive(tmp_path):
    receipt, partial = tmp_path / "worker.jsonl", tmp_path / "partial.jsonl"
    result = deadline.run_bounded(hangs, (partial,), .5, receipt)
    assert result["status"] == "timed_out" and result["shutdown_verified"]
    assert result["worker_exitcode"] == -signal.SIGKILL and result["elapsed_seconds"] < 3
    assert partial.read_text() == "partial archive\n"
    assert not (tmp_path / "complete.json").exists()
    events = [json.loads(line) for line in receipt.read_text().splitlines()]
    assert [row["event"] for row in events] == ["starting", "started", "terminal"]
    saved = receipt.read_bytes()
    with pytest.raises(FileExistsError):
        deadline.run_bounded(finished, (0,), 1, receipt)
    assert receipt.read_bytes() == saved and partial.read_text() == "partial archive\n"


def test_hard_deadline_also_stops_actual_blocked_local_http_requests(tmp_path):
    context = deadline.multiprocessing.get_context("fork")
    receiver, sender = context.Pipe(duplex=False)
    server = context.Process(target=serve_blocking, args=(sender,), daemon=True)
    server.start()
    sender.close()
    try:
        assert receiver.poll(2), "local fixture server did not start"
        port = receiver.recv()
        result = deadline.run_bounded(http_hangs, (port,), .5, tmp_path / "http-worker.jsonl")
        assert result["status"] == "timed_out" and result["shutdown_verified"]
        assert result["worker_exitcode"] == -signal.SIGKILL and result["elapsed_seconds"] < 3
    finally:
        if server.is_alive():
            server.kill()
        server.join(timeout=1)
        receiver.close()


@pytest.mark.parametrize("code,status", [(0, "completed"), (7, "worker_failed")])
def test_normal_and_failed_exit_are_distinct_and_observed(tmp_path, code, status):
    result = deadline.run_bounded(finished, (code,), 2, tmp_path / "worker.jsonl")
    assert result["status"] == status and result["shutdown_verified"]
    assert result["worker_exitcode"] == code
    assert result["finished_before_deadline"]


def test_exception_text_and_missing_result_cannot_become_success(tmp_path):
    receipt = tmp_path / "error.jsonl"
    result = deadline.run_bounded(fails, (), 2, receipt)
    assert result["status"] == "worker_failed" and result["exception_type"] == "RuntimeError"
    assert "synthetic detail" not in receipt.read_text()
    result = deadline.run_bounded(disappears, (), 2, tmp_path / "missing.jsonl")
    assert result["status"] == "worker_failed" and result["worker_exitcode"] == 0


@pytest.mark.parametrize("seconds", [0, -1, True, float("inf"), float("nan"), 1201])
def test_invalid_or_unbounded_worker_limits_refused_before_any_receipt(tmp_path, seconds):
    receipt = tmp_path / "worker.jsonl"
    with pytest.raises(ValueError):
        deadline.run_bounded(finished, (0,), seconds, receipt)
    assert not receipt.exists()


def test_request_timeout_is_remaining_time_not_a_fresh_full_timeout():
    assert deadline.request_timeout(11, 15, now=10) == 1
    assert deadline.request_timeout(100, 15, now=10) == 15
    with pytest.raises(deadline.DeadlineExceeded):
        deadline.request_timeout(10, 90, now=10)
    with pytest.raises(deadline.DeadlineExceeded):
        deadline.request_timeout(9, 90, now=10)

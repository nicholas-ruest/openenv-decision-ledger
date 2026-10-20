import importlib.util
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import signal
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

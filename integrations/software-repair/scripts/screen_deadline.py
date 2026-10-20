"""Linux supervision for this in-process calibration worker and its HTTP threads.

No provider API, job creation, credential lookup or billing cancellation exists
here. Killing a local worker does not attest remote request cancellation.
"""
import json
import math
import multiprocessing
import os
from pathlib import Path
import time


class DeadlineExceeded(TimeoutError):
    pass


def request_timeout(deadline, cap, *, now=None):
    if type(cap) not in (int, float) or not math.isfinite(cap) or cap <= 0:
        raise ValueError("finite positive request cap required")
    remaining = deadline - (time.monotonic() if now is None else now)
    if not math.isfinite(remaining) or remaining <= 0:
        raise DeadlineExceeded("stage deadline consumed")
    return min(cap, remaining)


def _entry(connection, target, args, deadline):
    try:
        code = target(deadline, *args)
        code = 0 if code is None else code
        if type(code) is not int or not 0 <= code <= 255:
            raise TypeError("worker return code required")
    except BaseException as exc:
        # Never serialize exception text or arbitrary worker return values.
        connection.send({"exception_type": type(exc).__name__, "finished_at": time.monotonic()})
        code = 1
    else:
        connection.send({"returncode": code, "finished_at": time.monotonic()})
    finally:
        connection.close()
    raise SystemExit(code)


def run_bounded(target, args, seconds, receipt):
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 1200:
        raise ValueError("worker wall bound must be positive and at most1200 seconds")
    context = multiprocessing.get_context("fork")  # Existing runner also requires Linux/fcntl.
    with Path(receipt).open("x") as stream:
        def record(value):
            stream.write(json.dumps(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        started = time.monotonic()
        deadline = started + seconds
        record({"event": "starting", "wall_seconds": seconds, "target": target.__name__})
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(target=_entry, args=(sender, target, args, deadline), daemon=True)
        try:
            process.start()
            sender.close()
            record({"event": "started", "pid": process.pid})
            timed_out = False
            while process.is_alive():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    process.kill()  # Owned, unreaped child; all its HTTP threads stop together.
                    break
                process.join(timeout=min(.05, remaining))
            process.join(timeout=1)
            message = {}
            while receiver.poll():
                try:
                    message = receiver.recv()
                except EOFError:
                    break
            stopped = not process.is_alive()
            finished = message.get("finished_at")
            before_deadline = type(finished) in (int, float) and math.isfinite(finished) and finished <= deadline
            late = type(finished) in (int, float) and math.isfinite(finished) and finished > deadline
            timed_out = timed_out or late
            status = ("timed_out" if timed_out else "completed"
                      if stopped and before_deadline and process.exitcode == 0 and message.get("returncode") == 0
                      else "worker_failed")
            result = {"status": status, "pid": process.pid, "worker_exitcode": process.exitcode,
                      "shutdown_verified": stopped, "finished_before_deadline": before_deadline,
                      "elapsed_seconds": time.monotonic() - started}
            if "exception_type" in message:
                result["exception_type"] = message["exception_type"]
            record({"event": "terminal", **result})
            return result
        except BaseException:
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
            record({"event": "supervisor_interrupted", "shutdown_verified": not process.is_alive()})
            raise
        finally:
            sender.close()
            receiver.close()

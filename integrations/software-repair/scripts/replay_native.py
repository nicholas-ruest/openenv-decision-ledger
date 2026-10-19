"""Exercise declared, repaired and rejected-code controls over OpenEnv WebSocket."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.request

from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from repair_env.tasks import TASK_IDS, make_task  # noqa: E402


def exchange(socket, kind, data):
    socket.send(json.dumps({"type": kind, "data": data}))
    message = json.loads(socket.recv(timeout=20))
    assert message["type"] == "observation", message.get("type")
    result = message["data"]
    assert type(result["done"]) is bool
    assert type(result["reward"]) in (int, float) and 0 <= result["reward"] <= 1
    return result


def replay(url):
    parsed = urllib.parse.urlsplit(url)
    assert parsed.scheme in ("http", "https") and parsed.hostname
    assert not (parsed.username or parsed.password or parsed.query or parsed.fragment)
    base = url.rstrip("/")
    ws = ("wss" if parsed.scheme == "https" else "ws") + "://" + parsed.netloc + parsed.path.rstrip("/") + "/ws"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(base + "/schema", timeout=10) as response:
        schema = json.load(response)
    assert {"action", "observation"} <= schema.keys()
    records = []
    for index, task_id in enumerate(TASK_IDS):
        reference = make_task(task_id, 983000 + index).reference_source  # Exact public level-specific fixture.
        for control in ("declared_examples", "reference_repair", "rejected_host_access", "protected_test_file"):
            with connect(ws, proxy=None, max_size=1_048_576, open_timeout=10, close_timeout=3) as socket:
                reset = exchange(socket, "reset", {"task_id": task_id, "seed": 983000 + index})
                assert not reset["done"] and reset["reward"] == 0
                files = exchange(socket, "step", {"op": "read", "path": "*"})
                workspace = json.loads(files["observation"]["content"])
                assert set(workspace) == {"README.md", "pyproject.toml", "src/solution.py", "tests/test_public.py"}
                if control == "reference_repair":
                    exchange(socket, "step", {"op": "write", "path": "src/solution.py", "content": reference})
                    tested = exchange(socket, "step", {"op": "test"})
                    assert json.loads(tested["observation"]["content"])["passed"] == 6
                elif control == "rejected_host_access":
                    exchange(socket, "step", {"op": "write", "path": "src/solution.py",
                        "content": "import os\ndef f(): return os.environ\n"})
                    tested = exchange(socket, "step", {"op": "test"})
                    assert tested["observation"]["error"]
                elif control == "protected_test_file":
                    result = exchange(socket, "step", {"op": "write", "path": "tests/test_public.py", "content": "pass"})
                    assert result["observation"]["error"]
                terminal = exchange(socket, "step", {"op": "submit"})
                expected = 1.0 if control == "reference_repair" else 0.0
                assert terminal["done"] and terminal["reward"] == expected, (task_id, control, terminal["reward"])
                records.append({"task_id": task_id, "control": control, "reward": expected,
                    "workspace_sha256": hashlib.sha256(json.dumps(workspace, sort_keys=True).encode()).hexdigest()})
    return {"status": "passed", "episodes_passed": len(records), "episodes_expected": 4 * len(TASK_IDS),
        "schema": {key: schema[key] for key in ("action", "observation")}, "records": records,
        "is_model_benchmark": False, "private_arena_score": None,
        "limits": ["Native protocol and reference fixtures only; no model learning/transfer evidence",
                   "Source reference fixtures are public algorithms, not independently sampled model actions"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = replay(args.url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps({key: report[key] for key in ("status", "episodes_passed", "episodes_expected")}))

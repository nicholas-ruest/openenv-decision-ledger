"""Independent anonymous WebSocket controls for the direct-code application."""
import argparse
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.request

from websockets.sync.client import connect

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from repair_env.direct_environment import DIRECT_TASK_IDS, SYNTHESIS_TASK_ID, DirectRepairAction
from repair_env.environment import RepairAction, RepairEnvironment
from repair_env.tasks import SOURCE_PATH, make_task


def exchange(socket, kind, data):
    socket.send(json.dumps({"type": kind, "data": data}))
    reply = json.loads(socket.recv(timeout=20))
    assert reply["type"] == "observation", reply.get("type")
    return reply["data"]


def replay(url):
    parsed = urllib.parse.urlsplit(url)
    assert parsed.scheme in ("http", "https") and not (parsed.username or parsed.password or parsed.query or parsed.fragment)
    base = url.rstrip("/")
    request = urllib.request.Request(base + "/schema")
    with urllib.request.urlopen(request, timeout=10) as response:
        schema = json.load(response)
    assert schema["action"] == DirectRepairAction.model_json_schema()
    ws = ("wss" if parsed.scheme == "https" else "ws") + "://" + parsed.netloc + parsed.path.rstrip("/") + "/ws"
    records = []
    tasks = DIRECT_TASK_IDS + (SYNTHESIS_TASK_ID,)
    for task_id in tasks:
        for seed in (1110000, 1110100, 1110200, 1110300):
            task = make_task(task_id, seed)
            partial = (task.reference_source.replace('"cycles": sorted(cycles)', '"cycles": []')
                       if task_id == SYNTHESIS_TASK_ID else
                       task.initial_source.replace("if cost < budget:", "if cost <= budget:"))
            for control, code in (("reference", task.reference_source),
                                  ("unchanged", task.initial_source), ("empty", ""),
                                  ("local_partial_control", partial),
                                  ("host_access_rejected", "import os\ndef plan_release(a,b,c,d): return os.environ")):
                core = RepairEnvironment(); core.reset(task_id=task_id, seed=seed)
                core.step(RepairAction(op="write", path=SOURCE_PATH, content=code))
                expected = float(core.step(RepairAction(op="submit")).reward)
                with connect(ws, proxy=None, open_timeout=10, close_timeout=3, max_size=1_048_576) as socket:
                    initial = exchange(socket, "reset", {"task_id": task_id, "seed": seed})
                    assert initial["observation"]["source"] == task.initial_source and not initial["done"]
                    result = exchange(socket, "step", {"content": code})
                    assert result["done"] and result["reward"] == expected
                if control == "reference":
                    assert expected == 1
                if control in ("unchanged", "empty", "host_access_rejected"):
                    assert expected == 0
                records.append({"task_id": task_id, "seed": seed, "control": control,
                                "reward": expected, "passed": True})
    return {"status": "passed", "episodes_passed": len(records), "episodes_expected": len(tasks) * 4 * 5,
            "records": records, "model_solves": False, "training": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    value = replay(args.url); args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, indent=2))
    print(json.dumps({k: value[k] for k in ("status", "episodes_passed", "episodes_expected")}))

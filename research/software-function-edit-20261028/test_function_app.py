"""Native in-process HTTP/WebSocket controls, with no provider/model calls."""
import ast
import unittest
from fastapi.testclient import TestClient
from function_app import app
from function_edit import FunctionEditAction, TARGETS
from repair_env.direct_environment import DirectRepairObservation
from repair_env.tasks import make_task


def definition(code, name):
    node = next(n for n in ast.parse(code).body
                if isinstance(n, ast.FunctionDef) and n.name == name)
    return "".join(code.splitlines(keepends=True)[node.lineno-1:node.end_lineno])


def exchange(ws, kind, data):
    ws.send_json({"type": kind, "data": data})
    result = ws.receive_json()
    if result["type"] != "observation":
        raise AssertionError(result)
    return result["data"]


class NativeAppTests(unittest.TestCase):
    def test_http_schema_matches_actual_models(self):
        with TestClient(app) as client:
            response = client.get("/schema")
            self.assertEqual(response.status_code, 200)
            schema = response.json()
            self.assertEqual(schema["action"], FunctionEditAction.model_json_schema())
            self.assertEqual(schema["observation"], DirectRepairObservation.model_json_schema())

    def test_both_tasks_and_modes_terminate_with_unchanged_reference_grade(self):
        with TestClient(app) as client:
            for index, (task, target) in enumerate(TARGETS.items()):
                seed = 2440000 + index
                ref = make_task(task, seed).reference_source
                for mode in ("function", "module"):
                    with client.websocket_connect("/ws") as ws:
                        reset = exchange(ws, "reset", {"task_id": task, "seed": seed})
                        self.assertFalse(reset["done"])
                        self.assertEqual(reset["observation"]["task_id"], task)
                        content = definition(ref, target) if mode == "function" else ref
                        final = exchange(ws, "step", {"mode": mode, "content": content})
                        self.assertTrue(final["done"])
                        self.assertEqual(final["reward"], 1)
                        self.assertEqual(final["observation"]["source"], "")

    def test_additive_helper_survives_transport(self):
        task = "software_repair-ignore-d3"
        seed = 2440100
        ref = definition(make_task(task, seed).reference_source, TARGETS[task])
        content = ref.replace("def classify_ignore(", "def new_aggregation(")
        content += "\ndef classify_ignore(a,b):\n    return new_aggregation(a,b)\n"
        with TestClient(app) as client, client.websocket_connect("/ws") as ws:
            exchange(ws, "reset", {"task_id": task, "seed": seed})
            final = exchange(ws, "step", {"content": content})
            self.assertTrue(final["done"])
            self.assertEqual(final["reward"], 1)

    def test_invalid_function_and_empty_finish_are_terminal_zero(self):
        with TestClient(app) as client:
            for action in ({"content": "import os"}, {}):
                with client.websocket_connect("/ws") as ws:
                    exchange(ws, "reset", {"task_id": "software_repair-ignore-d3", "seed": 2440200})
                    final = exchange(ws, "step", action)
                    self.assertTrue(final["done"])
                    self.assertEqual(final["reward"], 0)

    def test_concurrent_sessions_keep_separate_task_and_terminal_state(self):
        first, second = tuple(TARGETS)
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as one, client.websocket_connect("/ws") as two:
                exchange(one, "reset", {"task_id": first, "seed": 2440300})
                exchange(two, "reset", {"task_id": second, "seed": 2440301})
                failed = exchange(one, "step", {"content": "import os"})
                ref = make_task(second, 2440301).reference_source
                passed = exchange(two, "step", {"mode": "module", "content": ref})
                self.assertEqual(failed["observation"]["task_id"], first)
                self.assertEqual(passed["observation"]["task_id"], second)
                self.assertEqual((failed["reward"], passed["reward"]), (0, 1))


if __name__ == "__main__":
    unittest.main()

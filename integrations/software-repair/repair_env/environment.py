"""OpenEnv edit/test workflow backed by a bounded Python-subset interpreter."""
from __future__ import annotations

import json
import secrets
from typing import Literal
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field

from .runner import Program, Rejected
from .tasks import SOURCE_PATH, TASK_IDS, make_task, visible_files

MAX_STEPS = 12


class RepairAction(Action):
    op: Literal["list", "read", "write", "test", "submit"]
    path: str = ""
    content: str = Field(default="", max_length=8192)


class RepairObservation(Observation):
    task_id: str = ""
    prompt: str = ""
    files: list[str] = Field(default_factory=list)
    content: str = ""
    error: str = ""
    remaining_steps: int = 0


def exact(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) in (list, tuple):
        return len(actual) == len(expected) and all(exact(a, b) for a, b in zip(actual, expected))
    if type(expected) is dict:
        return actual.keys() == expected.keys() and all(exact(actual[k], expected[k]) for k in actual)
    return actual == expected


def check(program, task, cases, *, details=False):
    passed, results = 0, []
    for index, case in enumerate(cases):
        try:
            actual = program.run(task.entrypoint, case.args)
            good, error = exact(actual, case.expected), None
        except (Rejected, ArithmeticError, TypeError, ValueError, KeyError, IndexError, RecursionError, RuntimeError):
            actual, good, error = None, False, "candidate execution rejected or failed"
        passed += good
        if details:
            results.append({"test": index + 1, "passed": good, "args": case.args,
                            "expected": case.expected, "actual": actual, "error": error})
    return passed, results


class RepairEnvironment(Environment[RepairAction, RepairObservation, State]):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        super().__init__()
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._task = None
        self._done, self._reward = False, 0.0

    def reset(self, seed=None, episode_id=None, **kwargs):
        task_id = kwargs.get("task_id", TASK_IDS[0])
        seed = secrets.randbelow(2**63) if seed is None else seed
        self._task = make_task(task_id, seed)
        self._files = visible_files(self._task)
        self._original = Program(self._task.initial_source)
        self._baseline, _ = check(self._original, self._task, self._task.hidden)
        if self._baseline == len(self._task.hidden):
            raise ValueError("generated task lacks an observable defect")
        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)
        self._done, self._reward = False, 0.0
        return self._observe(prompt=self._files["README.md"], files=sorted(self._files))

    def _observe(self, **fields):
        return RepairObservation(task_id=self._task.task_id if self._task else "",
            done=self._done, reward=self._reward,
            remaining_steps=max(0, MAX_STEPS - self._state.step_count), **fields)

    def step(self, action: RepairAction, timeout_s=None, **kwargs):
        if self._task is None:
            raise RuntimeError("reset required")
        if self._done:
            return self._observe(error="episode is terminal")
        self._state.step_count += 1
        if action.op == "submit":
            self._done = True
            try:
                program = Program(self._files[SOURCE_PATH])
                if program.fingerprint != self._original.fingerprint:
                    passed, _ = check(program, self._task, self._task.hidden)
                    total = len(self._task.hidden)
                    if passed == total:
                        self._reward = 1.0
                    elif passed > self._baseline:
                        self._reward = min(0.95, (passed - self._baseline) / (total - self._baseline))
            except (Rejected, RecursionError):
                self._reward = 0.0
            return self._observe()
        if self._state.step_count >= MAX_STEPS:
            self._done = True
            return self._observe(error="step budget exhausted; submit before the last step")
        if action.op == "list":
            return self._observe(files=sorted(self._files))
        if action.op == "read":
            if action.path == "*":
                return self._observe(content=json.dumps(self._files, separators=(",", ":")))
            return self._observe(content=self._files[action.path]) if action.path in self._files else self._observe(error="unknown workspace path")
        if action.op == "write":
            if action.path != SOURCE_PATH or len(action.content.encode()) > 8192:
                return self._observe(error="only src/solution.py is writable; source limit8192 bytes")
            self._files[SOURCE_PATH] = action.content
            return self._observe(content="module updated; use test for visible feedback")
        if action.op == "test":
            try:
                program = Program(self._files[SOURCE_PATH])
                passed, results = check(program, self._task, self._task.public, details=True)
                feedback, detailed_failures = [], 0
                for result in results:
                    if not result["passed"] and detailed_failures < 2:
                        feedback.append(result)
                        detailed_failures += 1
                    else:
                        feedback.append({"test": result["test"], "passed": result["passed"], "error": result["error"]})
                return self._observe(content=json.dumps({"passed": passed, "total": len(results), "tests": feedback,
                    "feedback": "Full inputs and expectations are in tests/test_public.py; at most two failing examples are repeated here."}, separators=(",", ":")))
            except (Rejected, RecursionError):
                return self._observe(error="invalid or unsupported Python; see README.md")
        raise ValueError("unknown action")

    @property
    def state(self):
        return self._state.model_copy(deep=True)

"""One-response repair interface over the existing, unchanged semantic grader.

This is a separate experimental application. The submitted edit/test application
and its eight-task export are unaffected. No candidate code executes on the host.
"""
from __future__ import annotations

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field

from .environment import RepairAction, RepairEnvironment
from .tasks import SOURCE_PATH, compact_literal

DIRECT_TASK_IDS = ("software_repair-release-d2", "software_repair-release-d3")
SYNTHESIS_TASK_ID = "software_repair-release-d4"
KV_TASK_IDS = ("software_repair-kv-d1", "software_repair-kv-d2")
LINEAR_TASK_IDS = ("software_repair-linear-d1", "software_repair-linear-d2")


class DirectRepairAction(Action):
    content: str = Field(description="Complete repaired Python module, without markdown fences.",
                         max_length=8192)


class DirectRepairObservation(Observation):
    task_id: str = ""
    prompt: str = ""
    source: str = ""
    examples: str = ""
    error: str = ""


class DirectRepairEnvironment(Environment[DirectRepairAction, DirectRepairObservation, State]):
    SUPPORTS_CONCURRENT_SESSIONS = True
    _finish_action = DirectRepairAction(content="")

    def __init__(self):
        super().__init__()
        self._core = RepairEnvironment()
        self._terminal = None

    @property
    def _task(self):
        return self._core._task

    @property
    def _files(self):
        return self._core._files

    def reset(self, seed=None, episode_id=None, **kwargs):
        task_id = kwargs.get("task_id", DIRECT_TASK_IDS[-1])
        if task_id not in DIRECT_TASK_IDS + (SYNTHESIS_TASK_ID,) + KV_TASK_IDS + LINEAR_TASK_IDS:
            raise ValueError("direct pilot requires a declared release or kv task")
        self._core.reset(seed=seed, episode_id=episode_id, task_id=task_id)
        self._terminal = None
        task = self._task
        # Reuse only the language contract, not obsolete tool instructions.
        readme = self._files["README.md"]
        subset = readme[readme.index("Python subset:"):]
        prompt = (task.instructions + "\n" + subset +
                  '\nRepair the supplied source. Reply once with the action instance '
                  '{"content":"the complete repaired Python module"}. '
                  "Do not return the JSON schema, markdown, a diff or a tool command. "
                  "The six examples are illustrative; satisfy the complete contract. "
                  "Unchanged or non-improving code earns zero; full reward requires all "
                  "independent hidden cases. This is one final code submission, with no "
                  "interactive test tool or second attempt.")
        return DirectRepairObservation(task_id=task_id, prompt=prompt,
            source=task.initial_source,
            examples=compact_literal([(c.args, c.expected) for c in task.public]),
            reward=0.0, done=False)

    def step(self, action: DirectRepairAction, timeout_s=None, **kwargs):
        if self._task is None:
            raise RuntimeError("reset required")
        if self._terminal is not None:
            return self._terminal.model_copy(deep=True)
        # Delegation preserves byte limits, AST identity, hidden cases, baseline,
        # partial reward and host-code rejection. A rejected oversized write must
        # not accidentally grade some other module as the proposed repair.
        written = self._core.step(RepairAction(op="write", path=SOURCE_PATH,
                                               content=action.content))
        result = self._core.step(RepairAction(op="submit"))
        self._terminal = DirectRepairObservation(task_id=self._task.task_id,
            done=True, reward=0.0 if written.error else result.reward,
            error=written.error or result.error)
        return self._terminal.model_copy(deep=True)

    @property
    def state(self):
        state = self._core.state
        # Two internal calls implement one externally visible action.
        return state.model_copy(update={"step_count": int(self._terminal is not None)})

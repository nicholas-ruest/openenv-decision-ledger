"""One-response native grading adapter. No provider, reservation or submission driver."""
import copy
import json
from pathlib import Path
import sys


class NativeBinding:
    """Lazy imports let offline lifecycle tests run without pretending to run OpenEnv."""
    def __init__(self, job):
        root = Path(__file__).resolve().parents[2]
        sys.path[:0] = [str(root / p) for p in (
            'research/software-function-edit-20261028',
            'research/software-function-block-protocol-20261028',
            'research/software-terminal-audit-20261028',
            'integrations/software-repair')]
        from protocol import capture, schedule
        from function_edit import FunctionEditEnvironment, FunctionEditAction
        from repair_env.direct_environment import DirectRepairEnvironment, DirectRepairAction
        from terminal_audit import classify
        from types import SimpleNamespace
        if job not in schedule('screen', job.get('namespace', '')):
            raise ValueError('exact frozen screen assignment required; no confirmation materialization')
        arm = job['arm']
        if arm not in ('full_module', 'function_block_available'):
            raise ValueError('declared arm required')
        frozen = capture(job['task_id'], job['seed'], arm)
        self.env = DirectRepairEnvironment() if arm == 'full_module' else FunctionEditEnvironment()
        self.action_type = DirectRepairAction if arm == 'full_module' else FunctionEditAction
        reset = self.env.reset(task_id=job['task_id'], seed=job['seed']).model_dump()
        if reset != json.loads(frozen['messages'][1]['content']):
            raise ValueError('fresh native reset differs from frozen capture')
        self.messages = frozen['messages']
        self.prompt_sha256 = frozen['prompt_sha256']
        self.problem_sha256 = frozen['problem_sha256']
        self.audit = lambda native: classify(
            SimpleNamespace(_direct=self.env) if arm == 'full_module' else self.env, native)

    def parse(self, text):
        # Preserve the actual native model's schema/default/extra-field behavior.
        return self.action_type.model_validate_json(text, strict=True)

    def step(self, action):
        return self.env.step(action).model_dump()

    def diagnose(self, native):
        if native['error'].startswith('Invalid function edit;'):
            return dict(category='edit_rejection', native_reward=native['reward'], semantic_reward=None)
        return self.audit(native)


class Trial:
    """Consume exactly one externally obtained assistant response, without retry.

    No paid calls or execution authority. Caller must bind immutable inputs,
    authenticate provider/accounting records, admit the complete phase, reserve
    before each call, enforce actual token/context costs and hard deadlines, and
    store private raw replies durably. This adapter performs none of those.
    """
    def __init__(self, job, expected_prompt_sha256, expected_problem_sha256, *, binding_factory=NativeBinding):
        self.job = copy.deepcopy(job)
        self.binding = binding_factory(self.job)
        if (self.binding.prompt_sha256 != expected_prompt_sha256 or
                self.binding.problem_sha256 != expected_problem_sha256):
            raise ValueError('frozen input binding mismatch')
        self.messages = copy.deepcopy(self.binding.messages)
        self.closed = False
        self.native = None

    def _close(self, category, native_reward=None, semantic_reward=None, **fields):
        return dict(category=category, native_reward=native_reward,
                    semantic_reward=semantic_reward, done=True, **fields)

    def consume(self, reply, *, finish_reason):
        if self.closed:
            raise ValueError('attempt already terminal; no retry/redraw')
        # Close before parsing or stepping: exceptions cannot admit a replacement.
        self.closed = True
        if finish_reason == 'length':
            return self._close('truncation')
        if finish_reason != 'stop':
            return self._close('provider')
        if type(reply) is not str:
            return self._close('format')
        try:
            action = self.binding.parse(reply)
        except (ValueError, TypeError):
            return self._close('format')
        self.messages.append(dict(role='assistant', content=reply))
        try:
            native = self.binding.step(action)
        except Exception:
            return self._close('execution')
        self.native = copy.deepcopy(native)
        if native.get('done') is not True:
            raise ValueError('one-response native terminal contract violated')
        # Terminal native observation only. Hidden diagnostic counts are analysis
        # output and never enter any model-visible transcript or second request.
        self.messages.append(dict(role='user', content=json.dumps(native, sort_keys=True, separators=(',', ':'))))
        result = self.binding.diagnose(native)
        return dict(result, done=True)

    def abort(self, category):
        if self.closed or category not in ('provider', 'budget', 'execution'):
            raise ValueError('open attempt and external failure category required')
        self.closed = True
        return self._close(category)

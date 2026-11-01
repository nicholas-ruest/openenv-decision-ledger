"""Qualification-only Native adapter for the prepared helper-preservation prompt.

No provider, reservation driver, live case generator, or execution authority.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
TASK = 'software_repair-ignore-d3'
# Already materialized by the closed October 29 selfcheck8 screen. Qualification
# must not consume new screen/confirmation inputs or reopen that old study.
QUALIFICATION_SEED = 2560000
ARMS = ('baseline', 'preserve_supplied')
SAMPLING = dict(model='Qwen/Qwen3.8-27B:deepinfra', temperature=0.7,
                response_format={'type': 'json_object'})


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


policy = load('preserve_first_original_policy', 'scripts/software-helper-policy.py')
original = load('preserve_first_original_trial',
                'research/software-function-trial-20261029/trial.py')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def qualification_job(arm):
    if arm not in ARMS:
        raise ValueError('explicit declared arm required')
    return dict(phase='qualification', task_id=TASK, seed=QUALIFICATION_SEED,
                arm=arm, namespace='preserve-first-native-qualification')


class QualificationBinding:
    def __init__(self, job):
        if job != qualification_job(job.get('arm')):
            raise ValueError('only the already-seen qualification input is enabled')
        sys.path[:0] = [str(ROOT / 'integrations/software-repair'),
                       str(ROOT / 'research/software-terminal-audit-20261028')]
        from repair_env.direct_environment import DirectRepairEnvironment, DirectRepairAction
        from terminal_audit import classify
        self.env = DirectRepairEnvironment()
        self.action_type = DirectRepairAction
        reset = self.env.reset(task_id=TASK, seed=QUALIFICATION_SEED)
        raw = reset.model_dump()
        changed = policy.transform(reset, job['arm']).model_dump()
        restored = copy.deepcopy(changed)
        if job['arm'] == 'preserve_supplied':
            suffix = policy.guidance(TASK)
            if not restored['prompt'].endswith(suffix):
                raise ValueError('original guidance missing')
            restored['prompt'] = restored['prompt'][:-len(suffix)]
        if restored != raw or reset.model_dump() != raw:
            raise ValueError('guidance changed Native input beyond prompt suffix')
        self.problem_sha256 = digest(raw)
        self.messages = [dict(role='system', content=
            'Return exactly one JSON action instance matching this schema. '
            'No markdown, diff or tool command. ' + canonical(DirectRepairAction.model_json_schema())),
            dict(role='user', content=canonical(changed))]
        self.prompt_sha256 = digest(self.messages)
        self.audit = lambda native: classify(SimpleNamespace(_direct=self.env), native)

    def parse(self, text):
        return self.action_type.model_validate_json(text, strict=True)

    def step(self, action):
        return self.env.step(action).model_dump()

    def diagnose(self, native):
        return self.audit(native)


class QualificationTrial(original.Trial):
    def __init__(self, job):
        frozen = QualificationBinding(job)
        super().__init__(job, frozen.prompt_sha256, frozen.problem_sha256,
                         binding_factory=QualificationBinding)

    def consume(self, reply, *, finish_reason):
        before = len(self.messages)
        result = super().consume(reply, finish_reason=finish_reason)
        # Report exactly the unchanged terminal Native observation. Analysis-only
        # hidden grading counts from Trial never enter model-visible messages.
        observations = [json.loads(m['content']) for m in self.messages[before:]
                        if m['role'] == 'user']
        return dict(result, new_observations=observations, controller_actions=[],
                    model_responses=1)


def materialize(*args, **kwargs):
    raise ValueError('live screen and confirmation are unsealed; qualification only')


def limits():
    return dict(first_generation_limit=6000, completion_with_all_observations=8192,
                context=24576, final_observation_reserve=96,
                request_wall_seconds=360, attempt_wall_seconds=600,
                whole_phase_wall_seconds=1200, model_calls_per_attempt=1,
                retries=0, live_execution_ready=False, new_model_calls=0)

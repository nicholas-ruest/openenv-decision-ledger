"""Separate final-revision affordance; current frozen studies are unchanged."""
import ast
import hashlib
import json
from pathlib import Path
import sys
from typing import Literal
from pydantic import ConfigDict, Field
from openenv.core.env_server.types import Action

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'research/software-public-runtime-diagnostics-20261030'))
from diagnostic_environment import DiagnosticEnvironment
from mandatory_environment import ProposalAction
from joint_revision_environment import RevisionObservation
from repair_env.tasks import SOURCE_PATH


def source_digest(source):
    return hashlib.sha256(source.encode()).hexdigest()


def replace_blocks(original, replacement, expected_sha256):
    """Replace named top-level functions in the public current module, never execute."""
    if source_digest(original) != expected_sha256:
        raise ValueError('current module hash differs')
    if len(replacement.encode()) > 8192:
        raise ValueError('replacement byte limit')
    before, edits = ast.parse(original), ast.parse(replacement)
    if not edits.body or any(not isinstance(n, ast.FunctionDef) or n.decorator_list
                             for n in edits.body):
        raise ValueError('function definitions only')
    names = [n.name for n in edits.body]
    if len(names) != len(set(names)):
        raise ValueError('duplicate function blocks')
    old = {n.name: n for n in before.body if isinstance(n, ast.FunctionDef)}
    if len(old) != len([n for n in before.body if isinstance(n, ast.FunctionDef)]):
        raise ValueError('ambiguous original function')
    supplied = replacement.splitlines(keepends=True)
    lines = original.splitlines(keepends=True)
    replacements, additions = [], []
    for node in edits.body:
        text = ''.join(supplied[node.lineno-1:node.end_lineno]).rstrip()+'\n'
        if node.name in old:
            original_node = old[node.name]
            replacements.append((original_node.lineno-1, original_node.end_lineno, text))
        else:
            additions.append(text)
    for start, end, text in sorted(replacements, reverse=True):
        lines[start:end] = [text]
    merged = ''.join(lines)
    if additions:
        merged = merged.rstrip()+'\n\n'+'\n'.join(additions)
    if len(merged.encode()) > 8192:
        raise ValueError('complete module byte limit')
    ast.parse(merged)
    return merged


class FunctionRevisionAction(Action):
    model_config = ConfigDict(extra='ignore')
    mode: Literal['module', 'functions'] = 'module'
    content: str = Field(default='', max_length=8192,
                         description='Complete module, or final replacement function definitions. Empty content retains the current module.')
    base_sha256: str = Field(default='', max_length=64,
                            description='For nonempty functions mode, copy revision_base_sha256 from the preceding feedback.')


class FunctionRevisionEnvironment(DiagnosticEnvironment):
    _finish_action = FunctionRevisionAction()

    def __init__(self, *, arm):
        if arm not in ('module_review', 'function_review'):
            raise ValueError('explicit function-revision policy arm required')
        self.function_arm = arm
        super().__init__(arm='diagnostic_review')

    def reset(self, *args, **kwargs):
        self._revision_error = False
        self._applied_function_revision = False
        obs = super().reset(*args, **kwargs)
        guide = (' First propose a complete module using mode="module". For the final response, '
                 'mode="functions" may replace any named top-level functions and add new helpers; '
                 'other current code is retained. Copy revision_base_sha256 from feedback to base_sha256 '
                 'for nonempty functions mode. Mode="module" remains available for a complete replacement. '
                 'Empty content in either mode retains the current module. Native source limits and grading are unchanged.')
        return obs.model_copy(update={'prompt': obs.prompt+guide})

    def step(self, action, timeout_s=None, **kwargs):
        if self._terminal is not None:
            return self._terminal.model_copy(deep=True)
        content = action.content
        if content and action.mode == 'functions':
            try:
                if self._steps != 1:
                    raise ValueError('function blocks require a preceding proposal')
                original = self._direct._core._files[SOURCE_PATH]
                content = replace_blocks(original, content, action.base_sha256)
                self._applied_function_revision = True
            except (ValueError, SyntaxError, RecursionError, UnicodeError):
                self._revision_error = True
                self._steps += 1
                self._terminal = RevisionObservation(task_id=self._direct._core._task.task_id,
                    stage='terminal', remaining_responses=0, done=True, reward=0,
                    error='Invalid function revision or current-module hash.')
                return self._terminal.model_copy(deep=True)
        obs = super().step(ProposalAction(content=content), timeout_s=timeout_s, **kwargs)
        if obs.done:
            return obs
        current = self._direct._core._files[SOURCE_PATH]
        review = json.loads(obs.feedback)
        review['revision_base_sha256'] = source_digest(current)
        review['editable_functions'] = [n.name for n in ast.parse(current).body
                                       if isinstance(n, ast.FunctionDef)]
        if self.function_arm == 'function_review':
            review['review_advice'] = ('Repair the proposed module against the original contract and supplied examples. '
                'For a localized repair, use mode="functions" and return only changed function definitions '
                'plus any necessary new helpers, with base_sha256 copied from revision_base_sha256. '
                'A complete module remains valid in mode="module". No further review follows.')
        return obs.model_copy(update={'feedback': json.dumps(review, sort_keys=True, separators=(',', ':'))})

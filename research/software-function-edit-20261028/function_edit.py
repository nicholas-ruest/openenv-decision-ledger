"""Separate one-response repair affordance: edit one function or submit a full module."""
import ast
from typing import Literal
from pydantic import Field
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import Action,State
from repair_env.direct_environment import DirectRepairEnvironment,DirectRepairAction,DirectRepairObservation

TARGETS={'software_repair-ignore-d3':'classify_ignore','software_repair-ignore-d4':'rule_mode'}

def replace_function(original,replacement,target):
    if len(replacement.encode())>8192:raise ValueError('existing source byte limit')
    tree=ast.parse(replacement);base=ast.parse(original)
    if not tree.body or any(not isinstance(n,ast.FunctionDef) or n.decorator_list for n in tree.body):raise ValueError('function definitions only')
    names=[n.name for n in tree.body]
    if len(names)!=len(set(names)) or names.count(target)!=1:raise ValueError('unique declared target required')
    supplied={n.name for n in base.body if isinstance(n,ast.FunctionDef)}
    if (set(names)-{target}) & supplied:raise ValueError('supplied helper replacement requires module mode')
    new=next(n for n in tree.body if n.name==target)
    extras=[n for n in tree.body if n.name!=target]
    old=[x for x in base.body if isinstance(x,ast.FunctionDef) and x.name==target]
    if len(old)!=1:raise ValueError('unique original target required')
    lines=original.splitlines(keepends=True);node=old[0]
    # Only source bytes belonging to the selected function are replaced.
    # No reference implementation or hidden data is consulted.
    text=''.join(replacement.splitlines(keepends=True)[new.lineno-1:new.end_lineno]).rstrip()+'\n'
    lines[node.lineno-1:node.end_lineno]=[text]
    merged=''.join(lines)
    for extra in extras:
        merged+='\n'+''.join(replacement.splitlines(keepends=True)[extra.lineno-1:extra.end_lineno]).rstrip()+'\n'
    if len(merged.encode())>8192:raise ValueError('existing complete module byte limit')
    return merged

class FunctionEditAction(Action):
    mode:Literal['function','module']='function'
    content:str=Field(default='',max_length=8192,description='A target function and optional new helpers for function mode, or the complete module for module mode.')

class FunctionEditEnvironment(Environment[FunctionEditAction,DirectRepairObservation,State]):
    SUPPORTS_CONCURRENT_SESSIONS=True
    _finish_action=FunctionEditAction(content='')
    def __init__(self):
        super().__init__();self._direct=DirectRepairEnvironment();self._terminal=None;self._reset=None
    def reset(self,seed=None,episode_id=None,**kwargs):
        task=kwargs.get('task_id',next(iter(TARGETS)))
        if task not in TARGETS:raise ValueError('function-edit prerequisite tasks only')
        o=self._direct.reset(seed=seed,episode_id=episode_id,task_id=task);self._terminal=None
        marker='\nRepair the supplied source. Reply once'
        if marker not in o.prompt:raise ValueError('frozen direct instruction contract changed')
        o=o.model_copy(update={'prompt':o.prompt.split(marker)[0]+'\nReply once with a JSON action. In mode="function", content is a replacement function block for '+TARGETS[task]+', optionally with new helper definitions, without markdown. Existing supplied helpers may not be replaced in function mode. The environment replaces only that function and retains all other supplied code. In mode="module", content is a complete repaired module; alternate implementations remain valid. Both modes use the same original full-contract hidden grader. There is no feedback or second attempt.'})
        self._reset=o.model_copy(deep=True);return o
    def step(self,action:FunctionEditAction,timeout_s=None,**kwargs):
        if self._reset is None:raise RuntimeError('reset required')
        if self._terminal is not None:return self._terminal.model_copy(deep=True)
        code=action.content
        if code and action.mode=='function':
            try:code=replace_function(self._reset.source,code,TARGETS[self._reset.task_id])
            except (ValueError,SyntaxError,RecursionError):
                self._terminal=DirectRepairObservation(task_id=self._reset.task_id,done=True,reward=0,error='Invalid function edit; submit the declared target and optional new helper definitions within the original source limits.')
                return self._terminal.model_copy(deep=True)
        self._terminal=self._direct.step(DirectRepairAction(content=code))
        return self._terminal.model_copy(deep=True)
    @property
    def state(self):return self._direct.state.model_copy(update={'step_count':int(self._terminal is not None)})

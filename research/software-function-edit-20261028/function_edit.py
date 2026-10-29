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
    tree=ast.parse(replacement)
    if len(tree.body)!=1 or not isinstance(tree.body[0],ast.FunctionDef):raise ValueError('one function definition required')
    new=tree.body[0]
    if new.name!=target or new.decorator_list:raise ValueError('declared target function required')
    old=[x for x in ast.parse(original).body if isinstance(x,ast.FunctionDef) and x.name==target]
    if len(old)!=1:raise ValueError('unique original target required')
    lines=original.splitlines(keepends=True);node=old[0]
    # Only source bytes belonging to the selected function are replaced.
    # No reference implementation or hidden data is consulted.
    text=''.join(replacement.splitlines(keepends=True)[new.lineno-1:new.end_lineno]).rstrip()+'\n'
    lines[node.lineno-1:node.end_lineno]=[text]
    merged=''.join(lines)
    if len(merged.encode())>8192:raise ValueError('existing complete module byte limit')
    return merged

class FunctionEditAction(Action):
    mode:Literal['function','module']='function'
    content:str=Field(default='',max_length=8192,description='One complete target function for function mode, or the complete module for module mode.')

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
        o=o.model_copy(update={'prompt':o.prompt.split(marker)[0]+'\nReply once with a JSON action. In mode="function", content is one complete replacement definition for '+TARGETS[task]+', without markdown. The environment replaces only that function and retains all other supplied code. In mode="module", content is a complete repaired module; alternate implementations remain valid. Both modes use the same original full-contract hidden grader. There is no feedback or second attempt.'})
        self._reset=o.model_copy(deep=True);return o
    def step(self,action:FunctionEditAction,timeout_s=None,**kwargs):
        if self._reset is None:raise RuntimeError('reset required')
        if self._terminal is not None:return self._terminal.model_copy(deep=True)
        code=action.content
        if code and action.mode=='function':
            try:code=replace_function(self._reset.source,code,TARGETS[self._reset.task_id])
            except (ValueError,SyntaxError,RecursionError):
                self._terminal=DirectRepairObservation(task_id=self._reset.task_id,done=True,reward=0,error='Invalid function edit; submit one definition for the declared target within the original source limits.')
                return self._terminal.model_copy(deep=True)
        self._terminal=self._direct.step(DirectRepairAction(content=code))
        return self._terminal.model_copy(deep=True)
    @property
    def state(self):return self._direct.state.model_copy(update={'step_count':int(self._terminal is not None)})

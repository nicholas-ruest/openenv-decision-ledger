"""Public-failure revision advice only; no action editing or provider API."""
import copy
import json

ARMS=('standard_revision','focused_failure_advice')
NOTE=(
    'Fix the specific contract violation exposed by the public examples; reuse unaffected code. '
    'Prioritize one complete repaired module in a final JSON action; avoid task restatement and alternatives. '
    'Preserve contract requirements beyond these examples.'
)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def failed_public_review(observation):
    """Use only explicit public review fields, never reference or hidden grades."""
    if observation.get('done') is not False or observation.get('stage')!='revision':return False
    raw=observation.get('feedback')
    try:value=json.loads(raw) if isinstance(raw,str) else raw
    except (ValueError,TypeError):return False
    return (isinstance(value,dict) and value.get('kind')=='public_field_check'
        and value.get('public_only') is True and value.get('hidden_access') is False
        and type(value.get('passed')) is int and type(value.get('total')) is int
        and 0<=value['passed']<value['total'])


class FailureAdviceTrial:
    def __init__(self,base,*,arm):
        if arm not in ARMS:raise ValueError('explicit isolated intervention required')
        self.base=base;self.arm=arm;self.calls=0;self.advice=[]
    @property
    def messages(self):return copy.deepcopy(self.base.messages)
    def consume(self,text,*,finish_reason):
        if finish_reason!='stop':raise ValueError('never recover an incomplete response')
        if self.calls>=2:raise ValueError('no retry or third response')
        before=len(self.base.native)
        result=self.base.consume(text);self.calls+=1
        native=copy.deepcopy(self.base.native[before:]);new_advice=[]
        if self.calls==1 and not result['done'] and self.arm==ARMS[1] and native and failed_public_review(native[-1]):
            receipt=dict(kind='public_failure_revision_advice',authored_by='environment',
                changes_candidate=False,hidden_access=False,advice=NOTE)
            self.base.messages.append(dict(role='user',content=canonical(receipt)))
            self.advice.append(receipt);new_advice.append(receipt)
        return dict(result,new_observations=native,advice_observations=new_advice,
            advice_delivered=bool(new_advice),controller_actions=[],model_responses=self.calls)


def observation_tokens(result,count):
    return sum(count(canonical(x)) for x in result['new_observations']+result['advice_observations'])


def materialize(*args,**kwargs):
    raise ValueError('new live protocol, independent case lease and financial admission required')

"""Reference-free relation check using only the originally visible examples.

Candidate code runs solely inside the unchanged bounded Native interpreter.
No task generator, reference implementation, grader, provider or file access.
"""
import ast
import copy
import itertools
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integrations/software-repair'))
from repair_env.runner import Program,Rejected

RELATION='Permuting the entries list must preserve the returned path-to-boolean mapping; entry order is not part of the published contract.'
ARMS=('relation_only','computed_relation')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def visible_inputs(observation):
    if (type(observation) is not dict or observation.get('task_id')!='software_repair-ignore-d3'
        or type(observation.get('examples')) is not str or len(observation['examples'])>16000):
        raise ValueError('original visible joint-task observation required')
    examples=ast.literal_eval(observation['examples'])
    if type(examples) is not list or len(examples)!=6:
        raise ValueError('six originally visible examples required')
    inputs=[]
    for example in examples:
        if type(example) not in (tuple,list) or len(example)!=2:
            raise ValueError('original public example structure required')
        args=example[0] # Deliberately do not use the supplied expected answer.
        if type(args) is not list or len(args)!=2:raise ValueError('original argument pair required')
        rules,entries=args
        if (type(rules) is not list or len(rules)>4 or any(type(x) is not str for x in rules)
            or type(entries) is not list or len(entries)!=4
            or any(type(e) is not dict or set(e)!= {'path','is_dir'} or type(e['path']) is not str or type(e['is_dir']) is not bool for e in entries)
            or len({e['path'] for e in entries})!=4):
            raise ValueError('original public input bounds required')
        inputs.append(copy.deepcopy(args))
    return inputs


def diagnose(observation,code):
    inputs=visible_inputs(observation)
    if type(code) is not str or len(code.encode())>8192:
        return dict(kind='program_unavailable',reason='source_bound',public_only=True)
    try:program=Program(code)
    except (Rejected,RecursionError):
        return dict(kind='program_unavailable',reason='compile_rejected',public_only=True)
    changed=0;evaluations=0;first=None
    try:
        for index,(rules,entries) in enumerate(inputs):
            baseline=program.run('classify_ignore',copy.deepcopy([rules,entries]));evaluations+=1
            sensitive=False
            for permutation in itertools.permutations(range(4)):
                if permutation==(0,1,2,3):continue
                args=[copy.deepcopy(rules),[copy.deepcopy(entries[i]) for i in permutation]]
                actual=program.run('classify_ignore',args);evaluations+=1
                if actual!=baseline:
                    sensitive=True
                    if first is None:first=dict(public_example=index+1,zero_based_entry_order=list(permutation))
            changed+=sensitive
    except (Rejected,ArithmeticError,TypeError,ValueError,KeyError,IndexError,RecursionError,RuntimeError):
        return dict(kind='program_unavailable',reason='runtime_rejected',public_only=True)
    return dict(kind='public_entry_order_relation',public_only=True,reference_answers_used=False,
        examples_checked=6,program_evaluations=evaluations,order_sensitive_examples=changed,
        first_counterexample=first,semantic_correctness_established=False)


def review(observation,code,arm):
    if arm not in ARMS:raise ValueError('explicit original feedback arm required')
    # Both arms perform identical bounded local work. Only exposure differs.
    diagnostic=diagnose(observation,code)
    visible=diagnostic if arm=='computed_relation' else dict(kind='computed_result_withheld',public_only=True)
    return dict(relation=RELATION,diagnostic=visible,
        instruction='Review the previous module against the original contract. Return the final complete module; a consistent result can still be semantically wrong.')

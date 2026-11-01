"""Public output-domain contract check; no expected answers, hidden data or provider."""
import copy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/software-entry-order-review-20261101'))
from order_diagnostic import visible_inputs,canonical
from repair_env.runner import Program,Rejected
RELATION='Return exactly the paths explicitly listed in entries, each mapped to a boolean. Implicit parent directories may affect decisions but are not additional output entries.'
ARMS=('domain_reminder','computed_domain')


def probes(observation):
    """Retain four valid entries; move one into a fresh, implicit parent."""
    for example,args in enumerate(visible_inputs(observation),1):
        yield example,None,copy.deepcopy(args)
        rules,entries=args
        roots={e['path'].split('/')[0] for e in entries}
        n=0
        while 'domain_probe_'+str(n) in roots:n+=1
        root='domain_probe_'+str(n)
        for index in range(4):
            variant=copy.deepcopy(entries)
            variant[index]['path']=root+'/leaf'
            yield example,index,[copy.deepcopy(rules),variant]


def diagnose(observation,code):
    # Validate the original visible observation even when the module is rejected.
    inputs=list(probes(observation))
    if type(code) is not str or len(code.encode())>8192:
        return dict(kind='program_unavailable',reason='source_bound',public_only=True)
    try:program=Program(code)
    except (Rejected,RecursionError):
        return dict(kind='program_unavailable',reason='compile_rejected',public_only=True)
    failures=0;first=None;evaluations=0
    try:
        for example,moved,args in inputs:
            result=program.run('classify_ignore',copy.deepcopy(args));evaluations+=1
            expected_keys={e['path'] for e in args[1]}
            valid=type(result) is dict and set(result)==expected_keys and all(type(v) is bool for v in result.values())
            if not valid:
                failures+=1
                if first is None:
                    first=dict(public_example=example,moved_entry_index=moved,input=copy.deepcopy(args),
                        requirement='Exactly the four explicitly supplied paths, each mapped to a boolean; no inferred parent keys.',
                        result_type=type(result).__name__,returned_key_count=len(result) if type(result) is dict else None)
    except (Rejected,ArithmeticError,TypeError,ValueError,KeyError,IndexError,RecursionError,RuntimeError):
        return dict(kind='program_unavailable',reason='runtime_rejected',public_only=True)
    return dict(kind='public_output_domain_contract',public_only=True,reference_answers_used=False,
        program_evaluations=evaluations,violations=failures,first_counterexample=first,semantic_correctness_established=False)


def review(observation,code,arm):
    if arm not in ARMS:raise ValueError('explicit original feedback arm required')
    value=diagnose(observation,code)
    visible=value if arm=='computed_domain' or value['kind']=='program_unavailable' else dict(kind='computed_result_withheld',public_only=True)
    return dict(relation=RELATION,diagnostic=visible,instruction='Review the complete module against the original contract. A valid output shape can still contain wrong decisions.')

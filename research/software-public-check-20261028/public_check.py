"""Public-example-only feedback for a separately controlled revision experiment."""
import ast
import copy
import json


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


def exact(a,b):
    if type(a) is not type(b):return False
    if type(b) in (list,tuple):return len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
    if type(b) is dict:return a.keys()==b.keys() and all(exact(a[k],v) for k,v in b.items())
    return a==b


def examples_from_reset(reset):
    """No runtime task/hidden case object is accepted by this API."""
    if type(reset) is not dict or type(reset.get('examples')) is not str:raise ValueError('visible reset examples required')
    text=reset['examples']
    if len(text.encode())>32768:raise ValueError('public examples byte limit')
    tree=ast.parse(text,mode='eval')
    if sum(1 for _ in ast.walk(tree))>4096:raise ValueError('public examples AST limit')
    rows=ast.literal_eval(tree)
    if type(rows) not in (list,tuple) or len(rows)!=6:raise ValueError('six visible examples required')
    for row in rows:
        if type(row) not in (list,tuple) or len(row)!=2 or type(row[0]) not in (list,tuple):raise ValueError('public example shape')
    canonical(rows)
    return rows


def feedback(reset,source,program_factory):
    """program_factory must be the frozen bounded interpreter, never host exec.

    Code is neither repaired nor silently substituted. Format/execution errors
    remain distinct from valid public mismatches. This never scores hidden cases.
    """
    if type(source) is not str or len(source.encode())>8192:raise ValueError('candidate source byte limit')
    rows=examples_from_reset(reset);results=[];failures=[]
    try:program=program_factory(source)
    except Exception as exc:
        return {'kind':'candidate_rejected','exception_type':type(exc).__name__,'public_only':True,'hidden_access':False}
    passed=0;execution_errors=0
    for index,(args,expected) in enumerate(rows):
        try:actual=program.run('classify_ignore',copy.deepcopy(args));good=exact(actual,expected);error=None
        except Exception as exc:actual=None;good=False;error=type(exc).__name__;execution_errors+=1
        passed+=good;results.append({'test':index+1,'passed':good,'error_type':error})
        if not good and len(failures)<2:failures.append({'test':index+1,'args':args,'expected':expected,'actual':actual,'error_type':error})
    out={'kind':'public_example_check','public_only':True,'hidden_access':False,'passed':passed,'total':6,
         'execution_errors':execution_errors,'tests':results,'first_failures':failures}
    if len(canonical(out).encode())>4096:
        # Preserve test flags and classification; omit verbose values explicitly.
        out['first_failures']=[];out['failure_values_omitted']=True
    return out


def revision_message(arm,public_feedback):
    if arm=='review_control':
        return 'Review your previous module against the original contract and supplied examples. Return one JSON action with the complete final module. You have one revision; no more feedback follows.'
    if arm!='public_check':raise ValueError('explicit separate revision arm required')
    if public_feedback.get('public_only') is not True or public_feedback.get('hidden_access') is not False:raise ValueError('public-only feedback required')
    return 'Check of your previous module against the examples already in the original prompt: '+canonical(public_feedback)+'\nReturn one JSON action with your complete final module. You have one revision; no more feedback follows.'

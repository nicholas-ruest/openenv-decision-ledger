"""Compact field-level feedback from the SAME six supplied examples only."""
import json
from public_check import canonical,exact

def mismatches(actual,expected,path=(),limit=4):
    out=[]
    def add(kind,a,b,p):
        if len(out)<limit:
            out.append(dict(path=list(p),kind=kind,actual=canonical(a)[:48],expected=canonical(b)[:48]))
    def walk(a,b,p):
        if len(out)>=limit:return
        if type(a) is not type(b):add('type',a,b,p);return
        if isinstance(b,dict):
            for key in sorted(set(a)|set(b),key=str):
                if key not in a:add('missing',None,b[key],p+(key,))
                elif key not in b:add('unexpected',a[key],None,p+(key,))
                else:walk(a[key],b[key],p+(key,))
                if len(out)>=limit:return
        elif isinstance(b,(list,tuple)):
            if len(a)!=len(b):add('length',len(a),len(b),p)
            for index,(x,y) in enumerate(zip(a,b)):
                walk(x,y,p+(index,))
                if len(out)>=limit:return
        elif not exact(a,b):add('value',a,b,p)
    walk(actual,expected,path)
    return out

def compact(value):
    if value.get('public_only') is not True or value.get('hidden_access') is not False:
        raise ValueError('only already-computed visible feedback accepted')
    if value.get('kind')!='public_example_check':return dict(value)
    out={k:value[k] for k in ('public_only','hidden_access','passed','total','execution_errors')}
    out['kind']='public_field_check'
    out['tests']=[[r['test'],r['passed'],r['error_type']] for r in value['tests']]
    items=[]
    for failure in value.get('first_failures',[]):
        if failure['error_type'] is not None:continue
        for diff in mismatches(failure['actual'],failure['expected'],limit=2):
            items.append(dict(test=failure['test'],**diff))
    out['field_mismatches']=items[:4]
    if len(canonical(out).encode())>768:
        out['field_mismatches']=[{k:v for k,v in x.items() if k not in ('actual','expected')} for x in items[:4]]
    if len(canonical(out).encode())>768:out['field_mismatches']=out['field_mismatches'][:2]
    if len(canonical(out).encode())>768:raise ValueError('visible field feedback byte limit')
    return out

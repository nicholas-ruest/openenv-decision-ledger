"""Public submitted-source diagnostics; no task, hidden data or model access."""
import ast
from repair_env.runner import Program,Rejected,MAX_SOURCE

def diagnose(source):
    if type(source) is not str or len(source.encode())>MAX_SOURCE:
        return None
    try:
        Program(source)
    except Rejected as error:
        reason=str(error)
    else:
        return None
    if reason not in ('unsupported Python syntax','invalid Python syntax'):
        return None
    scope=dict(public_submitted_source_only=True,hidden_access=False)
    try:
        tree=ast.parse(source)
    except SyntaxError as error:
        return dict(scope,kind='syntax_error',line=error.lineno,column=error.offset)
    nodes=[dict(node=type(n).__name__,line=getattr(n,'lineno',None),
                byte_column=getattr(n,'col_offset',-1)+1)
           for n in ast.walk(tree) if not isinstance(n,Program._syntax)]
    if not nodes:
        return None
    nodes.sort(key=lambda x:(x['line'] or 0,x['byte_column'],x['node']))
    return dict(scope,kind='unsupported_syntax',nodes=nodes[:8],total_nodes=len(nodes))

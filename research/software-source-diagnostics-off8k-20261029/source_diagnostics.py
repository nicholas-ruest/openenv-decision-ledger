"""Bounded compiler diagnostics from submitted source only, never hidden cases."""
import ast
import copy
from public_check import canonical
from repair_env.runner import MAX_SOURCE,MAX_AST_NODES

HINTS={
    'keyword':'Keyword arguments are outside the declared subset. Use the supported positional call signatures or supported list methods.',
    'Lambda':'Lambdas are outside the declared subset. Use a named top-level helper or supported loops.',
    'Try':'Exceptions are outside the declared subset. Use explicit conditional checks.',
    'ExceptHandler':'Exceptions are outside the declared subset. Use explicit conditional checks.',
    'AnnAssign':'Annotated assignments are outside the declared subset. Use ordinary assignments.',
    'JoinedStr':'Formatted string literals are outside the declared subset. Use supported string operations.',
    'FormattedValue':'Formatted string literals are outside the declared subset. Use supported string operations.',
}

def augment(public_feedback,source,program_factory):
    """Augment only a public compiler rejection; no execution or repair occurs.

    The syntax tuple is the actual pinned bounded compiler's manifest. We do not
    change its accepted language, limits, code or grading. No task object, case
    input, reference source, expected answer, filesystem or credential is read.
    """
    if public_feedback.get('public_only') is not True or public_feedback.get('hidden_access') is not False:
        raise ValueError('public-only feedback required')
    if public_feedback.get('kind')!='candidate_rejected':return copy.deepcopy(public_feedback)
    if type(source) is not str or len(source.encode())>MAX_SOURCE:raise ValueError('existing source byte limit')
    syntax=getattr(program_factory,'_syntax',None)
    if not isinstance(syntax,tuple) or not syntax or not all(isinstance(t,type) and issubclass(t,ast.AST) for t in syntax):
        return copy.deepcopy(public_feedback)
    try:tree=ast.parse(source)
    except (SyntaxError,RecursionError,ValueError):return copy.deepcopy(public_feedback)
    nodes=list(ast.walk(tree))
    if len(nodes)>MAX_AST_NODES:return copy.deepcopy(public_feedback)
    diagnostics=[];seen=set()
    for node in nodes:
        if isinstance(node,syntax):continue
        kind=type(node).__name__;line=getattr(node,'lineno',None)
        identity=(kind,line)
        if identity in seen:continue
        seen.add(identity)
        row=dict(syntax_kind=kind,line=line)
        if kind in HINTS:row['hint']=HINTS[kind]
        diagnostics.append(row)
        if len(diagnostics)==8:break
    if not diagnostics:return copy.deepcopy(public_feedback)
    result=copy.deepcopy(public_feedback)
    result.update(source_diagnostics=diagnostics,diagnostic_scope='submitted_source_only')
    if len(canonical(result).encode())>4096:return copy.deepcopy(public_feedback)
    return result

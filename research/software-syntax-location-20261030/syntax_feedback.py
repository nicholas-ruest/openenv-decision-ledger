"""Python syntax-error location from the proposed module only."""
import ast
import copy

def augment(review,source):
    if review.get('public_only') is not True or review.get('hidden_access') is not False:
        raise ValueError('public-only review required')
    if review.get('kind')!='candidate_rejected':
        return copy.deepcopy(review)
    if type(source) is not str or len(source.encode())>8192:
        raise ValueError('existing source byte limit')
    result=copy.deepcopy(review)
    try:
        ast.parse(source)
    except SyntaxError as error:
        result['syntax_error']=dict(message=error.msg[:120],
            line=error.lineno,offset=error.offset)
        result['diagnostic_scope']='submitted_source_only'
    except (RecursionError,ValueError):
        pass
    return result

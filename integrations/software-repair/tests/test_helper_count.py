import pytest
from repair_env.runner import Program,Rejected,MAX_SOURCE,MAX_AST_NODES,MAX_ITEMS,MAX_STRING,MAX_STEPS


@pytest.mark.parametrize('count',[1,4,5,7,16])
def test_normal_modular_code_uses_same_interpreter_and_aggregate_limits(count):
    code='\n'.join('def f'+str(i)+'(x):\n    return x+1\n' for i in range(count))
    p=Program(code)
    assert p.run('f'+str(count-1),[5])==6
    assert (MAX_SOURCE,MAX_AST_NODES,MAX_ITEMS,MAX_STRING,MAX_STEPS)==(8192,2048,128,2048,80000)


def test_count_remains_finite_and_recursive_depth_and_source_guards_remain_closed():
    code='\n'.join('def f'+str(i)+'(x):\n    return x\n' for i in range(17))
    with pytest.raises(Rejected,match='sixteen'):Program(code)
    with pytest.raises(Rejected):Program('def f(x):\n    return f(x)').run('f',[1])
    with pytest.raises(Rejected):Program('def f(x):\n    return '+repr('x'*8192))

import pytest
from repair_env.runner import Program, Rejected


@pytest.mark.parametrize('expression,args,expected',[
    ("x.split('/')",['a/b/c'],['a','b','c']),
    ("x.rsplit('/',1)",['a/b/c'],['a/b','c']),
    ("x.startswith('ab')",['abc'],True),
    ("x.endswith('bc')",['abc'],True),
    ("x.replace('a','z',1)",['aaba'],'zaba'),
    ("x.strip()",[' a '],'a'),
    ("x.lstrip(' ')",[' a '],'a '),
    ("x.rstrip(' ')",[' a '],' a'),
    ("x.find('bc')",['abc'],1),
    ("x.count('a')",['aba'],2),
    ("x.join(['a','b'])",['/'],'a/b'),
    ("x.lower()",['AbC'],'abc'),
    ("x.upper()",['aBc'],'ABC'),
])
def test_only_bounded_pure_string_methods_are_supported(expression,args,expected):
    p=Program('def f(x):\n    return '+expression+'\n')
    assert p.run('f',args)==expected


@pytest.mark.parametrize('code,args',[
    ("def f(x):\n    return x.replace('a','b'*2048)",['a'*2048]),
    ("def f(x):\n    return x.split(',')",['a,'*128]),
    ("def f(x):\n    return x.format()",['{0.__class__}']),
    ("def f(x):\n    return x.__class__",['a']),
])
def test_expansion_collection_and_attribute_guards_remain_closed(code,args):
    with pytest.raises(Rejected):Program(code).run('f',args)

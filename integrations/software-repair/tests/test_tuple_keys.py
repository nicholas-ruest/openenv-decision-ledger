import pytest

from repair_env.runner import Program, Rejected


def test_dictionary_literal_comprehension_and_assignment_have_same_tuple_key_semantics():
    sources = [
        'def f(a,b):\n    d={(a,b):3}\n    return d[(a,b)]\n',
        'def f(a,b):\n    d={(a,b):v for v in [3]}\n    return d[(a,b)]\n',
        'def f(a,b):\n    d={}\n    d[(a,b)]=3\n    return d[(a,b)]\n',
    ]
    for a, b in [('a','b'), (1,2), (('a',1),('b',2))]:
        assert [Program(s).run('f',[a,b]) for s in sources] == [3,3,3]


def test_tuple_key_updates_get_and_pop_support_graph_dynamic_programming():
    code = '''def closure(nodes,edges):
    reach={}
    for a in nodes:
        for b in nodes:
            reach[(a,b)]=a==b
    for edge in edges:
        reach[(edge[0],edge[1])]=True
    for k in nodes:
        for a in nodes:
            for b in nodes:
                reach[(a,b)]=reach[(a,b)] or (reach[(a,k)] and reach[(k,b)])
    return [[reach.get((a,b),False) for b in nodes] for a in nodes]
'''
    assert Program(code).run('closure', [['a','b','c'],[['a','b'],['b','c']]]) == [
        [True,True,True], [False,True,True], [False,False,True]]
    pop = 'def f(a,b):\n    d={}\n    d[(a,b)]=1\n    d[(a,b)]+=2\n    return d.pop((a,b))\n'
    assert Program(pop).run('f',['a','b']) == 3


def test_tuple_keys_do_not_allow_tuple_list_indices_unhashable_keys_or_non_json_results():
    with pytest.raises(Rejected):
        Program('def f():\n    a=[0]\n    a[(0,1)]=2\n    return a\n').run('f', [])
    with pytest.raises((Rejected,TypeError)):
        Program('def f():\n    a={}\n    a[([1],2)]=3\n    return 1\n').run('f', [])
    with pytest.raises(Rejected,match='JSON'):
        Program('def f():\n    a={}\n    a[(1,2)]=3\n    return a\n').run('f', [])

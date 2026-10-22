import copy
import random
import pytest
from repair_env import linear_repair as linear
from repair_env.runner import Program
from repair_env.tasks import make_task, SOURCE_PATH, TRAINING_TASK_IDS
from repair_env.environment import check, exact
from repair_env.direct_environment import DirectRepairEnvironment, DirectRepairAction, LINEAR_TASK_IDS


def evaluate(task,code):
    e=DirectRepairEnvironment();e.reset(task_id=task.task_id,seed=task.seed)
    return e.step(DirectRepairAction(content=code)).reward


def test_independent_permutation_oracle_and_bounded_recursive_reference_agree():
    p=Program(linear.REFERENCE)
    for seed in (1240000,1240100,1240200):
        for args in linear.inputs(random.Random(seed),30):
            before=copy.deepcopy(args)
            assert exact(p.run('check_history',args),linear.reference(args))
            assert args==before


@pytest.mark.parametrize('index',range(len(linear.MUTATIONS)))
def test_each_semantic_mutation_is_executable_and_has_visible_witness(index):
    p=Program(linear.mutate([index]))
    cases=linear.witnesses(random.Random(1240300))
    outcomes=[exact(p.run('check_history',a),linear.reference(a)) for a in cases]
    assert not all(outcomes),linear.MUTATIONS[index][2]


@pytest.mark.parametrize('task_id',LINEAR_TASK_IDS)
@pytest.mark.parametrize('seed',[1240400,1240500])
def test_generated_history_repair_has_full_partial_and_no_change_controls(task_id,seed):
    t=make_task(task_id,seed)
    b,rows=check(Program(t.initial_source),t,t.hidden,details=True)
    assert b<30 and not any(r['error'] for r in rows)
    assert evaluate(t,t.reference_source)==1
    assert evaluate(t,t.initial_source)==evaluate(t,'# comment\n'+t.initial_source)==0
    partial=[]
    for index in range(len(linear.MUTATIONS)):
        source=linear.mutate([index]);_,after=check(Program(source),t,t.hidden,details=True)
        assert not any(r['error'] for r in after)
        baseline=sum(sum(k in r['actual'] and exact(r['actual'][k],v) for k,v in r['expected'].items()) for r in rows)
        repaired=sum(sum(k in r['actual'] and exact(r['actual'][k],v) for k,v in r['expected'].items()) for r in after)
        expected=1 if all(r['passed'] for r in after) else max(0,min(.95,(repaired-baseline)/(120-baseline)))
        observed=evaluate(t,source);assert observed==expected
        if 0<observed<1:partial.append(observed)
    assert partial


def test_pending_only_empty_and_search_state_pressure_remain_semantic_not_resource_failures():
    p=Program(linear.REFERENCE)
    cases=[[2,[]],[2,[linear._op('a','write',0,None,value=1)]]]
    # Five overlapping writes cannot justify a final completed read of a value
    # never written. This explores many failed prefixes without larger limits.
    ops=[linear._op(chr(97+i),'write',i,11-i,value=i%3) for i in range(5)]
    ops.append(linear._op('z','read',12,13,result=3));cases.append([0,ops])
    for a in cases:assert exact(p.run('check_history',a),linear.reference(a))


def test_levels_share_case_stream_and_do_not_modify_default_training_mix():
    a=make_task(LINEAR_TASK_IDS[0],1240600);b=make_task(LINEAR_TASK_IDS[1],1240600)
    assert a.public==b.public and a.hidden==b.hidden and a.initial_source!=b.initial_source
    assert len(TRAINING_TASK_IDS)==8 and not set(LINEAR_TASK_IDS)&set(TRAINING_TASK_IDS)

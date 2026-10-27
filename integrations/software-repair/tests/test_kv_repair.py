import copy
import random

import pytest

from repair_env import kv_repair
from repair_env.environment import RepairEnvironment, RepairAction, check, exact
from repair_env.direct_environment import DirectRepairEnvironment, DirectRepairAction, KV_TASK_IDS
from repair_env.runner import Program
from repair_env.tasks import make_task, SOURCE_PATH, TRAINING_TASK_IDS


def reward(task, code, direct=True):
    env = DirectRepairEnvironment() if direct else RepairEnvironment()
    env.reset(task_id=task.task_id, seed=task.seed)
    if direct:
        return env.step(DirectRepairAction(content=code)).reward
    env.step(RepairAction(op="write",path=SOURCE_PATH,content=code))
    return env.step(RepairAction(op="submit")).reward


def test_owned_reference_matches_independent_oracle_without_execution_errors_or_input_mutation():
    program = Program(kv_repair.REFERENCE)
    for seed in (1190000,1190100,1190200):
        for args in kv_repair.inputs(random.Random(seed),18):
            original=copy.deepcopy(args)
            assert exact(program.run('replay_store',args),kv_repair.reference(args))
            assert args==original


@pytest.mark.parametrize('index',range(len(kv_repair.MUTATIONS)))
def test_each_seeded_defect_has_a_visible_semantic_witness_not_a_crash(index):
    broken=Program(kv_repair.mutate([index]))
    outcomes=[]
    for args in kv_repair.inputs(random.Random(1190300),6):
        outcomes.append(exact(broken.run('replay_store',args),kv_repair.reference(args)))
    assert not all(outcomes),kv_repair.MUTATIONS[index][2]


@pytest.mark.parametrize('task_id',KV_TASK_IDS)
@pytest.mark.parametrize('seed',[1190400,1190500])
def test_full_partial_unchanged_and_case_component_semantics(task_id,seed):
    task=make_task(task_id,seed)
    before,rows=check(Program(task.initial_source),task,task.hidden,details=True)
    assert before<30 and all(r['error'] is None for r in rows)
    assert reward(task,task.reference_source)==reward(task,task.reference_source,False)==1
    for code in (task.initial_source,'# cosmetic\n'+task.initial_source,''):
        assert reward(task,code)==0
    partials=[]
    for index in range(len(kv_repair.MUTATIONS)):
        code=kv_repair.mutate([index])
        _,outcomes=check(Program(code),task,task.hidden,details=True)
        assert all(x['error'] is None for x in outcomes)
        # Independent root-field equality for these trusted typed fixtures.
        baseline=sum(sum(k in r['actual'] and exact(r['actual'][k],v) for k,v in r['expected'].items()) for r in rows)
        repaired=sum(sum(k in r['actual'] and exact(r['actual'][k],v) for k,v in r['expected'].items()) for r in outcomes)
        expected=1 if all(r['passed'] for r in outcomes) else max(0,min(.95,(repaired-baseline)/(180-baseline)))
        observed=reward(task,code)
        assert observed==expected
        if 0<observed<1:partials.append(observed)
    assert partials,'task must admit genuine executable partial progress'


def test_cases_shared_across_difficulty_and_primary_eight_task_export_unchanged():
    a=make_task(KV_TASK_IDS[0],1190600);b=make_task(KV_TASK_IDS[1],1190600)
    assert a.public==b.public and a.hidden==b.hidden
    assert a.reference_source==b.reference_source
    assert a.initial_source!=b.initial_source
    assert len(TRAINING_TASK_IDS)==8 and not set(KV_TASK_IDS)&set(TRAINING_TASK_IDS)

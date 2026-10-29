import copy
import pathlib
import random
import shutil
import subprocess
import tempfile
import pytest
from repair_env import ignore_repair as ignore
from repair_env.runner import Program
from repair_env.tasks import make_task,TRAINING_TASK_IDS
from repair_env.environment import check,exact
from repair_env.direct_environment import DirectRepairEnvironment,DirectRepairAction,IGNORE_TASK_IDS


def grade(task,code):
    e=DirectRepairEnvironment();e.reset(task_id=task.task_id,seed=task.seed)
    return e.step(DirectRepairAction(content=code)).reward


def git_oracle(args):
    with tempfile.TemporaryDirectory() as directory:
        root=pathlib.Path(directory)
        subprocess.run(['git','init','-q'],cwd=root,check=True,capture_output=True,timeout=5)
        (root/'.gitignore').write_text('\n'.join(args[0])+'\n')
        for entry in args[1]:
            path=root/entry['path'];path.parent.mkdir(parents=True,exist_ok=True)
            if entry['is_dir']:path.mkdir(exist_ok=True)
            else:path.write_text('')
        result=subprocess.run(['git','-c','core.excludesfile=/dev/null','-c','core.ignorecase=false',
                               'check-ignore','--no-index','-z','--stdin'],cwd=root,
                              input=b'\0'.join(e['path'].encode() for e in args[1])+b'\0',capture_output=True,timeout=5)
        assert result.returncode in (0,1),result.stderr
        ignored={x.decode() for x in result.stdout.split(b'\0') if x}
        return {e['path']:e['path'] in ignored for e in args[1]}


@pytest.mark.skipif(shutil.which('git') is None,reason='real Git is a CPU validation oracle, not a runtime dependency')
def test_independent_regex_and_bounded_dp_agree_with_actual_git():
    p=Program(ignore.REFERENCE)
    for seed in (1290000,1290100):
        for args in ignore.inputs(random.Random(seed),32):
            original=copy.deepcopy(args);expected=git_oracle(args)
            assert exact(ignore.reference(args),expected)
            assert exact(p.run('classify_ignore',args),expected)
            assert args==original and sum(expected.values())==2


@pytest.mark.parametrize('task_id',IGNORE_TASK_IDS)
@pytest.mark.parametrize('seed',[1290200,1290300])
def test_semantic_decision_reward_without_constant_or_resource_shortcuts(task_id,seed):
    t=make_task(task_id,seed)
    b,before=check(Program(t.initial_source),t,t.hidden,details=True)
    assert b<30 and not any(x['error'] for x in before)
    assert grade(t,t.reference_source)==1 and grade(t,t.initial_source)==0
    assert grade(t,'# cosmetic\n'+t.initial_source)==0
    for value in ('True','False','0'):
        code='def classify_ignore(ignore_lines,entries):\n    return {e["path"]: '+value+' for e in entries}\n'
        assert grade(t,code)==0
    variants=[
        ignore.REFERENCE.replace('negative = line[0] == "!"','negative = False'),
        ignore.REFERENCE.replace('anchored = anchored or "/" in line','anchored = False'),
        ignore.REFERENCE.replace('def rule_mode(line, path, is_dir):','def rule_mode(line, path, is_dir):\n    line = line.strip()'),
        ignore.initial(seed,1),
    ]
    partial=[]
    for code in variants:
        _,after=check(Program(code),t,t.hidden,details=True)
        assert not any(x['error'] for x in after)
        baseline=sum(sum(k in r['actual'] and exact(r['actual'][k],v) for k,v in r['expected'].items()) for r in before)
        repaired=sum(sum(k in r['actual'] and exact(r['actual'][k],v) for k,v in r['expected'].items()) for r in after)
        total=sum(len(r['expected']) for r in before)
        expected=1 if all(r['passed'] for r in after) else max(0,min(.95,(repaired-baseline)/(total-baseline)))
        observed=grade(t,code);assert observed==expected
        if 0<observed<1:partial.append(observed)
    assert partial


def test_primary_and_control_share_semantics_and_cases_default_mix_unchanged():
    a=make_task(IGNORE_TASK_IDS[0],1290400);b=make_task(IGNORE_TASK_IDS[1],1290400)
    assert a.public==b.public and a.hidden==b.hidden and a.instructions==b.instructions
    assert a.reference_source==b.reference_source and a.initial_source!=b.initial_source
    assert len(TRAINING_TASK_IDS)==8 and not set(IGNORE_TASK_IDS)&set(TRAINING_TASK_IDS)

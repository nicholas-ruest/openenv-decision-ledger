import importlib.util
from pathlib import Path
import pytest
import json
from argparse import Namespace

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("fresh_screen", ROOT / "scripts/repair-fresh-group-screen.py")
fresh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fresh)


def row(seed, reward, failure=None):
    return {"seed":seed,"reward":reward,"failure":failure,"prompt_sha256":str(seed),
            "calls":[{"client_call_label":"call"+str(seed),"provider_response_id_sha256":"response"+str(seed)}]}


def test_declared_fresh_seeds_are_unique_and_disjoint_from_splits_and_previous_probes():
    screen = fresh.plan('screen'); confirm = fresh.plan('confirm')
    a = {s for g in screen['groups'] for s in g}; b = {s for g in confirm['groups'] for s in g}
    assert len(a)==len(b)==10 and not a&b
    assert not (a|b)&{1150000,1150100,1151000,1151100}
    assert max(a|b)<1160000 and screen['max_calls']==10 and screen['no_retry']


def test_linear_curriculum_has_disjoint_frozen_fresh_groups_and_same_capacity():
    a=fresh.plan('screen','linear');b=fresh.plan('confirm','linear')
    seeds=lambda p:{s for g in p['groups'] for s in g}
    assert a['task_id']=='software_repair-linear-d2'
    assert len(seeds(a))==len(seeds(b))==10 and not seeds(a)&seeds(b)
    assert not (seeds(a)|seeds(b))&seeds(fresh.plan('screen'))
    assert max(seeds(a)|seeds(b))<1210000
    assert a['max_calls']==10 and a['selection']==fresh.plan('screen')['selection']


def test_synthesis_control_uses_same_new_cases_but_not_primary_or_confirmed_cases():
    a=fresh.plan('screen','linear_synthesis');b=fresh.plan('screen','linear_control')
    c=fresh.plan('confirm','linear_synthesis');d=fresh.plan('screen','linear')
    seeds=lambda p:{s for g in p['groups'] for s in g}
    assert a['groups']==b['groups'] and a['task_id']!=b['task_id']
    assert not seeds(a)&(seeds(c)|seeds(d))
    assert max(seeds(a)|seeds(c))<1210000


def test_first_four_valid_selection_is_completion_order_not_best_reward():
    seeds=list(range(5)); rows=[row(2,0,'completion_truncated'),row(4,.25),row(1,1),row(3,1),row(0,1)]
    x=fresh.assess(rows,seeds)
    assert x['selected_seeds']==[4,1,3,0] and x['productive']
    assert x['excluded']==[{'seed':2,'failure':'completion_truncated'}]
    allvalid=[row(i,1 if i<4 else .25) for i in seeds]
    assert fresh.assess(allvalid,seeds)['productive'] is False


def test_failures_are_not_wrong_answers_and_missing_fourth_valid_does_not_pass():
    rows=[row(0,1),row(1,.5),row(2,1),row(3,0,'invalid_candidate_code'),row(4,0,'provider_failure')]
    assert fresh.assess(rows,list(range(5)))['productive'] is False


@pytest.mark.parametrize('change',['seed','prompt','call'])
def test_duplicate_instance_prompt_or_provider_identity_fails_closed(change):
    rows=[row(i,1) for i in range(5)]
    if change=='seed': rows[-1]['seed']=0
    elif change=='prompt': rows[-1]['prompt_sha256']='0'
    else: rows[-1]['calls']=rows[0]['calls']
    with pytest.raises(ValueError):fresh.assess(rows,list(range(5)))


def test_preview_never_executes_or_requires_credentials(monkeypatch,capsys):
    monkeypatch.delenv('HF_TOKEN',raising=False)
    assert fresh.main([])==0
    assert '"max_calls": 10' in capsys.readouterr().out


def test_sampling_provenance_is_checked_across_group_boundaries():
    rows=[row(i,1) for i in range(10)]
    assert fresh.independent(rows)
    rows[-1]['calls']=rows[0]['calls']
    assert not fresh.independent(rows)


def test_bounded_executor_launches_exactly_ten_fresh_instances_and_preserves_every_record(monkeypatch,tmp_path):
    seen=[]
    monkeypatch.setenv('HF_TOKEN','fixture-not-a-credential')
    monkeypatch.setattr(fresh.base,'DollarReservations',lambda path:object())
    monkeypatch.setattr(fresh.base.helper,'load_counter',lambda args:object())
    monkeypatch.setattr(fresh.base,'quote',lambda *args:{'fixture':True})
    def episode(task,seed,sample,*args):
        seen.append(seed)
        return row(seed,1 if seed%2 else .5)
    monkeypatch.setattr(fresh.base,'episode',episode)
    args=Namespace(stage='screen',output=tmp_path/'fresh',budget_receipt=tmp_path/'fixture',tokenizer=tmp_path/'tokenizer')
    fresh.execute(fresh.base._now()+30,args)
    records=[json.loads(x) for x in (args.output/'episodes.jsonl').read_text().splitlines()]
    summary=json.loads((args.output/'complete.json').read_text())
    protocol=json.loads((args.output/'protocol.json').read_text())
    assert len(seen)==len(set(seen))==len(records)==10
    assert summary['signal_gate'] and all(g['observed']==5 for g in summary['groups'])
    assert protocol['max_calls']==10 and protocol['source_files_sha256']
    with pytest.raises(FileExistsError):fresh.execute(fresh.base._now()+30,args)
    fresh.verify_screen(args.output,'kv')
    confirm=Namespace(stage='confirm',screen=args.output,output=tmp_path/'confirm',
                      budget_receipt=args.budget_receipt,tokenizer=args.tokenizer)
    fresh.execute(fresh.base._now()+30,confirm)
    verified=json.loads((confirm.output/'complete.json').read_text())
    assert verified['signal_gate'] and verified['independent_from_primary']
    summary['signal_gate']=False
    (args.output/'complete.json').write_text(json.dumps(summary))
    with pytest.raises(ValueError,match='not productive'):fresh.verify_screen(args.output,'kv')


def test_confirmation_requires_frozen_primary_and_disjoint_actual_identities():
    with pytest.raises(ValueError,match='primary screen'):fresh.verify_screen(None,'linear')
    rows=[row(i,1) for i in range(5)]
    assert not fresh.disjoint(rows,rows)
    assert fresh.disjoint(rows,[row(i,1) for i in range(5,10)])

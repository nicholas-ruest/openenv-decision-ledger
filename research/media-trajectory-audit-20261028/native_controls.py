"""Scripted oracle trajectories + fresh TCP replay in the frozen media image.

No model/provider code, credentials or requests. Trusted root-side workspace
inspection consumes zero episode actions, so action32 remains action32.
"""
import contextlib
import hashlib
import json
import stat
import sys
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, '/app')
from qe_arena import skills
from websockets.sync.client import connect
from media_protocol import IMAGE, RUNTIME, build, digest, messages
from trajectory_audit import audit_episode


def exchange(ws, kind, data):
    ws.send(json.dumps({'type':kind,'data':data}))
    result = json.loads(ws.recv(timeout=20))
    if result['type'] != 'observation':
        raise ValueError('native observation required')
    return result['data']


@contextlib.contextmanager
def session(task, seed):
    root = Path('/tmp/qe-arena-ws')
    before = set(root.glob('ep-*'))
    with connect('ws://127.0.0.1:8000/ws', open_timeout=10) as ws:
        reset = exchange(ws,'reset',{'task_id':task,'seed':seed})
        added = set(root.glob('ep-*'))-before
        if len(added)!=1:
            raise ValueError('one fresh real episode workspace required')
        cwd = added.pop(); info=cwd.stat()
        if not (20000<=info.st_uid<20064 and stat.S_IMODE(info.st_mode)==0o700):
            raise ValueError('native UID shell workspace required')
        workspace={}
        for p in sorted(cwd.rglob('*')):
            if p.is_symlink():raise ValueError('unexpected workspace symlink')
            if p.is_file():
                data=p.read_bytes()
                workspace[p.relative_to(cwd).as_posix()]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        yield ws,reset,workspace


def replay(task, seed, actions):
    with session(task,seed) as (ws,reset,workspace):
        return {'image':IMAGE,'runtime_source':RUNTIME,'uid_shell':True,
                'reset_transport':reset,'workspace':workspace,
                'transports':[exchange(ws,'step',action) for action in actions]}


def capture(task, seed, variant, index, plan, schema):
    native=skills.make_skill_task(task,seed)
    answer=skills.solve(native)
    write={'action_type':'write_file','file_path':native.output,'content':answer if variant!='wrong' else '{}'}
    actions=[{'action_type':'exec','command':'true'},write]
    if variant=='recovered_command_error':actions.insert(1,{'action_type':'exec','command':'false'})
    if variant=='autograde32':actions += [{'action_type':'exec','command':'true'}]*30
    elif variant=='explicit_evaluate32':actions += [{'action_type':'exec','command':'true'}]*29+[{'action_type':'evaluate'}]
    else:actions.append({'action_type':'evaluate'})
    with session(task,seed) as (ws,reset,workspace):
        episode={'phase':'screen','task_id':task,'seed':seed,'sample':0,'image':IMAGE,'runtime_source':RUNTIME,
                 'uid_shell':True,'sampling_sha256':plan['sampling_sha256'],'reset_transport':reset,'workspace':workspace,'events':[]}
        ledger=[];history=messages(reset,schema)
        for i,action in enumerate(actions):
            label=f'scripted-{index}-{i}'
            text=json.dumps(action)
            observation=exchange(ws,'step',action)
            episode['events'].append({'kind':'call','status':'returned','call_id_sha256':digest('synthetic-call-'+label),
                                     'reservation_label':label,'request_sha256':digest(history),
                                     'response':{'response_id_sha256':digest('synthetic-reply-'+label),'finish_reason':'stop',
                                                 'content':text,'usage':{'prompt_tokens':100,'completion_tokens':10}},
                                     'native':observation})
            ledger.append({'label':label,'usd':'0','prompt_bound':200,'generation_bound':100})
            history += [{'role':'assistant','content':text},{'role':'user','content':json.dumps(observation,sort_keys=True,separators=(',',':'))}]
    return episode,ledger


def main():
    if Path('/proc/1/comm').read_text().strip()!='tini':raise ValueError('native image entrypoint required')
    if not Path(skills.__file__).resolve().is_relative_to(Path('/app/qe_arena')):raise ValueError('frozen package path required')
    with urlopen('http://127.0.0.1:8000/schema',timeout=10) as r:schema=json.load(r)
    preserved=json.loads((Path(__file__).parent/'native-captures.json').read_text())
    if schema!=preserved['schema']:raise ValueError('frozen actual schema mismatch')
    plan=build(preserved['captures'],schema)
    records=[];raw=[]
    for group in plan['phases']['screen']['groups']:
        for variant in ('full','wrong'):
            episode,ledger=capture(group['task_id'],group['seed'],variant,len(raw),plan,schema)
            result=audit_episode(episode,plan,schema,ledger,replay)
            if result['category']!=variant:raise ValueError('scripted native outcome mismatch')
            raw.append({'variant':variant,'episode':episode,'synthetic_reservations':ledger});records.append(result)
    group=plan['phases']['screen']['groups'][0]
    for variant,expected in [('recovered_command_error','full'),('autograde32','budget'),('explicit_evaluate32','full')]:
        episode,ledger=capture(group['task_id'],group['seed'],variant,len(raw),plan,schema)
        result=audit_episode(episode,plan,schema,ledger,replay)
        if result['category']!=expected:raise ValueError('scripted native boundary mismatch')
        raw.append({'variant':variant,'episode':episode,'synthetic_reservations':ledger});records.append(result)
    print(json.dumps({'scripted_oracle_controls':True,'provider_fields_synthetic':True,'actual_native_tcp':True,
                      'trusted_workspace_inspection':'root reads fresh UID workspace without consuming actions',
                      'scripted_trajectories':len(raw),'native_replay_episodes':len(records),'records':records,'raw':raw,
                      'new_model_calls':0,'new_training':False,'is_model_confirmation':False,
                      'v12_changed':False,'v13_changed':False},sort_keys=True,indent=2))


if __name__=='__main__':main()

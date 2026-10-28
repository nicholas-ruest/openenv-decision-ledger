"""Actual native session/cleanup check; scripted oracle data, no provider calls."""
import hashlib
import json
import sys
import time
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0,'/app')
from qe_arena import skills
from native_session import NativeSession
from media_protocol import IMAGE,RUNTIME,build


def workspace_added(before):
    added=set(Path('/tmp/qe-arena-ws').glob('ep-*'))-before
    if len(added)!=1:raise ValueError('one native workspace expected')
    p=added.pop()
    if not 20000<=p.stat().st_uid<20064:raise ValueError('UID workspace required')
    return p


def removed(path):
    stop=time.monotonic()+2
    while path.exists() and time.monotonic()<stop:time.sleep(.01)
    if path.exists():raise ValueError('server workspace remained after session close')


def main():
    if Path('/proc/1/comm').read_text().strip()!='tini':raise ValueError('native entrypoint required')
    with urlopen('http://127.0.0.1:8000/schema',timeout=5) as r:schema=json.load(r)
    preserved=json.loads((Path(__file__).parent/'native-captures.json').read_text());plan=build(preserved['captures'],schema)
    if schema!=preserved['schema']:raise ValueError('frozen schema mismatch')
    rows=[]
    for group in (plan['phases']['screen']['groups'][0],plan['phases']['screen']['groups'][2]):
        before=set(Path('/tmp/qe-arena-ws').glob('ep-*'))
        with NativeSession(deadline=time.monotonic()+30) as s:
            reset=s.reset(group['task_id'],group['seed']);p=workspace_added(before)
            native=skills.make_skill_task(group['task_id'],group['seed'])
            files={f.relative_to(p).as_posix():{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in p.rglob('*') if f.is_file()}
            from media_protocol import digest
            if digest(reset)!=group['reset_sha256'] or digest(files)!=group['workspace_sha256']:raise ValueError('native manifest mismatch')
            uid=s.step({'action_type':'exec','command':'true'},schema)
            if not uid['observation']['success']:raise ValueError('enabled shell required')
            expected=1 if group['task_id'].endswith('d1') else 0
            s.step({'action_type':'write_file','file_path':native.output,'content':skills.solve(native) if expected else '{}'},schema)
            final=s.step({'action_type':'evaluate'},schema)
            if not final['done'] or final['reward']!=expected:raise ValueError('scripted native outcome mismatch')
            rows.append({'task_id':group['task_id'],'seed':group['seed'],'reward':final['reward']})
        removed(p)
    # More than the server's8 simultaneous-session limit, closed sequentially
    # without evaluate: independently verify cleanup on nonterminal disconnect.
    group=plan['phases']['screen']['groups'][0]
    for _ in range(10):
        before=set(Path('/tmp/qe-arena-ws').glob('ep-*'))
        with NativeSession(deadline=time.monotonic()+10) as s:
            s.reset(group['task_id'],group['seed']);p=workspace_added(before)
        removed(p)
    print(json.dumps({'image':IMAGE,'runtime_source':RUNTIME,'native_scripted_episodes':rows,
                      'nonterminal_disconnect_cleanups':10,'new_model_calls':0,'is_training':False,
                      'model_confirmation':False,'v12_changed':False,'v13_changed':False},sort_keys=True,indent=2))


if __name__=='__main__':main()

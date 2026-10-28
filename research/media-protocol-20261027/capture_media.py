"""Native TCP identity capture inside the immutable image; no provider endpoint."""
import json
from pathlib import Path
from urllib.request import urlopen
from websockets.sync.client import connect
from media_protocol import IMAGE,RUNTIME,TASKS,SEEDS,build
import sys
sys.path.insert(0,'/app')
from qe_arena import skills
if not Path(skills.__file__).resolve().is_relative_to(Path('/app/qe_arena')):
    raise ValueError('native frozen package path required')

# Trusted inspection in the visible episode cwd, executed as the episode UID.
INSPECT="""import pathlib,hashlib,json
out={};total=0
for p in sorted(pathlib.Path('.').rglob('*')):
 if p.is_symlink(): raise ValueError('unexpected symlink')
 if p.is_file():
  b=p.read_bytes();total+=len(b)
  if len(out)>=32 or total>131072: raise ValueError('visible workspace bound')
  out[p.as_posix()]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
print(json.dumps(out,sort_keys=True))
"""

def exchange(ws,kind,data):
    ws.send(json.dumps({'type':kind,'data':data}));r=json.loads(ws.recv(timeout=20))
    if r['type']!='observation':raise ValueError('native observation required')
    return r['data']


def main():
    if Path('/proc/1/comm').read_text().strip()!='tini':raise ValueError('native entrypoint required')
    with urlopen('http://127.0.0.1:8000/schema',timeout=10) as r:schema=json.load(r)
    captures=[]
    for phase,tasks in SEEDS.items():
        for task,seeds in tasks.items():
            for seed in seeds:
                for repeat in range(2):
                    with connect('ws://127.0.0.1:8000/ws',open_timeout=10) as ws:
                        reset=exchange(ws,'reset',{'task_id':task,'seed':seed})
                        uid=exchange(ws,'step',{'action_type':'exec','command':'id -u'})
                        if not uid['observation']['success'] or not 20000<=int(uid['observation']['output'].strip())<20064:raise ValueError('enabled UID shell required')
                        # shlex.quote handles the trusted multiline inspection code.
                        import shlex
                        out=exchange(ws,'step',{'action_type':'exec','command':'python3 -c '+shlex.quote(INSPECT)})
                        if not out['observation']['success']:raise ValueError('workspace inspection failed')
                        native=skills.make_skill_task(task,seed)
                        import hashlib
                        expected={name:{'sha256':hashlib.sha256(text.encode()).hexdigest(),'bytes':len(text.encode())} for name,text in native.files.items()}
                        workspace=json.loads(out['observation']['output'])
                        if workspace!=expected:raise ValueError('actual TCP workspace differs from native generator')
                        captures.append({'phase':phase,'task_id':task,'seed':seed,'repeat':repeat,'family':native.kind,'image':IMAGE,'runtime_source':RUNTIME,'uid_shell':True,'reset_observation':reset['observation'],'workspace':workspace})
    plan=build(captures,schema)
    print(json.dumps({'plan':plan,'captures':captures,'schema':schema},sort_keys=True,indent=2))

if __name__=='__main__':main()

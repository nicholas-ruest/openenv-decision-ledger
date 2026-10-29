"""Supervise real native scripted phase and intentional stalled native session."""
import hashlib
import json
import time
from pathlib import Path

from media_protocol import build
from phase_supervisor import supervise


def main():
    source=Path(__file__).parent;data=json.loads((source/'native-captures.json').read_text());plan=build(data['captures'],data['schema'])
    root=Path('/native-composition-evidence');root.mkdir(mode=0o700)
    before=set(Path('/tmp/qe-arena-ws').glob('ep-*'))
    script=source/'scripted_worker.py'
    normal=supervise(root/'normal',script,hashlib.sha256(script.read_bytes()).hexdigest(),plan,'screen',deadline=time.monotonic()+150)
    if normal['status']!='completed' or not normal['archive_verified']:raise ValueError('native durable phase verification failed')
    integration=json.loads((root/'normal/phase/integration.json').read_text())
    script=source/'hanging_worker.py'
    hanging=supervise(root/'stalled',script,hashlib.sha256(script.read_bytes()).hexdigest(),plan,'screen',deadline=time.monotonic()+2)
    if hanging['status']!='deadline' or hanging['archive_verified']:raise ValueError('stalled native worker classification failed')
    if not (root/'stalled/phase/opened-native-session.json').exists():raise ValueError('timeout fixture never opened native session')
    stop=time.monotonic()+2
    while set(Path('/tmp/qe-arena-ws').glob('ep-*'))!=before and time.monotonic()<stop:time.sleep(.01)
    if set(Path('/tmp/qe-arena-ws').glob('ep-*'))!=before:raise ValueError('native server workspace retained after worker cleanup')
    summary={'normal_supervisor':normal,'stalled_supervisor':hanging,'integration':integration,
             'workspace_set_restored':True,'new_model_calls':0,'is_training':False,'model_confirmation':False,'v12_changed':False,'v13_changed':False}
    (root/'summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2))
    print(json.dumps(summary,sort_keys=True,indent=2))


if __name__=='__main__':main()

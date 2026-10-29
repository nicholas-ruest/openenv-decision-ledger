"""Explicit offline integration fixture. Responses/reservations are SYNTHETIC."""
import json
import sys
import time
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0,'/app')
from qe_arena import skills
from media_protocol import build,digest
from verified_phase import run_phase,schedule
from observation_budget import EpisodeBudget
from accounting_archive import make_config
from fixture_counter import SyntheticByteCounter
from native_bridge import NativeBridge


def main():
    root=Path(sys.argv[1]);source=Path(__file__).parent
    if Path('/proc/1/comm').read_text().strip()!='tini':raise ValueError('native entrypoint required')
    with urlopen('http://127.0.0.1:8000/schema',timeout=5) as r:schema=json.load(r)
    old=json.loads((source/'native-captures.json').read_text());plan=build(old['captures'],schema)
    if schema!=old['schema']:raise ValueError('frozen schema mismatch')
    deadline=time.monotonic()+120;bridge=NativeBridge(schema,deadline);ledger=[];jobs=schedule(plan,'screen');calls=[]
    counter=SyntheticByteCounter();config=make_config(counter)
    def reserve(label,history,remaining):ledger.append({'label':label,'usd':'0','prompt_bound':counter.context(history),'generation_bound':min(100,remaining)})
    def dispatch(history,label,wall):
        # No network/provider library exists in this callback. All fields below
        # describe a scripted response, not a real inference transaction.
        seq,index=map(int,label.split(':')[1:]);task,seed,sample=jobs[seq]
        calls.append(label)
        event={'kind':'call','status':'returned','call_id_sha256':digest('synthetic-call-'+label),
               'reservation_label':label,'request_sha256':digest(history)}
        if seq==0:
            event['status']='timeout';return event
        native=skills.make_skill_task(task,seed)
        action=({'action_type':'write_file','file_path':native.output,'content':skills.solve(native) if sample%2 else '{}'}
                if index==0 else {'action_type':'evaluate'})
        event['response']={'response_id_sha256':digest('synthetic-reply-'+label),'finish_reason':'stop','content':json.dumps(action),
                           'usage':{'prompt_tokens':100,'completion_tokens':10}}
        return event
    # True is only fixture admission: there is no model/provider route here.
    report=run_phase(root,plan,schema,'screen','native',deadline,True,time.monotonic,
                     bridge.open_env,reserve,lambda:ledger,dispatch,bridge.replay, accounting_factory=lambda h:EpisodeBudget(counter,h),accounting_config=config)
    if report['attempts']!=16:raise ValueError('complete scripted denominator required')
    (root/'fixture-ledger.json').write_text(json.dumps(ledger))
    if bridge.opened!=bridge.closed:raise ValueError('all native sessions must close')
    (root/'integration.json').write_text(json.dumps({'callbacks_synthetic':True,'new_model_calls':0,
        'counts':report['counts'],'attempts':report['attempts'],'synthetic_calls':len(calls),
        'native_sessions_opened':bridge.opened,'native_sessions_closed':bridge.closed,'is_training':False},sort_keys=True,indent=2))


if __name__=='__main__':main()

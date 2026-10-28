"""Exercise the raw binder on an existing frozen archive; never calls a provider."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from raw_evidence import bind


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def rows(path):return [json.loads(x) for x in path.read_text().splitlines() if x]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('archive','runtime-root','probe-root','ledger','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('fresh report required')
    pins=json.loads((a.probe_root/'config/software-probe-source-hashes-20261027.json').read_text())
    for name,expected in pins.items():
        if hashlib.sha256((a.runtime_root/name).read_bytes()).hexdigest()!=expected:raise ValueError('frozen runtime dependency drift')
    base=load('saved_base',a.runtime_root/'scripts/repair-signal-screen.py')
    runner=load('saved_probe',a.probe_root/'scripts/run-software-scaffold-probe.py')
    protocol=json.loads((a.archive/'protocol.json').read_text())
    settings=runner.digest({'settings':protocol['settings'],'provider':protocol['provider']})
    raw=rows(a.archive/'raw-episodes.jsonl');old=rows(a.archive/'records.jsonl')
    if len(raw)!=16:raise ValueError('only completed16sample legacy archive supported')
    jobs=[];normalized=[]
    for row,record in zip(raw,old,strict=True):
        snap=runner.capture(base,row['task_id'],row['seed'])
        if runner.normalize(row,snap,settings)!=record:raise ValueError('original normalized archive drift')
        if len(row['calls'])!=1:raise ValueError('this legacy adapter expects observed single response')
        label=row['calls'][0]['client_call_label']
        jobs.append({'arm':'baseline','task_id':row['task_id'],'seed':row['seed'],'sample':row['sample'],'planned_call_label':label,'raw':row})
        normalized.append({'arm':'baseline',**{k:v for k,v in record.items() if k!='raw_failure'}})
    def capture(arm,task,seed):
        if arm!='baseline':raise ValueError('legacy arm must be baseline')
        return runner.capture(base,task,seed)
    def replay(arm,task,seed,message):
        env=base.DirectRepairEnvironment();env.reset(task_id=task,seed=seed)
        action=json.loads(message['content'])
        if set(action)=={'action'}:action=action['action']
        obs=env.step(base.DirectRepairAction.model_validate(action))
        if not obs.done or obs.error:raise ValueError('saved native action failed')
        return float(obs.reward)
    report=bind(jobs,normalized,rows(a.ledger),runner.RUNTIME,settings,capture,replay,runner.classify)
    report.update(legacy_archive=True,new_provider_calls=0,paired_phase=False,all_source_pins_match=True)
    with a.output.open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps({k:v for k,v in report.items() if not k.endswith('sha256')}))


if __name__=='__main__':main()

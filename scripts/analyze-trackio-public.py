"""Read public Arena training metrics; no credentials, inference or submission."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import urllib.request

BASE = "https://openenvarena-training.hf.space/api/"
METRICS = ("reward","reward_std","frac_reward_zero_std","grad_norm",
           "completions/clipped_ratio","completions/mean_length","step/retries","loss")


def read(endpoint, payload):
    q=urllib.request.Request(BASE+endpoint,data=json.dumps(payload).encode(),
                             headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(q,timeout=15) as response: raw=response.read(2_000_001)
    if len(raw)>2_000_000:raise ValueError("public metric response exceeds bound")
    value=json.loads(raw)
    if value.get("error"):raise ValueError("Trackio returned an error")
    return value["data"]


def summarize(rows):
    values=[r['value'] for r in rows if type(r.get('value')) in (int,float)]
    if not values:return {"available":False}
    return {"available":True,"n":len(values),"first_step":rows[0]['step'],"last_step":rows[-1]['step'],
            "mean":statistics.mean(values),"min":min(values),"max":max(values),
            "first25_mean":statistics.mean(values[:25]),"last25_mean":statistics.mean(values[-25:]),
            "zeros":sum(x==0 for x in values),"ones":sum(x==1 for x in values)}


def analyze(project, run):
    payload={"project":project,"run":run,"run_id":run}
    summary=read('get_run_summary',payload)
    if not summary.get('num_logs') or not summary.get('metrics'):
        return {"project":project,"run":run,"status":"metrics_unavailable", "is_zero_training_claim":False}
    if (summary.get('config') or {}).get('recipe')=='cpu-dummy-simulation':
        raise ValueError('CPU simulation is not model training')
    records={name:read('get_metric_values',{**payload,'metric_name':name})
             for name in METRICS if name in summary['metrics']}
    zero=lambda name:{r['step'] for r in records.get(name,[]) if r['value']==0}
    return {"project":project,"run":run,"status":"available","num_logs":summary['num_logs'],
            "metrics":{k:summarize(v) for k,v in records.items()},
            "zero_std_and_zero_gradient_joint_steps":len(zero('reward_std')&zero('grad_norm')),
            "records_sha256":hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest(),
            "records":records,"is_learning_or_ranking_improvement_claim":False,
            "limitation":"Clipping flags alone do not distinguish actual budget exhaustion from EOS/custom-rollout accounting. Coarse reward windows are not a held-out trained-vs-base comparison."}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--run',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('fresh output required')
    result=analyze(a.project,a.run)
    with a.output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='records'}))

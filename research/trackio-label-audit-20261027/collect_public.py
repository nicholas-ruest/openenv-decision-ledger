"""Bounded read-only public Trackio collection for the fixed v11 run; no token."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import urllib.request

BASE='https://openenvarena-training.hf.space/api/'
RUN={'project':'GlobalBusinessAdvisors','run':'a3274296c46341a847407f97','run_id':'a3274296c46341a847407f97'}
ENDPOINTS={'get_run_summary','get_logs','get_alerts','get_metric_values'}
METRICS=('step/task','reward','reward_std','grad_norm','frac_reward_zero_std','step/retries','completions/clipped_ratio')


def read(endpoint,extra=None):
    if endpoint not in ENDPOINTS:raise ValueError('public read endpoints only')
    request=urllib.request.Request(BASE+endpoint,data=json.dumps({**RUN,**(extra or {})}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=20) as response:raw=response.read(2000001)
    if len(raw)>2000000:raise ValueError('public response bound')
    value=json.loads(raw)
    if value.get('error'):raise ValueError('public API error, not empty metrics')
    return value['data']


def collect(output):
    output.mkdir(mode=0o700,exist_ok=False)
    # Raw alerts stay local. Public reports use only numeric step summaries.
    for endpoint in ('get_run_summary','get_logs','get_alerts'):
        (output/(endpoint+'.json')).write_text(json.dumps(read(endpoint),indent=2)+'\n')
    summary=json.loads((output/'get_run_summary.json').read_text())
    names=[m for m in METRICS if m in summary['metrics']]
    with ThreadPoolExecutor(3) as pool:
        data=dict(pool.map(lambda m:(m,read('get_metric_values',{'metric_name':m})),names))
    (output/'metric-records.json').write_text(json.dumps(data,indent=2)+'\n')
    return {'project':RUN['project'],'run':RUN['run'],'metric_series':len(data),'new_model_calls':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(collect(a.output)))

"""Describe recorded v11 completion metrics; never infer finish reasons or task names."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from statistics import mean

KEYS=('step','step/task','step/retries','reward','reward_std','grad_norm',
 'completions/clipped_ratio','completions/mean_length','completions/min_length',
 'completions/max_length','completions/mean_terminated_length',
 'completions/min_terminated_length','completions/max_terminated_length')


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def validate(rows):
    if type(rows) is not list or len(rows)!=148:raise ValueError('original 148 updates required')
    for i,row in enumerate(rows,1):
        if any(type(row.get(k)) not in (int,float) or not math.isfinite(row[k]) for k in KEYS):raise ValueError('missing/nonfinite/non-numeric recorded field')
        if type(row['step']) is not int or row['step']!=i:raise ValueError('original ordered optimizer steps required')
        if type(row['step/task']) is not int or row['step/task'] not in (1,2,3):raise ValueError('observed numeric task ID required')
        if type(row['step/retries']) is not int or row['step/retries']<0:raise ValueError('recorded retry count required')
        if not 0<=row['reward']<=1 or not 0<=row['completions/clipped_ratio']<=1:raise ValueError('recorded ratio outside range')
        for prefix in ('length','terminated_length'):
            lo,mid,hi=(row['completions/'+name+'_'+prefix] for name in ('min','mean','max'))
            if not 0<=lo<=mid<=hi:raise ValueError('inconsistent recorded lengths')
    return rows


def describe(rows):
    clipped=[r for r in rows if r['completions/clipped_ratio']==1]
    return dict(updates=len(rows),clipped_ratio_histogram={str(k):v for k,v in sorted(Counter(r['completions/clipped_ratio'] for r in rows).items())},
        mean_of_update_clipped_ratios=mean(r['completions/clipped_ratio'] for r in rows),
        clip_one_updates=len(clipped),clip_one_with_positive_reward=sum(r['reward']>0 for r in clipped),
        clip_one_with_reward_one=sum(r['reward']==1 for r in clipped),
        clip_one_with_all_terminated_lengths_zero=sum(all(r['completions/'+n+'_terminated_length']==0 for n in ('min','mean','max')) for r in clipped),
        minimum_recorded_completion_length=min(r['completions/min_length'] for r in rows),
        maximum_recorded_completion_length=max(r['completions/max_length'] for r in rows),
        mean_of_update_mean_lengths=mean(r['completions/mean_length'] for r in rows))


def analyze(rows):
    rows=validate(rows)
    return dict(kind='recorded_training_completion_metric_audit',run='a3274296c46341a847407f97',project='GlobalBusinessAdvisors',
        selected_numeric_records_sha256=digest([{k:r[k] for k in KEYS} for r in rows]),
        all_updates=describe(rows),zero_retry_updates=describe([r for r in rows if r['step/retries']==0]),
        numeric_groups={str(i):dict(task_name=None,**describe([r for r in rows if r['step/task']==i])) for i in (1,2,3)},
        actual_trainer_revision_attested=False,provider_finish_reasons_available=False,
        total_rollout_count_inferred=False,clipped_metric_treated_as_semantic_failure=False,
        mapping_inferred_from_rotation=False,model_calls=0,new_cases=0,model_improvement=False,leaderboard_gain=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(allow_abbrev=False);p.add_argument('--logs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=analyze(json.loads(a.logs.read_text()))
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))

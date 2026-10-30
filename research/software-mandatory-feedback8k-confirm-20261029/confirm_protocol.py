"""Conditional confirmation only; importing never materializes its observations."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/software-mandatory-feedback8k-20261029'))
import feedback_protocol as original
Trial=original.Trial
canonical=original.canonical
digest=original.digest
ARMS=original.ARMS
NAMESPACE=original.NAMESPACE
SCREEN_SOURCE='1e49f5d7398dd2329b7aba650b97fd715b77ab49'
SCREEN_INPUTS=['e9d02179b121fe925e7612e11ef142cbb55584bd52c0cd33d1e375f72a886c58',
    'e051f128b76d7fbd028e65201a4c5f5b5c185e4e35092d06b2d645e4de251247',
    '38ca8cf07ec23f0055666c285d61bee7ca1555a18642b51b2dc49f6e8cb7fb29',
    '71b251379c444b4a8111cacce98b015201937db1e5507a22a4264629d1d011c9']
_CHOICE=None

def profile():
    return dict(sampling=original.SAMPLING,first_generation_limit=6000,
        completion_with_observations=8192,context=24576,attempt_wall_seconds=600)

def selection(value):
    def sha(s):return isinstance(s,str) and len(s)==64 and all(c in '0123456789abcdef' for c in s)
    if (value.get('screen_source')!=SCREEN_SOURCE or value.get('screen_inputs_sha256')!=SCREEN_INPUTS
        or value.get('screen_selection_passed') is not True or value.get('all_live_replies_verified') is not True
        or value.get('assigned')!=8 or value.get('unknown_usage')!=0
        or not 8<=value.get('actual_calls',0)<=16 or not value.get('full_rate_delta',0)>0
        or not value.get('semantic_mean_delta',-1)>=0 or value.get('profile_sha256')!=digest(profile())):
        raise ValueError('exact complete independently replayed positive screen required')
    ids=value.get('response_ids',[])
    if len(ids)!=value['actual_calls'] or len(set(ids))!=len(ids) or not all(sha(x) for x in ids):raise ValueError('all unique actual screen response identities required')
    for key in ['screen_problem_sha256','screen_assessment_sha256']:
        if not sha(value.get(key)):raise ValueError('immutable evidence hash required')
    for key in ['screen_raw_events_sha256','screen_records_sha256']:
        if len(value.get(key,[]))!=4 or not all(sha(x) for x in value[key]):raise ValueError('four bound raw chunk hashes required')
    return copy.deepcopy(value)

def configure(path,expected):
    global _CHOICE
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('immutable selection receipt changed')
    _CHOICE=selection(json.loads(raw))

def choice():
    if _CHOICE is None:raise ValueError('positive immutable selection required before confirmation capture')
    return copy.deepcopy(_CHOICE)

def schedule(phase):
    if phase!='confirmation':raise ValueError('frozen confirmation scope only')
    return original.schedule('confirmation')

def capture(job):
    selected=choice()
    if job not in schedule('confirmation'):raise ValueError('exact disjoint confirmation assignment required')
    trial=Trial(job);reset=json.loads(trial.messages[1]['content'])
    problem={k:reset[k] for k in ('task_id','prompt','source','examples')}
    hashed=digest(problem)
    if hashed==selected['screen_problem_sha256']:raise ValueError('procedural collision; no replacement seed or redraw')
    return dict(messages=copy.deepcopy(trial.messages),prompt_sha256=digest(trial.messages),problem_sha256=hashed)

def bundle(chunk):
    selected=choice()
    if type(chunk) is not int or chunk not in range(4):raise ValueError('four exact chunks required')
    jobs=schedule('confirmation');arms={arm:capture(next(j for j in jobs if j['arm']==arm)) for arm in ARMS}
    if arms[ARMS[0]]!=arms[ARMS[1]]:raise ValueError('first prompts must match')
    return dict(namespace=NAMESPACE,chunk=chunk,confirmation_jobs=[j for j in jobs if j['sample']==chunk],
        all_confirmation_jobs=jobs,confirmation_groups=[dict(task_id=jobs[0]['task_id'],seed=2690000,
            problem_sha256=arms[ARMS[0]]['problem_sha256'],arms=arms)],screen_selection=selected,
        selection_sha256=digest(selected),sampling=copy.deepcopy(original.SAMPLING),max_attempts=8,max_calls=16,
        max_calls_per_chunk=4,retries=0,first_generation_limit=6000,completion_with_observations=8192,
        context=24576,reserved_final_observation_tokens=96,attempt_wall_seconds=600,
        intervention='Exact unchanged required-review public-feedback versus neutral-review protocol; only procedural case and phase identities change from the selected screen.',
        limitations='One fresh procedural confirmation case, four samples per arm; no Arena wrapper, thinking, model-training or leaderboard attestation.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--selection',type=Path,required=True);p.add_argument('--selection-sha256',required=True)
    p.add_argument('--chunk',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    configure(a.selection,a.selection_sha256);value=bundle(a.chunk)
    with a.output.open('x') as f:json.dump(value,f,indent=2)
    print(digest(value))

"""Source-bound screen inventory gate. Public source refuses before private I/O."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[2]
CASE_AUDIT_SHA256=None
LATEST_CLOSED_AUDIT_SHA256=None
SAMPLING=dict(model='Qwen/Qwen3.8-27B:deepinfra',temperature=.7,response_format={'type':'json_object'})
LIMITS=dict(first_generation=6000,completion_plus_all_observations=8192,context=24576,terminal_reserve=96,request_seconds=360,attempt_seconds=600,whole_phase_seconds=1200)
FILES=tuple('research/software-final-domain-cue-20261101/'+n for n in ('revision_environment.py','matched_protocol.py','finite_caller.py','guarded_transport.py','qualification_supervisor.py','assess_qualification.mjs','financial_bridge.py','case_binding.py','financial-source-pins.json','closed-method-manifest.json'))

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sealed(value):return isinstance(value,str) and re.fullmatch('[a-f0-9]{64}',value) is not None

def operating_seconds():
    now=datetime.now(ZoneInfo('America/Toronto'));seconds=min(1200,(now.replace(hour=23,minute=0,second=0,microsecond=0)-now).total_seconds())
    if seconds<=0:raise ValueError('fixed23Toronto stop reached')
    return seconds

def source_guard(expected):
    if not isinstance(expected,str) or not re.fullmatch('[a-f0-9]{40}',expected):raise ValueError('exact source lease required')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=expected or subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('exact clean source required')

def method_hashes():return {n:sha(ROOT/n) for n in FILES}

def verify_inventory(value,job):
    # Called only after all immutable seals, full chain and method checks pass.
    sys.path.insert(0,str(ROOT/'integrations/software-repair'))
    from repair_env.tasks import make_task
    from repair_env.direct_environment import DirectRepairEnvironment
    pairs=value['prior_task_seed_pairs']
    if (not pairs or pairs!=sorted(pairs) or any(type(x) is not list or len(x)!=2 or type(x[0]) is not str or type(x[1]) is not int for x in pairs) or len({tuple(x) for x in pairs})!=len(pairs) or [job['task_id'],job['seed']] in pairs):raise ValueError('complete distinct prior inventory required')
    past=set()
    for task,seed in pairs:
        t=make_task(task,seed);past.update(digest(c.args) for c in t.public+t.hidden)
    t=make_task(job['task_id'],job['seed']);current={digest(c.args) for c in t.public+t.hidden}
    obs=DirectRepairEnvironment().reset(task_id=t.task_id,seed=t.seed)
    if (past&current or value['task_id']!=job['task_id'] or value['new_seed']!=job['seed'] or value['prior_case_count']!=len(pairs) or value['prior_input_count']!=len(past) or value['new_input_count']!=len(current) or value['prior_input_set_sha256']!=digest(sorted(past)) or value['new_input_set_sha256']!=digest(sorted(current)) or value['new_source_examples_sha256']!=digest(dict(source=obs.source,examples=obs.examples))):raise ValueError('independent regenerated inventory differs or overlaps')
    return dict(verified=True,input_overlap=0)

def jobs_for(value):
    seed=value['new_seed']
    if type(seed) is not int or value.get('task_id')!='software_repair-ignore-d3':raise ValueError('fixed software stage required')
    result=[]
    for sample in range(4):
        for arm in ('common_review','final_domain_reminder') if sample%2==0 else ('final_domain_reminder','common_review'):
            job=dict(namespace='final-review-domain-reminder-20261101',phase='screen',task_id=value['task_id'],seed=seed,sample=sample,arm=arm)
            result.append(dict(job,attempt_id=digest(job)))
    return result

def require_case(args):
    if not sealed(CASE_AUDIT_SHA256) or not sealed(LATEST_CLOSED_AUDIT_SHA256):raise ValueError('case/source and latest closed inventory unsealed; no private reads')
    if args.phase!='screen':raise ValueError('confirmation remains closed pending original positive screen evidence')
    operating_seconds();source_guard(args.expected_source)
    if args.case_audit_sha256!=CASE_AUDIT_SHA256 or sha(args.case_audit)!=CASE_AUDIT_SHA256:raise ValueError('exact source-bound case receipt required')
    value=json.loads(Path(args.case_audit).read_text())
    if value.get('kind')!='final-domain-cue-screen-case-audit' or value.get('method_sha256')!=method_hashes() or value.get('sampling')!=SAMPLING or value.get('limits')!=LIMITS:raise ValueError('original method, sampling and resource scope required')
    jobs=jobs_for(value)
    if value.get('jobs')!=jobs:raise ValueError('all eight original assignments required')
    manifest=json.loads(Path(__file__).with_name('closed-method-manifest.json').read_text())
    for group in manifest.values():
        if any(sha(ROOT/n)!=h for n,h in group.items()):raise ValueError('preceding closed method source changed')
    anchors=[('entry-order-review-case-audit','software_repair-ignore-d3',3220000,'entry_order'),('top-level-note-case-audit','software_repair-ignore-d3',3200000,'top_level'),('preserve-first-case-audit','software_repair-ignore-d3',3180000,'preserve_first'),('failure-advice-case-audit','software_repair-ignore-d2',3160000,None)]
    current=value;chain=[]
    for index,(kind,task,seed,key) in enumerate(anchors):
        path=Path(current['parent_audit_path']);expected=current['parent_audit_sha256']
        if index==0 and expected!=LATEST_CLOSED_AUDIT_SHA256:raise ValueError('latest closed study lease required')
        if sha(path)!=expected:raise ValueError('preceding audit changed')
        parent=json.loads(path.read_text())
        if parent.get('kind')!=kind or parent.get('task_id')!=task or parent.get('new_seed')!=seed or (key and parent.get('method_sha256')!=manifest[key]):raise ValueError('original closed study anchor required')
        required=sorted(parent['prior_task_seed_pairs']+[[task,seed]])
        if current['prior_task_seed_pairs']!=required or current['prior_inventory_sha256']!=digest(required):raise ValueError('prior cases dropped or replaced')
        chain.append((parent,dict(task_id=task,seed=seed)));current=parent
    for audit,job in reversed(chain):verify_inventory(audit,job)
    verify_inventory(value,jobs[0])
    return dict(jobs=jobs,case_audit_sha256=CASE_AUDIT_SHA256,independently_regenerated=True)

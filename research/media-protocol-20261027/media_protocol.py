"""Frozen media proxy plan and native identity manifest; no model calls."""
import hashlib
import json

IMAGE='ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:b80078c2cc8a05d3222fe22ee91321d29d881afff912097c6601a8cffd84c4e6'
RUNTIME='74a8727fa14270e29cf363fc2ad79b0f7f9cbce1'
TASKS=('qe_skill-media-d1','qe_skill-media-d2')
SEEDS={'screen':{'qe_skill-media-d1':(2290000,2290100),'qe_skill-media-d2':(2290000,2290100)},'confirmation':{'qe_skill-media-d1':(2300004,2300000),'qe_skill-media-d2':(2300009,2300002)}}
FAMILIES={'qe_skill-media-d1':('catalogue','timecode'),'qe_skill-media-d2':('subtitles','catalogue')}
SAMPLING={'model':'Qwen/Qwen3.8-27B','route':'deepinfra','thinking':True,'temperature':0.7,'response_format':{'type':'json_object'},'episode_generation_units':4096,'context_units':8192,'max_generation_per_call':4096,'max_actions':32,'retries':0}


def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()).hexdigest()


def messages(observation,schema):
    return [{'role':'system','content':'Complete the media task using the documented terminal actions. Emit exactly one JSON action instance, no markdown. Action schema: '+json.dumps(schema['action'],sort_keys=True,separators=(',', ':'))},
            {'role':'user','content':json.dumps(observation,sort_keys=True,separators=(',', ':'))}]


def build(captures,schema):
    expected={(phase,task,seed,repeat) for phase,tasks in SEEDS.items() for task,seeds in tasks.items() for seed in seeds for repeat in range(2)}
    seen=set();groups={}
    for c in captures:
        key=tuple(c[k] for k in ('phase','task_id','seed','repeat'))
        if type(c['seed']) is not int or type(c['repeat']) is not int or key not in expected or key in seen:
            raise ValueError('complete unique native capture identities required')
        seen.add(key)
        if c['image']!=IMAGE or c['runtime_source']!=RUNTIME or c['uid_shell'] is not True:
            raise ValueError('frozen image/source and enabled UID shell required')
        observation=c['reset_transport']
        if observation.get('done') is not False or observation.get('observation',{}).get('success') is not True:
            raise ValueError('successful nonterminal native reset required')
        workspace=c['workspace']
        if not isinstance(workspace,dict) or not workspace:
            raise ValueError('visible workspace hashes required')
        for name,meta in workspace.items():
            if not isinstance(name,str) or name.startswith('/') or '..' in name.split('/') or set(meta)!={'sha256','bytes'}:
                raise ValueError('bounded relative workspace records required')
            sha=meta['sha256']
            if not isinstance(sha,str) or len(sha)!=64 or any(v not in '0123456789abcdef' for v in sha) or type(meta['bytes']) is not int or meta['bytes']<0:
                raise ValueError('complete workspace digest and length required')
        position=SEEDS[c['phase']][c['task_id']].index(c['seed'])
        if c['family']!=FAMILIES[c['task_id']][position]:raise ValueError('actual native family differs from matched plan')
        snapshot={'family':c['family'],'reset_sha256':digest(observation),'workspace_sha256':digest(workspace),'prompt_sha256':digest(messages(observation,schema))}
        group=key[:3]
        if group in groups and groups[group]!=snapshot:
            raise ValueError('repeated reset/prompt/workspace mismatch')
        groups[group]=snapshot
    if seen!=expected:raise ValueError('incomplete native capture phase')
    phases={}
    for phase in SEEDS:
        rows=[{'task_id':t,'seed':s,**groups[phase,t,s]} for t in TASKS for s in SEEDS[phase][t]]
        if len({r['prompt_sha256'] for r in rows})!=4 or len({r['workspace_sha256'] for r in rows})!=4:
            raise ValueError('duplicate prompt/workspace cases within phase')
        phases[phase]={'groups':rows,'samples_per_prompt':4,'future_rollouts':16,'native_reset_controls_per_prompt':2,'executed':False}
    for field in ('prompt_sha256','workspace_sha256'):
        if {r[field] for r in phases['screen']['groups']} & {r[field] for r in phases['confirmation']['groups']}:
            raise ValueError('screen/confirmation prompt or visible-case leakage')
    return {'image':IMAGE,'runtime_source':RUNTIME,'schema_sha256':digest(schema),'sampling':SAMPLING,'sampling_sha256':digest(SAMPLING),'phases':phases,
            'native_reset_controls':16,'new_model_calls':0,'model_phase_executed':False,
            'budget_admitted':False,'fresh_provider_fingerprint_required':True,'whole_phase_reservation_required':True,
            'maximum_provider_calls_per_phase':16*SAMPLING['max_actions'],
            'failure_classes':['format','provider','truncation','execution','budget'],
            'semantic_rewards':[0,1],'partial_semantic_reward_supported':False,
            'productive_group_definition':'same prompt contains both valid reward0 and valid reward1; failures never substitute for semantic wrong',
            'confirmation_requirement':'disjoint screen/confirmation cases and observed calls; each sampled task/family cell needs productive prompts in both phases before provisional cell-signal claims',
            'scope':'four sampled task/family cells; no whole-task, unsampled-family or training-readiness claim',
            'confirmation_seed_selection':'first unused seed in2300000..2301023 matching the screen family; chosen solely from native generator labels before any model outcomes',
            'arena_wrapper_equivalent':False,'provider_checkpoint_attested':False,'thinking_attested':False,
            'is_training':False,'promotion':False}

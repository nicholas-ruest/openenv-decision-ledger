"""Recompute local accounting from saved raw events; no dispatch or admission API."""
import copy
import hashlib
import inspect
import importlib.metadata
import json
from pathlib import Path

import observation_budget
import media_protocol
import trajectory_audit
import durable_phase
from observation_budget import TOKENIZER_SHA, PinnedCounter, canonical
from media_protocol import digest, messages
from trajectory_audit import require, audit_episode, assess_phase


def source_hashes():
    paths={m.__name__:Path(m.__file__) for m in (observation_budget,media_protocol,trajectory_audit,durable_phase)}
    paths.update(accounting_archive=Path(__file__),verified_phase=Path(__file__).with_name('verified_phase.py'))
    return {name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in sorted(paths.items())}


def make_config(counter, *, completion=4096, context=8192):
    require(type(completion) is int and type(context) is int and 1<=completion<=context<=8192,'bounded accounting limits required')
    require(counter.mode=='pinned_tokenizer' and counter.sha256==TOKENIZER_SHA,'pinned tokenizer required')
    return {'version':1,'mode':'local_pinned_generation_plus_observation',
            'completion_limit':completion,'context_limit':context,'per_call_limit':4096,
            'tokenizers_version':importlib.metadata.version('tokenizers') if type(counter) is PinnedCounter else 'synthetic-counter-no-tokenizers',
            'tokenizer_sha256':TOKENIZER_SHA,'add_special_tokens':False,'padding':False,'truncation':False,
            'observation_serialization':'json sort_keys=True separators=comma:colon ensure_ascii=True allow_nan=False',
            'context_serialization':'canonical JSON message array; native message content uses json defaults ensure_ascii=True',
            'reset_counts_toward_completion':False,'terminal_observation_counts':True,
            'source_sha256':source_hashes(),'counter_type':type(counter).__module__+'.'+type(counter).__qualname__,
            'counter_source_sha256':hashlib.sha256(Path(inspect.getfile(type(counter))).read_bytes()).hexdigest(),
            'synthetic_counter':type(counter) is not PinnedCounter,'arena_wrapper_equivalent':False}


def validate_config(config):
    require(type(config) is dict and config.get('source_sha256')==source_hashes(),'accounting source manifest mismatch')
    require(config.get('version')==1 and config.get('tokenizer_sha256')==TOKENIZER_SHA,'unsupported accounting configuration')
    # Full structural/config comparison follows when a concrete counter is bound.
    canonical(config)


def bind_budget(budget,config):
    require(type(budget) is observation_budget.EpisodeBudget,'standard budget implementation required')
    require(make_config(budget.counter,completion=budget.completion,context=budget.context)==config,'factory/config mismatch')
    require(budget.generated==0 and budget.observed==0,'fresh budget required')


def _read(root,name):
    path=root/name
    require(not path.is_symlink() and path.is_file() and path.stat().st_size<=8*1024*1024,'bounded regular archive record required')
    def unique(pairs):
        value={}
        for key,item in pairs:
            require(key not in value,'duplicate archive key');value[key]=item
        return value
    return json.loads(path.read_text(),object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite archive value')))


def _envelope(root,name):
    value=_read(root,name)
    require(value['sha256']==digest(value['payload']),'archive checksum mismatch')
    return value


def recompute(root,seq,raw,schema,config,counter,ledger):
    """Independent arithmetic/history reconstruction, not EpisodeBudget methods."""
    history=messages(raw['reset_transport'],schema);initial=counter.context(history)
    generated=observed=0;context_used=initial;call_index=0;stopped=False
    c=config['completion_limit'];ctx=config['context_limit']
    for event in raw['events']:
        require(not stopped,'events after local stop')
        allowance=max(0,min(4096,c-generated-observed,ctx-counter.context(history)))
        if event['kind']=='budget':
            reason='generation' if generated+observed>c else 'context' if context_used>=ctx else 'generation'
            if allowance==0:require(event['reason']==reason,'incorrect exhausted-budget reason')
            stopped=True;continue
        require(allowance>0,'call after local budget exhausted')
        stem=f'{seq:02d}-{call_index:02d}';call_index+=1
        intent=_read(root,stem+'-intent.json')
        require(intent['accounting_sha256']==digest(config),'intent accounting identity mismatch')
        require(intent['request_sha256']==digest(history)==event['request_sha256'],'saved request/history mismatch')
        require(intent['label']==event['reservation_label'],'intent label mismatch')
        matches=[r for r in ledger if r['label']==intent['label']]
        require(len(matches)==1 and matches[0]==intent['reservation'],'intent/ledger mismatch')
        b=matches[0]
        require(type(b['prompt_bound']) is int and b['prompt_bound']>=counter.context(history) and type(b['generation_bound']) is int and 0<b['generation_bound']<=allowance and b['prompt_bound']+b['generation_bound']<=8192,'reservation outside recomputed allowance')
        provider=_envelope(root,stem+'-provider.json')['payload']
        require(provider=={k:v for k,v in event.items() if k not in ('native','native_error')},'provider/event mismatch')
        require(_envelope(root,stem+'-event.json')['payload']==event,'standalone event/episode mismatch')
        if event['status']=='returned':
            n=event['response']['usage']['completion_tokens']
            require(type(n) is int and n>=0,'invalid saved completion usage');generated+=n
        if 'response' in event:
            history.append({'role':'assistant','content':event['response']['content']})
            context_used=counter.context(history)
        if 'native' in event:
            history.append({'role':'user','content':json.dumps(event['native'],sort_keys=True,separators=(',',':'))})
            observed+=counter.count(canonical(event['native']));context_used=counter.context(history)
        overflow=generated+observed>c or context_used>ctx
        if overflow:
            # A nonterminal native overflow may be followed only by its budget marker.
            stopped=not ('native' in event and event['native'].get('done') is False)
    return {'generation_tokens':generated,'postreset_observation_tokens':observed,
            'completion_used':generated+observed,'context_used':context_used,'initial_context':initial,
            'completion_limit':c,'context_limit':ctx,
            'overflow_reason':'generation' if generated+observed>c else 'context' if context_used>ctx else None,
            'tokenizer_sha256':TOKENIZER_SHA,
            'serialization':'canonical JSON full native transport; canonical JSON message context',
            'arena_wrapper_equivalent':False}


def verify_archive(root,plan,schema,phase,expected_config,counter,ledger,replay):
    """Reaudit native semantics via supplied replay; recompute all local costs.

    replay must be a bounded trusted adapter or offline fixture. No provider
    invocation, ledger writes, receipt freshness change, resume or admission.
    expected_config is external trusted input, never learned from the archive.
    """
    from verified_phase import schedule
    root=Path(root);validate_config(expected_config)
    require(make_config(counter,completion=expected_config['completion_limit'],context=expected_config['context_limit'])==expected_config,'verifier counter/config mismatch')
    require(_read(root,'accounting.json')==expected_config,'saved accounting configuration mismatch')
    claim=_read(root,'claim.json');jobs=schedule(plan,phase)
    require(claim['phase']==phase and claim['plan_sha256']==digest(plan) and claim['jobs']==[list(j) for j in jobs] and claim['accounting_sha256']==digest(expected_config),'frozen archive claim mismatch')
    require(len(list(root.glob('*-episode.json')))==16,'complete16 records required')
    rows=[]
    for seq,(task,seed,sample) in enumerate(jobs):
        obj=_envelope(root,f'{seq:02d}-episode.json');raw=obj['payload']
        require((raw['task_id'],raw['seed'],raw['sample'],raw['phase'])==(task,seed,sample,phase),'episode schedule mismatch')
        require(raw['accounting_sha256']==digest(expected_config),'episode accounting mismatch')
        reset=copy.deepcopy(raw);reset['events']=[]
        require(_read(root,f'{seq:02d}-reset.json')==reset,'reset/episode mismatch')
        costs=recompute(root,seq,raw,schema,expected_config,counter,ledger)
        row=audit_episode(raw,plan,schema,ledger,replay);row['local_accounting']=costs
        if costs['overflow_reason']:
            row.update(native_audit_category=row['category'],category='budget',detail='local_generation_observation_or_context_overflow',semantic_reward=None)
        require(row==obj['validated'],'recomputed accounting or audit differs from saved row')
        rows.append(row)
    expected={**assess_phase(rows,plan,phase),'complete':True,'is_training':False,'promotion':False}
    require(_read(root,'complete.json')==expected,'recomputed phase report mismatch')
    return {'report':expected,'accounting_sha256':digest(expected_config),'episodes_recomputed':16,'arena_wrapper_equivalent':False,'execution_authorized':False}

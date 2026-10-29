"""Pinned local generation+observation accounting; not production-wrapper parity."""
import hashlib
import json
from pathlib import Path

TOKENIZER_SHA='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


class PinnedCounter:
    def __init__(self,path):
        p=Path(path)
        if p.is_symlink() or not p.is_file() or p.stat().st_size>128*1024*1024:raise ValueError('bounded regular local tokenizer required')
        raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=TOKENIZER_SHA:raise ValueError('frozen tokenizer mismatch')
        from tokenizers import Tokenizer
        self.tokenizer=Tokenizer.from_str(raw.decode());self.tokenizer.no_truncation();self.tokenizer.no_padding()
        self.mode='pinned_tokenizer';self.sha256=TOKENIZER_SHA
    def count(self,text):return len(self.tokenizer.encode(text,add_special_tokens=False).ids)
    def context(self,messages):return self.count(canonical(messages))


class EpisodeBudget:
    def __init__(self,counter,initial_messages,*,completion=4096,context=8192):
        if type(completion) is not int or type(context) is not int or not 1<=completion<=context<=32768:raise ValueError('bounded local capacities required')
        if counter.mode!='pinned_tokenizer' or counter.sha256!=TOKENIZER_SHA:raise ValueError('pinned counting method required')
        self.counter=counter;self.completion=completion;self.context=context;self.generated=0;self.observed=0
        self.initial_context=counter.context(initial_messages);self.context_used=self.initial_context
    def allowance(self,messages):
        self.context_used=self.counter.context(messages)
        return max(0,min(4096,self.completion-self.generated-self.observed,self.context-self.context_used))
    def reply(self,completion_tokens):
        if type(completion_tokens) is not int or completion_tokens<0:raise ValueError('verified provider generation count required')
        self.generated+=completion_tokens
    def observation(self,transport,messages):
        # The reset is never passed here: it affects context, not completion.
        self.observed+=self.counter.count(canonical(transport));self.context_used=self.counter.context(messages)
    def snapshot(self):
        reason=('generation' if self.generated+self.observed>self.completion else 'context' if self.context_used>self.context else None)
        return {'generation_tokens':self.generated,'postreset_observation_tokens':self.observed,
                'completion_used':self.generated+self.observed,'context_used':self.context_used,
                'initial_context':self.initial_context,'completion_limit':self.completion,'context_limit':self.context,
                'overflow_reason':reason,'tokenizer_sha256':self.counter.sha256,
                'serialization':'canonical JSON full native transport; canonical JSON message context',
                'arena_wrapper_equivalent':False}
    def project(self,row):
        result=dict(row);result['local_accounting']=self.snapshot()
        if result['local_accounting']['overflow_reason']:
            result.update(native_audit_category=row['category'],category='budget',detail='local_generation_observation_or_context_overflow',semantic_reward=None)
        return result

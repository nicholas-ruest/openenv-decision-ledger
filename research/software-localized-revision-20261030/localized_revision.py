"""Literal revision actions with the same full-module fallback in both arms."""
from typing import List
from pydantic import Field, ConfigDict
from openenv.core.env_server.types import Action
from mandatory_environment import RequiredReviewEnvironment, ProposalAction as ContentAction
from repair_env.tasks import SOURCE_PATH
import json

class Replacement(Action):
    model_config=ConfigDict(extra='forbid')
    before:str=Field(min_length=1,max_length=8192)
    after:str=Field(max_length=8192)

class ProposalAction(Action):
    model_config=ConfigDict(extra='forbid')
    content:str=Field(default='',max_length=8192)
    replacements:List[Replacement]=Field(default_factory=list,max_length=4)

def apply_replacements(source,replacements):
    """Validate the entire sequential transaction before returning a module."""
    value=source
    for replacement in replacements:
        if value.count(replacement.before)!=1:
            raise ValueError('each before text must occur exactly once in the current module')
        value=value.replace(replacement.before,replacement.after,1)
        if len(value)>8192:
            raise ValueError('complete module length exceeds 8192')
    return value

class LocalizedReviewEnvironment(RequiredReviewEnvironment):
    def __init__(self,*,arm):
        if arm not in ('full_module','local_patch'):raise ValueError('explicit arm required')
        self.preference=arm
        super().__init__(arm='field_contract')
    def reset(self,*args,**kwargs):
        obs=super().reset(*args,**kwargs)
        text=obs.prompt.replace('The action contains only content; there is no early-submit command.',
            'Both responses accept content or replacements, never both. The first response must supply a complete module in content. On the second response you may provide a complete module in content, or up to four literal replacements with before and after strings. Each before string must occur exactly once in the current proposed module. Replacements are validated sequentially and applied atomically; empty content and no replacements retain the proposal. There is no early-submit command.')
        return obs.model_copy(update={'prompt':text})
    def step(self,action:ProposalAction,**kwargs):
        if action.content and action.replacements:raise ValueError('choose one representation')
        if self._steps==0 and action.replacements:raise ValueError('first proposal requires complete content')
        content=action.content
        if action.replacements:
            content=apply_replacements(self._direct._files[SOURCE_PATH],action.replacements)
        obs=super().step(ContentAction(content=content),**kwargs)
        if not obs.done:
            review=json.loads(obs.feedback)
            review['revision_advice']=(
                'Prefer literal replacements for the identified defects so unrelated working code is retained. A complete module remains accepted.'
                if self.preference=='local_patch' else
                'Prefer a complete revised module for the identified defects. Literal replacements remain accepted.')
            obs=obs.model_copy(update={'feedback':json.dumps(review,sort_keys=True,separators=(',',':'))})
        return obs

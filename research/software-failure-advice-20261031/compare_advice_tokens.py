"""Reproducible fixed-note token comparison on existing qualification case only."""
import argparse
import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

import failure_protocol as p
import failure_advice as advice

PREVIOUS_SOURCE='3ecd31f88fdfb055dcbf041c515da8702eef5adb'
NOTE_PATH='research/software-failure-advice-20261031/failure_advice.py'
TOKENIZER_SHA='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'


def previous_note():
    source=subprocess.check_output(['git','-C',str(p.ROOT),'show',PREVIOUS_SOURCE+':'+NOTE_PATH],text=True)
    tree=ast.parse(source)
    return ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='NOTE' for t in n.targets)))


def compare(counter):
    old=previous_note();new=advice.NOTE
    first=p.QualificationTrial(p.jobs('qualification')[1]);second=p.QualificationTrial(p.jobs('qualification')[1])
    assert first.messages==second.messages
    text=json.dumps(dict(content=json.loads(first.messages[1]['content'])['source']))
    with patch.object(advice,'NOTE',old):before=first.consume(text,finish_reason='stop')
    after=second.consume(text,finish_reason='stop')
    assert before['advice_delivered'] and after['advice_delivered']
    assert before['new_observations']==after['new_observations']
    assert first.messages[:-1]==second.messages[:-1]
    old_receipt=before['advice_observations'][0];new_receipt=after['advice_observations'][0]
    assert {k:v for k,v in old_receipt.items() if k!='advice'}=={k:v for k,v in new_receipt.items() if k!='advice'}
    original=counter.count(first.messages[-1]['content']);compact=counter.count(second.messages[-1]['content'])
    assert compact<original
    native=sum(counter.count(p.canonical(x)) for x in after['new_observations'])
    assert advice.observation_tokens(before,counter.count)==native+original
    assert advice.observation_tokens(after,counter.count)==native+compact
    return dict(kind='fixed_advice_token_cost_control',previous_public_source=PREVIOUS_SOURCE,
        tokenizer_sha256=TOKENIZER_SHA,old_receipt_tokens=original,new_receipt_tokens=compact,
        saved_tokens=original-compact,reduction_fraction=(original-compact)/original,
        first_prompts_identical=True,native_review_identical=True,only_note_text_changed=True,
        cases_already_used=True,new_cases=0,model_calls=0,hidden_terminal_grades_requested=False,
        model_improvement=False,leaderboard_gain=False)


def load_counter(tokenizer):
    spec=importlib.util.spec_from_file_location('advice_compaction_counter',p.ROOT/'integrations/openenv-arena/scripts/calibrate.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path(tokenizer),tokenizer_sha256=TOKENIZER_SHA))


if __name__=='__main__':
    parser=argparse.ArgumentParser(allow_abbrev=False);parser.add_argument('--tokenizer',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=compare(load_counter(args.tokenizer))
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))

"""Replay saved modules as analysis controls; not new provider responses or a matched model trial."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/software-matched-inputs-20261028'))
from matched_inputs import Trial

ARCHIVE_SHA='721ae7c85adf1ac6a4868c2edc5847b51af04f4f651101ceac3a495c2a5a8793'

def replay(archive,output):
    raw=archive.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ARCHIVE_SHA:raise ValueError('original saved archive hash mismatch')
    rows=[json.loads(s) for s in raw.splitlines()];partials=[r for r in rows if 0<r['reward']<1]
    if len(rows)!=16 or len(partials)!=4:raise ValueError('frozen legacy diagnosis archive required')
    output.mkdir(exist_ok=False);controls=[]
    for row in partials:
        action=json.loads(next(m['content'] for m in row['messages'] if m['role']=='assistant'))
        if set(action)=={'action'}:action=action['action']
        # Preserve saved MODULE bytes, but explicitly reconstruct revision actions.
        # Original replies came from one-shot prompts and are not current trial data.
        for arm in ('review_control','public_check'):
            t=Trial(dict(task_id=row['task_id'],seed=row['seed'],arm=arm))
            t.consume(json.dumps(dict(content=action['content'],submit=False)))
            final=t.consume('{"submit":true}')
            if abs(final['native_reward']-row['reward'])>1e-9:raise ValueError('legacy native grade changed')
            if final['category']!='partial':raise ValueError('valid partial misclassified')
            controls.append(dict(task_id=row['task_id'],seed=row['seed'],sample=row['sample'],arm=arm,**final))
    result=dict(saved_responses=4,replayed_native_controls=len(controls),categories=dict(Counter(r['category'] for r in controls)),
                original_native_grades_preserved=True,new_model_calls=0,matched_model_trial=False,
                confirmation=False,archive_sha256=ARCHIVE_SHA)
    (output/'private-controls.json').write_text(json.dumps(controls,indent=2)+'\n')
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();replay(a.archive,a.output)

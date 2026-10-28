"""Bounded native WebSocket token diagnostic. Scripted actions, no model/provider driver."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / p) for p in (
    'research/software-revision-candidate-20261028', 'research/software-public-check-20261028',
    'research/media-observation-accounting-20261028', 'integrations/software-repair')]
from observation_budget import PinnedCounter, canonical

REQUEST_SHA = '2cf57b603a61d1d9cbca39995123c13a62e5306fcdadbee3395eabbfac8b0ae7'


def costs(counter, reset, actions, observations):
    if len(actions) != 2 or len(observations) != 2:
        raise ValueError('complete two-response trajectory required')
    if reset['data']['done'] or observations[0]['data']['done'] or not observations[-1]['data']['done']:
        raise ValueError('native reset/intermediate/terminal sequence required')
    # Full native frames include transport overhead; also expose data-only counts.
    # Model outputs are reconstructed action JSON, not provider usage measurements.
    generated = [counter.count(canonical(a)) for a in actions]
    observed = [counter.count(canonical(o)) for o in observations]
    data_only = [counter.count(canonical(o['data'])) for o in observations]
    messages = [{'role':'user','content':canonical(reset)}]
    contexts = [counter.context(messages)]
    for a, o in zip(actions, observations):
        messages += [{'role':'assistant','content':canonical(a)}, {'role':'user','content':canonical(o)}]
        contexts.append(counter.context(messages))
    return dict(action_tokens=generated, postreset_frame_tokens=observed,
                postreset_data_tokens=data_only, completion_total=sum(generated + observed),
                context_counts=contexts, context_max=max(contexts),
                final_observation_tokens=observed[-1], reset_completion_tokens=0)


def audit(tokenizer, output):
    from fastapi.testclient import TestClient
    from revision_app import app
    from revision_environment import TASKS
    from repair_env.tasks import make_task
    output.mkdir(exist_ok=False)
    req = (ROOT / 'config/software-feedback-v14-review-20261028.json').read_bytes()
    if hashlib.sha256(req).hexdigest() != REQUEST_SHA:
        raise ValueError('frozen request drift')
    counter = PinnedCounter(tokenizer)
    rows = []
    with (output / 'native-trajectories.jsonl').open('x') as raw:
        for task in TASKS:
            for seed in [*range(2360000,2360016), *range(2361000,2361004), *range(2362000,2362004)]:
                for path in ('wrong_then_reference','reference_then_keep'):
                    with TestClient(app) as client, client.websocket_connect('/ws') as ws:
                        def exchange(kind, data):
                            ws.send_json({'type':kind,'data':data})
                            frame = ws.receive_json()
                            if frame.get('type') != 'observation':
                                raise ValueError('native observation frame required')
                            return frame
                        reset = exchange('reset',dict(task_id=task, seed=seed))
                        ref = make_task(task,seed).reference_source
                        a1 = dict(content=reset['data']['observation']['source'] if path=='wrong_then_reference' else ref, submit=False)
                        a2 = dict(content=ref if path=='wrong_then_reference' else '', submit=True)
                        first = exchange('step',a1); final = exchange('step',a2)
                        if first['data']['reward'] != 0 or final['data']['reward'] != 1:
                            raise ValueError('scripted native grade control failed')
                        row = dict(task_id=task,seed=seed,path=path,**costs(counter,reset,[a1,a2],[first,final]))
                        rows.append(row)
                        raw.write(canonical(dict(identity=[task,seed,path],reset=reset,actions=[a1,a2],observations=[first,final]))+'\n')
    result = dict(scripted_native_trajectories=len(rows),public_cases=48,rows=rows,
                  tokenizer_sha256=counter.sha256, new_model_calls=0,
                  production_wrapper_equivalent=False, model_improvement=False,
                  max_completion=max(r['completion_total'] for r in rows),
                  max_context=max(r['context_max'] for r in rows),
                  max_final_observation=max(r['final_observation_tokens'] for r in rows),
                  exceeding_4096=sum(r['completion_total']>4096 for r in rows),
                  exceeding_8192=sum(r['completion_total']>8192 for r in rows),
                  exceeding_context_8192=sum(r['context_max']>8192 for r in rows),
                  exceeding_context_24576=sum(r['context_max']>24576 for r in rows),
                  native_archive_sha256=hashlib.sha256((output/'native-trajectories.jsonl').read_bytes()).hexdigest(),
                  limits='Scripted reference actions, canonical JSON full-frame counts; reconstructed message context omits unattested production system/schema/chat-template and model thinking. Not an upper bound for model trajectories, budget parity, training or provider billing.')
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tokenizer',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();audit(a.tokenizer,a.output)

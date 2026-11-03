"""Offline source-runtime probe on one already-seen case; no provider or credentials."""
import argparse,hashlib,importlib.util,json,subprocess,sys,time
from pathlib import Path

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    parser=argparse.ArgumentParser(allow_abbrev=False);parser.add_argument('--root',type=Path,required=True);parser.add_argument('--mode',choices=['direct','revision_v14','domain_cue'],required=True);parser.add_argument('--output',type=Path);args=parser.parse_args();root=args.root.resolve()
    sys.path.insert(0,str(root/'integrations/software-repair'))
    from repair_env.direct_environment import DirectRepairEnvironment,DirectRepairAction
    started=time.monotonic();schema=DirectRepairAction.model_json_schema();metadata={}
    if args.mode=='direct':env=DirectRepairEnvironment();action=DirectRepairAction(content='import os')
    elif args.mode=='revision_v14':
        sys.path.insert(0,str(root/'research/software-public-check-20261028'))
        module=load('audited_revision_candidate',root/'research/software-revision-candidate-20261028/revision_environment.py');schema=module.RevisionAction.model_json_schema();env=module.RevisionEnvironment(arm='review_control');action=module.RevisionAction(content='import os',submit=True);metadata['early_submit_requested']=True
    else:
        module=load('audited_domain_cue',root/'research/software-final-domain-cue-20261101/revision_environment.py');env=module.RevisionEnvironment(arm='final_domain_reminder');action=DirectRepairAction(content='import os')
    initial=env.reset(seed=2560000,task_id='software_repair-ignore-d3');first=env.step(action)
    metadata.update(first_done=first.done,first_reward=first.reward,first_stage=getattr(first,'stage',None),first_has_review=bool(getattr(first,'feedback','')),action_properties=sorted(schema['properties']),reset_observation_properties=sorted(initial.model_dump()))
    if args.mode=='domain_cue':
        feedback=json.loads(first.feedback);metadata['review_keys']=sorted(feedback);metadata['reminder_exposed']=feedback.get('final_output_domain_reminder')==module.REMINDER
        final=env.step(DirectRepairAction(content=''));metadata.update(second_done=final.done,second_reward=final.reward,second_stage=final.stage)
        assert first.done is False and first.reward==0 and final.done is True and final.reward==0 and metadata['reminder_exposed']
    else:assert first.done is True and first.reward==0
    paths=['integrations/software-repair/repair_env/'+n for n in ('direct_app.py','direct_environment.py','environment.py','runner.py','tasks.py','ignore_repair.py')]
    out=dict(kind='offline_runtime_applicability_probe',mode=args.mode,source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),task_id='software_repair-ignore-d3',already_seen_seed=2560000,synthetic_action='compile-rejected import; empty retention only',runtime_file_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},observed=metadata,elapsed_seconds=time.monotonic()-started,container_executed=False,native_interpreter_executed=True,model_calls=0,new_cases=0,is_training=False,model_improvement=False)
    if args.output:
        with args.output.open('x') as f:json.dump(out,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(out,sort_keys=True))
if __name__=='__main__':main()

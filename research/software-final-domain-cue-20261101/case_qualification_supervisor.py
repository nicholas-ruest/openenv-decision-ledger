"""Scripted qualification of case-bound components under the original supervisor.

No real backend, credential access, live entry point or spending admission.
"""
import argparse,importlib.util,json,math,os,sys,threading,time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from types import SimpleNamespace
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('bound_original_supervision_support',HERE/'qualification_supervisor.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)


def components():
    import case_caller as c
    if Path(c.__file__).resolve()!=HERE/'case_caller.py':raise ValueError('exact case caller required')
    return c


def worker_entry(deadline,output,expected,tokenizer,parent_pid):
    support.require_source(expected);support.require_fresh_parent()
    import case_worker as w
    if Path(w.__file__).resolve()!=HERE/'case_worker.py':raise ValueError('exact worker entry required')
    c=w.components();holder={}
    args=SimpleNamespace(expected_source=expected,output=output,phase='screen',tokenizer=tokenizer)
    def scripted_factory(original_args):
        if original_args is not args:raise ValueError('original worker arguments changed')
        os.environ['HELPER_TEST_TOKENIZER']=str(tokenizer)
        from test_case_caller import Original
        from test_case_replay import BoundReplayTests as fixture
        holder['fixture']=fixture;fixture.setUpClass()
        class ObservedOriginal(Original):
            def __init__(self):
                super().__init__(fixture);self.lock=threading.Lock()
                self.inflight=self.reserving=self.max_inflight=self.max_reserving=0
            def reserve(self,*items):
                with self.lock:self.reserving+=1;self.max_reserving=max(self.max_reserving,self.reserving)
                try:return super().reserve(*items)
                finally:
                    with self.lock:self.reserving-=1
            def call(self,*items):
                with self.lock:self.inflight+=1;self.max_inflight=max(self.max_inflight,self.inflight)
                try:return super().call(*items)
                finally:
                    with self.lock:self.inflight-=1
        original=ObservedOriginal();holder['original']=original
        return c.transport._AtomicOriginal(original,dict(fixture.verdict,independently_regenerated=True))
    try:
        # Qualification replaces only authorization/constructor boundaries with inert fixtures.
        # The exact prepared worker performs startup, phase execution and artifact writes.
        with patch.object(w,'require_worker',return_value={'qualification_only':True}),patch.object(c.transport,'prepare',side_effect=scripted_factory),patch.object(c.transport.bridge,'preflight_complete_plan',return_value={'synthetic_only':True}):
            status=w.worker_entry(deadline,args,parent_pid)
        summary=json.loads((output/'complete.json').read_text());original=holder['original']
        binding_summary=dict(scripted=True,live_evidence=False,assigned=summary['assigned'],recorded=summary['recorded'],calls=summary['observed_calls'],unknown_usage_calls=summary['unknown_usage_calls'],complete=summary['complete'])
        support.write(output/'qualification-summary.json',binding_summary)
        support.write(output/'qualification-worker-binding.json',dict(worker_pid=os.getpid(),parent_pid=os.getppid(),deadline=deadline,finished_at=time.monotonic(),source=expected,archive=str(output.resolve()),mode='scripted_qualification',counter_initialized_in_worker=True,max_inflight=original.max_inflight,max_reserving=original.max_reserving))
        return status
    finally:
        if 'fixture' in holder:holder['fixture'].doClassCleanups()


def assess(output,expected,tokenizer):
    support.require_source(expected)
    read=lambda p:json.loads(p.read_text()) if p.exists() else {}
    events=[json.loads(x) for x in output.with_suffix('.supervision.jsonl').read_text().splitlines()]
    binding=read(output/'qualification-worker-binding.json');startup=read(output.with_suffix('.worker-startup.json'))
    raw_binding=read(output/'worker-binding.json')
    if (startup.get('mode')!='guarded_original_backend_worker' or raw_binding.get('mode')!='guarded_original_backend_worker'
        or raw_binding.get('worker_pid')!=binding.get('worker_pid') or raw_binding.get('parent_pid')!=binding.get('parent_pid')
        or raw_binding.get('source')!=expected or raw_binding.get('deadline')!=binding.get('deadline')
        or raw_binding.get('archive')!=str(output.resolve()) or raw_binding.get('phase_complete') is not True
        or raw_binding.get('counter_initialized_in_worker') is not True
        or raw_binding.get('selection_passed') is not False or raw_binding.get('model_improvement') is not False):
        return dict(complete=False,scripted_supervisor_binding_verified=False,execution_authorized=False,live_worker_binding_qualified=False,model_improvement=False,new_cases=0,new_model_calls=0)
    # Adapt only the fixed mode name for the unchanged scripted binding validator.
    startup=dict(startup,mode='scripted_qualification')
    launch=read(output.with_suffix('.launch.json'));summary=read(output/'qualification-summary.json')
    if not support.binding_valid(events,binding,startup,launch,summary,expected,output):
        return dict(complete=False,scripted_supervisor_binding_verified=False,execution_authorized=False,
            live_worker_binding_qualified=False,model_improvement=False,new_cases=0,new_model_calls=0)
    c=components();jobs=c.gate.jobs_for(dict(task_id='software_repair-ignore-d3',new_seed=2560000))
    verdict=dict(jobs=jobs,case_audit_sha256='a'*64)
    counter=support.counter(None,tokenizer)
    with patch.object(c.gate,'require_case',return_value=verdict):
        report=c.archive.assemble(output,counter,SimpleNamespace(expected_source=expected))
    if report!=read(output/'phase-evidence.json'):raise ValueError('independent parent replay differs')
    if not report['all_terminal_attempts_reconstructed']:raise ValueError('all assigned raw Native outcomes required')
    return dict(complete=True,scripted_supervisor_binding_verified=True,
        original_worker_entry_exercised=True,worker_qualification_gate_mocked=True,
        assigned=8,synthetic_calls=summary['calls'],max_inflight=binding['max_inflight'],
        max_reserving=binding['max_reserving'],independent_parent_raw_replay_verified=True,
        native_and_tokenizer_initialized_in_worker=True,private_case_gate_mocked=True,
        whole_plan_preflight_mocked=True,actual_private_inventory_verified=False,
        actual_backend_constructed=False,live_evidence=False,live_worker_binding_qualified=False,
        execution_authorized=False,selection_passed=False,model_improvement=False,
        actual_metaharness_executed=False,new_cases=0,new_model_calls=0)


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--qualify',action='store_true');parser.add_argument('--source',required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--tokenizer',type=Path,required=True)
    parser.add_argument('--seconds',type=float,default=1200);args=parser.parse_args()
    if not args.qualify:raise ValueError('explicit scripted qualification only')
    support.require_source(args.source);state=support.require_fresh_parent()
    now=datetime.now(ZoneInfo('America/Toronto'));remaining=(now.replace(hour=23,minute=0,second=0,microsecond=0)-now).total_seconds()
    if not math.isfinite(args.seconds) or not 0<args.seconds<=1200 or remaining<=0:raise ValueError('original operating window required')
    for path in (args.output,args.output.with_suffix('.supervision.jsonl'),args.output.with_suffix('.launch.json'),args.output.with_suffix('.worker-startup.json'),args.output.with_suffix('.assessment.json'),args.output.with_suffix('.worker-qualification.json')):
        if path.exists():raise ValueError('fresh qualification archive required')
    support.write(args.output.with_suffix('.launch.json'),dict(parent_pid=os.getpid(),parent_state=state,source=args.source,archive=str(args.output.resolve())))
    result=support.supervisor().run_bounded(worker_entry,(args.output,args.source,args.tokenizer,os.getpid()),min(args.seconds,remaining),args.output.with_suffix('.supervision.jsonl'))
    value=assess(args.output,args.source,args.tokenizer)
    support.write(args.output.with_suffix('.assessment.json'),value)
    if value['complete']:
        c=components()
        receipt=dict(kind='case_bound_original_worker_qualification',method_sha256=c.gate.method_hashes(),original_supervisor_sha256=support.PIN,scripted_supervisor_binding_verified=True,independent_parent_raw_replay_verified=True,native_and_tokenizer_initialized_after_fork=True,actual_backend_constructed=False,synthetic_provider_only=True,assigned=8,synthetic_calls=value['synthetic_calls'],unknown_usage_calls=0,max_inflight=value['max_inflight'],max_reserving=value['max_reserving'],qualified_source=args.source,execution_authorized=False,model_improvement=False)
        support.write(args.output.with_suffix('.worker-qualification.json'),receipt)
    print(json.dumps(dict(supervisor=result,assessment=value)))
    if not value['complete']:raise SystemExit(1)

if __name__=='__main__':main()

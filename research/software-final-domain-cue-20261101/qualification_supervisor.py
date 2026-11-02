"""Fresh-parent scripted Native qualification. No live backend or case factory."""
import argparse
from datetime import datetime
import hashlib,importlib.util,json,math,os,re,subprocess,sys,threading,time
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[2]
PIN='08950e6ff362572f34c4fa2397de80c97dbf15d0380c04c5398be12e6abc9977'
TOKENIZER_SHA='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'

def write(path,value):
    with Path(path).open('x') as f:
        json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())

def parent_state():
    modules=sorted(n for n in sys.modules if n.split('.')[0] in {'tokenizers','repair_env','openenv','matched_protocol','finite_caller'})
    return dict(native_modules=modules,python_threads=threading.active_count(),os_threads=len(list(Path('/proc/self/task').iterdir())))

def require_fresh_parent():
    value=parent_state()
    if value['native_modules'] or value['python_threads']!=1 or value['os_threads']!=1:raise ValueError('fresh single-threaded parent required before supervision')
    return value

def require_source(expected):
    if not isinstance(expected,str) or not re.fullmatch('[a-f0-9]{40}',expected):raise ValueError('exact source required')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=expected or subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('exact clean immutable source required')

def supervisor():
    path=ROOT/'integrations/software-repair/scripts/screen_deadline.py'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=PIN:raise ValueError('original supervisor changed')
    spec=importlib.util.spec_from_file_location('domain_original_supervisor',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def candidate():
    sys.path.insert(0,str(Path(__file__).parent))
    import finite_caller as c
    if Path(c.__file__).resolve()!=Path(__file__).with_name('finite_caller.py'):raise ValueError('exact candidate caller required')
    return c

def counter(c,tokenizer):
    from types import SimpleNamespace
    sys.path.insert(0,str(ROOT/'integrations/openenv-arena'))
    path=ROOT/'integrations/openenv-arena/scripts/calibrate.py'
    spec=importlib.util.spec_from_file_location('domain_worker_counter',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m.load_counter(SimpleNamespace(accounting='arena',tokenizer_json=tokenizer,tokenizer_sha256=TOKENIZER_SHA))

def worker_entry(deadline,output,expected,tokenizer,parent_pid):
    require_source(expected);startup=require_fresh_parent()
    if os.getppid()!=parent_pid:raise ValueError('original parent changed')
    startup.update(worker_pid=os.getpid(),parent_pid=os.getppid(),deadline=deadline,source=expected,mode='scripted_qualification')
    write(output.with_suffix('.worker-startup.json'),startup)
    c=candidate()
    # Scripted fixtures are constructed only after the original supervisor fork.
    os.environ['HELPER_TEST_TOKENIZER']=str(tokenizer)
    spec=importlib.util.spec_from_file_location('domain_scripted_fixtures',Path(__file__).with_name('test_finite.py'))
    fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
    fixtures.FiniteTests.setUpClass()
    original=fixtures.Backend(fixtures.FiniteTests.counter,fixtures.FiniteTests.responses)
    _,summary=c.run(fixtures.b.AtomicDelegation(original),original.counter,output,deadline)
    report=c.assemble(output,original.counter)
    c.write(output/'phase-evidence.json',report)
    c.write(output/'worker-binding.json',dict(worker_pid=os.getpid(),parent_pid=os.getppid(),deadline=deadline,finished_at=time.monotonic(),source=expected,archive=str(output.resolve()),mode='scripted_qualification',counter_initialized_in_worker=True,max_inflight=original.max_inflight,max_reserving=original.max_reserving))
    return 0 if summary['complete'] and report['complete'] and time.monotonic()<deadline else 1

def binding_valid(events,binding,startup,launch,summary,expected,output):
    starts=[e for e in events if e.get('event')=='starting'];started=[e for e in events if e.get('event')=='started'];terminal=events[-1] if events else {}
    if len(starts)!=1 or len(started)!=1:return False
    deadline=binding.get('deadline');finished=binding.get('finished_at')
    pid=started[0].get('pid');parent=launch.get('parent_pid')
    return (type(pid) is int and type(parent) is int and pid>0 and parent>0
        and starts[0].get('target')=='worker_entry' and 0<starts[0].get('wall_seconds',0)<=1200
        and terminal.get('event')=='terminal' and terminal.get('status')=='completed' and terminal.get('worker_exitcode')==0
        and terminal.get('shutdown_verified') is True and terminal.get('finished_before_deadline') is True
        and terminal.get('pid')==binding.get('worker_pid')==startup.get('worker_pid')==pid
        and binding.get('parent_pid')==startup.get('parent_pid')==parent
        and binding.get('source')==startup.get('source')==launch.get('source')==expected
        and binding.get('mode')==startup.get('mode')=='scripted_qualification'
        and binding.get('archive')==launch.get('archive')==str(Path(output).resolve())
        and type(deadline) in (int,float) and math.isfinite(deadline) and startup.get('deadline')==deadline
        and type(finished) in (int,float) and math.isfinite(finished) and finished<=deadline
        and binding.get('counter_initialized_in_worker') is True and type(binding.get('max_inflight')) is int and 0<binding['max_inflight']<=2 and type(binding.get('max_reserving')) is int and binding['max_reserving']==1
        and startup.get('native_modules')==[] and startup.get('python_threads')==startup.get('os_threads')==1
        and launch.get('parent_state')==dict(native_modules=[],python_threads=1,os_threads=1)
        and summary.get('scripted') is True and summary.get('live_evidence') is False and summary.get('complete') is True
        and summary.get('assigned')==summary.get('recorded')==8 and 8<=summary.get('calls',0)<=16 and summary.get('unknown_usage_calls')==0)

def assess(output,expected,tokenizer):
    require_source(expected)
    events=[json.loads(x) for x in output.with_suffix('.supervision.jsonl').read_text().splitlines() if x]
    def read(path):return json.loads(path.read_text()) if path.exists() else {}
    binding=read(output/'worker-binding.json');startup=read(output.with_suffix('.worker-startup.json'));launch=read(output.with_suffix('.launch.json'));summary=read(output/'complete.json')
    if not binding_valid(events,binding,startup,launch,summary,expected,output):return dict(complete=False,supervisor_binding_verified=False,scripted=True,live_evidence=False,selection_passed=False,model_improvement=False)
    c=candidate();report=c.assemble(output,counter(c,tokenizer))
    if not report['complete']:raise ValueError('complete original raw Native replay required')
    module=Path(__file__).with_name('assess_qualification.mjs').as_uri()
    js="import {readFileSync} from 'node:fs';import {assess} from "+json.dumps(module)+";console.log(JSON.stringify(assess(JSON.parse(readFileSync(0,'utf8')))));"
    fitness=json.loads(subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(report['evidence']),text=True,capture_output=True,check=True).stdout)
    return dict(complete=True,supervisor_binding_verified=True,scripted=True,live_evidence=False,qualification_fitness=fitness,actual_model_requests=0,new_cases=0,selection_passed=False,model_improvement=False,remote_cancellation_attested=False)

def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--qualify',action='store_true');parser.add_argument('--output',type=Path,required=True);parser.add_argument('--source',required=True);parser.add_argument('--tokenizer',type=Path,required=True);parser.add_argument('--seconds',type=float,default=1200)
    args=parser.parse_args()
    if not args.qualify:raise ValueError('explicit scripted qualification only')
    require_source(args.source);state=require_fresh_parent()
    now=datetime.now(ZoneInfo('America/Toronto'));remaining=(now.replace(hour=23,minute=0,second=0,microsecond=0)-now).total_seconds()
    if not math.isfinite(args.seconds) or not 0<args.seconds<=1200 or remaining<=0:raise ValueError('original time limits required')
    for path in (args.output,args.output.with_suffix('.supervision.jsonl'),args.output.with_suffix('.launch.json'),args.output.with_suffix('.worker-startup.json'),args.output.with_suffix('.assessment.json')):
        if path.exists():raise ValueError('fresh qualification archive required')
    write(args.output.with_suffix('.launch.json'),dict(parent_pid=os.getpid(),parent_state=state,source=args.source,archive=str(args.output.resolve())))
    result=supervisor().run_bounded(worker_entry,(args.output,args.source,args.tokenizer,os.getpid()),min(args.seconds,remaining),args.output.with_suffix('.supervision.jsonl'))
    value=assess(args.output,args.source,args.tokenizer)
    write(args.output.with_suffix('.assessment.json'),value)
    print(json.dumps(dict(supervisor=result,assessment=value)))
    if not value['complete']:raise SystemExit(1)

if __name__=='__main__':main()

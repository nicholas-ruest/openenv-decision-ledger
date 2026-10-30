"""One-response shared-program compatibility screen; no paid authority."""
import copy,hashlib,importlib,importlib.util,json,shutil,sys,tempfile
from pathlib import Path
from pydantic import ValidationError
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integrations/software-repair'))
from repair_env.direct_environment import DirectRepairEnvironment,DirectRepairAction
import repair_env.runner as baseline_runner
import repair_env.environment as baseline_core
from repair_env.tasks import SOURCE_PATH
BASELINE_SHA='be2672ea479dc2520af5366b3cad6741e0195497cc6fdea1198232ab40a4e4a8'
CANDIDATE_SHA='fcb0f8b5cb5321ae998f71a38502125a595cc39d6b6331eedd659ba9ceed65a6'
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x):return hashlib.sha256(canonical(x).encode()).hexdigest()
def file_sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def candidate():
 global _temporary
 name='sorted_bool_candidate_native'
 if name in sys.modules:return importlib.import_module(name+'.direct_environment')
 base=ROOT/'integrations/software-repair/repair_env'
 assert Path(baseline_runner.__file__).resolve()==base/'runner.py' and file_sha(base/'runner.py')==BASELINE_SHA
 _temporary=tempfile.TemporaryDirectory(prefix='sorted-bool-native-');path=Path(_temporary.name)/name;path.mkdir()
 for source in base.glob('*.py'):shutil.copyfile(source,path/source.name)
 data=Path(__file__).with_name('candidate_runner.py').read_bytes();assert hashlib.sha256(data).hexdigest()==CANDIDATE_SHA
 (path/'runner.py').write_bytes(data)
 assert {p.name for p in path.glob('*.py')}=={p.name for p in base.glob('*.py')}
 assert [p.name for p in base.glob('*.py') if p.read_bytes()!=(path/p.name).read_bytes()]==['runner.py']
 spec=importlib.util.spec_from_file_location(name,path/'__init__.py',submodule_search_locations=[str(path)])
 module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
 return importlib.import_module(name+'.direct_environment')
def classify(env,obs,source,runner,core):
 rejected=False;reason=None;errors=0
 try:
  program=runner.Program(source)
 except (runner.Rejected,RecursionError) as error:rejected=True;reason=str(error)
 if not rejected:
  passed,details=core.check(program,env._task,env._task.hidden,details=True)
  errors=sum(x['error'] is not None for x in details)
  if obs.reward==1:assert passed==len(env._task.hidden)
 category=('execution' if obs.error or rejected or errors else
           'full' if obs.reward==1 else 'partial' if obs.reward>0 else 'wrong')
 return dict(category=category,native_reward=obs.reward,semantic_reward=None if category=='execution' else obs.reward,
             compile_rejected=rejected,compile_reason=reason,hidden_execution_errors=errors)
class Trial:
 def __init__(self,job):
  self.job=copy.deepcopy(job);self.env=DirectRepairEnvironment()
  module=candidate();self.other=module.DirectRepairEnvironment()
  reset=self.env.reset(task_id=job['task_id'],seed=job['seed']).model_dump()
  other=self.other.reset(task_id=job['task_id'],seed=job['seed']).model_dump()
  assert reset==other and DirectRepairAction.model_json_schema()==module.DirectRepairAction.model_json_schema()
  self.initial_source=reset['source'];self.other_action=module.DirectRepairAction
  self.other_runner=importlib.import_module('sorted_bool_candidate_native.runner')
  self.other_core=importlib.import_module('sorted_bool_candidate_native.environment')
  self.messages=[dict(role='system',content='Return exactly one JSON action instance matching this schema. No markdown, diff, or tool command. '+canonical(DirectRepairAction.model_json_schema())),dict(role='user',content=canonical(reset))]
  self.turn=0;self.closed=False;self.native=[]
 def consume(self,reply):
  if self.closed or self.turn:raise ValueError('one response only; no retry')
  self.turn=1
  try:
   if type(reply) is not str:raise ValueError('raw assistant text required')
   action=DirectRepairAction.model_validate_json(reply,strict=True)
  except (ValidationError,ValueError):
   self.closed=True;return dict(category='format',done=True,native_reward=None,semantic_reward=None,paired_native=None)
  obs=self.env.step(action);other=self.other.step(self.other_action(content=action.content));assert obs.done and other.done
  self.native=[obs.model_dump()];self.messages += [dict(role='assistant',content=reply),dict(role='user',content=canonical(self.native[0]))];self.closed=True
  source=action.content or self.initial_source
  before=classify(self.env,obs,source,baseline_runner,baseline_core)
  after=classify(self.other,other,source,self.other_runner,self.other_core)
  pair=dict(baseline=before,candidate=after,source_sha256=hashlib.sha256(source.encode()).hexdigest(),
    actual_same_program=True,compatibility_exposure=before['category']=='execution' and after['category']!='execution')
  return dict(before,done=True,paired_native=pair)
NAMESPACE='sorted-bool-runtime-paired-20261030'
SEEDS={'screen':3020000,'confirmation':3030000}
SAMPLING=dict(model='Qwen/Qwen3.8-27B:deepinfra',temperature=0.7,response_format=dict(type='json_object'))
def schedule(phase):
 if phase not in SEEDS:raise ValueError('frozen phase required')
 return [dict(j,attempt_id=digest(j)) for j in [dict(namespace=NAMESPACE,phase=phase,task_id='software_repair-ignore-d3',seed=SEEDS[phase],sample=i,arm='shared_program') for i in range(4)]]
def sampling_for(job,turn):
 if job not in schedule(job['phase']) or type(turn) is not int or turn!=0:raise ValueError('one frozen turn required')
 return copy.deepcopy(SAMPLING)
def capture(job):
 if job not in schedule('screen'):raise ValueError('confirmation observations unmaterialized')
 t=Trial(job);reset=json.loads(t.messages[1]['content'])
 return dict(messages=copy.deepcopy(t.messages),prompt_sha256=digest(t.messages),problem_sha256=digest({k:reset[k] for k in ('task_id','prompt','source','examples')}))
def bundle(chunk):
 if type(chunk) is not int or chunk not in range(2):raise ValueError('two frozen chunks required')
 jobs=schedule('screen');bound=capture(jobs[0])
 assert all(capture(j)==bound for j in jobs)
 return dict(namespace=NAMESPACE,chunk=chunk,screen_jobs=jobs[chunk*2:chunk*2+2],all_screen_jobs=jobs,confirmation_jobs=schedule('confirmation'),
   screen_groups=[dict(task_id=jobs[0]['task_id'],seed=SEEDS['screen'],problem_sha256=bound['problem_sha256'],arms={'shared_program':bound})],
   confirmation_observations_materialized=False,sampling=SAMPLING,max_attempts=4,max_calls=4,max_calls_per_chunk=2,retries=0,
   first_generation_limit=6000,completion_with_observations=8192,context=24576,reserved_final_observation_tokens=96,
   attempt_wall_seconds=600,intervention='One actual model program per sample is graded by both isolated pinned Native interpreters. Only bounded bool conversion support differs; sorted support is present in both. Only baseline terminal observation is accounted as model observation; paired analysis is never feedback.',
   selection='Four complete known model responses, exact input/request/usage bindings, positive paired full-solve delta, no lost baseline full solves, nonnegative paired semantic delta, at least one actual bool compatibility exposure. Fresh disjoint confirmation required.',
   limitations='Execution compatibility analysis, not model learning, training, Arena transfer or leaderboard evidence. One screen case and four sampled programs; actual generation costs counted once.')

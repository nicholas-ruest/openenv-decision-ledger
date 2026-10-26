import pathlib,importlib.util,json,hashlib,zipfile,argparse
parser=argparse.ArgumentParser()
parser.add_argument('--source-root',type=pathlib.Path,required=True)
parser.add_argument('--output',type=pathlib.Path,required=True)
args=parser.parse_args()
base=args.source_root
spec=importlib.util.spec_from_file_location('exporter',base/'scripts/export-direct-pilot.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
out=args.output;out.mkdir(exist_ok=False)
source='164cb2b1fdd9217093cc7182c1801b571908decc'
image='ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:77e34e465b514ef619ad2c02db57451c815bb478cf054eb16ce885516bd3ab7a'
profiles=[('release','software_repair-release-d4',1400000),('transactions','software_repair-kv-d2',1500000),('ignore','software_repair-ignore-d2',1600000)]
reports=[]
for name,task,start in profiles:
 splits={'train':(start,128),'validation':(start+10000,32),'test':(start+20000,64)}
 m.CURRICULA[name]=(task,splits,'temporary-part','Software transfer preparation','docs/software-ignore-modularity-2026-10-22.md')
 report=m.export(out/name,image,source,name)
 reports.append(report)
 (out/'progress.json').write_text(json.dumps({'finished_families':len(reports),'total_families':3,'model_calls':0}))
for split in ('train','validation','test'):
 with (out/(split+'.jsonl')).open('x') as f:
  for name,_,_ in profiles:f.write((out/name/(split+'.jsonl')).read_text())
req=m.request(image,source,'kv')
req.update(submission_id='decision-ledger-software-transfer-v11-20261026',name='Decision Ledger: software transfer curriculum')
req['tasks']=[{**req['tasks'][0],'task_id':task} for _,task,_ in profiles]
(out/'submission-candidate.json').write_text(json.dumps(req,indent=2)+'\n')
(out/'environment-source.zip').write_bytes((out/'ignore/environment-source.zip').read_bytes())
(out/'README.md').write_text('---\nlicense: mit\ntask_categories:\n- reinforcement-learning\n---\n\n# Software transfer curriculum\n\nThree equally scheduled SOFTWARE tasks: dependency planning, transactional command processing, and ignore-rule classification. Same frozen bounded interpreter and independent semantic rewards as the admitted v10 image. One JSON code answer per episode. 384 training,96 validation,192 test fixtures; disjoint procedural seeds. Reference controls are not model solves.\n\nHypothesis: broader software structures may transfer better than the previous single classifier. Prior v10 training132updates,training reward first25 .345667,last25 .423667,private evaluation1/40 and software0/5. This proposed mix is untrained and unconfirmed. No ranking improvement claimed.\n')
names=['README.md','environment-source.zip','submission-candidate.json','train.jsonl','validation.jsonl','test.jsonl']
manifest={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in names}
review={'source':source,'image':image,'tasks':[t for _,t,_ in profiles],'rows':sum(r['rows'] for r in reports),'controls':reports,'manifest':manifest,'request_sha256':manifest['submission-candidate.json'],'approved':False,'submitted':False,'model_calls':0,'trained':False,'hypothesis':'Cross-structure SOFTWARE coverage improves held-out transfer. Not demonstrated.','success_criteria':{'private_software_solved_min':1,'private_total_solved_min':4},'limits':['No access to trained weights for local matched evaluation','Prior proxy failures prevent signal confirmation','One evaluation draw is noisy; no ranking guarantee']}
(out/'REVIEW.json').write_text(json.dumps(review,indent=2))
print(json.dumps({k:v for k,v in review.items() if k!='controls'}))

"""Stage and test only the qualified runtime files, without Docker or network."""
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
QUALIFIED='f5b5a87ecc303ffe111148e607b01502fd698546'
STUDY='research/software-portable-review-default-20261030'
RUNTIME=('portable_environment.py','portable_app.py','review_environment.py',
         'mandatory_environment.py','joint_revision_environment.py','field_feedback.py')
def sha(data):return hashlib.sha256(data).hexdigest()
def stage(output):
    if output.exists():raise ValueError('fresh staging archive required')
    files=[(p,'app/repair_env/'+p.name) for p in sorted((ROOT/'integrations/software-repair/repair_env').glob('*.py'))]
    files += [(ROOT/STUDY/n,'app/'+STUDY+'/'+n) for n in RUNTIME]
    files += [(ROOT/'research/software-public-check-20261028/public_check.py','app/research/software-public-check-20261028/public_check.py')]
    files += [(ROOT/n,'app/'+n) for n in ('LICENSE','THIRD_PARTY.md')]
    files += [(ROOT/STUDY/n,'tests/'+n) for n in ('test_portable_app.py','test_portable_environment.py')]
    frozen={}
    for source,dest in files:
        if source.is_symlink() or not source.is_file():raise ValueError('regular allowlisted files only')
        data=source.read_bytes()
        expected=subprocess.check_output(['git','-C',str(ROOT),'show',QUALIFIED+':'+source.relative_to(ROOT).as_posix()])
        if data!=expected:raise ValueError('qualified runtime changed: '+str(source))
        frozen[dest]=dict(bytes=data,sha256=sha(data))
    output.mkdir(mode=0o700)
    for name,item in frozen.items():
        dest=output/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(item['bytes'])
    app=(output/'app').resolve()
    modules=('portable_app','portable_environment','review_environment','mandatory_environment',
             'joint_revision_environment','field_feedback','public_check','repair_env.runner','repair_env.tasks')
    code="import importlib,pathlib,unittest,sys;app=pathlib.Path("+repr(str(app))+");names="+repr(modules)+";modules=[importlib.import_module(n) for n in names];assert all(pathlib.Path(m.__file__).resolve().is_relative_to(app) for m in modules);suite=unittest.defaultTestLoader.discover("+repr(str((output/'tests').resolve()))+");result=unittest.TextTestRunner(verbosity=2).run(suite);assert result.testsRun==8;sys.exit(not result.wasSuccessful())"
    env=os.environ.copy();env['PYTHONPATH']=str(app/STUDY)+os.pathsep+str(app);env['PYTHONNOUSERSITE']='1'
    with (output/'transport.log').open('x') as log:
        result=subprocess.run([sys.executable,'-c',code],cwd=output,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=45)
    manifest=dict(qualified_runtime=QUALIFIED,files={n:v['sha256'] for n,v in frozen.items()},
        tests=8,tests_passed=result.returncode==0,all_runtime_imports_confined_to_staged_app=True,
        log_sha256=sha((output/'transport.log').read_bytes()),model_calls=0,image_qualified=False)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if result.returncode:raise ValueError('staged transport test failed; inspect preserved archive')
    return manifest
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(stage(a.output)))

"""Exercise the Dockerfile COPY tree without claiming a container build or image test."""
import hashlib,json,os,shlex,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent

def main():
    docker=(HERE/'Dockerfile').read_text();copies=[]
    assert 'FROM ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:9455e57ef88fe99d94a0f0b32651c1f52472f9aba6da68c11a68db18c936ed22' in docker
    with tempfile.TemporaryDirectory(prefix='domain-runtime-copy-') as temp:
        app=Path(temp)/'app';app.mkdir()
        for line in docker.splitlines():
            if not line.startswith('COPY '):continue
            _,source,target=shlex.split(line);assert target.startswith('/app/')
            origin=ROOT/source;dest=app/target.removeprefix('/app/');dest.parent.mkdir(parents=True,exist_ok=True)
            if origin.is_dir():shutil.copytree(origin,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            else:shutil.copy2(origin,dest)
            copies.append(dict(source=source,target=target))
        tests=app/'probe_tests';tests.mkdir();shutil.copy2(HERE/'test_runtime.py',tests/'test_runtime.py')
        env=dict(os.environ,PYTHONPATH=str(app/'research/software-domain-runtime-20261102')+':'+str(app),PYTHONDONTWRITEBYTECODE='1')
        # Import paths must be the copy tree, not the source repository.
        code="from pathlib import Path;import runtime_environment,repair_env.runner;root=Path.cwd().resolve();assert Path(runtime_environment.__file__).resolve().is_relative_to(root);assert Path(repair_env.runner.__file__).resolve().is_relative_to(root)"
        subprocess.run([sys.executable,'-B','-c',code],cwd=app,env=env,text=True,capture_output=True,check=True,timeout=15)
        r=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(tests),'-p','test_runtime.py','-v'],cwd=app,env=env,text=True,capture_output=True,timeout=45)
        if r.returncode:raise RuntimeError(r.stdout+r.stderr)
        assert 'Ran 5 tests' in r.stderr and '\nOK\n' in r.stderr
        print(json.dumps(dict(kind='docker_copy_tree_smoke',copy_entries=copies,native_sdk_checks=5,exit_code=0,imports_confined_to_copy_tree=True,container_built=False,container_executed=False,image_published=False,new_model_calls=0,new_cases=0,is_training=False,model_improvement=False),sort_keys=True))
if __name__=='__main__':main()

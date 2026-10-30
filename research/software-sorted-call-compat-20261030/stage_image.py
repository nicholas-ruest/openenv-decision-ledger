"""Stage only the pinned interpreter and Dockerfile; never builds, publishes or submits."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN='be2672ea479dc2520af5366b3cad6741e0195497cc6fdea1198232ab40a4e4a8'
BASE='ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:9455e57ef88fe99d94a0f0b32651c1f52472f9aba6da68c11a68db18c936ed22'
def sha(value):return hashlib.sha256(value).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 runner=(ROOT/'integrations/software-repair/repair_env/runner.py').read_bytes()
 assert sha(runner)==PIN,'exact frozen interpreter required'
 docker=Path(__file__).with_name('Dockerfile').read_bytes()
 assert docker.decode().splitlines()==[
  'FROM '+BASE,
  'LABEL org.opencontainers.image.description="Unqualified bounded sorted-call compatibility candidate"',
  'COPY --chown=10001:10001 runner.py /app/repair_env/runner.py']
 a.output.mkdir(mode=0o700)
 for name,value in [('runner.py',runner),('Dockerfile',docker)]:
  dest=a.output/name
  with dest.open('xb') as f:f.write(value)
  dest.chmod(0o644)
 manifest=dict(base_image=BASE,files={'runner.py':sha(runner),'Dockerfile':sha(docker)},
  runtime_changes=['/app/repair_env/runner.py'],source='34ae9401ec3a9530e2a71916060ea3a4c75eaa72',
  image_built=False,container_qualified=False,arena_submission_approved=False)
 with (a.output/'stage-manifest.json').open('x') as f:json.dump(manifest,f,indent=2)
 assert {x.name for x in a.output.iterdir()}=={'runner.py','Dockerfile','stage-manifest.json'}
 print(json.dumps(manifest))
if __name__=='__main__':main()

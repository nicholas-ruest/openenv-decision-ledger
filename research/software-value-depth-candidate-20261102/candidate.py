"""Isolated dictionary-depth traversal proposal; never patches the serving interpreter."""
import hashlib,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUNNER_SHA256='fcb0f8b5cb5321ae998f71a38502125a595cc39d6b6331eedd659ba9ceed65a6'
OLD='''        for item in (value.items() if type(value) is dict else value):
            bounded(item, depth + 1)
'''
NEW='''        if type(value) is dict:
            for key, item in value.items():
                bounded(key, depth + 1)
                bounded(item, depth + 1)
        else:
            for item in value:
                bounded(item, depth + 1)
'''

def load_pair(runtime_root=ROOT):
    path=Path(runtime_root)/'integrations/software-repair/repair_env/runner.py';raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=RUNNER_SHA256:raise ValueError('exact unchanged Native runner required')
    source=raw.decode();assert source.count(OLD)==1
    modules=[]
    for name,text in [('original_depth_native',source),('candidate_depth_native',source.replace(OLD,NEW))]:
        module=types.ModuleType(name);module.__file__=str(path)
        # Only hash-pinned trusted framework code is compiled here. Submitted
        # programs still run solely through its bounded AST interpreter.
        exec(compile(text,str(path),'exec'),module.__dict__);modules.append(module)
    return tuple(modules)

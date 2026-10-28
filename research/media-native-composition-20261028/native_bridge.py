"""Trusted in-image native adapter composition. No provider implementation.

Workspace inspection is root-side test/preflight instrumentation; it must never
be exposed to a model. The server and this adapter must share the same pinned
container filesystem. Remote arbitrary hosts are not supported.
"""
import hashlib
import time
from pathlib import Path

from media_protocol import IMAGE,RUNTIME
from native_session import NativeSession


class NativeBridge:
    def __init__(self,schema,deadline):self.schema=schema;self.deadline=deadline;self.opened=0;self.closed=0
    def open_env(self,task,seed):
        root=Path('/tmp/qe-arena-ws');before=set(root.glob('ep-*'))
        session=NativeSession(deadline=self.deadline)
        try:
            reset=session.reset(task,seed)
            added=set(root.glob('ep-*'))-before
            if len(added)!=1:raise ValueError('unique fresh native workspace required')
            path=added.pop()
            if not 20000<=path.stat().st_uid<20064:raise ValueError('UID workspace required')
            files={};total=0
            for p in sorted(path.rglob('*')):
                if p.is_symlink():raise ValueError('workspace symlink refused')
                if p.is_file():
                    body=p.read_bytes();total+=len(body)
                    if total>131072 or len(files)>=32:raise ValueError('workspace inspection bound')
                    files[p.relative_to(path).as_posix()]={'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
            self.opened+=1
        except BaseException:
            session.close();raise
        closed=False
        def close():
            nonlocal closed
            if closed:return
            session.close();closed=True
            stop=time.monotonic()+2
            while path.exists() and time.monotonic()<stop:time.sleep(.01)
            if path.exists():raise RuntimeError('native workspace cleanup unverified')
            self.closed+=1
        def step(action,deadline):
            # Caller cannot extend the original episode deadline.
            session.deadline=min(session.deadline,deadline)
            return session.step(action,self.schema)
        return {'reset_record':{'image':IMAGE,'runtime_source':RUNTIME,'uid_shell':True,
                                'reset_transport':reset,'workspace':files},'step':step,'close':close}
    def replay(self,task,seed,actions):
        env=self.open_env(task,seed)
        try:return {**env['reset_record'],'transports':[env['step'](a,self.deadline) for a in actions]}
        finally:env['close']()

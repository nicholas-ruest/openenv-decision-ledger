"""Bounded synchronous facade over a persistent native asyncio WebSocket.

Loopback /ws only, no credential/provider support. Each operation runs on the
same asyncio.Runner and has a total send+receive deadline. No retry or reconnect.
"""
import asyncio
import json
import math
import time
from websockets.asyncio.client import connect

from trajectory_audit import action_from_reply, inspect_transport, strict_json


class NativeSession:
    def __init__(self, *, deadline, port=8000, seconds=10, connector=connect, now=time.monotonic):
        current=now()
        if type(port) is not int or not 1024<=port<=65535:
            raise ValueError('unprivileged loopback port required')
        if type(seconds) not in (int,float) or not math.isfinite(seconds) or not 0<seconds<=15:
            raise ValueError('finite per-operation deadline within15seconds required')
        if type(deadline) not in (int,float) or not math.isfinite(deadline) or not 0<deadline-current<=1800:
            raise ValueError('finite episode deadline within1800seconds required')
        self.deadline=deadline;self.now=now;self.seconds=seconds;self.port=port;self.connector=connector
        self.runner=asyncio.Runner();self.ws=None;self.closed=False;self.reset_done=False;self.done=False

    def _run(self, operation):
        remaining=min(self.seconds,self.deadline-self.now())
        if self.closed or remaining<=0:
            operation.close();self.close()
            raise TimeoutError('native session unavailable or deadline reached')
        async def bounded():return await asyncio.wait_for(operation,timeout=remaining)
        try:return self.runner.run(bounded())
        except Exception as exc:
            self.close()
            if isinstance(exc,TimeoutError):raise TimeoutError('native send/receive deadline reached') from None
            raise RuntimeError('native WebSocket operation failed; session closed') from None

    async def _exchange(self, kind, data):
        if self.ws is None:
            self.ws=await self.connector(f'ws://127.0.0.1:{self.port}/ws',proxy=None,
                open_timeout=self.seconds,close_timeout=.2,ping_interval=None,
                compression=None,max_size=65536,max_queue=4)
        payload=json.dumps({'type':kind,'data':data},allow_nan=False)
        if len(payload.encode())>131072:raise ValueError('bounded native request required')
        await self.ws.send(payload)
        wire=await self.ws.recv()
        if not isinstance(wire,str):raise ValueError('native text response required')
        value=strict_json(wire)
        if value.get('type')!='observation':raise ValueError('native observation envelope required')
        result=value['data'];inspect_transport(result)
        self.done=result['done']
        return result

    def reset(self, task_id, seed):
        if self.reset_done or task_id not in ('qe_skill-media-d1','qe_skill-media-d2') or type(seed) is not int or not 0<=seed<2**64:
            raise ValueError('one declared media reset per session required')
        result=self._run(self._exchange('reset',{'task_id':task_id,'seed':seed}))
        if result['done'] or not result['observation']['success']:
            self.close();raise RuntimeError('successful nonterminal reset required')
        self.reset_done=True
        return result

    def step(self, action, schema):
        if not self.reset_done or self.done or self.closed:raise ValueError('active nonterminal reset required')
        # Match the exact pinned schema before sending any shell text.
        checked=action_from_reply(json.dumps(action,allow_nan=False),schema)
        return self._run(self._exchange('step',checked))

    def close(self):
        if self.closed:return
        self.closed=True
        if self.ws is not None:
            async def finish():
                try:await asyncio.wait_for(self.ws.close(),timeout=.3)
                except Exception:pass
                finally:
                    transport=getattr(self.ws,'transport',None)
                    if transport is not None:transport.abort()
            try:self.runner.run(finish())
            finally:self.runner.close()
        else:self.runner.close()

    def __enter__(self):return self
    def __exit__(self,*args):self.close()

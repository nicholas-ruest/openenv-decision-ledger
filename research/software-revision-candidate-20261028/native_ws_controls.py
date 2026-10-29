"""Scripted reference/wrong controls against the experimental native app."""
import asyncio
import json
from urllib.request import urlopen
from websockets.asyncio.client import connect
from revision_environment import TASKS
from repair_env.tasks import make_task


async def main():
    episodes=0
    for index,task in enumerate(TASKS):
        for early in (False,True):
            seed=2340100+index
            async with connect('ws://127.0.0.1:8000/ws',open_timeout=5,close_timeout=.2,ping_interval=None,max_size=131072) as ws:
                async def exchange(kind,data):
                    await ws.send(json.dumps({'type':kind,'data':data}))
                    value=json.loads(await asyncio.wait_for(ws.recv(),10))
                    if value['type']!='observation':raise ValueError('native observation required')
                    return value['data']
                reset=await exchange('reset',{'task_id':task,'seed':seed})
                if reset['done']:raise ValueError('nonterminal reset required')
                if early:
                    final=await exchange('step',{'submit':True})
                    if not final['done'] or final['reward']!=0:raise ValueError('unchanged early grade required')
                else:
                    first=await exchange('step',{'content':reset['observation']['source']})
                    if first['done'] or first['reward']!=0:raise ValueError('no intermediate grade')
                    if json.loads(first['observation']['feedback'])['public_only'] is not True:raise ValueError('public feedback required')
                    final=await exchange('step',{'content':make_task(task,seed).reference_source})
                    if not final['done'] or final['reward']!=1:raise ValueError('reference revision full required')
                episodes+=1
    print(json.dumps({'scripted_native_episodes':episodes,'reference_revision_full':2,'unchanged_early_zero':2,'new_model_calls':0,'is_training':False}))

if __name__=='__main__':asyncio.run(asyncio.wait_for(main(),60))

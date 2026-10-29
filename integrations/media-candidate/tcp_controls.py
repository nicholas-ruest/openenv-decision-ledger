"""Real TCP controls in the running image; no model calls, exact native references."""
import json
import os
from pathlib import Path
from urllib.request import urlopen
from websockets.sync.client import connect
from qe_arena import skills


def exchange(ws, kind, data):
    ws.send(json.dumps({'type': kind, 'data': data}))
    reply = json.loads(ws.recv(timeout=20))
    assert reply['type'] == 'observation', reply
    return reply['data']


def main():
    # The deployed entrypoint, not an unrelated test runner, must reap orphans.
    assert Path('/proc/1/comm').read_text().strip() == 'tini'
    with urlopen('http://127.0.0.1:8000/health', timeout=10) as r:
        assert r.status == 200
    with urlopen('http://127.0.0.1:8000/schema', timeout=10) as r:
        schema = json.load(r)
        assert 'action' in schema and 'observation' in schema
    for task_id in ('qe_skill-media-d1', 'qe_skill-media-d2'):
        task = skills.make_skill_task(task_id, 2250000)
        with connect('ws://127.0.0.1:8000/ws', open_timeout=10) as ws:
            reset = exchange(ws, 'reset', {'task_id': task_id, 'seed': 2250000})
            assert not reset['done']
            command = exchange(ws, 'step', {'action_type': 'exec', 'command': 'id -u'})
            assert command['observation']['success'], command
            uid = int(command['observation']['output'].strip())
            assert 20000 <= uid <= 20063, uid
            wrote = exchange(ws, 'step', {'action_type':'write_file', 'file_path':task.output, 'content':skills.solve(task)})
            assert wrote['observation']['success']
            result = exchange(ws, 'step', {'action_type':'evaluate'})
            assert result['done'] and result['reward'] == 1, result
    print(json.dumps({'health': True, 'schema': True, 'tcp_reference_episodes': 2, 'uid_shell': True, 'pid1': 'tini', 'model_calls': 0}))


if __name__ == '__main__':
    main()

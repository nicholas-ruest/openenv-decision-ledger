"""App HTTP/WebSocket controls; no inference or model code execution."""
from fastapi.testclient import TestClient
import pytest
from qe_arena import shell, skills
from qe_arena.terminal_env import TerminalAction, TerminalObservation
from media_app import app, MEDIA_TASKS


@pytest.fixture(autouse=True)
def disabled_shell(monkeypatch, tmp_path):
    monkeypatch.delenv(shell.ENV_FLAG, raising=False)
    monkeypatch.setenv(shell.ROOT_ENV, str(tmp_path/'workspaces'))
    monkeypatch.setattr(shell, '_probe', lambda: 'disabled')
    shell._reset_mode_for_tests()
    yield
    shell._reset_mode_for_tests()


def exchange(ws, kind, data):
    ws.send_json({'type': kind, 'data': data})
    reply = ws.receive_json()
    assert reply['type'] == 'observation', reply
    return reply['data']


def test_http_schema_health():
    with TestClient(app) as client:
        assert client.get('/health').status_code == 200
        schema = client.get('/schema').json()
        assert schema['action'] == TerminalAction.model_json_schema()
        assert schema['observation'] == TerminalObservation.model_json_schema()


@pytest.mark.parametrize('task_id', MEDIA_TASKS)
@pytest.mark.parametrize('mode', ('reference','wrong','empty'))
def test_websocket_media_episode(task_id, mode):
    task = skills.make_skill_task(task_id, 2240000)
    with TestClient(app) as client, client.websocket_connect('/ws') as ws:
        reset = exchange(ws,'reset',{'task_id':task_id,'seed':2240000})
        assert not reset['done'] and task.output in reset['observation']['instruction']
        if mode != 'empty':
            if mode == 'reference': answer = skills.solve(task)
            else:
                wrong = next(k for k,v in task.private['family'].traps.items() if task.difficulty in v)
                answer = skills.solve(task, wrong)
            wrote = exchange(ws,'step',{'action_type':'write_file','file_path':task.output,'content':answer})
            assert wrote['observation']['success'] and not wrote['done']
        result = exchange(ws,'step',{'action_type':'evaluate'})
        assert result['done'] and result['reward'] == (1 if mode == 'reference' else 0)


def test_nonmedia_reset_rejected_through_websocket():
    with TestClient(app) as client, client.websocket_connect('/ws') as ws:
        ws.send_json({'type':'reset','data':{'task_id':'qe_skill-math-d1','seed':2240000}})
        reply = ws.receive_json()
        assert reply['type'] == 'error', reply

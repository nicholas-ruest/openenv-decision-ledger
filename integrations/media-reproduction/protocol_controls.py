"""Media terminal protocol controls; output is data, never candidate host code."""
import pytest
import hashlib
from pathlib import Path
import qe_arena
from qe_arena import shell, skills
from qe_arena.terminal_env import TerminalEnvironment, TerminalAction

SOURCE_HASHES = {'qe_arena/terminal_env.py': '6ea5cfcffc292e52ead2687728ad6d9c040dfaf32a5610386ac6514d4b1438b3', 'qe_arena/shell.py': '4e9aabefa6f23793a05804ec413aaa5d1c5125365156f22cdb50ff600808d34d', 'qe_arena/skills/__init__.py': '5e0050e8e65569c14cf70963755254f75456f6597177a25e014373ae37cdb3c9', 'qe_arena/skills/media.py': '005eabea342ba948e6b68dcc341f3756a8ebdd5fb44830cb13bb482a16ef200c', 'qe_arena/skills/subtitles.py': '872054f7309500113beab2c853bfeceebd146e60dc36d42f42f9e98e6c4a7b84'}


@pytest.fixture(scope="session", autouse=True)
def pinned_media_source():
    root = Path(qe_arena.__file__).resolve().parents[1]
    for name, sha in SOURCE_HASHES.items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == sha


CASES = [(task, kind, seed) for task in ('qe_skill-media-d1', 'qe_skill-media-d2')
         for kind in skills.SERVED[task] for seed in (2230000, 2230100)]


@pytest.fixture(autouse=True)
def disabled_shell(monkeypatch, tmp_path):
    monkeypatch.delenv(shell.ENV_FLAG, raising=False)
    monkeypatch.setenv(shell.ROOT_ENV, str(tmp_path / 'workspace'))
    monkeypatch.setattr(shell, '_probe', lambda: 'disabled')
    shell._reset_mode_for_tests()
    yield
    shell._reset_mode_for_tests()


@pytest.mark.parametrize('task_id,kind,seed', CASES)
def test_media_write_evaluate_reference_wrong_and_empty(task_id, kind, seed):
    task = skills.make_skill_task(task_id, seed, pool=(kind,))
    applicable = [name for name, levels in task.private['family'].traps.items() if task.difficulty in levels]
    assert applicable
    for mode in ('reference', 'wrong', 'empty'):
        env = TerminalEnvironment(corpus_pool=(kind,))
        obs = env.reset(task_id=task_id, seed=seed)
        assert not obs.done and task.output in obs.instruction
        denied = env.step(TerminalAction(action_type='exec', command='echo never-executed'))
        assert not denied.success and not denied.done
        if mode != 'empty':
            content = skills.solve(task, applicable[0] if mode == 'wrong' else None)
            written = env.step(TerminalAction(action_type='write_file', file_path=task.output, content=content))
            assert written.success and not written.done
        graded = env.step(TerminalAction(action_type='evaluate'))
        assert graded.done and graded.reward == (1 if mode == 'reference' else 0)
        repeated = env.step(TerminalAction(action_type='evaluate'))
        assert repeated.done and repeated.reward == graded.reward

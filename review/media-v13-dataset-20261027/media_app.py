"""Media-only adaptation of Profa-QE's MIT terminal environment.

Requires attributed upstream source at958198e55299eb18ad812f438a6b2ca6abaa7f5c.
No inference, submission or credentials are used by this module.
"""
from openenv.core.env_server.http_server import create_app
from qe_arena.terminal_env import TerminalEnvironment, TerminalAction, TerminalObservation

MEDIA_TASKS = ('qe_skill-media-d1', 'qe_skill-media-d2')


class MediaEnvironment(TerminalEnvironment):
    def reset(self, seed=None, episode_id=None, **kwargs):
        task = kwargs.get('task_id', MEDIA_TASKS[0])
        if task not in MEDIA_TASKS:
            raise ValueError('media-only candidate requires a declared media task')
        kwargs['task_id'] = task
        return super().reset(seed=seed, episode_id=episode_id, **kwargs)


app = create_app(MediaEnvironment, TerminalAction, TerminalObservation,
                 env_name='decision_ledger_media', max_concurrent_envs=8)

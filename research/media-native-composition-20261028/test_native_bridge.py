import hashlib
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import native_bridge as nb


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.closed=False;self.created=False;self.symlink=False;self.fail=False;self.sent=[]
        owner=self
        class File:
            def is_symlink(self):return owner.symlink
            def is_file(self):return True
            def read_bytes(self):return b'input'
            def relative_to(self,p):return Path('input.json')
        class Directory:
            def stat(self):return SimpleNamespace(st_uid=20000)
            def rglob(self,pattern):return [File()]
            def exists(self):return not owner.closed
        self.directory=Directory()
        class Root:
            def glob(self,pattern):return [owner.directory] if owner.created else []
        class Session:
            def __init__(self,deadline):self.deadline=deadline
            def reset(self,task,seed):
                if owner.fail:raise RuntimeError('private error')
                owner.created=True;return {'done':False}
            def step(self,action,schema):owner.sent.append(action);return {'done':True}
            def close(self):owner.closed=True
        self.patches=[patch.object(nb,'Path',lambda p:Root()),patch.object(nb,'NativeSession',Session)]
        for p in self.patches:p.start();self.addCleanup(p.stop)
    def test_snapshot_no_action_consumed_and_close_idempotent(self):
        bridge=nb.NativeBridge({},100);env=bridge.open_env('qe_skill-media-d1',1)
        self.assertEqual(self.sent,[])
        self.assertEqual(env['reset_record']['workspace']['input.json']['sha256'],hashlib.sha256(b'input').hexdigest())
        env['step']({'action_type':'evaluate'},200);env['close']();env['close']()
        self.assertEqual((bridge.opened,bridge.closed),(1,1));self.assertTrue(self.closed)
    def test_symlink_and_reset_failure_close_without_replay(self):
        for symlink,fail in ((True,False),(False,True)):
            self.created=False;self.closed=False;self.symlink=symlink;self.fail=fail
            with self.assertRaises((ValueError,RuntimeError)):nb.NativeBridge({},100).open_env('qe_skill-media-d1',1)
            self.assertTrue(self.closed);self.assertEqual(self.sent,[])
    def test_replay_closes_its_independent_session(self):
        bridge=nb.NativeBridge({},100);out=bridge.replay('qe_skill-media-d2',2,[{'action_type':'evaluate'}])
        self.assertEqual(out['transports'],[{'done':True}]);self.assertTrue(self.closed);self.assertEqual(bridge.closed,1)


if __name__=='__main__':unittest.main()

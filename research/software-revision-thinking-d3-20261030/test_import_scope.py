"""Offline import regression; no environment cases, credentials or calls."""
import ast
from pathlib import Path
import sys
import tempfile
import unittest


class ImportScopeTests(unittest.TestCase):
    def test_external_loader_selects_joint_protocol_before_peer_protocol(self):
        # Execute the real function without importing the environment/provider
        # dependencies. Neither the script directory nor cwd supplies a fallback.
        tree = ast.parse(Path(__file__).with_name('caller.py').read_text())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'modules')
        code = compile(ast.Module(body=[function], type_ignores=[]), 'caller.py', 'exec')
        previous_path = sys.path[:]
        previous_module = sys.modules.pop('feedback_protocol', None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                joint = root / 'research/software-revision-thinking-d3-20261030'
                peer = root / 'research/software-function-trial-20261029'
                for path, marker in ((joint, 'joint'), (peer, 'peer')):
                    path.mkdir(parents=True)
                    (path / 'feedback_protocol.py').write_text('origin = ' + repr(marker) + '\nclass Trial: pass\n')
                scope = {'ROOT': root, 'sys': sys}
                exec(code, scope)
                protocol, trial = scope['modules']()
                self.assertEqual(protocol.origin, 'joint')
                self.assertEqual(Path(protocol.__file__).parent, joint)
                self.assertIs(trial, protocol.Trial)
        finally:
            sys.path[:] = previous_path
            sys.modules.pop('feedback_protocol', None)
            if previous_module is not None:
                sys.modules['feedback_protocol'] = previous_module


if __name__ == '__main__':
    unittest.main()

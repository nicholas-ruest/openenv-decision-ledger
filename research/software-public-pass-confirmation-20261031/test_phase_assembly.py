"""Whole-phase scripted qualification on an existing case; never model evidence."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import caller
import test_protocol_caller as fixture

protocol, _ = caller.modules()


class AssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ProtocolTests.setUpClass()
        cls.counter = fixture.ProtocolTests.counter

    def test_four_chunks_replay_and_scripted_archives_cannot_enter_live_assembly(self):
        replay = caller.load('phase_exact_replay', Path(__file__).with_name('replay.py'))
        assembly = caller.load('phase_exact_assembly', Path(__file__).with_name('assemble.py'))
        all_rows = []; responses = []; calls = []
        with patch.dict(protocol.SEEDS, confirmation=3100000), patch.object(protocol,"GATE_VERIFIED",True), tempfile.TemporaryDirectory() as t:
            for chunk in range(4):
                parent = Path(t)/str(chunk); parent.mkdir()
                frozen = protocol.bundle(chunk)
                (parent/'inputs.json').write_text(json.dumps(frozen))
                out = parent/'live'; backend = fixture.Backend(self.counter)
                rows = caller.phase(frozen, protocol.digest(frozen), out, backend,
                                    self.counter, time.monotonic()+90)
                events = [json.loads(x) for x in (out/'events.jsonl').read_text().splitlines()]
                proof = replay.verify_chunk(frozen, rows, events, self.counter)
                responses += proof['response_ids']; calls += proof['call_ids']; all_rows += rows
                self.assertEqual(len(backend.calls), 3)
                with self.assertRaisesRegex(ValueError, 'live frozen chunk'):
                    assembly.load_live_chunk(chunk, out, self.counter)
            self.assertEqual([r['attempt_id'] for r in all_rows],
                             [j['attempt_id'] for j in protocol.schedule('confirmation')])
        self.assertEqual(len(all_rows), 8)
        self.assertEqual(len(responses), 12)
        self.assertEqual(len(set(responses)), 12)
        self.assertEqual(len(set(calls)), 12)
        self.assertEqual(sum(len(r['controller_actions']) for r in all_rows), 4)
        self.assertTrue(all(r['category']=='full' for r in all_rows))


if __name__ == '__main__': unittest.main()

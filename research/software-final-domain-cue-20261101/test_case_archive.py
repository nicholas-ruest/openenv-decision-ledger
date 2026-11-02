"""Actual Native replay on the already-seen fixture; synthetic provider archives only."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import case_archive as archive
import test_case_replay as fixture


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.BoundReplayTests.setUpClass()
        cls.addClassCleanup(fixture.BoundReplayTests.doClassCleanups)
        cls.f=fixture.BoundReplayTests

    def put(self,path,value):path.write_text(json.dumps(value))

    def manifest(self,root):self.put(root/'assignments.json',self.f.jobs)

    def terminal(self,root,trace):
        job=trace['job'];path=root/job['attempt_id'];path.mkdir();events=[]
        for turn,(request,response) in enumerate(zip(trace['requests'],trace['responses'])):
            label=job['attempt_id']+':'+str(turn)
            self.put(path/('request-'+str(turn)+'.json'),request)
            self.put(path/('response-'+str(turn)+'.json'),response)
            events.extend([dict(event='reserved',label=label),dict(event='calling',label=label,
                request_sha256=archive.replay.binding.gate.digest(request),generation_limit=request['max_tokens']),
                dict(event='response_received',response_id=response['id'])])
        (path/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
        self.put(path/'trace.json',trace)
        labels=[job['attempt_id']+':'+str(i) for i in range(2)]
        self.put(path/'record.json',dict(trace['record'],job=job,reservations=labels,calls=labels,
            response_ids=[r['id'] for r in trace['responses']],unknown_usage=False,
            known_generation_tokens=trace['record']['generation_tokens']))

    def test_complete_native_archive_has_no_live_or_selection_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.manifest(root)
            for trace in self.f.traces:self.terminal(root,trace)
            value=archive.assemble(root,self.f.counter,self.f.args)
            self.assertEqual(len(value['rows']),8)
            self.assertTrue(value['all_terminal_attempts_reconstructed'])
            for key in ['execution_authorized','provider_provenance_attested','selection_passed','model_improvement']:
                self.assertFalse(value[key])

    def test_missing_records_keep_all_assignments_and_unknown_cost_unrewarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.manifest(root);trace=self.f.traces[0];job=trace['job']
            path=root/job['attempt_id'];path.mkdir();label=job['attempt_id']+':0'
            request=trace['requests'][0];self.put(path/'request-0.json',request)
            (path/'events.jsonl').write_text(json.dumps(dict(event='reserved',label=label))+'\n'+json.dumps(dict(event='calling',label=label,request_sha256=archive.replay.binding.gate.digest(request),generation_limit=request['max_tokens']))+'\n')
            value=archive.assemble(root,self.f.counter,self.f.args)
            self.assertEqual(len(value['rows']),8);self.assertFalse(value['all_terminal_attempts_reconstructed'])
            self.assertIsNone(value['phase_reconstruction'])
            row=value['rows'][0];self.assertTrue(row['unknown_usage']);self.assertFalse(row['recorded'])
            self.assertIsNone(row['total_generation_tokens']);self.assertIsNone(row['reconstructed_terminal_reward'])
            self.assertIsNone(row['terminal_reward_observed'])
            self.assertEqual(row['known_generation_tokens'],0)
            self.assertTrue(all(not r['recorded'] for r in value['rows']))
            # A saved reply without its received event cannot be promoted to known usage.
            self.put(path/'response-0.json',trace['responses'][0])
            with self.assertRaisesRegex(ValueError,'saved files'):archive.assemble(root,self.f.counter,self.f.args)

    def test_original_manifest_and_local_order_tampering_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.put(root/'assignments.json',list(reversed(self.f.jobs)))
            with self.assertRaisesRegex(ValueError,'ordered assignments'):archive.assemble(root,self.f.counter,self.f.args)
            self.manifest(root);self.terminal(root,self.f.traces[0]);path=root/self.f.jobs[0]['attempt_id']/'events.jsonl'
            original=path.read_text();events=original.splitlines();events[0],events[1]=events[1],events[0];path.write_text('\n'.join(events)+'\n')
            with self.assertRaisesRegex(ValueError,'sequence'):archive.assemble(root,self.f.counter,self.f.args)
            events=[json.loads(x) for x in original.splitlines()]
            response_path=path.parent/'response-1.json';response=json.loads(response_path.read_text())
            response['id']=self.f.traces[0]['responses'][0]['id'];events[-1]['response_id']=response['id']
            self.put(response_path,response);path.write_text(''.join(json.dumps(e)+'\n' for e in events))
            with self.assertRaisesRegex(ValueError,'unique reply'):archive.assemble(root,self.f.counter,self.f.args)

    def test_unsealed_gate_refuses_before_archive_io(self):
        with patch.object(archive.replay.binding.gate,'require_case',side_effect=ValueError('unsealed')):
            with patch.object(archive,'read',side_effect=AssertionError('private I/O')):
                with self.assertRaisesRegex(ValueError,'unsealed'):archive.assemble('/absent',None,None)

if __name__=='__main__':unittest.main()

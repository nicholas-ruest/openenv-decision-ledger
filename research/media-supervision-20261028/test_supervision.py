import asyncio
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import httpx
from bounded_native import native_get
from phase_supervisor import supervise, verify_saved_phase
from test_trajectory_audit import fixture_data


class NativeTests(unittest.TestCase):
    def test_get_only_fixed_loopback_no_auth_proxy_or_redirect(self):
        async def handler(request):
            self.assertEqual(request.method,'GET');self.assertEqual(request.url.host,'127.0.0.1')
            self.assertNotIn('authorization',request.headers)
            return httpx.Response(200,json={'status':'ok'})
        self.assertEqual(native_get('/health',transport=httpx.MockTransport(handler)),{'status':'ok'})
        for path in ('https://example.com/','/ws','/schema?x=1','/../schema'):
            with self.assertRaises(ValueError):native_get(path)
    def test_total_timeout_cancels_stalled_connect(self):
        cancelled=[]
        async def handler(request):
            try:await asyncio.sleep(10)
            finally:cancelled.append(True)
        start=time.monotonic()
        with self.assertRaises(TimeoutError):native_get('/schema',seconds=.05,transport=httpx.MockTransport(handler))
        self.assertLess(time.monotonic()-start,1);self.assertEqual(cancelled,[True])
    def test_stream_total_deadline_not_just_per_chunk(self):
        closed=[]
        class Slow(httpx.AsyncByteStream):
            async def __aiter__(self):
                while True:
                    await asyncio.sleep(.02);yield b' '
            async def aclose(self):closed.append(True)
        async def handler(request):return httpx.Response(200,stream=Slow())
        with self.assertRaises(TimeoutError):native_get('/schema',seconds=.08,transport=httpx.MockTransport(handler))
        self.assertEqual(closed,[True])
    def test_redirect_errors_oversize_and_nonobject_sanitized(self):
        for response in (httpx.Response(302,headers={'location':'https://example.com'}),httpx.Response(500,text='private error'),httpx.Response(200,content=b'x'*65537),httpx.Response(200,json=[])):
            async def handler(request):return response
            with self.assertRaisesRegex(RuntimeError,'^bounded native preflight failed$'):native_get('/schema',transport=httpx.MockTransport(handler))
    def test_invalid_deadlines_ports_before_network(self):
        for seconds in (float('nan'),float('inf'),0,16,True):
            with self.assertRaises(ValueError):native_get('/health',seconds=seconds)
        for port in (True,80,65536):
            with self.assertRaises(ValueError):native_get('/health',port=port)


CHILD_CODE="""import os,signal,time,json,pathlib
signal.signal(signal.SIGTERM,signal.SIG_IGN)
p=pathlib.Path('/proc/self')
identity={'pid':os.getpid(),'start_ticks':(p/'stat').read_text().split()[21], 'argv':(p/'cmdline').read_bytes().decode().split('\\0')[:-1]}
pathlib.Path('child-identity.json').write_text(json.dumps(identity))
while True:time.sleep(.01)
"""


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.root=self.base/'supervised';_,self.plan=fixture_data()
    def worker(self,source):
        p=self.base/'worker.py';p.write_text(source)
        return p,hashlib.sha256(p.read_bytes()).hexdigest()
    def launch(self,source,seconds=3):
        p,sha=self.worker(source)
        return supervise(self.root,p,sha,self.plan,'screen',deadline=time.monotonic()+seconds)
    def assert_child_stopped(self):
        identity=json.loads((self.root/'child-identity.json').read_text());pid=identity['pid']
        self.assertIn('time.sleep',identity['argv'][-1])
        stat=Path(f'/proc/{pid}/stat')
        if stat.exists():
            fields=stat.read_text().split()
            # A reused PID is not the old worker. A zombie has no executing code.
            self.assertTrue(fields[21]!=identity['start_ticks'] or fields[2]=='Z')
    def test_stalled_worker_and_term_resistant_descendant_killed(self):
        source=f"import subprocess,signal,time,pathlib,sys\nsubprocess.Popen([sys.executable,'-c',{CHILD_CODE!r}])\nsignal.signal(signal.SIGTERM,signal.SIG_IGN)\np=pathlib.Path(sys.argv[1]);p.mkdir();(p/'intent.json').write_text('{{}}')\nwhile True:time.sleep(.01)\n"
        start=time.monotonic();r=self.launch(source,.7)
        self.assertEqual(r['status'],'deadline');self.assertFalse(r['archive_verified']);self.assertIsNone(r['provider_billing_stopped']);self.assertLess(time.monotonic()-start,2)
        self.assertTrue((self.root/'phase/intent.json').exists());self.assertFalse((self.root/'phase/complete.json').exists());self.assert_child_stopped()
    def test_zero_exit_still_cleans_orphan_and_requires_real_archive(self):
        source=f"import subprocess,sys,time,pathlib\nsubprocess.Popen([sys.executable,'-c',{CHILD_CODE!r}])\nwhile not pathlib.Path('child-identity.json').exists():time.sleep(.01)\n"
        r=self.launch(source);self.assertEqual(r['status'],'invalid_archive');self.assertEqual(r['process_status'],'completed');self.assert_child_stopped()
    def test_actual_child_runs_full_synthetic_phase_then_readonly_verifies(self):
        source="from test_media_durable import PhaseTests\nfrom pathlib import Path\nimport sys\nt=PhaseTests();t.setUp();t.root=Path(sys.argv[1]);t.run_phase()\n"
        absolute=os.pathsep.join(str(Path(p).resolve()) for p in os.environ.get('PYTHONPATH','').split(os.pathsep) if p)
        with patch.dict(os.environ,{'PYTHONPATH':absolute}):r=self.launch(source,10)
        self.assertEqual(r['status'],'completed');self.assertTrue(r['archive_verified'])
        self.assertEqual(verify_saved_phase(self.root/'phase',self.plan,'screen')['attempts'],16)
        with self.assertRaises(FileExistsError):self.launch(source)
    def test_failed_worker_no_unverified_completion(self):
        r=self.launch("raise RuntimeError('private text must not be recorded')")
        self.assertEqual(r['status'],'failed');self.assertFalse(r['archive_verified'])
        self.assertNotIn('private text',(self.root/'supervisor-result.json').read_text())
    def test_source_hash_symlink_and_expiry_reject_before_launch(self):
        p,sha=self.worker('pass')
        with self.assertRaises(ValueError):supervise(self.root,p,'0'*64,self.plan,'screen',deadline=time.monotonic()+1)
        link=self.base/'link';link.symlink_to(p)
        with self.assertRaises(ValueError):supervise(self.root,link,sha,self.plan,'screen',deadline=time.monotonic()+1)
        for seconds in (0,float('nan'),float('inf'),1801):
            with self.assertRaises(ValueError):supervise(self.root,p,sha,self.plan,'screen',deadline=time.monotonic()+seconds)
        self.assertFalse(self.root.exists())


if __name__=='__main__':unittest.main()

import asyncio
import json
import time
import unittest

from native_session import NativeSession
from test_trajectory_audit import fixture_data


class Socket:
    def __init__(self):self.sent=[];self.slow=None;self.cancelled=[];self.closed=False;self.aborted=False;self.transport=self;self.bad=False
    async def send(self,payload):
        self.sent.append(json.loads(payload))
        if self.slow=='send':
            try:await asyncio.sleep(5)
            finally:self.cancelled.append('send')
    async def recv(self):
        if self.slow=='recv':
            try:await asyncio.sleep(5)
            finally:self.cancelled.append('recv')
        if self.bad:return '{"type":"error","data":"sensitive text"}'
        done=self.sent[-1]['type']=='step'
        return json.dumps({'type':'observation','data':{'done':done,'reward':1 if done else 0,'observation':{'success':True,'error':'','output':''}}})
    async def close(self):self.closed=True
    def abort(self):self.aborted=True


class SessionTests(unittest.TestCase):
    def setUp(self):self.sock=Socket();self.schema=fixture_data()[0]['schema'];self.kwargs=None
    async def connect(self,url,**kwargs):
        self.assertEqual(url,'ws://127.0.0.1:8000/ws');self.kwargs=kwargs;return self.sock
    def session(self,**kwargs):return NativeSession(deadline=time.monotonic()+3,seconds=.05,connector=self.connect,**kwargs)
    def test_reset_step_and_close_fixed_surface(self):
        with self.session() as s:
            s.reset('qe_skill-media-d1',2290000);self.assertTrue(s.step({'action_type':'evaluate'},self.schema)['done'])
            with self.assertRaises(ValueError):s.step({'action_type':'evaluate'},self.schema)
        self.assertTrue(self.sock.closed and self.sock.aborted);self.assertIsNone(self.kwargs['proxy']);self.assertNotIn('additional_headers',self.kwargs)
    def test_stalled_send_and_receive_cancel_poison_session(self):
        for mode in ('send','recv'):
            self.sock=Socket();self.sock.slow=mode;s=self.session();start=time.monotonic()
            with self.assertRaises(TimeoutError):s.reset('qe_skill-media-d1',1)
            self.assertTrue(s.closed);self.assertEqual(self.sock.cancelled,[mode]);self.assertTrue(self.sock.aborted);self.assertLess(time.monotonic()-start,1)
            with self.assertRaises(TimeoutError):s.reset('qe_skill-media-d1',1)
    def test_handshake_total_deadline(self):
        cancelled=[]
        async def stall(*args,**kwargs):
            try:await asyncio.sleep(5)
            finally:cancelled.append(True)
        s=NativeSession(deadline=time.monotonic()+2,seconds=.05,connector=stall)
        with self.assertRaises(TimeoutError):s.reset('qe_skill-media-d2',2)
        self.assertEqual(cancelled,[True]);self.assertTrue(s.closed)
    def test_error_is_sanitized_and_closed(self):
        self.sock.bad=True;s=self.session()
        with self.assertRaisesRegex(RuntimeError,'^native WebSocket operation failed; session closed$'):s.reset('qe_skill-media-d1',1)
        self.assertTrue(self.sock.aborted)
    def test_deadline_and_invalid_configuration_no_connection(self):
        for kwargs in ({'port':80},{'seconds':float('nan')},{'deadline':float('inf')}):
            args={'deadline':time.monotonic()+2};args.update(kwargs)
            with self.assertRaises(ValueError):NativeSession(**args)
        s=self.session();s.deadline=time.monotonic()-1
        with self.assertRaises(TimeoutError):s.reset('qe_skill-media-d1',1)
        self.assertEqual(self.sock.sent,[])
    def test_reset_reuse_and_invalid_action_do_not_send(self):
        with self.session() as s:
            s.reset('qe_skill-media-d1',1)
            with self.assertRaises(ValueError):s.reset('qe_skill-media-d1',1)
            with self.assertRaises(ValueError):s.step({'action_type':'evaluate','extra':1},self.schema)
            self.assertEqual(len(self.sock.sent),1)
    def test_stalled_close_is_aborted_with_bounded_grace(self):
        async def stall():await asyncio.sleep(5)
        s=self.session();s.reset('qe_skill-media-d1',1);self.sock.close=stall
        start=time.monotonic();s.close();self.assertLess(time.monotonic()-start,1);self.assertTrue(self.sock.aborted)


if __name__=='__main__':unittest.main()

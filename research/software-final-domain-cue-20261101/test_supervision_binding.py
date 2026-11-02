import copy,importlib.util,math,sys,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('fresh_domain_supervision',Path(__file__).with_name('qualification_supervisor.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)

class BindingTests(unittest.TestCase):
    def fixture(self):
        source='a'*40;output=Path('/qualification/original')
        events=[dict(event='starting',target='worker_entry',wall_seconds=1200),dict(event='started',pid=101),dict(event='terminal',status='completed',pid=101,worker_exitcode=0,shutdown_verified=True,finished_before_deadline=True)]
        binding=dict(worker_pid=101,parent_pid=100,deadline=1000.,finished_at=999.,source=source,archive=str(output),mode='scripted_qualification',counter_initialized_in_worker=True,max_inflight=2,max_reserving=1)
        startup=dict(worker_pid=101,parent_pid=100,deadline=1000.,source=source,mode='scripted_qualification',native_modules=[],python_threads=1,os_threads=1)
        launch=dict(parent_pid=100,source=source,archive=str(output),parent_state=dict(native_modules=[],python_threads=1,os_threads=1))
        summary=dict(scripted=True,live_evidence=False,complete=True,assigned=8,recorded=8,calls=16,unknown_usage_calls=0)
        return [events,binding,startup,launch,summary,source,output]

    def test_exact_original_qualification_binding(self):
        self.assertTrue(s.binding_valid(*self.fixture()))

    def test_detached_worker_source_archive_parent_and_deadline_refused(self):
        for index,key,value in [(1,'worker_pid',102),(1,'parent_pid',99),(1,'source','b'*40),(1,'archive','/other'),(1,'deadline',float('nan')),(1,'finished_at',1001.),(1,'counter_initialized_in_worker',False),(1,'max_inflight',3),(2,'native_modules',['tokenizers']),(3,'parent_state',dict(native_modules=[],python_threads=2,os_threads=2))]:
            args=self.fixture();args[index][key]=value
            self.assertFalse(s.binding_valid(*args),(index,key))

    def test_missing_incomplete_unknown_live_or_failed_supervision_refused(self):
        for field,value in [('complete',False),('scripted',False),('live_evidence',True),('recorded',7),('unknown_usage_calls',1)]:
            args=self.fixture();args[4][field]=value;self.assertFalse(s.binding_valid(*args))
        for field,value in [('status','timed_out'),('shutdown_verified',False),('worker_exitcode',1),('finished_before_deadline',False)]:
            args=self.fixture();args[0][-1][field]=value;self.assertFalse(s.binding_valid(*args))
        args=self.fixture();args[0]=[];self.assertFalse(s.binding_valid(*args))
        args=self.fixture();args[0][0]['target']='unrelated';self.assertFalse(s.binding_valid(*args))

    def test_fresh_parent_guard_rejects_loaded_native_or_threads(self):
        for state in [dict(native_modules=['tokenizers'],python_threads=1,os_threads=1),dict(native_modules=[],python_threads=2,os_threads=2),dict(native_modules=[],python_threads=1,os_threads=2)]:
            with patch.object(s,'parent_state',return_value=state),self.assertRaises(ValueError):s.require_fresh_parent()
        with patch.object(s,'parent_state',return_value=dict(native_modules=[],python_threads=1,os_threads=1)):
            self.assertEqual(s.require_fresh_parent()['native_modules'],[])

if __name__=='__main__':unittest.main()

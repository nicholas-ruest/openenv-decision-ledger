import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import pytest
from paired_coordinator import coordinate, schedule


def test_counterbalanced_unique_schedule():
    jobs = schedule(('d3','d4'), (1,2))
    assert len(jobs) == 32
    assert [j[0] for j in jobs[:4]] == ['baseline','preserve_supplied','preserve_supplied','baseline']


def test_expiry_prevents_worker():
    r = coordinate([1], lambda *a: pytest.fail('must not launch'), lambda *a: None, 1, True, now=lambda: 2)
    assert not r['complete'] and not r['completed']


def test_no_admission_no_work():
    with pytest.raises(ValueError): coordinate([], None, None, 100, False)


def test_fatal_saved_once_no_retry():
    calls, saved = [], []
    def worker(job, deadline):
        calls.append(job)
        return {'fatal_guard_failure': True}
    r = coordinate([1,2], worker, lambda *a: saved.append(a), 10, True, now=lambda: 0)
    assert calls == [1] and len(saved) == 1 and not r['complete']


def test_save_failure_prevents_next_worker():
    calls = []
    def worker(job, deadline): calls.append(job); return {}
    def save(*args): raise OSError('disk failure')
    with pytest.raises(OSError): coordinate([1,2], worker, save, 10, True, now=lambda: 0)
    assert calls == [1]
import sys
import time
from pathlib import Path
import pytest
from paired_coordinator import isolated_worker, coordinate


def test_real_success_discards_output(tmp_path):
    r = isolated_worker([sys.executable, '-c', "print('fixture output')"], tmp_path, time.monotonic()+3)
    assert r['process_status'] == 'completed' and not r['fatal_guard_failure']
    assert 'output' not in r and r['provider_billing_stopped'] is None


def test_real_failure_stops_next_process(tmp_path):
    calls, saved = [], []
    def worker(job, deadline):
        calls.append(job)
        return isolated_worker([sys.executable, '-c', 'raise SystemExit(7)'], tmp_path, deadline)
    r = coordinate([1,2], worker, lambda *args: saved.append(args), time.monotonic()+3, True)
    assert calls == [1] and len(saved) == 1 and r['reason'] == 'fatal_guard'
    assert saved[0][1]['returncode'] == 7


def test_real_timeout_kills_process_group(tmp_path):
    pidfile = tmp_path/'pid'
    code = ('import os,time,pathlib;pathlib.Path(' + repr(str(pidfile)) + ').write_text(str(os.getpid()));time.sleep(30)')
    r = isolated_worker([sys.executable,'-c',code], tmp_path, time.monotonic()+.3)
    assert r['process_status'] == 'deadline' and r['fatal_guard_failure']
    if pidfile.exists(): assert not Path('/proc/'+pidfile.read_text()).exists()


@pytest.mark.parametrize('deadline', [float('nan'),float('inf'),-1])
def test_bad_deadline_never_launches(tmp_path, deadline):
    with pytest.raises(ValueError): isolated_worker(['/missing-worker'], tmp_path, deadline)


def test_timeout_stops_descendant_ignoring_term(tmp_path):
    pidfile = tmp_path/'grandchild'
    child = 'import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(30)'
    code = ('import subprocess,sys,time,pathlib;p=subprocess.Popen([sys.executable,"-c",' + repr(child) + ']);'
            'pathlib.Path(' + repr(str(pidfile)) + ').write_text(str(p.pid));time.sleep(30)')
    r = isolated_worker([sys.executable,'-c',code], tmp_path, time.monotonic()+.4)
    assert r['process_status'] == 'deadline'
    assert pidfile.exists()
    stat = Path('/proc/'+pidfile.read_text()+'/stat')
    assert not stat.exists() or stat.read_text().split()[2] == 'Z'

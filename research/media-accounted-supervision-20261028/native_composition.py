"""Actual frozen-native composition; provider replies/cost counter scripted."""
import hashlib
import json
from pathlib import Path
import time
from accounted_supervisor import supervise_accounted
from accounting_archive import make_config
from fixture_counter import SyntheticByteCounter
from media_protocol import build

source=Path(__file__).parent;data=json.loads((source/'native-captures.json').read_text());plan=build(data['captures'],data['schema'])
worker=source/'native_worker.py';verifier=source/'native_verifier.py'
before=set(Path('/tmp/qe-arena-ws').glob('ep-*'))
result=supervise_accounted(Path('/accounted-composition-evidence'),worker,hashlib.sha256(worker.read_bytes()).hexdigest(),verifier,hashlib.sha256(verifier.read_bytes()).hexdigest(),plan,'screen',make_config(SyntheticByteCounter()),deadline=time.monotonic()+180)
if result['status']!='completed' or not result['archive_verified']:raise ValueError('accounted native composition failed')
if set(Path('/tmp/qe-arena-ws').glob('ep-*'))!=before:raise ValueError('native workspace set not restored')
proof=json.loads(Path('/accounted-composition-evidence/verification.json').read_text())
print(json.dumps({'status':result['status'],'independent_accounted_verification':True,'attempts_recomputed':proof['episodes_recomputed'],'counts':proof['report']['counts'],'workspace_set_restored':True,'counter_synthetic':True,'provider_responses_scripted':True,'new_model_calls':0,'arena_wrapper_equivalent':False}))

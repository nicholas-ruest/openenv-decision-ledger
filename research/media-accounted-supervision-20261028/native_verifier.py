"""Independent in-image verifier entrypoint; offline fixture ledger only."""
import json
import sys
import time
from pathlib import Path
from media_protocol import build
from accounting_archive import verify_archive
from fixture_counter import SyntheticByteCounter
from native_bridge import NativeBridge
from durable_phase import durable_new

root=Path(sys.argv[1]);config=json.loads(Path(sys.argv[2]).read_text());output=Path(sys.argv[3])
data=json.loads((Path(__file__).parent/'native-captures.json').read_text())
plan=build(data['captures'],data['schema']);bridge=NativeBridge(data['schema'],time.monotonic()+60)
proof=verify_archive(root,plan,data['schema'],'screen',config,SyntheticByteCounter(),json.loads((root/'fixture-ledger.json').read_text()),bridge.replay)
if bridge.opened!=bridge.closed:raise ValueError('verifier session cleanup required')
durable_new(output.parent,output.name,proof)

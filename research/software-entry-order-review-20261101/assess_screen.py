"""Original raw replay and original supervisor binding; no provider access."""
import json
import math
import guarded_transport as b
from pathlib import Path
import subprocess
import finite_caller as c


def assess(output,counter,path,expected):
    output=Path(output);report=c.assemble(output,counter,'screen',path,expected)
    receipt=output.with_suffix('.supervision.jsonl');events=[json.loads(x) for x in receipt.read_text().splitlines() if x] if receipt.exists() else []
    terminal=events[-1] if events else {};summary=json.loads((output/'complete.json').read_text()) if (output/'complete.json').exists() else {}
    binding=json.loads((output/'supervision-binding.json').read_text()) if (output/'supervision-binding.json').exists() else {}
    starts=[e for e in events if e.get('event')=='starting'];started=[e for e in events if e.get('event')=='started']
    bound=(len(starts)==len(started)==1 and starts[0].get('target')=='execute_phase' and 0<starts[0].get('wall_seconds',0)<=1200
        and type(binding.get('worker_pid')) is int and binding['worker_pid']==started[0].get('pid')==terminal.get('pid')
        and binding.get('case_audit_sha256')==expected and binding.get('archive')==str(output.resolve())
        and type(binding.get('deadline')) in (int,float) and math.isfinite(binding['deadline']))
    if (not bound or not report['complete'] or summary.get('complete') is not True or summary.get('scripted') is not False or summary.get('live_evidence') is not True
        or summary.get('assigned')!=8 or summary.get('recorded')!=8 or not 8<=summary.get('calls',0)<=16 or summary.get('unknown_usage_calls')!=0
        or terminal.get('event')!='terminal' or terminal.get('status')!='completed' or terminal.get('worker_exitcode')!=0
        or terminal.get('shutdown_verified') is not True or terminal.get('finished_before_deadline') is not True):
        return dict(kind='entry_order_incomplete_screen',complete=False,selection_passed=False,fitness_computed=False,model_improvement=False,leaderboard_gain=False)
    b.verify_clean_source(binding['source'])
    value=report['evidence'];value.update(kind='entry_order_supervised_screen',case_audit_sha256=expected,supervision_completed=True)
    module=Path(__file__).with_name('assess_qualification.mjs').as_uri()
    js="import {readFileSync} from 'node:fs';import {assessScreen} from "+json.dumps(module)+";console.log(JSON.stringify(assessScreen(JSON.parse(readFileSync(0,'utf8')))));"
    return json.loads(subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(value),text=True,capture_output=True,check=True).stdout)

"""Read-only original archive replay plus original supervisor completion binding."""
import json
from pathlib import Path
import subprocess
import paired_caller as c


def assess(output,counter,path,expected):
    output=Path(output);report=c.assemble(output,counter,'screen',path,expected)
    receipt=output.with_suffix('.supervision.jsonl')
    events=[json.loads(line) for line in receipt.read_text().splitlines() if line] if receipt.exists() else []
    terminal=events[-1] if events else {}
    summary=json.loads((output/'complete.json').read_text()) if (output/'complete.json').exists() else {}
    if (not report['complete'] or summary.get('complete') is not True or summary.get('scripted') is not False
        or summary.get('live_evidence') is not True or summary.get('assigned')!=8 or summary.get('recorded')!=8
        or summary.get('calls')!=8 or summary.get('unknown_usage_calls')!=0
        or summary.get('stopped_on_infrastructure_or_budget') is not False
        or terminal.get('event')!='terminal' or terminal.get('status')!='completed'
        or terminal.get('worker_exitcode')!=0 or terminal.get('shutdown_verified') is not True
        or terminal.get('finished_before_deadline') is not True):
        return dict(kind='top_level_note_incomplete_screen',complete=False,selection_passed=False,
            fitness_computed=False,model_improvement=False,leaderboard_gain=False)
    report.update(supervision_completed=True,all_assigned_in_denominator=True)
    module=Path(__file__).with_name('assess_qualification.mjs').as_uri()
    js="import {readFileSync} from 'node:fs';import {assessScreen} from "+json.dumps(module)+";console.log(JSON.stringify(assessScreen(JSON.parse(readFileSync(0,'utf8')))));"
    result=subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(report),text=True,capture_output=True,check=True)
    return json.loads(result.stdout)

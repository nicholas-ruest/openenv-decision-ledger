"""Independent sealed Native replay and original supervisor binding, no paid API."""
import json
from pathlib import Path
import subprocess
import assemble_qualification as assembly
import preserve_first as p


def assess(output,counter,path,expected):
    output=Path(output)
    report=assembly.assemble_screen(output,counter,path,expected)
    receipt=output.with_suffix('.supervision.jsonl')
    events=[json.loads(line) for line in receipt.read_text().splitlines() if line] if receipt.exists() else []
    terminal=events[-1] if events else {}
    if (not report['complete'] or terminal.get('event')!='terminal' or terminal.get('status')!='completed'
        or terminal.get('worker_exitcode')!=0 or not terminal.get('shutdown_verified')
        or not terminal.get('finished_before_deadline')):
        return dict(kind='preserve_first_incomplete_screen',complete=False,selection_passed=False,
                    model_improvement=False,leaderboard_gain=False,fitness_computed=False)
    report.update(supervision_completed=True,all_assigned_in_denominator=True)
    module=Path(__file__).with_name('assess_qualification.mjs').as_uri()
    js="import {readFileSync} from 'node:fs';import {assessScreen} from "+json.dumps(module)+";console.log(JSON.stringify(assessScreen(JSON.parse(readFileSync(0,'utf8')))));"
    result=subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(report),
                          text=True,capture_output=True,check=True)
    return json.loads(result.stdout)

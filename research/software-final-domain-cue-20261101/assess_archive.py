"""Read-only Native replay followed by descriptive pinned MetaHarness analysis.

Never authenticates provider replies or returns permission to select or execute.
"""
import json,subprocess
from pathlib import Path
import case_archive as archive
if Path(archive.__file__).resolve()!=Path(__file__).with_name('case_archive.py').resolve():
    raise ValueError('exact sibling archive assembler required')

def assess(output,counter,args):
    report=archive.assemble(output,counter,args)
    module=Path(__file__).with_name('assess_reconstruction.mjs').as_uri()
    script="import {readFileSync} from 'node:fs';import {assessReconstruction} from "+json.dumps(module)+";console.log(JSON.stringify(assessReconstruction(JSON.parse(readFileSync(0,'utf8')))));"
    result=subprocess.run(['node','--input-type=module','-e',script],input=json.dumps(report,allow_nan=False),text=True,capture_output=True,check=True)
    return json.loads(result.stdout)

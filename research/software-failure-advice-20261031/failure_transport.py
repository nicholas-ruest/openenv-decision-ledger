"""Source-guarded delegation to existing accounting/transport and supervision.

No new cap, route, token source or reservation implementation is introduced.
Live source/case admission remains unsealed; qualification cannot admit it.
"""
from datetime import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

import finite_qualification as finite_caller

ROOT=Path(__file__).resolve().parents[2]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def verify_dependencies():
    pins=json.loads(Path(__file__).with_name('transport-source-pins.json').read_text())
    for name,expected in pins.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('existing transport/accounting/supervisor dependency changed')


def verify_clean_source(expected):
    if (subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()!=expected
            or subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True).strip()):
        raise ValueError('exact clean immutable source required')


def operating_seconds(now=None):
    local=datetime.now(ZoneInfo('America/Toronto')) if now is None else now
    if local.tzinfo is None:raise ValueError('timezone-aware clock required')
    local=local.astimezone(ZoneInfo('America/Toronto'))
    seconds=min(1200,(local.replace(hour=23,minute=0,second=0,microsecond=0)-local).total_seconds())
    if seconds<=0:raise ValueError('fixed23:00Toronto stop reached')
    return seconds


def guarded_backend(args):
    # Order matters: no token lookup, route quote, backend or private artifact
    # inspection before the independently sealed live source/case requirement.
    finite_caller.require_live_ready(getattr(args,'case_audit',None),getattr(args,'case_audit_sha256',None))
    verify_clean_source(args.expected_source)
    operating_seconds()
    verify_dependencies()
    original=load('existing_failure_advice_financial_transport',ROOT/'research/software-public-pass-confirmation-20261031/caller.py')
    return original.LiveBackend(args.receipt,args.reconciliation,args.tokenizer,args.amendment_sha256)


def _qualification_entry(deadline,chunk,backend,counter,output):
    finite_caller.run_chunk(chunk,backend,counter,output,deadline)
    return 0


def supervise_qualification(chunk,backend,counter,output,seconds,*,now=None):
    if backend.scripted is not True:raise ValueError('scripted qualification backend required')
    if type(seconds) not in (int,float) or not math.isfinite(seconds) or not 0<seconds<=1200:
        raise ValueError('finite unchanged supervisor limit required')
    seconds=min(seconds,operating_seconds(now))
    output=Path(output);receipt=output.with_suffix('.supervision.jsonl')
    if output.exists() or receipt.exists():raise ValueError('fresh qualification archive and supervision receipt required')
    verify_dependencies()
    supervisor=load('existing_failure_advice_supervisor',ROOT/'integrations/software-repair/scripts/screen_deadline.py')
    result=supervisor.run_bounded(_qualification_entry,(chunk,backend,counter,output),seconds,receipt)
    return dict(result,scripted=True,live_evidence=False,remote_cancellation_attested=False)


def require_live_supervision(expected_source,output,case_audit=None,case_sha256=None):
    # Validate the immutable case lease before source inspection or any worker.
    finite_caller.require_live_ready(case_audit,case_sha256)
    verify_clean_source(expected_source)
    seconds=operating_seconds()
    verify_dependencies()
    if Path(output).exists() or Path(output).with_suffix('.supervision.jsonl').exists():
        raise ValueError('fresh live archive required')
    return seconds

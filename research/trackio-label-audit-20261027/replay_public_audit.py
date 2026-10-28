"""Reproduce sanitized public-metric findings from preserved numeric fixtures."""
import importlib.util
import json
import os
from pathlib import Path
from audit_task_labels import audit,event_step_audit

HERE=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('AUDIT_REPO_ROOT',HERE.parents[1]))


def reproduce():
    logs=json.loads((HERE/'compact-logs.json').read_text())
    pairs=json.loads((HERE/'series-values.json').read_text())
    records={k:[{'step':s,'value':v} for s,v in values] for k,values in pairs.items()}
    summary=json.loads((HERE/'summary.json').read_text())
    result=audit(summary,logs,records,(HERE/'schema-fields.py').read_text())
    spec=importlib.util.spec_from_file_location('step_learning',ROOT/'scripts/analyze-task-learning.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    result['groups']=helper.analyze(records)['groups']
    result['events']=event_step_audit(json.loads((HERE/'alert-step-records.json').read_text()),logs)
    result['mapping_complete']=False if not result['explicit_task_labels'] else result['mapping_complete']
    if result['raw_log_rows']!=148 or result['metric_values_cross_checked']!=1036 or result['mapping_complete']:
        raise ValueError('preserved public audit expectations changed')
    return result


if __name__=='__main__':print(json.dumps(reproduce(),indent=2))

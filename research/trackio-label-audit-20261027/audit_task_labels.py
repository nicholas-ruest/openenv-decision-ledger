"""Offline audit of public raw logs and metric joins; never infer task rotation."""
import ast
import hashlib
import json
import math


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()).hexdigest()


def allowlists(source):
    values={}
    for node in ast.parse(source).body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in ('STRING_CONFIG','NUMBER_CONFIG'):
                    value=ast.literal_eval(node.value)
                    if not isinstance(value,set) or not all(isinstance(v,str) for v in value):raise ValueError('literal field sets required')
                    values[target.id]=sorted(value)
    if set(values)!= {'STRING_CONFIG','NUMBER_CONFIG'}:raise ValueError('logging allowlists unavailable')
    return values


def identity(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value<1 or int(value)!=value:
        raise ValueError('recorded positive integer task ID required')
    return str(int(value))


def audit(summary,logs,records,source):
    config=summary.get('config') or {}
    if config.get('simulated') is True or config.get('recipe')=='cpu-dummy-simulation':raise ValueError('simulation is not target training')
    if len(logs)!=summary['num_logs']:raise ValueError('raw log count differs from summary')
    indexed={};labels={}
    for row in logs:
        step=row.get('step')
        if type(step) is not int or step<0 or step in indexed:raise ValueError('unique exact optimizer steps required')
        task=identity(row['step/task']);indexed[step]=row
        name=row.get('step/task_name')
        if name is not None:
            if not isinstance(name,str) or not name:raise ValueError('explicit task name required')
            if task in labels and labels[task]!=name:raise ValueError('conflicting observed labels')
            labels[task]=name
    numeric_ids={identity(r['step/task']) for r in logs}
    explicit=config.get('task_id_map')
    if explicit is not None:
        if not isinstance(explicit,dict) or set(explicit)!=numeric_ids or not all(isinstance(v,str) and v for v in explicit.values()) or len(set(explicit.values()))!=len(explicit):raise ValueError('complete explicit one-to-one mapping required')
        if any(k in labels and labels[k]!=v for k,v in explicit.items()):raise ValueError('config and per-step labels conflict')
        labels=dict(explicit)
    if len(set(labels.values()))!=len(labels):raise ValueError('ambiguous task name mapping')
    checked=0
    for name,rows in records.items():
        seen=set()
        for item in rows:
            step=item['step'];value=item['value']
            if type(step) is not int or step in seen or step not in indexed:raise ValueError('invalid metric step join')
            seen.add(step)
            if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('finite numeric metric required')
            if name not in indexed[step] or indexed[step][name]!=value:raise ValueError('metric series differs from raw log')
            checked+=1
        if seen!=set(indexed):raise ValueError('incomplete metric series is unavailable, not zero')
    schema=allowlists(source)
    return {'raw_log_rows':len(logs),'raw_fields':sorted({k for r in logs for k in r}),
            'optimizer_step_min':min(indexed),'optimizer_step_max':max(indexed),
            'metric_values_cross_checked':checked,'numeric_task_ids':sorted(numeric_ids),
            'explicit_task_labels':labels,'mapping_complete':set(labels)==numeric_ids,
            'mapping_inferred_from_rotation':False,'reweighting_by_named_family_supported':set(labels)==numeric_ids,
            'current_logging_config_fields':schema,'training_time_logging_source_attested':False,
            'raw_logs_sha256':digest(logs),'records_sha256':digest(records),
            'is_training_or_improvement_claim':False}


def event_step_audit(alerts,logs):
    """Keep alert and optimizer step domains separate; never infer an offset."""
    alert_steps={r['step'] for r in alerts if type(r.get('step')) is int}
    retry_steps={r['step'] for r in logs if r.get('step/retries',0)>0}
    return {'alert_rows':len(alerts),'distinct_alert_steps':sorted(alert_steps),
            'optimizer_retry_steps':sorted(retry_steps),
            'same_number_overlap':sorted(alert_steps & retry_steps),
            'alert_to_task_attribution':None,'inferred_offset_applied':False}

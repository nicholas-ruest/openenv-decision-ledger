"""Pure local archive/reservation consistency. Never authenticates a provider or funds work."""
import hashlib,math
from decimal import Decimal,InvalidOperation
import json

def need(value,message):
    if not value:raise ValueError(message)

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def ledger(raw):
    need(type(raw) is bytes and (not raw or raw.endswith(b'\n')),'original complete ledger bytes required')
    rows=[json.loads(x) for x in raw.splitlines() if x.strip()];labels=set()
    for r in rows:
        need(type(r.get('label')) is str and r['label'] and r['label'] not in labels,'retained unique reservation labels required')
        labels.add(r['label'])
        try:amount=Decimal(r['usd'])
        except (InvalidOperation,TypeError,KeyError):raise ValueError('retained positive reservation required')
        need(amount.is_finite() and amount>0,'retained positive reservation required')
    return rows

def check(*,events,binding,startup,launch,summary,report,attempts,before,after,prices,source,archive):
    """Inputs must come from separately leased/replayed artifacts; JSON is not provenance."""
    need(type(source) is str and len(source)==40 and all(c in '0123456789abcdef' for c in source),'exact source identity required')
    need(len(events)==3 and [e.get('event') for e in events]==['starting','started','terminal'],'one original supervisor lifecycle required')
    first,started,end=events;pid=binding.get('worker_pid');parent=binding.get('parent_pid');deadline=binding.get('deadline')
    need(first.get('target')=='worker_entry' and type(first.get('wall_seconds')) in (int,float) and math.isfinite(first['wall_seconds']) and 0<first['wall_seconds']<=1200,'original worker target and bound required')
    need(type(pid) is int and pid>0 and type(parent) is int and parent>0 and pid!=parent and pid==started.get('pid')==end.get('pid')==startup.get('worker_pid') and parent==startup.get('parent_pid')==launch.get('parent_pid'),'original process binding required')
    need(end.get('status')=='completed' and type(end.get('worker_exitcode')) is int and end['worker_exitcode']==0 and end.get('shutdown_verified') is True and end.get('finished_before_deadline') is True,'verified original shutdown required')
    need(type(end.get('elapsed_seconds')) in (int,float) and math.isfinite(end['elapsed_seconds']) and 0<=end['elapsed_seconds']<=first['wall_seconds'],'bounded elapsed time required')
    need(type(deadline) in (int,float) and math.isfinite(deadline) and startup.get('deadline')==deadline,'one finite original deadline required')
    need(binding.get('source')==startup.get('source')==launch.get('source')==report.get('source')==source and binding.get('archive')==launch.get('archive')==archive,'exact source and archive binding required')
    need(binding.get('mode')==startup.get('mode')==launch.get('mode')=='guarded_original_backend_worker' and binding.get('counter_initialized_in_worker') is True and binding.get('phase_complete') is True,'original guarded worker required')
    need(startup.get('native_modules')==[] and startup.get('python_threads')==startup.get('os_threads')==1 and launch.get('parent_state')==dict(native_modules=[],python_threads=1,os_threads=1),'fresh single-threaded original parent required')
    need(summary.get('kind')=='case_bound_finite_phase' and summary.get('complete') is True and summary.get('assigned')==summary.get('recorded')==8 and summary.get('unknown_usage_calls')==0 and summary.get('retries')==0 and summary.get('max_inflight_requests')==2,'complete unchanged finite phase required')
    need(all(type(summary.get(k)) is int for k in ('assigned','recorded','unknown_usage_calls','retries','max_inflight_requests','observed_calls')),'strict original summary counts required')
    need(all(type(report.get(k)) is int for k in ('assigned','independently_replayed_terminal_attempts')),'strict original reconstruction counts required')
    need(report.get('kind')=='case_bound_archive_reconstruction' and report.get('all_assigned_in_denominator') is True and report.get('all_terminal_attempts_reconstructed') is True and report.get('independently_replayed_terminal_attempts')==8 and report.get('assigned')==8 and len(report.get('rows',[]))==len(attempts)==8,'all eight independent terminal reconstructions required')
    need(type(before) is bytes and type(after) is bytes and after.startswith(before),'all original ledger bytes retained required')
    old=ledger(before);new=ledger(after);old_labels={r['label'] for r in old};appended=new[len(old):];by_label={r['label']:r for r in appended};wanted=set();calls=0
    rates={k:Decimal(str(prices[k])) for k in ('input','output')}
    need(all(x.is_finite() and x>=0 for x in rates.values()),'finite original route rates required')
    response_ids=set()
    for row,attempt in zip(report['rows'],attempts):
        record=attempt['record'];requests=attempt['requests'];job=row['job'];stem=job['attempt_id'];labels=[stem+':'+str(i) for i in range(len(requests))]
        need(digest(record['job'])==digest(job) and record['reservations']==record['calls']==labels and record['response_ids']==attempt['response_ids'] and len(labels)==len(record['response_ids'])==row['model_responses'] and 1<=len(labels)<=2,'one original reservation per complete call/reply required')
        need(record.get('unknown_usage') is False and row.get('verified') is True and row.get('recorded') is True and row.get('replay_only') is True and row.get('provider_provenance_attested') is False,'independent replay without unknown usage required')
        need(all(record.get(k)==v for k,v in row.items() if k not in ('verified','recorded','replay_only','provider_provenance_attested')),'original record differs from independent replay')
        for reply in record['response_ids']:
            need(type(reply) is str and reply and reply not in response_ids,'unique original reply identities required');response_ids.add(reply)
        for turn,(label,request) in enumerate(zip(labels,requests)):
            need(label not in wanted and label not in old_labels and label in by_label,'unique newly appended original reservation required');wanted.add(label);r=by_label[label];bound=request['max_tokens']
            need(type(bound) is int and 0<bound<=8096 and (turn!=0 or bound==6000) and type(r.get('generation_bound')) is int and r['generation_bound']==bound and type(r.get('prompt_bound')) is int and r['prompt_bound']==28672,'unchanged request reservation bounds required')
            amount=(Decimal(28672)*rates['input']+Decimal(bound)*rates['output'])/Decimal(1000000)*Decimal('1.10')
            need(Decimal(r['usd'])==amount,'original conservative reservation quote required')
        calls+=len(labels)
    need(set(by_label)==wanted and len(appended)==len(wanted) and summary.get('observed_calls')==calls,'no dropped or unexplained appended reservations required')
    return dict(kind='local_archive_reservation_consistency',consistent=True,assigned=8,calls=calls,retained_reservations=len(old),new_reservations=len(appended),ledger_prefix_retained=True,provider_provenance_attested=False,actual_credit_verified=False,root_current_spending_attested=False,execution_authorized=False,selection_passed=False,confirmation_authorized=False,model_improvement=False)

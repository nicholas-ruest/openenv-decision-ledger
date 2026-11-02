"""Synthetic local artifacts only; no Native, original provider or actual ledger."""
import copy,json,unittest
from decimal import Decimal
import archive_custody as c

def fixture():
    source='a'*40;archive='/synthetic/unexecuted';mode='guarded_original_backend_worker'
    rows=[];attempts=[];new=[]
    old=(json.dumps(dict(label='retained',usd='1'))+'\n').encode()
    for sample in range(4):
        for arm in ('common_review','final_domain_reminder') if sample%2==0 else ('final_domain_reminder','common_review'):
            j=dict(namespace='final-review-domain-reminder-20261101',phase='screen',task_id='software_repair-ignore-d3',seed=1,sample=sample,arm=arm);j['attempt_id']=c.digest(j)
            labels=[j['attempt_id']+':'+str(turn) for turn in (0,1)];replies=[x+'-reply' for x in labels]
            record=dict(job=j,reservations=labels,calls=labels,response_ids=replies,unknown_usage=False,model_responses=2,category='full',semantic_reward=1)
            rows.append(dict(record,verified=True,recorded=True,replay_only=True,provider_provenance_attested=False));requests=[]
            for turn,label in enumerate(labels):
                bound=6000 if turn==0 else 1000;requests.append(dict(max_tokens=bound))
                amount=(Decimal(28672)*Decimal('.2')+Decimal(bound)*Decimal('2.5'))/Decimal(1000000)*Decimal('1.10')
                new.append(dict(label=label,usd=str(amount),prompt_bound=28672,generation_bound=bound))
            attempts.append(dict(record=record,requests=requests,response_ids=replies))
    return dict(events=[dict(event='starting',target='worker_entry',wall_seconds=1200),dict(event='started',pid=2),dict(event='terminal',pid=2,status='completed',worker_exitcode=0,shutdown_verified=True,finished_before_deadline=True,elapsed_seconds=10)],binding=dict(worker_pid=2,parent_pid=1,deadline=100,source=source,archive=archive,mode=mode,counter_initialized_in_worker=True,phase_complete=True),startup=dict(worker_pid=2,parent_pid=1,deadline=100,source=source,mode=mode,native_modules=[],python_threads=1,os_threads=1),launch=dict(parent_pid=1,source=source,archive=archive,mode=mode,parent_state=dict(native_modules=[],python_threads=1,os_threads=1)),summary=dict(kind='case_bound_finite_phase',complete=True,assigned=8,recorded=8,unknown_usage_calls=0,retries=0,max_inflight_requests=2,observed_calls=16),report=dict(kind='case_bound_archive_reconstruction',source=source,assigned=8,rows=rows,all_assigned_in_denominator=True,all_terminal_attempts_reconstructed=True,independently_replayed_terminal_attempts=8),attempts=attempts,before=old,after=old+''.join(json.dumps(r)+'\n' for r in new).encode(),prices=dict(input=.2,output=2.5),source=source,archive=archive)

class Custody(unittest.TestCase):
    def test_complete_consistency_retains_every_row_without_authority(self):
        f=fixture();before=copy.deepcopy(f);r=c.check(**f);self.assertEqual(f,before);self.assertEqual(r['retained_reservations'],1);self.assertEqual(r['new_reservations'],16)
        for k in ['provider_provenance_attested','actual_credit_verified','root_current_spending_attested','execution_authorized','selection_passed','confirmation_authorized','model_improvement']:self.assertIs(r[k],False)
    def test_supervisor_source_archive_pid_deadline_and_shutdown(self):
        for field,value in [('worker_pid',3),('source','b'*40),('archive','/other'),('deadline',float('nan')),('mode','scripted_qualification')]:
            f=fixture();f['binding'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):c.check(**f)
        f=fixture();f['events'][-1]['shutdown_verified']=False
        with self.assertRaises(ValueError):c.check(**f)
    def test_retained_prefix_missing_extra_duplicate_or_changed_quote(self):
        edits=[lambda f:f.update(after=f['after'][len(f['before']):]),lambda f:f.update(after=f['after']+b'{"label":"extra","usd":"1"}\n'),lambda f:f.update(after=f['after']+f['before']),lambda f:f.update(after=f['after'].replace(b'"generation_bound": 6000',b'"generation_bound": 5999',1)),lambda f:f.update(after=f['after'].replace(b'"usd": "0.',b'"usd": "1.',1))]
        for edit in edits:
            f=fixture();edit(f)
            with self.assertRaises(ValueError):c.check(**f)
    def test_missing_unknown_reused_reply_or_unreserved_call(self):
        for edit in [lambda f:f['attempts'].pop(),lambda f:f['attempts'][0]['record'].update(unknown_usage=True),lambda f:f['attempts'][0]['requests'][0].update(max_tokens=5999),lambda f:f['summary'].update(observed_calls=15),lambda f:f['summary'].update(unknown_usage_calls=False),lambda f:f['report']['rows'][0].update(semantic_reward=0)]:
            f=fixture();edit(f)
            with self.assertRaises(ValueError):c.check(**f)
    def test_reused_reply_identity_refused(self):
        f=fixture();f['attempts'][1]['record']['response_ids'][0]=f['attempts'][0]['record']['response_ids'][0];f['attempts'][1]['response_ids'][0]=f['attempts'][0]['response_ids'][0]
        with self.assertRaises(ValueError):c.check(**f)
    def test_unverified_reconstruction_cannot_become_custody(self):
        f=fixture();f['report']['rows'][0]['verified']=False
        with self.assertRaises(ValueError):c.check(**f)
    def test_provider_credit_and_root_cannot_be_attested_by_json(self):
        f=fixture();f['summary'].update(actual_credit_verified=True,root_current_spending_attested=True,provider_provenance_attested=True);r=c.check(**f)
        self.assertFalse(r['actual_credit_verified']);self.assertFalse(r['provider_provenance_attested']);self.assertFalse(r['root_current_spending_attested'])
if __name__=='__main__':unittest.main()

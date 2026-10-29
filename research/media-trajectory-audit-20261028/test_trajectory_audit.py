import copy
import json
import unittest
from pathlib import Path

from media_protocol import IMAGE, RUNTIME, build, digest, messages
from trajectory_audit import audit_episode, audit_phase, assess_phase, confirm, action_from_reply


def fixture_data():
    path = Path(__file__).resolve().parent.parent / 'media-protocol-20261027/native-captures.json'
    if not path.exists():
        path = Path(__file__).resolve().parent.parent / 'research/media-protocol-20261027/native-captures.json'
    data = json.loads(path.read_text())
    return data, build(data['captures'], data['schema'])


def synthetic_episode(phase='screen', position=0, sample=0, reward=1):
    data, plan = fixture_data()
    group = plan['phases'][phase]['groups'][position]
    native = next(c for c in data['captures'] if c['phase']==phase and (c['task_id'],c['seed'])==(group['task_id'],group['seed']))
    label = f'{phase}-{position}-{sample}'
    episode = {k:copy.deepcopy(native[k]) for k in ('task_id','seed','reset_transport','workspace','image','runtime_source','uid_shell')}
    episode.update(phase=phase,sample=sample,sampling_sha256=plan['sampling_sha256'],events=[])
    ledger=[]; history=messages(episode['reset_transport'],data['schema'])
    def add(action, done=False, reward=0, error='', success=True):
        history=messages(episode['reset_transport'],data['schema'])
        for old in episode['events']:
            history.extend([{'role':'assistant','content':old['response']['content']},{'role':'user','content':json.dumps(old['native'],sort_keys=True,separators=(',',':'))}])
        i=len(episode['events']); name=f'{label}-{i}'
        transport={'done':done,'reward':reward,'observation':{'success':success,'error':error,'output':'graded' if done else ''}}
        text=json.dumps(action)
        episode['events'].append({'kind':'call','status':'returned','call_id_sha256':digest('call-'+name),'reservation_label':name,'request_sha256':digest(history),
                                 'response':{'response_id_sha256':digest('reply-'+name),'finish_reason':'stop','content':text,'usage':{'prompt_tokens':100,'completion_tokens':10}},'native':transport})
        ledger.append({'label':name,'usd':'0.01','prompt_bound':200,'generation_bound':100})
        history.extend([{'role':'assistant','content':text},{'role':'user','content':json.dumps(transport,sort_keys=True,separators=(',',':'))}])
    add({'action_type':'evaluate'}, True, reward, success=bool(reward))
    return episode, ledger, data['schema'], plan, add


def echo_replay(episode):
    # Test double only. Native TCP script supplies the real callback in CI.
    def replay(task,seed,actions):
        assert (task,seed)==(episode['task_id'],episode['seed'])
        return {**{k:episode[k] for k in ('image','runtime_source','uid_shell','reset_transport','workspace')},
                'transports':[e['native'] for e in episode['events'] if 'native' in e]}
    return replay


class TrajectoryTests(unittest.TestCase):
    def setUp(self):
        self.e,self.ledger,self.schema,self.plan,self.add=synthetic_episode()
    def audit(self,replay=None):
        return audit_episode(self.e,self.plan,self.schema,self.ledger,replay or echo_replay(self.e))
    def failure(self, category):
        self.assertEqual(self.audit()['category'],category)
        self.assertIsNone(self.audit()['semantic_reward'])
    def test_full_and_wrong_success_flag(self):
        self.assertEqual(self.audit()['semantic_reward'],1)
        self.e['events'][0]['native'].update(reward=0)
        self.e['events'][0]['native']['observation']['success']=False
        self.assertEqual(self.audit()['category'],'wrong')
    def test_fractional_and_boolean_reward_rejected(self):
        for reward in (.5,True,float('nan')):
            self.e['events'][0]['native']['reward']=reward
            with self.assertRaises(ValueError):self.audit()
    def test_incomplete_and_postterminal_rejected(self):
        self.e['events'][0]['native']['done']=False
        self.e['events'][0]['native']['reward']=0
        with self.assertRaises(ValueError):self.audit()
        self.e['events'][0]['native']['done']=True
        self.e['events'].append({'kind':'budget','reason':'actions'})
        with self.assertRaises(ValueError):self.audit()
    def test_duplicate_json_unknown_field_and_schema_copy_format(self):
        for text in ('{"action_type":"evaluate","action_type":"exec"}', '{"action_type":"evaluate","unknown":1}',json.dumps(self.schema['action']),'{"action_type":NaN}','[]','{"action_type":"evaluate","metadata":{"x":1e309}}'):
            event=self.e['events'][0];event.pop('native',None);event['response']['content']=text
            self.failure('format')
    def test_invalid_action_cannot_claim_native_result(self):
        self.e['events'][0]['response']['content']='not json'
        with self.assertRaises(ValueError):self.audit()
    def test_truncation_not_wrong(self):
        self.e['events'][0].pop('native');self.e['events'][0]['response']['finish_reason']='length'
        self.failure('truncation')
    def test_provider_timeout_and_filter_separate(self):
        event=self.e['events'][0];event.pop('native');event['response']['finish_reason']='content_filter'
        self.failure('provider')
        event.pop('response');event['status']='timeout'
        self.failure('provider')
    def test_native_exception_unscored(self):
        event=self.e['events'][0];event.pop('native');event['native_error']='verifier'
        self.failure('execution')
    def test_native_tool_timeout_separate(self):
        native=self.e['events'][0]['native'];native['done']=False;native['reward']=0;native['observation']['error']='timed out'
        self.failure('execution')
    def test_recoverable_nonterminal_exit_error_can_solve(self):
        self.e['events'].clear();self.ledger.clear()
        self.add({'action_type':'exec','command':'false'},False,error='exit code 1',success=False)
        self.add({'action_type':'evaluate'},True,1)
        self.assertEqual(self.audit()['category'],'full')
    def test_action_autograde_keeps_budget_separate(self):
        for explicit in (False,True):
            self.e['events'].clear();self.ledger.clear()
            for i in range(32):self.add({'action_type':'evaluate' if explicit and i==31 else 'exec','command':'true'},i==31,1 if i==31 else 0)
            result=self.audit()
            self.assertEqual(result['category'],'full' if explicit else 'budget')
            self.assertEqual(result['terminal_reward_observed'],1)
    def test_local_budget_stop_no_call_is_retained(self):
        self.e['events']=[{'kind':'budget','reason':'context'}]
        result=self.audit();self.assertEqual(result['category'],'budget');self.assertEqual(result['calls'],0)
    def test_reset_workspace_prompt_and_settings_mismatch(self):
        for key in ('workspace','reset_transport','sampling_sha256','runtime_source'):
            saved=copy.deepcopy(self.e[key]);self.e[key]={} if isinstance(saved,dict) else 'bad'
            with self.assertRaises(ValueError):self.audit()
            self.e[key]=saved
    def test_wrong_request_history(self):
        self.e['events'][0]['request_sha256']='0'*64
        with self.assertRaises(ValueError):self.audit()
    def test_replay_tampering(self):
        def replay(t,s,a):
            out=copy.deepcopy(echo_replay(self.e)(t,s,a));out['transports'][0]['reward']=0;return out
        with self.assertRaises(ValueError):self.audit(replay)
    def test_missing_overbound_and_nonfinite_reservation(self):
        for change in ('missing','usage','cap','nan'):
            e,l,s,p,_=synthetic_episode()
            if change=='missing':l=[]
            if change=='usage':e['events'][0]['response']['usage']['completion_tokens']=101
            if change=='cap':l[0]['generation_bound']=4097
            if change=='nan':l[0]['usd']='NaN'
            with self.assertRaises(ValueError):audit_episode(e,p,s,l,echo_replay(e))
    def test_no_provider_execution_or_authentication_claim(self):
        r=self.audit();self.assertFalse(r['provider_authenticated']);self.assertFalse(r['reservation_chronology_attested']);self.assertFalse(r['is_training'])
    def test_schema_change_requires_new_implementation(self):
        s=copy.deepcopy(self.schema);s['action']['additionalProperties']=True
        with self.assertRaises(ValueError):action_from_reply('{"action_type":"evaluate"}',s)
    def test_protocol_rewrite_rejected(self):
        self.plan['phases']['screen']['groups'][0]['seed']+=1
        with self.assertRaises(ValueError):self.audit()
    def test_duplicate_response_and_reservation_within_episode(self):
        self.e['events'].clear();self.ledger.clear()
        self.add({'action_type':'exec','command':'true'})
        self.add({'action_type':'evaluate'},True,1)
        for field in ('reservation_label','response'):
            saved=copy.deepcopy(self.e['events'][1][field]);self.e['events'][1][field]=copy.deepcopy(self.e['events'][0][field])
            with self.assertRaises(ValueError):self.audit()
            self.e['events'][1][field]=saved
    def test_cumulative_generation_reservation_checked_before_next_call(self):
        self.e['events'].clear();self.ledger.clear()
        self.add({'action_type':'exec','command':'true'})
        self.add({'action_type':'evaluate'},True,1)
        self.ledger[0]['generation_bound']=4090
        self.e['events'][0]['response']['usage']['completion_tokens']=4090
        with self.assertRaises(ValueError):self.audit()


class PhaseTests(unittest.TestCase):
    def rows(self,phase):
        result=[]
        for position in range(4):
            for sample in range(4):
                e,l,s,p,_=synthetic_episode(phase,position,sample,int(sample!=0))
                result.append(audit_episode(e,p,s,l,echo_replay(e)))
        return result,p
    def test_complete_denominator_and_productive_confirmation(self):
        a,p=self.rows('screen');b,_=self.rows('confirmation');out=confirm(a,b,p)
        self.assertTrue(out['all_sampled_cells_provisional_signal']);self.assertFalse(out['model_improvement_claim'])
    def test_failure_is_not_productive_wrong(self):
        rows,p=self.rows('screen')
        for row in rows:
            if row['category']=='wrong':row.update(category='provider',semantic_reward=None)
        report=assess_phase(rows,p,'screen');self.assertEqual(report['productive_groups'],0)
        self.assertEqual(report['full_fraction_all_attempts'],.75);self.assertEqual(report['full_fraction_valid'],1)
    def test_missing_duplicate_phase_and_call_reuse_rejected(self):
        rows,p=self.rows('screen')
        for variant in (rows[:-1],rows[:-1]+[rows[0]]):
            with self.assertRaises(ValueError):assess_phase(variant,p,'screen')
        rows[-1]['call_ids']=rows[0]['call_ids']
        with self.assertRaises(ValueError):assess_phase(rows,p,'screen')
    def test_cross_phase_call_reuse_rejected(self):
        a,p=self.rows('screen');b,_=self.rows('confirmation');b[-1]['response_ids']=a[0]['response_ids']
        with self.assertRaises(ValueError):confirm(a,b,p)
    def test_bound_phase_entrypoint_retains_unused_reservations(self):
        episodes=[];ledger=[]
        for pos in range(4):
            for sample in range(4):
                e,l,s,p,_=synthetic_episode(position=pos,sample=sample);episodes.append(e);ledger+=l
        ledger.append({'label':'reserved-not-dispatched','usd':'.01','prompt_bound':200,'generation_bound':100})
        def replay(task,seed,actions):return echo_replay(next(e for e in episodes if (e['task_id'],e['seed'])==(task,seed)))(task,seed,actions)
        report=audit_phase(episodes,p,s,ledger,replay,'screen')
        self.assertEqual(report['reservation_labels_without_observed_calls'],['reserved-not-dispatched'])
        self.assertFalse(report['reservation_refunds'])


if __name__=='__main__':unittest.main()

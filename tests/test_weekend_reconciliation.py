"""Source-backed repairs must preserve raw data, identities and field coverage."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from unittest.mock import patch

from operacao2026 import weekend
from operacao2026.weekend_reconciliation import load_review, reconcile, session_review

ROOT=Path(__file__).resolve().parents[1]


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.event=weekend.load_event(ROOT/'operacao2026/eventos/mexico2026.json')
        self.review=load_review(ROOT,self.event)
        self.fp3=next(s for s in self.event['sessions'] if s['session_name']=='Practice 3')
        self.qualifying=next(s for s in self.event['sessions'] if s['session_name']=='Qualifying')

    def data(self):
        return dict(drivers=[],session_result=[dict(driver_number=30,position=9,duration=78.113,number_of_laps=28)],
                    pit=[dict(driver_number=236,date='2026-10-31T17:27:39Z'),
                         dict(driver_number=30,date='2026-10-31T17:55:34Z')])

    def test_repair_is_documented_and_does_not_modify_the_raw_capture(self):
        raw=self.data();original=deepcopy(raw)
        output,audit=reconcile(raw,self.fp3,self.review)
        self.assertEqual(raw,original)
        self.assertEqual(output['drivers'][0]['full_name'],'Liam LAWSON')
        self.assertEqual([r['driver_number'] for r in output['pit']],[30])
        self.assertEqual(audit['acoes'][0]['indices_fonte'],[0])
        self.assertTrue(audit['acoes'][1]['fontes'])

    def test_profile_requires_the_reviewed_result_and_rejects_a_conflicting_name(self):
        raw=self.data();raw['session_result'][0]['duration']=79
        with self.assertRaisesRegex(ValueError,'native result'):
            reconcile(raw,self.fp3,self.review)
        raw=self.data();raw['drivers']=[dict(driver_number=30,first_name='Another',last_name='Driver',team_name='Racing Bulls')]
        with self.assertRaisesRegex(ValueError,'reviewed identity'):
            reconcile(raw,self.fp3,self.review)

    def test_in_session_unknown_number_is_not_excluded_as_earlier_context(self):
        raw=self.data();raw['pit'][0]['date']='2026-10-31T17:31:00Z'
        output,audit=reconcile(raw,self.fp3,self.review)
        self.assertEqual(output['pit'][0]['driver_number'],236)
        self.assertEqual(audit['acoes'][0]['indices_fonte'],[])
        with self.assertRaises(weekend.DriverIdentityUnavailable):
            weekend.verify_driver_profiles(output)

    def test_disqualification_is_not_a_numeric_position_or_a_valid_phase_time(self):
        raw=dict(drivers=[dict(driver_number=30,full_name='Liam LAWSON',team_name='Racing Bulls')],
                 session_result=[dict(driver_number=30,position=None,dsq=False,duration=[None,77.207,77.029],number_of_laps=0)],pit=[])
        original=deepcopy(raw)
        output,audit=reconcile(raw,self.qualifying,self.review)
        row=weekend.session_times(output,self.qualifying)[0]
        self.assertEqual(row['status'],'DSQ')
        self.assertIsNone(row['posicao'])
        self.assertIsNone(row['duracao'])
        self.assertEqual([row[k] for k in ('q1','q2','q3')],[None,None,None])
        self.assertIn('final_qualifying',row['fonte_validacao'])
        self.assertEqual(audit['acoes'][-1]['anterior']['duration'],[None,77.207,77.029])
        self.assertEqual(raw,original)

    def test_review_cannot_cross_a_meeting_or_session_date(self):
        session=dict(self.fp3,meeting_key=99)
        with self.assertRaisesRegex(ValueError,'Foreign adjudication session'):
            session_review(self.review,session)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'operacao2026/adjudicacoes/2026-19-rodriguez.json';path.parent.mkdir(parents=True)
            altered=deepcopy(self.review);altered['identidade']['rodada']=18;path.write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError,'identity'):
                load_review(tmp,self.event)

    def test_reviewed_zero_exclusion_recalculates_coverage_without_interpolation(self):
        from tests.test_race_weather import event,observation,window,summarize_sensors
        session=dict(session_key=7,meeting_key=9,session_name='Race',date_start='2024-01-01T10:00:00Z')
        data=dict(race_control=[event('10:00:00','SESSION STARTED'),event('10:04:00','SESSION FINISHED')],
                  weather=[observation('10:00:30',air_temperature=25,track_temperature=40),
                           observation('10:01:30',air_temperature=25,track_temperature=0),
                           observation('10:02:30',air_temperature=25,track_temperature=41),
                           observation('10:03:30',air_temperature=25,track_temperature=42)])
        original=deepcopy(data)
        review=dict(id='synthetic',sha256='0'*64,meeting_key=9,fontes={'weather':dict(url='https://www.fia.com/example',sha256='1'*64)},
                    sessoes={'7':dict(session_name='Race',inicio_utc=session['date_start'],exclusoes_clima=[
                        dict(date='2024-01-01T10:01:30Z',track_temperature=0,anterior=40,posterior=41,fontes=['weather'])])})
        result=weekend.observed_weather(data,session,review)
        track=result['campos']['track_temperature']
        self.assertEqual(track['n_medicoes_validas'],3)
        self.assertEqual(track['media_amostras'],41)
        self.assertEqual(track['cobertura_bins_60s'],.75)
        self.assertFalse(track['elegivel'])  # A reviewed exclusion cannot bypass the 95% gate.
        self.assertEqual(track['qualidade']['diagnostico_bruto']['media_amostras'],30.75)
        self.assertEqual(result['campos']['air_temperature'],summarize_sensors(data['weather'],window())['campos']['air_temperature'])
        self.assertEqual(data,original)
        review['sessoes']['7']['exclusoes_clima'][0]['posterior']=99
        self.assertEqual(weekend.observed_weather(data,session,review)['campos']['track_temperature']['qualidade']['codigo'],'zero_isolado_em_conferencia')

    def test_missing_initial_compound_is_not_filled_from_the_next_stint(self):
        from operacao2026.weekend_reconciliation import mark_tyre_gaps
        strategy=dict(numero=30,comparavel=True,qualidade=[],sequencia_stints=[dict(inicio=9,fim=28,composto='MEDIUM')])
        entry=dict(estado='dados_recebidos',dados_descritivos=dict(estrategias=[strategy]))
        mark_tyre_gaps(entry,self.fp3,self.review)
        self.assertEqual(entry['estado'],'parcial')
        self.assertFalse(strategy['comparavel'])
        self.assertEqual(entry['lacunas_documentadas'][0]['voltas'],list(range(1,9)))

    def lawson_native(self):
        return json.loads((ROOT/'tests/fixtures/mexico_fp3_lawson_native.json').read_text())

    def test_first_compound_recovered_without_changing_raw_laps_or_initial_age(self):
        raw=self.lawson_native(); original=deepcopy(raw)
        output,audit=reconcile(raw,self.fp3,self.review)
        first=next(s for s in output['stints'] if s['stint_number']==1)
        self.assertEqual((first['lap_start'],first['lap_end'],first['compound']),(1,8,'MEDIUM'))
        self.assertIsNone(first['tyre_age_at_start'])
        self.assertEqual(first['revisao_composto']['voltas_diretas'],list(range(2,9)))
        self.assertEqual(first['revisao_composto']['primeira_volta_por_continuidade'],1)
        self.assertEqual(output['laps'],raw['laps'])
        self.assertIsNone(output['laps'][0]['lap_duration'])
        self.assertEqual(output['stints'][:-1],raw['stints'])
        self.assertEqual(raw,original)
        self.assertEqual(audit['acoes'][-1]['tipo'],'composto_documentado')

    def test_missing_or_contradictory_lap_evidence_prevents_a_tyre_repair(self):
        for change in ['time','missing','clock','initial']:
            with self.subTest(change=change):
                raw=self.lawson_native()
                if change=='time':raw['laps'][3]['lap_duration']+=.001
                elif change=='missing':raw['laps'].pop(3)
                elif change=='clock':raw['laps'][3]['date_start']='2026-10-31T18:25:00Z'
                else:raw['laps'][0]['lap_duration']=1
                with self.assertRaisesRegex(ValueError,'native laps|unmeasured lap'):
                    reconcile(raw,self.fp3,self.review)

    def test_native_conflict_is_rejected_and_compatible_native_age_is_preserved(self):
        raw=self.lawson_native()
        first=dict(raw['stints'][0],stint_number=1,lap_start=1,lap_end=8,compound='SOFT',tyre_age_at_start=0)
        raw['stints'].append(first)
        with self.assertRaisesRegex(ValueError,'contradicts'):
            reconcile(raw,self.fp3,self.review)
        first['compound']='MEDIUM'
        output,_=reconcile(raw,self.fp3,self.review)
        self.assertEqual(len(output['stints']),5)
        self.assertEqual(next(s for s in output['stints'] if s['stint_number']==1)['tyre_age_at_start'],0)
        again,_=reconcile(output,self.fp3,self.review)
        self.assertEqual(output,again)

    def test_reviewed_stint_clears_only_the_verified_compound_gap_and_is_projected(self):
        entry={}
        raw=self.lawson_native();original=deepcopy(raw)
        weekend.project_received(entry,raw,self.fp3,self.review)
        strategy=entry['dados_descritivos']['estrategias'][0]
        self.assertEqual(entry['estado'],'dados_recebidos')
        self.assertTrue(strategy['comparavel'])
        self.assertNotIn('lacunas_documentadas',entry)
        self.assertEqual([(s['inicio'],s['fim']) for s in strategy['sequencia_stints']],[(1,8),(9,11),(12,19),(20,22),(23,28)])
        self.assertEqual(len(strategy['sequencia_stints'][0]['revisao_composto']['fontes']),4)
        self.assertEqual(entry['cobertura_validada']['stints'],5)
        self.assertEqual(raw,original)

    def test_completed_cache_receives_a_new_review_once_without_refetching_race_data(self):
        race=next(s for s in self.event['sessions'] if s['session_name']=='Race')
        ids=dict(session_key=race['session_key'],meeting_key=race['meeting_key'])
        clock=datetime(2026,11,2,1,tzinfo=timezone.utc)
        review=deepcopy(self.review)
        review['sessoes']={str(race['session_key']):dict(session_name='Race',inicio_utc=race['date_start'],
            exclusoes_clima=[dict(date='2026-11-01T20:01:30Z',track_temperature=0,anterior=40,posterior=41,fontes=['race_weather'])])}
        data=dict(drivers=[dict(ids,driver_number=7,full_name='Synthetic')],
                  session_result=[dict(ids,driver_number=7,position=1)],laps=[],stints=[],pit=[],
                  race_control=[dict(ids,date='2026-11-01T20:00:00Z',category='SessionStatus',message='SESSION STARTED'),
                                dict(ids,date='2026-11-01T20:04:00Z',category='SessionStatus',message='SESSION FINISHED')],
                  weather=[dict(ids,date='2026-11-01T20:0{}:30Z'.format(i),air_temperature=25,track_temperature=value)
                           for i,value in enumerate((40,0,41,42))])
        event=self.event
        class Client:
            calls=[]
            def __init__(self,destination,interval):
                self.destination=Path(destination);self.manifest={'fontes':[]}
            def capture(self,provider,endpoint,relative,url):
                self.calls.append((endpoint,relative))
                if relative.startswith(str(race['session_key'])+'/'):
                    raise AssertionError('Completed race data must come from cache')
                payload=event['sessions'] if endpoint=='sessions' else ({'hourly':{'time':[],'temperature_2m':[],'precipitation':[],'wind_speed_10m':[]}} if endpoint=='forecast' else [])
                path=self.destination/relative;path.parent.mkdir(parents=True,exist_ok=True);raw=json.dumps(payload).encode();path.write_bytes(raw)
                self.manifest['fontes'].append(dict(provider=provider,endpoint=endpoint,arquivo=relative,url=url,status=200,
                    sha256=sha256(raw).hexdigest(),obtido_em_utc=clock.isoformat()))
                return payload
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);base=root/'data/operacao_2026/fins_de_semana/rodriguez-2026';rawdir=base/'cached';rawdir.mkdir(parents=True)
            entry=dict(nome='Race',session_key=race['session_key'],estado='dados_recebidos',fontes=[],
                       encerramento_observado_utc='2026-11-01T20:04:00Z')
            for endpoint,payload in data.items():
                path=rawdir/(endpoint+'.json');raw=json.dumps(payload).encode();path.write_bytes(raw)
                entry['fontes'].append(dict(endpoint=endpoint,arquivo_local=str(path.relative_to(root)),status=200,
                    sha256=sha256(raw).hexdigest(),obtido_em_utc=clock.isoformat()))
            (base/'estado.json').write_text(json.dumps(dict(sessoes=[entry])))
            path=root/'operacao2026/adjudicacoes/2026-19-rodriguez.json';path.parent.mkdir(parents=True);path.write_text(json.dumps(review))
            with patch('operacao2026.weekend_official.standings',return_value={'disponivel':False}):
                state=weekend.collect(ROOT/'operacao2026/eventos/mexico2026.json',root,clock,Client)
                corrected=next(s for s in state['sessoes'] if s['nome']=='Race')
                self.assertEqual(corrected['clima_observado']['campos']['track_temperature']['qualidade']['codigo'],'zero_isolado_excluido')
                with patch.object(weekend,'project_received',side_effect=AssertionError('Current review must be reused')):
                    again=weekend.collect(ROOT/'operacao2026/eventos/mexico2026.json',root,
                                          clock+timedelta(seconds=2),Client,recheck_since=clock)
                self.assertEqual(next(s for s in again['sessoes'] if s['nome']=='Race'),corrected)

    def test_reviewed_practice_can_be_complete_with_fewer_results_than_drivers(self):
        event = weekend.load_event(ROOT/'operacao2026/eventos/saopaulo2026.json')
        review = load_review(ROOT, event)
        session = next(item for item in event['sessions'] if item['session_name'] == 'Practice 2')
        expected = session_review(review, session)['classificacao_treino']['carros_classificados']
        raw = dict(race_control=[], pit=[], laps=[], stints=[], weather=[{}],
                   drivers=[dict(driver_number=n, full_name=f'Driver {n}') for n in [*expected, 27]],
                   session_result=[dict(driver_number=n, position=pos) for pos, n in enumerate(expected, 1)])
        original = deepcopy(raw)
        entry = {}
        weekend.project_received(entry, raw, session, review)
        self.assertEqual(entry['estado'], 'dados_recebidos')
        self.assertEqual([row['numero'] for row in entry['tempos']], expected)
        self.assertEqual(entry['revisao_fontes']['acoes'][0]['tipo'], 'classificacao_treino_oficial')
        self.assertEqual(raw, original)

        raw['session_result'][-1]['driver_number'] = 27
        weekend.project_received(entry, raw, session, review)
        self.assertEqual(entry['estado'], 'parcial')
        self.assertEqual(entry['revisao_fontes']['acoes'], [])


if __name__=='__main__':
    unittest.main()

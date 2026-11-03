"""Reviewed Mexico additions, coherent denominators and bounded update failures."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import io
from unittest.mock import patch
from urllib.error import HTTPError
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from operacao2026 import driver_archive, weekend
from pitwall.data.driver_conditions import ASSET as BASE, load, validate, DriverConditionsError
from pitwall.data.driver_updates import ASSET, empty, merge, seal
from pitwall.research.driver_conditions import select_rows, summarize
from pitwall.research.driver_duel import duel

ROOT=Path(__file__).resolve().parents[1]
NOW=datetime(2026,11,3,21,tzinfo=timezone.utc)


class DriverUpdateTests(unittest.TestCase):
    def setUp(self):
        self.event=weekend.load_event(ROOT/'operacao2026/eventos/mexico2026.json')
        self.base=validate(json.loads((ROOT/BASE).read_text()))
        public=json.loads((ROOT/'frontend_assets/operacao_fim_semana.json').read_text())
        mexico=next(x for x in [public]+public.get('arquivo_eventos',[])
                    if (x['temporada'],x['rodada'],x['circuito_id'])==(2026,19,'rodriguez'))
        self.race=next(x for x in mexico['sessoes'] if x['nome']=='Race')
        self.canonical=json.loads((ROOT/'reports/saopaulo_readiness_20261103/admitted-sources/mexico-results.json').read_text())
        self.receipt=json.loads((ROOT/'reports/saopaulo_readiness_20261103/history-acquisition.json').read_text())['sources'][0]
        self.raw=(ROOT/'tests/fixtures/mexico_driver_race_native.json').read_bytes()
        self.native=json.loads(self.raw)
        self.native_receipt=next(x for x in self.race['fontes'] if x['endpoint']=='session_result')
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(),self.native_receipt['sha256'])
        self.circuit=json.loads((ROOT/'operacao2026/driver_circuit_reviews.json').read_text())['2026:rodriguez']

    def build(self):
        return driver_archive.build(self.event,self.race,self.canonical,self.receipt,
            self.native,self.native_receipt,self.circuit,NOW)

    def test_real_mexico_changes_exact_driver_counts_without_mutating_baseline(self):
        before=deepcopy(self.base);updates=empty(self.base);updates['events']['2026:19']=self.build();seal(updates)
        value=merge(self.base,updates)
        self.assertEqual(self.base,before)
        self.assertEqual((value['qualidade']['corridas'],value['qualidade']['resultados'],value['qualidade']['largadas']), (67,1376,1362))
        self.assertEqual(value['gps']['2026:19']['track_temperature'],40.72)
        self.assertEqual(value['gps']['2026:19']['rain_condition'],'not_recorded')
        old=summarize(select_rows(before));new=summarize(select_rows(value))
        self.assertEqual((new['wins']-old['wins'],new['podiums']-old['podiums'],new['starts']-old['starts']), (1,3,22))
        self.assertEqual(new['dns'],old['dns'])
        for driver in ['max_verstappen','hamilton','ryo_hirakawa']:
            self.assertEqual(summarize(select_rows(value,driver=driver))['starts']-summarize(select_rows(before,driver=driver))['starts'],1)

    def test_official_unknown_positions_are_not_filled_from_native_rank(self):
        record=self.build();rows=record['results']
        self.assertEqual(len([r for r in rows if r['position'] is None]),5)
        self.assertEqual({r['driver_id'] for r in rows if r['position'] in (1,2,3)}, {'max_verstappen','hamilton','antonelli'})
        self.assertTrue(all(r['retired'] for r in rows if r['position'] is None))
        self.assertEqual(next(r for r in rows if r['driver_id']=='lawson')['grid'],22)
        lawson=next(r for r in self.canonical['MRData']['RaceTable']['Races'][0]['Results'] if r['Driver']['driverId']=='lawson')
        lawson['grid']='0'
        self.assertIsNone(next(r for r in self.build()['results'] if r['driver_id']=='lawson')['grid'])

    def test_duels_add_common_starts_but_never_invent_a_missing_position(self):
        updates=empty(self.base);updates['events']['2026:19']=self.build();seal(updates);merged=merge(self.base,updates)
        for rival,delta in [('hamilton',1),('alonso',0)]:
            old=duel(self.base,'max_verstappen',rival,[2026]);new=duel(merged,'max_verstappen',rival,[2026])
            self.assertEqual(new['common_starts']-old['common_starts'],1)
            self.assertEqual(new['comparable_results']-old['comparable_results'],delta)

    def test_foreign_canonical_event_and_native_session_are_rejected(self):
        self.canonical['MRData']['RaceTable']['Races'][0]['round']='18'
        with self.assertRaisesRegex(ValueError,'another event'):self.build()
        self.setUp();self.native[0]['session_key']=11412
        with self.assertRaisesRegex(ValueError,'another race'):self.build()

    def test_divergent_positions_points_laps_and_dsq_are_pending(self):
        for field,value in [('position','2'),('points','0'),('laps','70'),('status','Disqualified')]:
            self.setUp();self.canonical['MRData']['RaceTable']['Races'][0]['Results'][0][field]=value
            with self.subTest(field=field),self.assertRaises(driver_archive.PendingDriverUpdate):self.build()

    def test_unverified_weather_circuit_and_identity_do_not_create_an_entry(self):
        self.race['clima_observado']['campos']['track_temperature']['elegivel']=False
        with self.assertRaisesRegex(driver_archive.PendingDriverUpdate,'weather'):self.build()
        self.setUp();self.circuit=None
        with self.assertRaisesRegex(driver_archive.PendingDriverUpdate,'circuit'):self.build()
        self.setUp();self.race['tempos'][0]['piloto_id']='hamilton'
        with self.assertRaisesRegex(ValueError,'IDs disagree'):self.build()

    def test_hash_baseline_and_overlapping_events_are_strict(self):
        updates=empty(self.base);updates['events']['2026:19']=self.build();seal(updates)
        updates['events']['2026:19']['gp']['track_temperature']=0
        with self.assertRaises(DriverConditionsError):merge(self.base,updates)
        seal(updates);updates['base_conteudo_sha256']='a'*64;seal(updates)
        with self.assertRaises(DriverConditionsError):merge(self.base,updates)
        updates=empty(self.base);record=self.build();record['gp']['rodada']=18;updates['events']['2026:18']=record;seal(updates)
        with self.assertRaisesRegex(DriverConditionsError,'overlaps'):merge(self.base,updates)

    def folder(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        for file in [BASE,'operacao2026/driver_circuit_reviews.json']:
            dest=root/file;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/file,dest)
        native_path=Path('data/operacao_2026/fins_de_semana/native/results.json');target=root/native_path;target.parent.mkdir(parents=True);target.write_bytes(self.raw)
        race=deepcopy(self.race);race['fontes']=[dict(self.native_receipt,arquivo_local=str(native_path))]
        state=dict(temporada=2026,rodada=19,circuito_id='rodriguez',sessoes=[race])
        folder=root/'data/operacao_2026/fins_de_semana/rodriguez-2026/pilotos';folder.mkdir(parents=True)
        data=json.dumps(self.canonical).encode();(folder/'results.json').write_bytes(data)
        receipt=dict(self.receipt,sha256=hashlib.sha256(data).hexdigest(),obtido_em_utc=NOW.isoformat())
        (folder/'consulta.json').write_text(json.dumps(dict(path=str((folder/'results.json').relative_to(root)),receipt=receipt)))
        return root,state

    def test_cached_reproduction_is_idempotent_and_future_finish_does_not_do_http(self):
        root,state=self.folder()
        def no_http(*a):raise AssertionError('No HTTP expected')
        self.assertTrue(driver_archive.update(root,state,self.event,NOW,no_http)['changed'])
        before=(root/ASSET).read_bytes()
        self.assertFalse(driver_archive.update(root,state,self.event,NOW+timedelta(minutes=30),no_http)['changed'])
        self.assertEqual((root/ASSET).read_bytes(),before)
        state['sessoes'][0]['encerramento_observado_utc']=(NOW+timedelta(days=5)).isoformat()
        with self.assertRaisesRegex(ValueError,'finish'):driver_archive.update(root,state,self.event,NOW,no_http)

    def test_last_valid_event_is_retained_and_overdue_gap_is_reported(self):
        root,state=self.folder();driver_archive.update(root,state,self.event,NOW)
        previous=json.loads((root/ASSET).read_text())['events']['2026:19']
        state['sessoes'][0]['clima_observado']['campos']['humidity']['elegivel']=False
        result=driver_archive.update(root,state,self.event,NOW)
        self.assertEqual(result['status'],'pending')
        self.assertEqual(json.loads((root/ASSET).read_text())['events']['2026:19'],previous)
        self.assertEqual(load(root)['qualidade']['corridas'],67)
        with self.assertRaisesRegex(RuntimeError,'need review'):driver_archive.check_pending(root,NOW)

    def test_fresh_capture_uses_real_client_constructor_and_persists_receipts(self):
        root,state=self.folder()
        folder=root/'data/operacao_2026/fins_de_semana/rodriguez-2026/pilotos'
        (folder/'consulta.json').unlink()
        payload=json.dumps(self.canonical).encode()
        class Response(io.BytesIO):
            status=200
            def geturl(self):return 'https://api.jolpi.ca/ergast/f1/2026/19/results/?limit=100&offset=0'
        def factory(directory,interval):
            return driver_archive.CaptureClient(directory,interval,opener=lambda *a,**kw:Response(payload))
        with patch('pitwall.data.archive_collection.utc_now',return_value=NOW.isoformat()):
            result=driver_archive.update(root,state,self.event,NOW,factory)
        self.assertEqual(result['races'],67)
        cached=json.loads((folder/'consulta.json').read_text())
        self.assertEqual((root/cached['path']).read_bytes(),payload)
        self.assertTrue((root/cached['path']).with_name('coleta_online.json').is_file())
        self.assertEqual(cached['receipt']['sha256'],hashlib.sha256(payload).hexdigest())

    def test_real_client_429_exception_preserves_cooldown_and_previous_data(self):
        root,state=self.folder();driver_archive.update(root,state,self.event,NOW)
        previous=json.loads((root/ASSET).read_text())['events']['2026:19']
        (root/'data/operacao_2026/fins_de_semana/rodriguez-2026/pilotos/consulta.json').unlink()
        def opener(request,timeout):
            raise HTTPError(request.full_url,429,'Limited',{'Retry-After':'7200'},io.BytesIO(b'limited'))
        def factory(directory,interval):return driver_archive.CaptureClient(directory,interval,opener=opener)
        with patch('pitwall.data.archive_collection.utc_now',return_value=NOW.isoformat()):
            result=driver_archive.update(root,state,self.event,NOW,factory)
        self.assertEqual(result['status'],'pending')
        self.assertEqual(json.loads((root/ASSET).read_text())['events']['2026:19'],previous)
        self.assertEqual(driver_archive.cloud.cooldown(root,NOW+timedelta(minutes=30)),
                         (NOW+timedelta(hours=2)).isoformat())

    def test_retry_after_is_persisted_and_blocks_next_runner_before_http(self):
        root,state=self.folder()
        folder=root/'data/operacao_2026/fins_de_semana/rodriguez-2026/pilotos'
        (folder/'consulta.json').unlink()
        class Limited:
            def __init__(self,*args):
                self.manifest={'fontes':[dict(status=429,obtido_em_utc=NOW.isoformat(),retry_after='7200')]}
            def capture(self,*args):return None
        result=driver_archive.update(root,state,self.event,NOW,Limited)
        self.assertEqual(result['status'],'pending')
        self.assertEqual(driver_archive.cloud.cooldown(root,NOW+timedelta(minutes=30)),
                         (NOW+timedelta(hours=2)).isoformat())

    def test_native_capture_symlink_is_rejected_even_inside_archive(self):
        root,state=self.folder();race=state['sessoes'][0]
        original=root/race['fontes'][0]['arquivo_local']
        link=original.with_name('linked.json');link.symlink_to(original)
        race['fontes'][0]['arquivo_local']=str(link.relative_to(root))
        with self.assertRaisesRegex(ValueError,'Symlink'):
            driver_archive.native(root,race,'session_result')

    def test_missing_update_file_never_silently_returns_the_old_baseline(self):
        root,state=self.folder()
        with self.assertRaises(DriverConditionsError):load(root)


if __name__=='__main__':unittest.main()

"""Identity repairs never infer names or change sporting observations."""
from copy import deepcopy
import csv
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from pitwall.data.archive import carregar, AcervoDashboardErro
from pitwall.data import identity_revision as revision
from pitwall.data import archive_normalization as normalization
from tests.test_tyre_age import differences

ROOT=Path(__file__).resolve().parents[1]


class IdentityRevision(unittest.TestCase):
    def before(self):
        from pitwall.data.tyre_age import carregar as tyres
        from pitwall.data.complementary_sources import load_projection
        raw=(ROOT/'frontend_assets/acervo_dashboard.json').read_bytes()
        return load_projection(ROOT,tyres(ROOT,json.loads(raw),raw))

    def test_exact_four_identity_leaves_only_no_race_entrant_or_values_added(self):
        before=self.before();original=deepcopy(before)
        with patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')):
            after=carregar(ROOT)
        delta=list(differences(before['gps'],after['gps']))
        self.assertEqual(len(delta),4)
        self.assertTrue(all(path[0]=='2025:9' and path[-1]=='piloto_id' and a is None and b=='stroll' for path,a,b in delta))
        gp=after['gps']['2025:9']
        for session in gp['sessoes']:
            rows=[r for r in session['tempos'] if r['numero']==18]
            if session['nome']=='Race':self.assertEqual(rows,[])
            else:self.assertEqual(rows[0]['piloto_id'],'stroll')
        self.assertEqual(before,original)
        self.assertEqual(revision.load_projection(ROOT,after),after)

    def test_wrong_event_session_driver_or_time_is_rejected_without_mutation(self):
        bundle=json.loads((ROOT/revision.ASSET).read_bytes())
        for field,value in [('data_corrida','2025-06-02'),('circuito_id','monaco'),('session_key',1),('numero',14)]:
            b=deepcopy(bundle);b['bindings'][0][field]=value;asset=self.before();before=deepcopy(asset)
            with self.subTest(field=field),self.assertRaises((ValueError,KeyError)):revision.project(asset,b)
            self.assertEqual(asset,before)
        asset=self.before();asset['gps']['2025:9']['sessoes'][0]['tempos'][0]['q1']='1:00.000'
        with self.assertRaises(ValueError):revision.project(asset,bundle)

    def test_missing_or_tampered_pinned_asset_is_fail_closed(self):
        for raw in [None,b'{}']:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td)
                if raw is not None:(root/'frontend_assets').mkdir();(root/revision.ASSET).write_bytes(raw)
                with self.subTest(raw=raw),self.assertRaises(ValueError):revision.load_projection(root,self.before())

    def local(self,root,name,rows):
        folder=root/'local';folder.mkdir(exist_ok=True)
        with (folder/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['temporada','rodada','circuito_id','piloto_id','equipe_id','numero','fonte_id']);w.writeheader();w.writerows(rows)

    def record(self,**changes):
        return dict(temporada='2025',rodada='9',circuito_id='catalunya',piloto_id='stroll',equipe_id='aston_martin',numero='18',fonte_id='q1',**changes)

    def test_qualifying_only_driver_is_identified_and_old_missing_number_is_not_guessed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);r=self.record();self.local(root,'classificacao.csv',[r])
            _,ids=normalization._locais(root,{(2025,9,'catalunya'): {}})
            self.assertEqual(ids[(2025,9,'catalunya',18)]['piloto_id'],'stroll')
            r['numero']='';self.local(root,'classificacao.csv',[r])
            self.assertEqual(normalization._locais(root,{(2025,9,'catalunya'): {}})[1],{})

    def test_conflicting_ids_or_teams_are_rejected_and_agreement_keeps_result_source(self):
        for field,value in [('piloto_id','other'),('equipe_id','other'),(None,None)]:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td);r=self.record();r['fonte_id']='race';q=self.record()
                if field:q[field]=value
                self.local(root,'resultados.csv',[r]);self.local(root,'classificacao.csv',[q]);events={(2025,9,'catalunya'): {}}
                if field:
                    with self.assertRaisesRegex(ValueError,'conflitante'):normalization._locais(root,events)
                else:self.assertEqual(normalization._locais(root,events)[1][(2025,9,'catalunya',18)]['fonte_id'],'race')

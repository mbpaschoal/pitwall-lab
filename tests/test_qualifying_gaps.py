"""Synthetic oracles; never fit the real frozen model or fetch data."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.special import expit

from pitwall.research import qualifying_gaps as q
from pitwall.research.calibration_v2 import _normalise_rows, FEATURES_V1


def sample_rows(year=2021):
    rows=[]
    for race in range(1,5):
        for d in range(6):
            row={f:0 for f in FEATURES_V1}
            row.update(temporada=year,rodada=race,piloto_id=str(d),podio=int((d+race)%6<3),posicao_classificacao=d+1,
                       media_posicao_final_5=None if race==1 else float(d+1),taxa_podios_5=d/6,media_pontos_equipe_5=6-d,
                       limite_inferior_referencia_utc="{}-03-{:02d}T00:00:00Z".format(year,race*5),data_corrida="{}-03-{:02d}".format(year,race*5+1))
            row.update({f:float(d+race)/10 for f in q.GAPS});row.update({f:0 for f in q.SUPPORT})
            rows.append(row)
    return _normalise_rows(rows)


class GapsTest(unittest.TestCase):
    def test_time_units_missing_invalid_and_zero(self):
        self.assertEqual(q.seconds("1:20.500"),80.5)
        for value in (None,"","0:00.000","1:60.000","nan","-1:20.000",80.5):self.assertIsNone(q.seconds(value))

    def test_exact_phase_oracle_no_cross_phase_comparison(self):
        f=q.phase_features({"a":{"Q1":"1:20.000","Q2":"1:30.000"},"b":{"Q1":"1:24.000","Q2":"1:21.000"}})
        self.assertAlmostEqual(f['b']['q_gap_pct_Q1'],5)
        self.assertAlmostEqual(f['a']['q_gap_pct_Q2'],100/9)
        self.assertEqual(f['a']['q_gap_pct_Q1'],0)
        self.assertEqual(f['a']['q_gap_missing_Q3'],1)

    def test_single_time_has_no_reference_and_future_race_is_not_combined(self):
        a=q.phase_features({'a':{'Q1':'1:20.000'},'b':{'Q1':None}})
        self.assertIsNone(a['a']['q_gap_pct_Q1']);self.assertEqual(a['a']['q_n_valid_Q1'],1)

    def fixture(self,root):
        rows=[];ident={}
        for year in range(2021,2026):
            records=[]
            for d,time in (('a','1:20.000'),('b','1:24.000')):
                r={'temporada':year,'rodada':1,'piloto_id':d,'elegivel_previsao':True,'posicao_classificacao':len(records)+1}
                rows.append(r);ident[q.key(r)]={'equipe_id_entrada':'team'}
                records.append({'Driver':{'driverId':d},'Constructor':{'constructorId':'team'},'position':str(len(records)+1),'Q1':time})
            data={'MRData':{'offset':'0','limit':'100','total':'2','RaceTable':{'season':str(year),'Races':[{'season':str(year),'round':'1','QualifyingResults':records}]}}}
            raw=root/'data/historico'/str(year)/'raw/classificacao_offset_0000.json';raw.parent.mkdir(parents=True);raw.write_text(json.dumps(data))
            receipt=raw.parent.parent/'proveniencia'/raw.name;receipt.parent.mkdir();receipt.write_text(json.dumps({'sha256':q._sha(raw)}))
        return rows,ident

    def test_complete_local_source_gate_and_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            rows,ident=self.fixture(Path(td));c=q.local_gaps(td,rows,ident)
            self.assertEqual(c['status'],'sufficient');self.assertEqual(len(c['sources']),10)
            self.assertTrue(all(r['q_gap_pct_Q1'] is not None for r in rows))

    def test_gate_refuses_identity_conflict_without_dropping_row(self):
        with tempfile.TemporaryDirectory() as td:
            rows,ident=self.fixture(Path(td));ident[(2021,1,'a')]['equipe_id_entrada']='wrong'
            c=q.local_gaps(td,rows,ident);self.assertEqual(c['status'],'cobertura_insuficiente');self.assertEqual(len(rows),10)

    def test_gate_refuses_inadequate_q1_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);rows,ident=self.fixture(root)
            raw=root/'data/historico/2021/raw/classificacao_offset_0000.json';data=json.loads(raw.read_text());data['MRData']['RaceTable']['Races'][0]['QualifyingResults'][0]['Q1']='0:00.000';raw.write_text(json.dumps(data))
            (raw.parent.parent/'proveniencia'/raw.name).write_text(json.dumps({'sha256':q._sha(raw)}))
            c=q.local_gaps(td,rows,ident);self.assertEqual(c['status'],'cobertura_insuficiente');self.assertEqual(c['seasons'][0]['invalid_times_Q1'],1)

    def test_corrupt_hash_incomplete_pagination_duplicate_and_season_rejected(self):
        for change in ('hash','offset','total','duplicate','season'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as td:
                root=Path(td);rows,ident=self.fixture(root);raw=root/'data/historico/2021/raw/classificacao_offset_0000.json';data=json.loads(raw.read_text());mr=data['MRData']
                if change=='offset':mr['offset']='1'
                if change=='total':mr['total']='3'
                if change=='duplicate':mr['RaceTable']['Races'][0]['QualifyingResults'][1]=mr['RaceTable']['Races'][0]['QualifyingResults'][0]
                if change=='season':mr['RaceTable']['season']='2026'
                raw.write_text(json.dumps(data)+' ')
                if change!='hash':(raw.parent.parent/'proveniencia'/raw.name).write_text(json.dumps({'sha256':q._sha(raw)}))
                with self.assertRaises(ValueError):q.local_gaps(td,rows,ident)

    def test_diagnosis_unknown_not_zero_and_loss_oracle(self):
        preds=[{'metodo':'v1_temporal','temporada':2022,'rodada':1,'piloto_id':d,'podio':y,'probabilidade':p} for d,y,p in [('a',0,.8),('b',1,.1),('c',None,.4)]]
        ident={q.key(p):{'corrida':'GP','circuito_id':'track','equipe_id_entrada':'team','_q':1} for p in preds}
        out=q.diagnose(preds,ident,{})
        self.assertEqual(out['n'],2);self.assertEqual(out['high_confidence_failures'],1);self.assertEqual(out['underestimated_podiums'],1)
        self.assertAlmostEqual(out['worst_cases'][0]['log_loss'],-np.log(.1))

    def test_postrace_status_never_changes_losses_or_gaps(self):
        p={'metodo':'v1_temporal','temporada':2022,'rodada':1,'piloto_id':'a','podio':0,'probabilidade':.8};meta={q.key(p):{'corrida':'GP','circuito_id':'t','equipe_id_entrada':'team','_q':1}}
        a=q.diagnose([p],meta,{});b=q.diagnose([p],meta,{q.key(p):{'status':'accident'}})
        self.assertEqual(a['groups'],b['groups'])

    def test_training_only_imputer_and_independent_prediction_formula(self):
        train=sample_rows();external=sample_rows(2022);features=FEATURES_V1+q.SUPPORT+q.GAPS
        p,fit=q.fit_candidate(train,external,features)
        raw=np.array([[np.nan if r[f] is None else r[f] for f in features] for r in external])
        z=(np.where(np.isnan(raw),fit['medians'],raw)-fit['means'])/fit['scales']
        np.testing.assert_allclose(p,expit(fit['intercept']+z@fit['coef']),atol=1e-14)
        extreme=copy.deepcopy(external)
        for r in extreme:r['media_posicao_final_5']=999999;r['podio']=1-r['podio']
        _,other=q.fit_candidate(train,extreme,features)
        self.assertEqual({k:v for k,v in fit.items() if k!='predict_partition'},
                         {k:v for k,v in other.items() if k!='predict_partition'})

    def test_training_prediction_gp_overlap_and_future_ref_rejected(self):
        train=sample_rows()
        with self.assertRaises(ValueError):q.fit_candidate(train,train,FEATURES_V1)
        bad=sample_rows(2022)
        for r in bad:r['limite_inferior_referencia_utc']='2020-01-01T00:00:00Z'
        with self.assertRaises(ValueError):q.fit_candidate(train,bad,FEATURES_V1)

    def test_failed_gradient_not_accepted(self):
        with patch.object(q,'fit_ridge',return_value={'converged':False}):
            with self.assertRaises(ValueError):q.fit_candidate(sample_rows(),sample_rows(2022),FEATURES_V1)

    def test_output_refuses_existing_or_source_path_before_any_write(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for destination in (root,root/'data/preparado'):
                with self.assertRaises(ValueError):q.run(root,destination)


if __name__=='__main__':unittest.main()

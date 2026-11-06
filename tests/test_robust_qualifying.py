"""Property checks and synthetic oracles; no real-source fitting or networking."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.special import expit

from pitwall.research import robust_qualifying as r
from tests.test_qualifying_gaps import sample_rows


def ordinal_rows(values, year=2021, race=1):
    return [{'temporada': year, 'rodada': race, 'piloto_id': str(i),
             **{'q_gap_pct_'+ph: value for ph in r.q.PHASES}} for i, value in enumerate(values)]


class RobustQualifyingTest(unittest.TestCase):
    def test_ties_and_missing_exact_oracle(self):
        rows = r.attach_ranks(ordinal_rows([0, 2, 2, 10000, None]))
        self.assertEqual([x[r.RANKS[0]] for x in rows], [0, .5, .5, 1, None])

    def test_all_tied_single_and_all_missing(self):
        self.assertEqual([x[r.RANKS[0]] for x in r.attach_ranks(ordinal_rows([4, 4]))], [.5, .5])
        for values in ([4, None], [None, None]):
            self.assertTrue(all(x[r.RANKS[0]] is None for x in r.attach_ranks(ordinal_rows(values))))

    def test_magnitude_invariance_and_range(self):
        a = r.attach_ranks(ordinal_rows([0, 2, 4, 20]))
        b = r.attach_ranks(ordinal_rows([0, .02, 999, 1e100]))
        self.assertEqual([x[r.RANKS[0]] for x in a], [x[r.RANKS[0]] for x in b])
        self.assertTrue(all(0 <= x[f] <= 1 for x in b for f in r.RANKS))

    def test_phase_gp_and_future_isolation(self):
        a = ordinal_rows([0, 1, 2]); a[0]['q_gap_pct_Q2'] = 10
        b = ordinal_rows([0, 99, 100, 1000], 2022)
        alone = r.attach_ranks(copy.deepcopy(a)); together = r.attach_ranks(copy.deepcopy(a+b))
        self.assertEqual(alone, together[:3])
        self.assertEqual(alone[0][r.RANKS[0]], 0)
        self.assertEqual(alone[0][r.RANKS[1]], 1)

    def test_nonfinite_or_negative_input_rejected(self):
        for value in (-.1, float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                r.attach_ranks(ordinal_rows([0, value]))

    def test_prediction_oracle_and_training_only_parameters(self):
        train = r.attach_ranks(sample_rows())
        external = r.attach_ranks(sample_rows(2022))
        features = r.FEATURES_V1+r.q.SUPPORT+r.RANKS
        p, fit = r.q.fit_candidate(train, external, features)
        x = np.array([[np.nan if row[f] is None else row[f] for f in features] for row in external])
        expected = expit(fit['intercept']+((np.where(np.isnan(x), fit['medians'], x)-fit['means'])/fit['scales'])@fit['coef'])
        np.testing.assert_allclose(p, expected, atol=1e-14)
        altered = copy.deepcopy(external)
        for row in altered:
            row['podio'] = 1-row['podio']; row['media_posicao_final_5'] = None
        _, other = r.q.fit_candidate(train, altered, features)
        self.assertEqual({k:v for k,v in fit.items() if k!='predict_partition'}, {k:v for k,v in other.items() if k!='predict_partition'})

    def test_future_season_and_existing_output_refused(self):
        with self.assertRaises(ValueError):
            r.experiment([{'temporada':2026}], [])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for out in (root, root/'data/preparado', root/r.PARENT):
                with self.assertRaises(ValueError):r.run(root,out)

    def previous_fixture(self, root):
        rows = ordinal_rows([0, 1], 2022)
        for row in rows:
            row.update({f:0 for f in r.q.SUPPORT}); row['podio'] = int(row['piloto_id']=='0')
        previous = root/r.PREVIOUS; previous.mkdir(parents=True)
        r.q._csv(previous/'gap_features.csv',rows)
        predictions = [{**{k:row[k] for k in ('temporada','rodada','piloto_id','podio')}, 'metodo':m, 'probabilidade':.5} for m in r.q.METHODS for row in rows]
        r.q._csv(previous/'predictions.csv',predictions)
        manifest = {'files':{p.name:r.q._sha(p) for p in previous.iterdir()}}
        r.q._json(previous/'manifest.json',manifest)
        return rows,previous

    def test_previous_predictions_retained_exactly(self):
        with tempfile.TemporaryDirectory() as td:
            rows,_ = self.previous_fixture(Path(td))
            p = r.load_previous(td,rows)
            self.assertEqual(len(p),8); self.assertTrue(all(x['probabilidade']==.5 for x in p))

    def test_previous_hash_cohort_features_targets_fail_closed(self):
        for kind in ('hash','cohort','feature','target'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as td:
                rows,previous = self.previous_fixture(Path(td))
                if kind=='hash':(previous/'predictions.csv').write_text('changed')
                elif kind=='cohort':rows.pop()
                elif kind=='feature':rows[0][r.q.GAPS[0]]=99
                else:rows[0]['podio']=1-rows[0]['podio']
                with self.assertRaises(ValueError):r.load_previous(td,rows)

    def audit_fixture(self,root):
        rows=r.attach_ranks(ordinal_rows([0,20])); ident={r.q.key(x):{'corrida':'GP','equipe_id_entrada':'team'} for x in rows}
        records=[{'Driver':{'driverId':str(i)},'position':str(i+1),**{ph:t for ph in r.q.PHASES}} for i,t in enumerate(('1:00.000','1:12.000'))]
        path=root/'data/historico/2021/raw/classificacao_offset_0000.json';path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'MRData':{'RaceTable':{'Races':[{'season':'2021','round':'1','QualifyingResults':records}]}}}))
        receipt=path.parent.parent/'proveniencia'/path.name;receipt.parent.mkdir();receipt.write_text(json.dumps({'url_real':'https://example.test','obtido_em_utc':'2026-01-01T00:00:00Z'}))
        evidence={'cases':[{'key':[2021,1,'1'],'phase':ph,'canonical_time':'1:12.000'} for ph in r.q.PHASES]}
        return rows,ident,evidence

    def test_audit_input_selection_not_outcome_and_distributions(self):
        with tempfile.TemporaryDirectory() as td:
            rows,ident,evidence=self.audit_fixture(Path(td))
            out=r.audit_extremes(td,rows,ident,evidence)
            self.assertEqual(out['n_extremes'],3);self.assertEqual(out['n_driver_phases'],6)
            self.assertAlmostEqual(out['distributions'][0]['median'],10)
            for row in rows:row['podio']=1;row['status']='failure'
            self.assertEqual(out,r.audit_extremes(td,rows,ident,evidence))
            self.assertFalse(out['cases'][0]['excluded_from_fitting'])
            self.assertEqual(out['cases'][0]['source_url'],'https://example.test')

    def test_audit_missing_duplicate_wrong_evidence_and_source_drift_rejected(self):
        for kind in ('missing','duplicate','time','gap','extra'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as td:
                rows,ident,evidence=self.audit_fixture(Path(td))
                if kind=='missing':evidence['cases'].pop()
                elif kind=='duplicate':evidence['cases'].append(copy.deepcopy(evidence['cases'][0]))
                elif kind=='time':evidence['cases'][0]['canonical_time']='1:22.000'
                elif kind=='gap':rows[1]['q_gap_pct_Q1']=100
                else:evidence['cases'].append({'key':[2021,2,'x'],'phase':'Q1'})
                with self.assertRaises(ValueError):r.audit_extremes(td,rows,ident,evidence)

    def test_four_annual_fits_and_identical_comparator_predictions(self):
        rows=r.attach_ranks(sum([sample_rows(y) for y in range(2021,2026)],[]))
        predictions=[{'metodo':m, 'temporada':x['temporada'],'rodada':x['rodada'],'piloto_id':x['piloto_id'],'podio':x['podio'],
                      'probabilidade':.65 if x['podio'] else .15} for m in r.q.METHODS for x in rows if x['temporada']>=2022]
        with patch.object(r.q,'paired_interval',return_value={'status':'not_estimable'}):
            out=r.experiment(rows,predictions)
        self.assertEqual(len(out['fits']),4)
        self.assertEqual(out['predictions'][:len(predictions)],predictions)
        self.assertFalse(out['all_primary_criteria_met']);self.assertFalse(out['automatic_promotion'])
        self.assertEqual({f['year'] for f in out['fits']},{2022,2023,2024,2025})

    def test_incomplete_cohort_and_changed_protection_prevent_execution(self):
        rows=r.attach_ranks(sum([sample_rows(y) for y in range(2021,2026)],[]))
        with patch.object(r.q,'evaluate_methods',return_value={'methods':{'x':{'status':'cobertura_insuficiente'}}}),self.assertRaises(ValueError):
            r.experiment(rows,[])
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);parent=root/r.PARENT;parent.mkdir(parents=True)
            r.q._json(parent/'protected_before.json',{'files':{}})
            with patch.object(r.q,'preservation',return_value={'status':'divergent'}),self.assertRaises(ValueError):
                r.run(root,parent/'run-001')
            self.assertFalse((parent/'run-001').exists())


if __name__=='__main__':unittest.main()

"""All-team coverage, comparable samples, temporal scope and actual dashboard states."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import json
import tempfile
import unittest
from streamlit.testing.v1 import AppTest
from pitwall.data.car_comparison import ASSET, CarDataError, for_event, load
from pitwall.dashboard.navigation import route_params, selected_route, search
from pitwall.i18n import set_language, translate
from pitwall.research.car_comparison import TEAMS, digest, evaluate_driver, team_metric

ROOT=Path(__file__).resolve().parents[1]


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.asset=load(ROOT)

    def test_all_teams_and_actual_event_drivers_are_present(self):
        self.assertEqual(len(self.asset['events']),21)
        for event in self.asset['events']:
            self.assertEqual({t['team_id'] for t in event['teams']},set(TEAMS))
            self.assertEqual(sum(len(t['drivers']) for t in event['teams']),22)

    def test_gp_identity_and_unsupported_year_are_never_inferred(self):
        self.assertIsNone(for_event(self.asset,2025,21))
        self.assertIsNone(for_event(self.asset,2026,22))
        with self.assertRaises(CarDataError):for_event(self.asset,2026,21,'monaco')

    def test_one_driver_cannot_become_a_complete_team_mean(self):
        rows=[{'q1':{'eligible':True,'eligible_no_flags':True,'gap_percent':0.}},
              {'q1':{'eligible':False,'eligible_no_flags':False,'gap_percent':None}}]
        self.assertIsNone(team_metric(rows)['gap_percent'])
        self.assertEqual(team_metric(rows)['status'],'partial')
        self.assertEqual(team_metric(rows)['eligible_drivers'],1)

    def test_legitimate_zero_is_not_missing(self):
        rows=[{'q1':{'eligible':True,'eligible_no_flags':True,'gap_percent':0.}}]*2
        self.assertEqual(team_metric(rows)['gap_percent'],0.)
        self.assertEqual(team_metric(rows)['status'],'complete')

    def test_both_drivers_use_same_q1_reference_and_independent_decimal_arithmetic(self):
        for event in self.asset['events']:
            for team in event['teams']:
                for driver in team['drivers']:
                    q=driver['q1']
                    if not q['eligible']:continue
                    self.assertEqual(q['reference_number'],event['reference']['number'])
                    expected=100*(Decimal(str(q['q1_seconds']))/Decimal(str(q['reference_seconds']))-1)
                    self.assertAlmostEqual(q['gap_percent'],float(expected),places=10)
                if team['q1']['gap_percent'] is not None:
                    expected=sum(Decimal(str(d['q1']['gap_percent'])) for d in team['drivers'])/2
                    self.assertAlmostEqual(team['q1']['gap_percent'],float(expected),places=10)

    def test_mixed_weather_cannot_enter_dry_comparison(self):
        mixed=[e for e in self.asset['events'] if e['wet_or_mixed_qualifying']]
        self.assertTrue(mixed)
        self.assertTrue(all(t['q1']['gap_percent'] is None for e in mixed for t in e['teams']))

    def test_flags_are_a_stricter_subset(self):
        for e in self.asset['events']:
            for t in e['teams']:
                self.assertLessEqual(t['q1_no_flags']['eligible_drivers'],t['q1']['eligible_drivers'])
                if t['q1_no_flags']['gap_percent'] is not None:
                    self.assertEqual(t['q1_no_flags']['gap_percent'],t['q1']['gap_percent'])

    def test_disqualification_is_not_a_legal_timed_comparison(self):
        miami=for_event(self.asset,2026,4)
        rb=next(t for t in miami['teams'] if t['team_id']=='red_bull')
        hadjar=next(d for d in rb['drivers'] if d['number']==6)
        self.assertEqual(hadjar['qualifying_status'],'DQ')
        self.assertFalse(hadjar['q1']['eligible'])
        self.assertIsNone(rb['q1']['gap_percent'])

    def test_replacement_driver_is_preserved_instead_of_backfilled(self):
        for n in (12,13,14):
            rb=next(t for t in for_event(self.asset,2026,n)['teams'] if t['team_id']=='red_bull')
            self.assertIn('Liam Lawson',{d['name'] for d in rb['drivers']})
            self.assertNotIn('Isack Hadjar',{d['name'] for d in rb['drivers']})

    def test_declarations_are_not_promoted_to_component_usage(self):
        declarations=[t['declaration'] for e in self.asset['events'] for t in e['teams']]
        self.assertEqual(len(declarations),231)
        self.assertTrue(any(d['no_updates_declared'] for d in declarations))
        self.assertTrue(all(c['used_exact_driver_session'] is None and c['version_id'] is None
                            for d in declarations for c in d['components']))
        conflict=next(t for t in for_event(self.asset,2026,7)['teams'] if t['team_id']=='racing_bulls')['declaration']
        self.assertEqual(conflict['status'],'event_identity_review')

    def test_secu_versions_cover_every_team_in_both_captured_events(self):
        for n in (4,15):
            event=for_event(self.asset,2026,n)
            self.assertEqual(sum(t['secu_software'] is not None for t in event['teams']),11)
            self.assertTrue(all(t['secu_software']['performance_effect'] is None for t in event['teams']))

    def test_capture_time_remains_unknown_when_only_date_is_known(self):
        self.assertTrue(all(e['source']['qualifying_captured_at_utc'] is None for e in self.asset['events']))
        self.assertTrue(all(e['source']['qualifying_capture_date_utc']=='2026-11-23' for e in self.asset['events']))

    def test_tampering_and_missing_team_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/ASSET;path.parent.mkdir()
            changed=deepcopy(self.asset);changed['events'][0]['teams'].pop()
            changed['content_sha256']=digest(changed)
            path.write_text(json.dumps(changed))
            with self.assertRaises(CarDataError):load(tmp)
            changed=deepcopy(self.asset);changed['forecast_input']=True
            path.write_text(json.dumps(changed))
            with self.assertRaises(CarDataError):load(tmp)

    def test_new_route_retains_gp_and_language_and_is_searchable(self):
        for lang in ('pt','en'):
            q=route_params('cars',2026,7,lang)
            self.assertEqual((q['temporada'],q['gp'],q['lang']),(2026,7,lang))
            self.assertEqual(selected_route(q['tela'],q),'cars')
            self.assertIn('cars',{r['value'] for r in search('upgrades',lang)})


class InterfaceTests(unittest.TestCase):
    def app(self,lang='pt',gp=21,year=2026):
        at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=40)
        at.query_params.update(tela='Carros',temporada=str(year),gp=str(gp),lang=lang)
        at.run();self.assertFalse(at.exception)
        return at

    def test_pt_en_comparison_has_all_eleven_teams(self):
        for lang in ('pt','en'):
            at=self.app(lang)
            self.assertEqual(len(at.dataframe[0].value),11)
            self.assertEqual(at.radio(key='tela').value,'Carros')
            self.assertIn('Q1',at.dataframe[0].value.columns[1])

    def test_all_views_have_actual_content_in_both_languages(self):
        for lang in ('pt','en'):
            at=self.app(lang)
            at.radio(key='car_view').set_value('Evolução').run()
            self.assertFalse(at.exception)
            self.assertEqual(len(at.get('plotly_chart')),1)
            at.radio(key='car_view').set_value('Alterações').run()
            self.assertFalse(at.exception)
            self.assertTrue(at.subheader)
            self.assertTrue(at.dataframe)

    def test_conflicting_title_withholds_component_list(self):
        at=self.app(gp=7)
        at.radio(key='car_view').set_value('Alterações').run()
        at.selectbox(key='car_update_team').set_value('racing_bulls').run()
        self.assertFalse(at.exception)
        self.assertTrue(any('diverge' in w.value for w in at.warning))
        self.assertEqual(len(at.dataframe),0)

    def test_no_data_year_has_truthful_empty_state(self):
        for lang in ('pt','en'):
            at=self.app(lang,year=2024,gp=1)
            self.assertTrue(at.info)
            self.assertEqual(len(at.dataframe),0)

    def test_team_selection_survives_view_and_language_changes(self):
        at=self.app()
        at.radio(key='car_view').set_value('Evolução').run()
        at.multiselect(key='car_teams').set_value(['mclaren','ferrari']).run()
        at.radio(key='car_view').set_value('Alterações').run()
        at.radio(key='car_view').set_value('Evolução').run()
        self.assertEqual(at.multiselect(key='car_teams').value,['mclaren','ferrari'])
        next(b for b in at.button if b.label=='🇬🇧').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.multiselect(key='car_teams').value,['mclaren','ferrari'])
        self.assertEqual(at.radio(key='tela').value,'Carros')

    def tearDown(self):set_language('pt')


if __name__=='__main__':unittest.main()

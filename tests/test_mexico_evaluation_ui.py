"""Validated binary podium outcomes do not impute unclassified positions."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pitwall.data import race_weekend
from pitwall.dashboard import fan_views, model_views
from pitwall.i18n import set_language, visible_text
from pitwall.research.prospective_evaluation import prospective_races

ROOT=Path(__file__).resolve().parents[1]


def participants():
    """Explicit synthetic22-driver fixture:17classified,5documentedDNF."""
    model_order=[0,1,3,2]+list(range(4,22))
    qualifying_order=[0,3,4,1,2]+list(range(5,22))
    model_rank={driver:rank for rank,driver in enumerate(model_order,1)}
    qualifying_rank={driver:rank for rank,driver in enumerate(qualifying_order,1)}
    return [dict(temporada=2026,rodada=19,piloto_id='fixture_{}'.format(i),
                 elegivel_previsao=True,probabilidade_modelo=(22-i)/50,
                 ranking_modelo=model_rank[i],ranking_classificacao=qualifying_rank[i],
                 resultado_observado=i+1 if i<17 else None,
                 podio_resultado_confirmado=int(i<3),status_resultado='Finished' if i<17 else 'DNF')
            for i in range(22)]


def asset_for(rows, validated=True):
    race=dict(temporada=2026,rodada=19,corrida='Mexico City Grand Prix',
              cidade='Mexico City',pais='Mexico',data='2026-11-01',circuito_id='rodriguez',
              estado_previsao='previsao_registrada',estado_qualificacao='local_disponivel',
              estado_operacao='previsao_registrada',estado_resultado='observado_local',
              resultado_posterior_validado=validated,
              participantes_esperados_previsao=['fixture_{}'.format(i) for i in range(22)])
    return dict(versao=2,temporadas=[2024,2025,2026],identidades={},
                dados_2026=dict(corridas=[race],previsoes=rows,
                               campeonato_pilotos=dict(disponivel=False,classificacao=[],motivo='synthetic fixture')))


def evaluate(rows,**kwargs):
    return race_weekend.avaliar_previsao_registrada('previsao_registrada',rows,
        populacao_esperada=['fixture_{}'.format(i) for i in range(22)],**kwargs)


class Recorder:
    def __init__(self):self.events=[]
    def markdown(self,value,**kwargs):self.events.append(('markdown',visible_text(value)))
    def caption(self,value):self.events.append(('caption',visible_text(value)))
    def subheader(self,value):self.events.append(('subheader',visible_text(value)))
    def title(self,value):self.events.append(('title',visible_text(value)))
    def info(self,value):self.events.append(('info',visible_text(value)))
    def dataframe(self,value,**kwargs):self.events.append(('dataframe',value))


class MexicoEvaluationUITests(unittest.TestCase):
    def setUp(self):
        set_language('pt')
        self.addCleanup(set_language,'pt')

    def test_known_non_podium_DNF_is_evaluated_without_creating_positions(self):
        rows=participants();before=copy.deepcopy(rows)
        result=evaluate(rows)
        self.assertTrue(result['avaliavel_ranking'])
        self.assertEqual(result['acertos_modelo'],2)
        self.assertEqual(result['acertos_classificacao'],1)
        self.assertEqual(result['podio_observado'],['fixture_0','fixture_1','fixture_2'])
        self.assertEqual(rows,before)
        self.assertTrue(all(row['resultado_observado'] is None for row in rows[17:]))

    def test_DNF_without_confirmed_target_stays_unknown(self):
        rows=participants();rows[-1].pop('podio_resultado_confirmado')
        result=evaluate(rows)
        self.assertFalse(result['avaliavel_ranking'])
        self.assertEqual(result['motivo'],'resultado_posterior_ausente')
        self.assertIsNone(result['acertos_modelo'])
        package=race_weekend.pacote_2026(asset_for(rows))
        self.assertEqual(package['corridas'][0]['alvos_conhecidos'],21)
        self.assertIsNone(package['participantes_por_rodada'][19][-1]['podio'])

    def test_binary_DNF_requires_validated_result_and_explicit_non_podium_status(self):
        rows=participants()
        for changes in [dict(resultado_validado=False),dict(estado_resultado='indisponivel')]:
            with self.subTest(changes=changes):
                result=evaluate(rows,**changes)
                self.assertFalse(result['avaliavel_ranking'])
                self.assertEqual(result['motivo'],'resultado_posterior_nao_validado')
        for status in [None,'','Finished','Unknown','Mechanical issue']:
            with self.subTest(status=status):
                changed=copy.deepcopy(rows);changed[-1]['status_resultado']=status
                self.assertFalse(evaluate(changed)['avaliavel_ranking'])
        package=race_weekend.pacote_2026(asset_for(rows,validated=False))
        self.assertEqual(package['corridas'][0]['alvos_conhecidos'],17)
        self.assertTrue(all(row['podio'] is None for row in package['participantes_por_rodada'][19][17:]))

    def test_invalid_or_contradictory_targets_are_not_scores(self):
        for target in [True,False,'0',0.0,2,-1]:
            with self.subTest(target=target):
                rows=participants();rows[-1]['podio_resultado_confirmado']=target
                self.assertEqual(evaluate(rows)['motivo'],'alvo_posterior_invalido')
        for index,target,status in [(0,0,'Finished'),(4,1,'Finished'),(21,1,'DNF'),(0,1,'DNF')]:
            with self.subTest(index=index,target=target,status=status):
                rows=participants();rows[index].update(podio_resultado_confirmado=target,status_resultado=status)
                result=evaluate(rows)
                self.assertEqual(result['motivo'],'alvo_posterior_inconsistente')
                self.assertIsNone(result['acertos_modelo'])

    def test_three_unique_observed_podium_positions_remain_required(self):
        for index,value in [(0,None),(1,1),(2,4),(3,0),(3,False),(3,'4')]:
            with self.subTest(index=index,value=value):
                rows=participants();rows[index]['resultado_observado']=value
                result=evaluate(rows)
                self.assertFalse(result['avaliavel_ranking'])
                self.assertIsNone(result['acertos_modelo'])
        # Three confirmed positive targets without positions never manufacture a podium.
        rows=participants()
        for row in rows[:3]:row['resultado_observado']=None
        self.assertFalse(evaluate(rows)['avaliavel_ranking'])

    def test_coverage_identity_and_frozen_ranking_guards_are_preserved(self):
        mutations=[lambda rows:rows.pop(),
                   lambda rows:rows[-1].update(piloto_id='extra_driver'),
                   lambda rows:rows[-1].update(piloto_id=rows[0]['piloto_id']),
                   lambda rows:rows[-1].update(elegivel_previsao=False),
                   lambda rows:rows[0].update(ranking_modelo=2),
                   lambda rows:rows[0].update(ranking_classificacao=None),
                   lambda rows:rows[0].update(probabilidade_modelo=float('nan'))]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                rows=participants();mutate(rows)
                self.assertFalse(evaluate(rows)['avaliavel_ranking'])
        for field in ('ranking_modelo','ranking_classificacao'):
            with self.subTest(duplicate_top_rank=field):
                rows=participants();rows[-1][field]=1
                result=evaluate(rows)
                self.assertFalse(result['avaliavel_ranking'])
                self.assertEqual(result['motivo'],'ranking_publicado_incompleto')
                self.assertIsNone(result['acertos_modelo'])
        rows=participants()
        self.assertFalse(race_weekend.avaliar_previsao_registrada('ensaio_retrospectivo',rows)['avaliavel_ranking'])

    def test_package_knows_22_binary_outcomes_and_retains_five_null_positions(self):
        asset=asset_for(participants());before=copy.deepcopy(asset)
        package=race_weekend.pacote_2026(asset)
        race=package['corridas'][0]
        self.assertEqual(race['alvos_conhecidos'],22)
        self.assertEqual(race['participantes_preparados'],22)
        self.assertTrue(race['avaliavel_ranking'])
        observed=package['participantes_por_rodada'][19]
        self.assertTrue(all(row['podio']==0 and row['resultado_observado'] is None for row in observed[17:]))
        self.assertEqual(prospective_races(package),[dict(rodada=19,corrida='Mexico City Grand Prix',modelo=2,classificacao=1)])
        self.assertEqual(asset,before)

    def test_optional_target_is_structurally_validated_by_loader(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);file=root/'frontend_assets/race_weekend.json';file.parent.mkdir()
            asset=asset_for(participants());file.write_text(json.dumps(asset))
            self.assertEqual(race_weekend.carregar_asset(root),asset)
            asset['dados_2026']['previsoes'][-1]['podio_resultado_confirmado']=False
            file.write_text(json.dumps(asset))
            with self.assertRaises(race_weekend.RaceWeekendDadosErro):race_weekend.carregar_asset(root)

    def test_excluded_prospective_GP_is_visible_without_an_artificial_zero(self):
        rows=participants();rows[-1].pop('podio_resultado_confirmado')
        package=race_weekend.pacote_2026(asset_for(rows));race=package['corridas'][0]
        for lang,state,reason in [('pt','Fora da avaliação','Alvo de pódio desconhecido'),('en','Not evaluated','Podium outcome is unknown')]:
            with self.subTest(lang=lang):
                set_language(lang)
                markup=fan_views.performance_cards([],package['corridas'],2026,observed_rounds={19})
                self.assertIn(state,markup);self.assertIn(reason,markup)
                self.assertNotIn('0 de 3',markup);self.assertNotIn('0 of 3',markup)
                self.assertNotIn('Resultado em conferência',markup)
                self.assertNotIn('Result under review',markup)
                recorder=Recorder()
                with patch.object(model_views,'st',recorder),patch('pitwall.dashboard.weekend_views.observed_rounds',return_value={19}):
                    model_views.tela_desempenho(package,show_title=False)
                self.assertTrue(any(state in value for kind,value in recorder.events if kind=='markdown'))
                self.assertFalse(any(kind in ('info','dataframe') for kind,_ in recorder.events))
        self.assertFalse(race['avaliavel_ranking'])

    def test_inconsistent_validation_flag_does_not_promote_UI_status(self):
        from pitwall.dashboard import app
        source=asset_for(participants());source['dados_2026']['corridas'][0]['estado_resultado']='indisponivel'
        package=race_weekend.pacote_2026(source);block=race_weekend.dados_do_gp_2026(package,19)
        self.assertFalse(fan_views.has_validated_exclusions(package['corridas']))
        self.assertEqual(block['corrida']['motivos_nao_avaliavel'],'resultado_posterior_nao_validado')
        recorder=Recorder()
        with patch.object(app,'st',recorder),patch.object(app,'nome_piloto',side_effect=lambda package,row:row['piloto_id']),patch.object(app,'nome_equipe',return_value='Synthetic team'):
            app.renderizar_resultados_observados(package,block['corrida'],block,block['participantes'])
        captions=' '.join(value for kind,value in recorder.events if kind=='caption')
        self.assertIn('Resultado posterior ainda não validado',captions)
        self.assertNotIn('Resultado posterior validado;',captions)

    def test_prospective_NA_copy_does_not_relabel_the_emission_as_retrospective(self):
        from pitwall.dashboard import app
        rows=participants();rows[-1].pop('podio_resultado_confirmado')
        package=race_weekend.pacote_2026(asset_for(rows));block=race_weekend.dados_do_gp_2026(package,19)
        for lang,caption in [('pt','Resultado posterior validado; este GP ficou fora'),('en','The post-race result is validated; this GP is excluded')]:
            with self.subTest(lang=lang):
                set_language(lang);recorder=Recorder()
                with patch.object(app,'st',recorder),patch.object(app,'nome_piloto',side_effect=lambda package,row:row['piloto_id']),patch.object(app,'nome_equipe',return_value='Synthetic team'):
                    app.renderizar_resultados_observados(package,block['corrida'],block,block['participantes'])
                captions=' '.join(value for kind,value in recorder.events if kind=='caption')
                self.assertIn(caption,captions)
                self.assertNotIn('retrospectiv',captions.lower())
                table=next(value for kind,value in recorder.events if kind=='dataframe')
                dnf=table[table['Piloto'].isin(['fixture_{}'.format(i) for i in range(17,22)])]
                self.assertEqual(len(dnf),5)
                self.assertTrue(all(value=='N/A' for value in dnf['Resultado observado']))


if __name__=='__main__':unittest.main()

"""Contrato focal das etapas 1 e 2: asset offline Race Weekend."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import preparar_dashboard_race_weekend as preparar
import app
from dashboard_dados import carregar_temporada, dados_do_gp
from streamlit.testing.v1 import AppTest


RAIZ = Path(__file__).resolve().parents[1]


class TestAssetsRaceWeekend(unittest.TestCase):
    def test_gera_asset_local_com_nomes_historicos_e_cobertura_2026(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / 'race_weekend.json'
            asset = preparar.gerar(RAIZ, destino)
            self.assertEqual(json.loads(destino.read_text(encoding='utf-8')), asset)
        self.assertEqual(asset['versao'], 2)
        self.assertEqual(asset['temporadas'], [2024, 2025, 2026])
        self.assertEqual(asset['identidades']['2024:1:hamilton']['equipe_id'], 'mercedes')
        self.assertEqual(asset['identidades']['2025:1:hamilton']['equipe_id'], 'ferrari')
        self.assertEqual(asset['identidades']['2024:1:max_verstappen']['piloto'], 'Max Verstappen')
        corrida_2026 = {item['rodada']: item for item in asset['dados_2026']['corridas']}
        self.assertEqual(len(corrida_2026), 23)
        self.assertEqual(corrida_2026[1]['estado_resultado'], 'observado_local')
        self.assertEqual(corrida_2026[17]['estado_resultado'], 'observado_local')
        self.assertEqual(corrida_2026[17]['estado_previsao'], 'ensaio_retrospectivo')
        self.assertEqual(corrida_2026[18]['estado_qualificacao'], 'indisponivel')
        self.assertEqual(corrida_2026[18]['estado_resultado'], 'indisponivel')
        self.assertEqual(corrida_2026[18]['motivo_resultado'], 'snapshot local de resultados ausente; o calendário não prova que a corrida não foi concluída')
        singapura = [item for item in asset['dados_2026']['previsoes'] if item['rodada'] == 17]
        self.assertEqual(len(singapura), 22)
        self.assertEqual(singapura[0]['piloto'], 'Max Verstappen')
        self.assertEqual(singapura[0]['equipe_id'], 'red_bull')
        observados = [item for item in asset['dados_2026']['previsoes'] if item['resultado_observado'] is not None]
        self.assertEqual(len(observados), 374)
        self.assertEqual(len({(item['temporada'], item['rodada'], item['piloto_id']) for item in observados}), 374)
        self.assertEqual(sum(item['probabilidade_modelo'] is not None for item in singapura), 22)
        self.assertTrue(all(item['resultado_observado'] is not None for item in singapura))
        self.assertEqual(asset['proveniencia']['emissao']['modo'], 'ENSAIO_RETROSPECTIVO')
        self.assertEqual(
            asset['proveniencia']['emissao']['hashes_saidas']['probabilidades.csv'],
            '54bcac2526c326820533f0b4d96e3b9bb354cdd24a77496d634cd70d04932e2e',
        )

    def test_campeonato_2026_usa_driverstandings_jolpica_paginado_e_max_em_p4(self):
        with tempfile.TemporaryDirectory() as tmp:
            asset = preparar.gerar(RAIZ, Path(tmp) / 'race_weekend.json')
        campeonato = asset['dados_2026']['campeonato_pilotos']
        self.assertTrue(campeonato['disponivel'])
        self.assertEqual(campeonato['snapshot_id'], 'classificacao-pilotos-20261023T143930Z')
        self.assertEqual(campeonato['rodada_referencia'], 17)
        self.assertEqual(campeonato['paginas_validadas'], 1)
        self.assertIn('driverstandings.json', campeonato['url_base'])
        max_verstappen = next(item for item in campeonato['classificacao'] if item['piloto_id'] == 'max_verstappen')
        self.assertEqual(max_verstappen['posicao'], 4)
        self.assertEqual(max_verstappen['pontos'], 221.0)
        self.assertEqual(max_verstappen['vitorias'], 2)
        self.assertIsInstance(campeonato['classificacao'][0]['pontos'], float)

    def test_campeonato_incompleto_fica_indisponivel_sem_somar_resultados(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / 'data/operacao_2026/snapshots' / preparar.SNAPSHOT_CLASSIFICACAO_PILOTOS_2026
            base.mkdir(parents=True)
            (base / 'indice.json').write_text('{"paginacao": {"completa": false}}', encoding='utf-8')
            campeonato, _ = preparar._campeonato_pilotos_2026(Path(tmp))
        self.assertFalse(campeonato['disponivel'])
        self.assertEqual(campeonato['classificacao'], [])

    def test_figura_historica_usa_nomes_e_cores_contextuais_de_equipe(self):
        with tempfile.TemporaryDirectory() as tmp:
            asset = preparar.gerar(RAIZ, Path(tmp) / 'race_weekend.json')
        casos = ((2024, 'norris', 'McLaren', '#F58020'), (2024, 'hamilton', 'Mercedes', '#00A19B'),
                 (2025, 'norris', 'McLaren', '#F58020'), (2025, 'hamilton', 'Ferrari', '#E53935'))
        for temporada, piloto_id, equipe, cor in casos:
            pacote = carregar_temporada(RAIZ, temporada)
            pacote['asset_race_weekend'] = asset
            participantes = dados_do_gp(pacote, 1)['participantes']
            piloto = next(item for item in participantes if item['piloto_id'] == piloto_id)
            self.assertEqual(app.nome_equipe(pacote, piloto), equipe)
            figura = app.grafico_probabilidades(pacote, participantes)
            indice = list(figura.data[0].y).index(app.nome_piloto(pacote, piloto))
            self.assertEqual(figura.data[0].marker.color[indice], cor)

    def test_nao_chama_rede_nem_carrega_modelo(self):
        fonte = (RAIZ / 'preparar_dashboard_race_weekend.py').read_text(encoding='utf-8').lower()
        for proibido in ('urlopen', 'requests', 'socket', 'joblib', 'sklearn', 'predict', 'fit('):
            self.assertNotIn(proibido, fonte)

    def test_apptest_troca_temporada_e_gp_sem_reter_chave_invalida(self):
        with patch.dict(os.environ, {'PITWALL_DASHBOARD_ROOT': str(RAIZ)}, clear=False):
            at = AppTest.from_file(RAIZ / 'app.py', default_timeout=15)
            at.run(timeout=15)
            temporada = next(item for item in at.get('selectbox') if item.key == 'temporada')
            temporada.set_value(2026)
            at.run(timeout=15)
            self.assertFalse(at.exception, [str(item.value) for item in at.exception])
            gp = next(item for item in at.get('selectbox') if item.key == 'gp')
            self.assertEqual(len(gp.options), 23)
            gp.set_value('2026:17')
            at.run(timeout=15)
            texto = '\n'.join(str(item.value) for item in at.get('markdown') + at.get('text') + at.get('caption') + at.get('title'))
            self.assertIn('Max Verstappen', texto)
            temporada = next(item for item in at.get('selectbox') if item.key == 'temporada')
            temporada.set_value(2024)
            at.run(timeout=15)
            gp = next(item for item in at.get('selectbox') if item.key == 'gp')
            self.assertEqual(gp.value, '2024:1')


if __name__ == '__main__':
    unittest.main()

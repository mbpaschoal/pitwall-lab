"""A integração apresenta somente o asset portátil, sem dados brutos/modelos."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from tests.test_dashboard_app import copiar_artefatos, por_chave, texto_renderizado


RAIZ = Path(__file__).resolve().parents[1]


class TestDashboardAcervoApp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = copiar_artefatos(Path(self.tmp.name))
        source = RAIZ / 'frontend_assets/acervo_dashboard.json'
        shutil.copy2(source, self.raiz / 'frontend_assets/acervo_dashboard.json')
        self.asset = json.loads(source.read_text())
        self.env = patch.dict(os.environ, {'PITWALL_DASHBOARD_ROOT': str(self.raiz)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.at = AppTest.from_file(RAIZ / 'app.py', default_timeout=30)

    def executar(self, ano=2025, rodada=1):
        self.at.query_params.update({'temporada': str(ano), 'gp': str(rodada)})
        self.at.run(timeout=30)
        self.assertFalse(self.at.exception, [str(e.value) for e in self.at.exception])
        return self.at

    def test_australia_2025_exibe_clima_pneus_equipes_e_fontes_sem_rede(self):
        with patch('socket.create_connection', side_effect=AssertionError('Consulta de rede proibida')):
            self.executar()
        textos = [texto_renderizado(self.at)]
        for key in ('weather','strategy','teams','history'):
            por_chave(self.at.button, 'pw_nav_' + key).click()
            self.at.run(timeout=30)
            self.assertFalse(self.at.exception)
            textos.append(texto_renderizado(self.at))
        texto = '\n'.join(textos)
        for trecho in ('Clima do fim de semana', 'Open-Meteo.com', 'Modelo atmosférico histórico próximo ao circuito',
                       'Uso dos pneus', 'Resultados por equipe',
                       'Desempenho dos pilotos nesta pista', '2026-10-29-acervo-2'):
            self.assertIn(trecho, texto)
        self.assertNotIn('Clima não disponível', texto)
        self.assertFalse((self.raiz / 'data').exists())
        self.assertFalse((self.raiz / 'models').exists())

    def test_gp_futuro_tem_historico_da_mesma_pista_sem_podio_atual(self):
        self.at.query_params['aba'] = 'Histórico'
        self.executar(2026,19)
        texto=texto_renderizado(self.at)
        self.assertIn('Desempenho dos pilotos nesta pista',texto)
        self.assertIn('5 edições anteriores',texto)
        self.assertTrue(any('Vitórias' in df.value.columns and len(df.value)>0 for df in self.at.dataframe))

    def test_classificacao_2024_preserva_fases_sem_colunas_de_probabilidade(self):
        self.at.query_params['aba'] = 'Tempos'
        self.executar(2024, 1)
        gp = self.asset['gps']['2024:1']
        sessao = next(s for s in gp['sessoes'] if s['nome'] == 'Qualifying')
        por_chave(self.at.selectbox, 'acervo_2024_1_sessao_tempos').set_value(sessao['session_key'])
        self.at.run(timeout=30)
        self.assertFalse(self.at.exception)
        tabelas = [e.value for e in self.at.dataframe if 'Q1' in e.value.columns]
        self.assertEqual(len(tabelas), 1)
        self.assertEqual(len(tabelas[0]), len(sessao['tempos']))
        self.assertTrue({'Q1', 'Q2', 'Q3'}.issubset(tabelas[0].columns))
        self.assertFalse(any('Prob.' in c or 'previsão' in c for c in tabelas[0].columns))
        self.assertEqual(next(s for s in self.at.selectbox if s.key == 'temporada').value, 2024)

    def test_baku_classificacao_sem_voltas_mantem_tempos_agregados(self):
        self.at.query_params['aba'] = 'Tempos'
        self.executar(2025, 17)
        por_chave(self.at.selectbox, 'acervo_2025_17_sessao_tempos').set_value(9900)
        self.at.run(timeout=30)
        self.assertFalse(self.at.exception)
        self.assertIn('Voltas detalhadas desta sessão indisponíveis', texto_renderizado(self.at))
        tabela = next(e.value for e in self.at.dataframe if 'Q1' in e.value.columns)
        self.assertEqual(len(tabela), 20)
        self.assertTrue(tabela['Q1'].notna().any())

    def test_corrida_mostra_semantica_de_tempo_total(self):
        self.at.query_params['aba'] = 'Tempos'
        self.executar()
        gp = self.asset['gps']['2025:1']
        sessao = next(s for s in gp['sessoes'] if s['nome'] == 'Race')
        por_chave(self.at.selectbox, 'acervo_2025_1_sessao_tempos').set_value(sessao['session_key'])
        self.at.run(timeout=30)
        self.assertFalse(self.at.exception)
        self.assertIn('Tempo total publicado para a prova.', texto_renderizado(self.at))

    def test_austin_mantem_emissao_probabilidades_e_dados_congelados(self):
        fontes = list((self.raiz / 'reports').rglob('*.csv')) + [self.raiz / 'frontend_assets/race_weekend.json']
        hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in fontes}
        self.executar(2026, 18)
        texto = texto_renderizado(self.at)
        self.assertIn('Previsão registrada antes da corrida.', texto)
        for key, label in [('weather','Clima do fim de semana'),('strategy','Uso dos pneus')]:
            por_chave(self.at.button, 'pw_nav_' + key).click()
            self.at.run(timeout=30)
            self.assertFalse(self.at.exception)
            self.assertIn(label, texto_renderizado(self.at))
        self.assertEqual(hashes, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in fontes})

    def test_gp_futuro_sem_acervo_mantem_ausencia_sem_probabilidades(self):
        # Escolha um GP realmente sem emissão: México agora tem previsão registrada.
        dados = json.loads((self.raiz / 'frontend_assets/race_weekend.json').read_text())['dados_2026']
        emitidas = {p['rodada'] for p in dados['previsoes']}
        candidatas = [r['rodada'] for r in dados['corridas'] if r['rodada'] not in emitidas and '2026:{}'.format(r['rodada']) not in self.asset['gps']]
        if not candidatas:
            self.skipTest('O asset não possui GP sem emissão e sem acervo.')
        self.at.query_params['aba'] = 'Estratégias'
        self.executar(2026, candidatas[0])
        texto = texto_renderizado(self.at)
        self.assertNotIn('Favoritos por ranking publicado', texto)
        self.assertIn('Estratégias indisponíveis no pacote local.', texto)
        self.assertNotIn('Clima do fim de semana', texto)
        self.assertNotIn('Uso dos pneus', texto)
        self.assertNotIn('Favoritos por ranking publicado', texto)
        por_chave(self.at.radio, 'tela').set_value('Previsões')
        self.at.run(timeout=30)
        self.assertIn('Sem probabilidades publicadas', texto_renderizado(self.at))


if __name__ == '__main__':
    unittest.main()

"""Regressões de navegação, classificação completa e conteúdo canônico."""
from html.parser import HTMLParser
import importlib.util
import os
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
import app
import pitwall_ui
from acervo_dashboard_dados import carregar, para_gp
from pitwall_ui_dados import carregar_paineis, complementar_paineis
from tests.test_dashboard_app import copiar_artefatos, por_chave, texto_renderizado

ROOT = Path(__file__).resolve().parents[1]


class TabelasHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = 0
        self.links = []
        self._dentro_link = False

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.rows += 1
        if tag == 'a':
            if self._dentro_link:
                raise AssertionError('Link aninhado')
            self._dentro_link = True
            self.links.append(dict(attrs).get('href'))

    def handle_endtag(self, tag):
        if tag == 'a':
            self._dentro_link = False


class TestInterfaceEditorial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.asset = carregar(ROOT)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = copiar_artefatos(Path(self.tmp.name))
        shutil.copy2(ROOT / 'frontend_assets/acervo_dashboard.json', self.root / 'frontend_assets/acervo_dashboard.json')
        env = patch.dict(os.environ, {'PITWALL_DASHBOARD_ROOT': str(self.root)})
        env.start(); self.addCleanup(env.stop)
        self.at = AppTest.from_file(ROOT / 'app.py', default_timeout=30)

    def run_app(self, query):
        self.at.query_params.update(query)
        self.at.run(timeout=30)
        self.assertFalse(self.at.exception)
        return texto_renderizado(self.at)

    def test_campeonatos_completos_em_todos_os_66_gps_sem_posicoes_inventadas(self):
        for gp in self.asset['gps'].values():
            ident = gp['identidade']
            paineis = complementar_paineis(carregar_paineis(ROOT, ident['temporada'], ident['rodada'], ident['circuito_id']), gp)
            for campo, teams in [('driver_standings', False), ('constructor_standings', True)]:
                snapshot = paineis[campo]
                parser = TabelasHTML(); html = pitwall_ui.standings_table(snapshot, teams)
                parser.feed(html)
                esperado = len(snapshot.get('classificacao', [])) if snapshot['disponivel'] else 0
                self.assertEqual(parser.rows, esperado + (1 if esperado else 0), (ident, campo))
                self.assertNotIn('Top 5', html)
                if snapshot['disponivel']:
                    self.assertEqual(len(re.findall(r'<tr><td>—</td>', html)), sum(r.get('posicao') is None for r in snapshot['classificacao']))

    def test_corridas_nao_repete_previsoes_e_cada_campeonato_aparece_uma_vez(self):
        texto = self.run_app({'temporada': '2026', 'gp': '18'})
        self.assertNotIn('Antes da corrida', texto)
        self.assertNotIn('Acertos — modelo', texto)
        self.assertNotIn('Previsão e resultado observado', texto)
        self.assertEqual(texto.count('aria-label="Campeonato de pilotos"'), 0)
        self.assertEqual(sum(e.label == 'Fontes e cobertura' for e in self.at.expander), 1)
        texto = self.run_app({'tela': 'Campeonato', 'temporada': '2026', 'gp': '18'})
        self.assertEqual(texto.count('aria-label="Campeonato de pilotos"'), 1)
        self.assertEqual(texto.count('aria-label="Campeonato de construtores"'), 1)
        self.assertIn('Sergio Pérez', texto)
        self.assertFalse(any('campeonato' in e.label.lower() for e in self.at.expander
                             if not e.label.startswith('Explorar o Pitwall')))

    def test_atalho_real_preserva_gp_e_separa_paineis(self):
        texto = self.run_app({'temporada': '2025', 'gp': '1'})
        shortcut = next(button for button in self.at.button if button.label == 'Ver previsões deste GP')
        shortcut.click()
        self.at.run(timeout=30)
        self.assertFalse(self.at.exception)
        texto = texto_renderizado(self.at)
        self.assertEqual(por_chave(self.at.radio, 'tela').value, 'Previsões')
        self.assertEqual(por_chave(self.at.selectbox, 'gp').value, '2025:1')
        self.assertIn('Antes da corrida', texto)
        self.assertNotIn('aria-label="Campeonato de pilotos"', texto)
        self.assertNotIn('Histórico observado deste GP', texto)
        self.assertEqual(texto.count('Estudo retrospectivo com dados históricos.'), 1)
        self.assertEqual(texto.count('Avaliação após a corrida'), 1)

    def test_busca_exibe_identidade_sem_repetir_probabilidades(self):
        self.run_app({'temporada': '2026', 'gp': '18'})
        por_chave(self.at.text_input, 'busca_local').set_value('Verstappen')
        self.at.run(timeout=30)
        pesquisa = next(df.value for df in self.at.dataframe if list(df.value.columns) == ['Piloto', 'Equipe'])
        self.assertEqual(pesquisa.iloc[0]['Piloto'], 'Max Verstappen')

    def test_atalho_nativo_preserva_gp_e_idioma_nas_tres_temporadas(self):
        for lang, label in [('pt', 'Ver previsões deste GP'), ('en', 'View predictions for this GP')]:
            for year, round_ in [(2024, 1), (2025, 9), (2026, 19)]:
                with self.subTest(lang=lang, year=year, round=round_):
                    self.run_app({'tela':'Corridas', 'temporada':str(year), 'gp':str(round_), 'lang':lang})
                    next(button for button in self.at.button if button.label == label).click()
                    self.at.run(timeout=30)
                    self.assertFalse(self.at.exception)
                    self.assertEqual(por_chave(self.at.radio, 'tela').value, 'Previsões')
                    self.assertEqual(por_chave(self.at.selectbox, 'gp').value, '{}:{}'.format(year, round_))
                    self.assertEqual(self.at.query_params['lang'], lang)

    def test_atalho_classificacao_seleciona_sessoes_na_mesma_navegacao(self):
        self.run_app({'tela':'Corridas', 'temporada':'2025', 'gp':'1', 'lang':'pt'})
        next(button for button in self.at.button if button.label == 'Ver classificação completa da corrida').click()
        self.at.run(timeout=30)
        self.assertFalse(self.at.exception)
        self.assertEqual(por_chave(self.at.radio, 'tela').value, 'Corridas')
        self.assertEqual(por_chave(self.at.selectbox, 'gp').value, '2025:1')
        self.assertEqual(self.at.query_params['aba'], 'Tempos')

    def test_creditos_removem_html_externo_e_link_de_clima_tem_destino(self):
        texto = self.run_app({'temporada': '2025', 'gp': '1', 'aba': 'Clima'})
        parser = TabelasHTML(); parser.feed(texto)
        self.assertTrue(any('aba=Clima' in u for u in parser.links if u))
        self.assertTrue(all(u and not u.startswith(('javascript:', 'data:')) for u in parser.links))
        self.assertNotIn('href="//commons', texto)
        self.assertEqual(app.credito_texto('<a href="//invalid">Nome &amp; Autor</a>'), 'Nome & Autor')

    def test_documentacao_allowlistada_mantem_links_funcionais(self):
        caminho = ROOT / 'documentacao_local.py'
        if not caminho.exists():
            caminho = ROOT / 'publicacao/templates/documentacao_local.py'
        spec = importlib.util.spec_from_file_location('docs_editoriais', caminho)
        docs = importlib.util.module_from_spec(spec); spec.loader.exec_module(docs)
        texto = docs.reescrever_links('[Protocolo](protocolo_temporal.md) [CSV](../reports/modelo_v1/previsoes_validacao.csv) [API](https://openf1.org/docs/) [Privado](../../segredo.md)')
        self.assertIn('documento=protocolo-temporal', texto)
        self.assertIn('documento=relatorio-2024&amp;download=csv', texto)
        self.assertIn('[API](https://openf1.org/docs/)', texto)
        self.assertNotIn('](../../segredo.md)', texto)
        self.assertNotIn('disponível no seletor', texto)
        for documento in docs.documentos_disponiveis():
            query = parse_qs(urlsplit(docs.url_documento(documento['id'])).query)
            self.assertEqual(query['documento'], [documento['id']])
        with self.assertRaises(ValueError):
            docs.url_documento('../../segredo')


if __name__ == '__main__':
    unittest.main()

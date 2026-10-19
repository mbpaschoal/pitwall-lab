"""Aceite autocontido do pacote exportado."""
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]


def arquivos_reais():
    diretorios_locais = {'.git', '.venv', '__pycache__', '.pytest_cache'}
    encontrados = []
    for pasta, diretorios, arquivos in os.walk(RAIZ):
        diretorios[:] = [diretorio for diretorio in diretorios if diretorio not in diretorios_locais]
        pasta_atual = Path(pasta)
        encontrados.extend((pasta_atual / arquivo).relative_to(RAIZ).as_posix() for arquivo in arquivos)
    return sorted(encontrados)


def carregar_documentacao():
    caminho = RAIZ / 'documentacao_local.py'
    spec = importlib.util.spec_from_file_location('documentacao_local', caminho)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class StubStreamlit:
    def __init__(self):
        self.markdowns = []
        self.downloads = []

    def subheader(self, *_args, **_kwargs):
        pass

    def selectbox(self, _rotulo, opcoes, **_kwargs):
        return opcoes[1]

    def caption(self, *_args, **_kwargs):
        self.markdowns.extend(_args)

    def markdown(self, texto, **_kwargs):
        self.markdowns.append(texto)

    def download_button(self, rotulo, **kwargs):
        self.downloads.append((rotulo, kwargs))


class TestDistribuicao(unittest.TestCase):
    def test_manifesto_e_lista_descrevem_exatamente_o_pacote(self):
        manifesto = json.loads((RAIZ / 'MANIFESTO.json').read_text(encoding='utf-8'))
        publicados = (RAIZ / 'ARQUIVOS_PUBLICACAO.txt').read_text(encoding='utf-8').splitlines()
        self.assertEqual(sorted(publicados), arquivos_reais())
        self.assertIn('.gitignore', publicados)
        self.assertEqual((RAIZ / '.gitignore').read_text(encoding='utf-8').splitlines(), [
            '.venv/', '__pycache__/', '.pytest_cache/', '.DS_Store', '.env', '.env.*',
            '.streamlit/secrets.toml', '*.joblib', 'data/', 'models/',
        ])
        registros = {item['caminho']: item for item in manifesto['arquivos']}
        self.assertNotIn('MANIFESTO.json', registros)
        self.assertEqual(set(publicados) - {'MANIFESTO.json'}, set(registros))
        for caminho, registro in registros.items():
            self.assertEqual(registro['sha256_destino'], hashlib.sha256((RAIZ / caminho).read_bytes()).hexdigest())

    def test_documentacao_renderiza_localmente_e_oferece_csv_da_allowlist(self):
        modulo = carregar_documentacao()
        st = StubStreamlit()
        modulo.renderizar_documentacao_local(st)
        self.assertTrue(any('Relatório de 2024' in texto for texto in st.markdowns))
        self.assertTrue(any('Plano da avaliação de 2025' in texto for texto in st.markdowns))
        self.assertTrue(any('São registros históricos; 2025 já foi avaliado' in texto for texto in st.markdowns))
        self.assertEqual(len(st.downloads), 1)
        rotulo, kwargs = st.downloads[0]
        self.assertEqual(rotulo, 'Baixar previsões de 2024 (CSV)')
        self.assertEqual(kwargs['data'], (RAIZ / 'reports/modelo_v1/previsoes_validacao.csv').read_bytes())

    def test_inventario_ignora_so_diretorios_locais_conhecidos(self):
        raiz_real = RAIZ
        with tempfile.TemporaryDirectory() as temporario:
            raiz_ficticia = Path(temporario) / 'pacote-ficticio'
            raiz_ficticia.mkdir()
            segredo = raiz_ficticia / '.env'
            bytes_segredo = b'CHAVE_DE_TESTE=preservar\n\x00'
            segredo.write_bytes(bytes_segredo)
            (raiz_ficticia / 'arquivo-base.txt').write_text('base', encoding='utf-8')

            with patch(f'{__name__}.RAIZ', raiz_ficticia):
                esperado = arquivos_reais()
                for diretorio in ('.git', '.venv', '__pycache__', '.pytest_cache'):
                    caminho = RAIZ / diretorio
                    caminho.mkdir()
                    (caminho / 'stage7-probe.txt').write_text('temporario', encoding='utf-8')
                extra = RAIZ / 'arquivo-extra-stage7.txt'
                extra.write_text('NAO_IGNORAR', encoding='utf-8')

                self.assertEqual(arquivos_reais(), sorted(esperado + ['arquivo-extra-stage7.txt']))
                self.assertEqual(segredo.read_bytes(), bytes_segredo)

            self.assertEqual(RAIZ, raiz_real)
            self.assertFalse((raiz_real / 'arquivo-extra-stage7.txt').exists())

    def test_configuracao_nao_fixa_rede_publica_e_fontes_sao_locais(self):
        config = (RAIZ / '.streamlit/config.toml').read_text(encoding='utf-8')
        self.assertIn('headless = true', config)
        self.assertIn('gatherUsageStats = false', config)
        self.assertNotIn('address =', config)
        self.assertNotIn('port =', config)
        readme = (RAIZ / 'README.md').read_text(encoding='utf-8')
        self.assertIn('python3.12 -m venv .venv', readme)
        self.assertIn('não modifica o ambiente científico original', readme)
        guia = (RAIZ / 'GUIA_HOSPEDAGEM.md').read_text(encoding='utf-8')
        self.assertIn('git init -b main', guia)
        self.assertIn('ARQUIVOS_PUBLICACAO.txt', guia)
        self.assertIn('Yup, I have an app', guia)
        fontes = '\n'.join((RAIZ / nome).read_text(encoding='utf-8') for nome in ('app.py', 'dashboard_dados.py'))
        for proibido in ('joblib', 'sklearn', 'treinar_modelo', 'avaliar_modelo', 'data/', 'urllib', 'requests', 'socket'):
            self.assertNotIn(proibido, fontes.lower())


if __name__ == '__main__':
    unittest.main()

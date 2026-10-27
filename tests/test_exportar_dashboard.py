"""TDD da etapa 7: exportação mínima, reproduzível e sem fontes externas."""
import hashlib
import importlib.util
import json
import errno
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


RAIZ = Path(__file__).resolve().parents[1]
BASE = '05eec0b70b24abf9a68dae45aac36730eefb5bc5'


def sha256(caminho):
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def arquivos_reais(raiz):
    diretorios_locais = {'.git', '.venv', '__pycache__', '.pytest_cache'}
    encontrados = []
    for pasta, diretorios, arquivos in os.walk(raiz):
        diretorios[:] = [diretorio for diretorio in diretorios if diretorio not in diretorios_locais]
        pasta_atual = Path(pasta)
        encontrados.extend((pasta_atual / arquivo).relative_to(raiz).as_posix() for arquivo in arquivos)
    return sorted(encontrados)


def modulo_exportador():
    caminho = RAIZ / 'exportar_dashboard.py'
    spec = importlib.util.spec_from_file_location('exportar_dashboard', caminho)
    assert spec and spec.loader, 'Falta implementar exportar_dashboard.py'
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def modulo_local(caminho, nome):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class TestExportacaoDashboard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=str(Path(tempfile.gettempdir()).resolve()))
        self.addCleanup(self.tmp.cleanup)
        self.destino = Path(self.tmp.name) / 'pacote'
        self.exportador = modulo_exportador()

    def exportar(self, destino=None):
        return self.exportador.exportar(
            raiz_projeto=RAIZ,
            destino=destino or self.destino,
            commit_origem=BASE,
        )

    def test_allowlist_copia_bytes_cientificos_e_registra_manifesto(self):
        self.exportar()
        manifesto = json.loads((self.destino / 'MANIFESTO.json').read_text(encoding='utf-8'))
        publicados = (self.destino / 'ARQUIVOS_PUBLICACAO.txt').read_text(encoding='utf-8').splitlines()
        reais = arquivos_reais(self.destino)

        cientificos = {
            'reports/modelo_v1/previsoes_validacao.csv',
            'reports/modelo_v1/avaliacao_corridas.csv',
            'reports/modelo_v1/metricas.json',
            'reports/modelo_v1/calibracao.csv',
            'reports/avaliacao_final_v1/previsoes_pre_corrida.csv',
            'reports/avaliacao_final_v1/avaliacao_por_piloto.csv',
            'reports/avaliacao_final_v1/avaliacao_corridas.csv',
            'reports/avaliacao_final_v1/metricas.json',
            'reports/avaliacao_final_v1/calibracao.csv',
        }
        self.assertEqual(manifesto['commit_origem'], BASE)
        self.assertEqual(set(publicados), set(reais))
        self.assertEqual(len(publicados), len(set(publicados)))
        self.assertIn('MANIFESTO.json', publicados)
        self.assertIn('ARQUIVOS_PUBLICACAO.txt', publicados)
        self.assertIn('.gitignore', publicados)
        self.assertEqual((self.destino / '.gitignore').read_text(encoding='utf-8').splitlines(), [
            '.venv/', '__pycache__/', '.pytest_cache/', '.DS_Store', '.env', '.env.*',
            '.streamlit/secrets.toml', '*.joblib', 'data/', 'models/',
        ])
        self.assertNotIn('MANIFESTO.json', {item['caminho'] for item in manifesto['arquivos']})
        self.assertEqual(cientificos, set(manifesto['fontes_cientificas']))
        for relativo in cientificos:
            self.assertEqual((RAIZ / relativo).read_bytes(), (self.destino / relativo).read_bytes(), relativo)
        proibidos = ('data/', 'models/', '.venv/', '.env', 'joblib', 'coletar_', 'treinar_', 'avaliar_modelo')
        self.assertFalse(any(item.startswith(proibidos) for item in publicados))

    def test_inventario_ignora_so_diretorios_locais_conhecidos(self):
        self.exportar()
        esperado = arquivos_reais(self.destino)
        for diretorio in ('.git', '.venv', '__pycache__', '.pytest_cache'):
            caminho = self.destino / diretorio
            caminho.mkdir()
            (caminho / 'stage7-probe.txt').write_text('temporario', encoding='utf-8')
        (self.destino / '.env').write_text('NAO_IGNORAR', encoding='utf-8')
        (self.destino / 'arquivo-extra.txt').write_text('NAO_IGNORAR', encoding='utf-8')
        atuais = arquivos_reais(self.destino)
        self.assertEqual(atuais, sorted(esperado + ['.env', 'arquivo-extra.txt']))

    def test_documentos_tela_offline_e_download_csv_sao_whitelistados(self):
        self.exportar()
        modulo = modulo_local(self.destino / 'documentacao_local.py', 'documentacao_local_exportada')
        documentos = modulo.documentos_disponiveis()
        titulos = [item['titulo'] for item in documentos]
        self.assertIn('Protocolo temporal', titulos)
        self.assertIn('Relatório de 2024', titulos)
        self.assertIn('Plano da avaliação de 2025', titulos)
        protocolo = next(item for item in documentos if item['titulo'] == 'Protocolo temporal')
        texto = modulo.conteudo_documento(protocolo['id'])
        self.assertIn('estudo retrospectivo', texto.lower())
        self.assertNotIn('](protocolo_temporal.md)', texto)
        downloads = modulo.downloads_documento('relatorio-2024')
        self.assertEqual(len(downloads), 1)
        self.assertEqual(downloads[0]['nome'], 'previsoes_validacao.csv')
        self.assertEqual(downloads[0]['dados'], (self.destino / 'reports/modelo_v1/previsoes_validacao.csv').read_bytes())
        relatorio = (self.destino / 'docs/relatorio_2024.md').read_text(encoding='utf-8')
        self.assertIn('artefato de auditoria fora desta demonstração', relatorio)
        origem = (RAIZ / 'reports/modelo_v1/relatorio.md').read_bytes()
        self.assertIn(hashlib.sha256(origem).hexdigest(), relatorio)

    def test_documentacao_recusa_ancestral_symlink_para_fora_do_pacote(self):
        self.exportar()
        modulo = modulo_local(self.destino / 'documentacao_local.py', 'documentacao_local_symlink')
        documentos = self.destino / 'docs'
        externo = Path(self.tmp.name) / 'docs-externos'
        documentos.rename(externo)
        documentos.symlink_to(externo, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'fora da raiz'):
            modulo.conteudo_documento('protocolo-temporal')

    def test_destino_identico_e_idempotente_e_duas_exportacoes_sao_iguais(self):
        segundo = Path(self.tmp.name) / 'segundo'
        self.exportar(self.destino)
        self.exportar(self.destino)
        self.exportar(segundo)
        self.assertEqual(arquivos_reais(self.destino), arquivos_reais(segundo))
        for relativo in arquivos_reais(self.destino):
            self.assertEqual(sha256(self.destino / relativo), sha256(segundo / relativo), relativo)

    def test_zip_symlink_regular_ou_pendente_e_recusado_sem_tocar_no_alvo(self):
        zip_path = self.destino.parent / 'pitwall-dashboard.zip'
        sentinela = Path(self.tmp.name) / 'sentinela-externa.txt'
        sentinela.write_bytes(b'nao alterar sentinela')
        antes = sentinela.stat()
        zip_path.symlink_to(sentinela)
        link_antes = zip_path.lstat()
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.exportar()
        self.assertEqual(sentinela.read_bytes(), b'nao alterar sentinela')
        self.assertEqual(sentinela.stat().st_mtime_ns, antes.st_mtime_ns)
        self.assertEqual(zip_path.lstat().st_ino, link_antes.st_ino)
        self.assertTrue(zip_path.is_symlink())

        zip_path.unlink()
        pendente = Path(self.tmp.name) / 'alvo-ausente.zip'
        zip_path.symlink_to(pendente)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.exportar()
        self.assertTrue(zip_path.is_symlink())
        self.assertFalse(pendente.exists())
        self.assertFalse(self.destino.exists())

    def test_zip_regular_divergente_e_identico_preservam_bytes_inode_e_mtime(self):
        zip_path = self.destino.parent / 'pitwall-dashboard.zip'
        zip_path.write_bytes(b'zip rival divergente')
        antes = zip_path.stat()
        with self.assertRaisesRegex(ValueError, 'ZIP de destino diverge'):
            self.exportar()
        self.assertEqual(zip_path.read_bytes(), b'zip rival divergente')
        depois = zip_path.stat()
        self.assertEqual((depois.st_ino, depois.st_mtime_ns), (antes.st_ino, antes.st_mtime_ns))
        self.assertFalse(self.destino.exists())

        zip_path.unlink()
        self.exportar()
        antes = zip_path.stat()
        bytes_antes = zip_path.read_bytes()
        resultado = self.exportar()
        depois = zip_path.stat()
        self.assertTrue(resultado['idempotente'])
        self.assertEqual(zip_path.read_bytes(), bytes_antes)
        self.assertEqual((depois.st_ino, depois.st_mtime_ns), (antes.st_ino, antes.st_mtime_ns))

    def test_zip_diretorio_e_fifo_sao_recusados_sem_abertura(self):
        zip_path = self.destino.parent / 'pitwall-dashboard.zip'
        zip_path.mkdir()
        with self.assertRaisesRegex(ValueError, 'arquivo regular'):
            self.exportar()
        zip_path.rmdir()
        if not hasattr(os, 'mkfifo'):
            self.skipTest('mkfifo indisponível neste sistema')
        os.mkfifo(zip_path)
        with self.assertRaisesRegex(ValueError, 'arquivo regular'):
            self.exportar()
        self.assertTrue(zip_path.exists())

    def test_zip_rival_que_aparece_antes_do_link_e_preservado(self):
        zip_path = self.destino.parent / 'pitwall-dashboard.zip'
        link_real = self.exportador.os.link

        def rival_antes_do_link(origem, destino):
            Path(destino).write_bytes(b'zip rival concorrente')
            raise FileExistsError(errno.EEXIST, 'File exists', destino)

        with patch.object(self.exportador.os, 'link', side_effect=rival_antes_do_link):
            with self.assertRaisesRegex(ValueError, 'apareceu ou diverge'):
                self.exportar()
        self.assertEqual(zip_path.read_bytes(), b'zip rival concorrente')
        self.assertFalse(list(self.destino.parent.glob('.pitwall-dashboard-*.zip')))
        self.assertTrue(callable(link_real))

    def test_destino_divergente_ou_symlink_e_recusado_sem_sobrescrever(self):
        self.destino.mkdir()
        sentinela = self.destino / 'arquivo-do-usuario.txt'
        sentinela.write_text('preservar', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'destino'):
            self.exportar()
        self.assertEqual(sentinela.read_text(encoding='utf-8'), 'preservar')

        if hasattr(__import__('os'), 'symlink'):
            alvo = Path(self.tmp.name) / 'alvo'
            alvo.mkdir()
            link = Path(self.tmp.name) / 'link'
            link.symlink_to(alvo, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                self.exportar(link)

    def test_validar_destino_recusa_ancestral_symlink_fora_da_raiz_lexical(self):
        scratch = Path(os.environ.get('TMPDIR', tempfile.gettempdir()))
        with tempfile.TemporaryDirectory(dir=scratch) as temporario:
            destino_padrao = RAIZ / 'distribuicao' / 'pitwall-dashboard'
            destino_scratch = Path(temporario) / 'destino-legitimo'
            self.assertEqual(
                self.exportador._validar_destino(RAIZ, destino_padrao),
                destino_padrao.absolute(),
            )
            self.assertEqual(
                self.exportador._validar_destino(RAIZ, destino_scratch),
                destino_scratch.absolute(),
            )

            alias = Path(temporario) / 'alias-do-cofre'
            alias.symlink_to(RAIZ, target_is_directory=True)
            destino = alias / 'notes' / 'nao-criar-este-diretorio'

            with self.assertRaisesRegex(ValueError, 'symlink'):
                self.exportador._validar_destino(RAIZ, destino)

    def test_validar_destino_recusa_alias_com_diretorio_pai_no_cofre_falso_sem_escrever(self):
        scratch = Path(os.environ.get('TMPDIR', tempfile.gettempdir()))
        with tempfile.TemporaryDirectory(dir=scratch) as temporario:
            cofre = Path(temporario) / 'cofre-falso'
            cofre.mkdir()
            proibido = cofre / 'notes' / 'pacote-nao-permitido'
            alias = Path(temporario) / 'ponte'
            alias.mkdir()
            alias_com_diretorio_pai = alias / '..' / 'cofre-falso' / 'notes' / 'pacote-nao-permitido'
            permitido = cofre / 'distribuicao' / 'pitwall-dashboard'

            self.assertEqual(self.exportador._validar_destino(cofre, permitido), permitido.absolute())
            with self.assertRaisesRegex(ValueError, 'destino dentro do projeto'):
                self.exportador._validar_destino(cofre, proibido)
            with self.assertRaisesRegex(ValueError, 'diretório-pai'):
                self.exportador._validar_destino(cofre, alias_com_diretorio_pai)
            with self.assertRaisesRegex(ValueError, 'raiz do projeto.*diretório-pai'):
                self.exportador._validar_destino(alias / '..' / 'cofre-falso', permitido)

            self.assertFalse(proibido.exists())
            self.assertFalse((cofre / 'notes').exists())

    def test_exportar_recusa_alias_de_caixa_do_cofre_falso_sem_criar_arquivos(self):
        scratch = Path(os.environ.get('TMPDIR', tempfile.gettempdir()))
        with tempfile.TemporaryDirectory(dir=scratch) as temporario:
            cofre = Path(temporario) / 'cofre-falso'
            cofre.mkdir()
            direto = cofre / 'notes' / 'proibido' / 'pacote'
            alias_caixa = Path(temporario) / 'COFRE-FALSO' / 'notes' / 'proibido' / 'pacote'

            if not (Path(temporario) / 'COFRE-FALSO').exists():
                self.skipTest('o sistema de arquivos deste ambiente diferencia maiúsculas e minúsculas')
            self.assertTrue((Path(temporario) / 'COFRE-FALSO').samefile(cofre))
            self.assertFalse((Path(temporario) / 'COFRE-FALSO').is_symlink())

            arquivos_sinteticos = {
                'sentinela.txt': {
                    'conteudo': b'DADOS SINTETICOS: regressao de confinamento',
                    'modo': 'gerado',
                    'fonte': None,
                    'sha256_origem': None,
                    'nota': None,
                },
            }
            with patch.object(self.exportador, 'validar_fontes_no_commit', return_value={}), \
                    patch.object(self.exportador, '_montar_arquivos', return_value=arquivos_sinteticos), \
                    patch.object(self.exportador, '_data_do_commit', return_value='sintetico'), \
                    patch.object(self.exportador, '_lista_templates_com_hashes', return_value=[]):
                for destino in (direto, alias_caixa):
                    with self.assertRaisesRegex(ValueError, 'destino dentro do projeto'):
                        self.exportador.exportar(cofre, destino)
                    self.assertFalse(destino.exists())
                    self.assertFalse((direto / 'sentinela.txt').exists())
                    self.assertFalse((direto / 'ARQUIVOS_PUBLICACAO.txt').exists())
                    self.assertFalse((direto / 'MANIFESTO.json').exists())
            self.assertFalse((cofre / 'notes').exists())

    def test_configuracao_requisitos_e_testes_portaveis_nao_dependem_do_cofre(self):
        self.exportar()
        requisitos = (self.destino / 'requirements.txt').read_text(encoding='utf-8').splitlines()
        self.assertEqual(requisitos, [
            'streamlit==1.50.0',
            'plotly==6.3.1',
            'pandas==2.2.3',
            'pyarrow==20.0.0',
            'numpy==1.26.4',
            'protobuf==5.29.5',
        ])
        for linha in requisitos:
            if linha.startswith(('-c ', '-r ')):
                self.assertTrue((self.destino / linha.split(maxsplit=1)[1]).is_file(), linha)
        config = (self.destino / '.streamlit/config.toml').read_text(encoding='utf-8')
        self.assertIn('gatherUsageStats = false', config)
        self.assertIn('headless = true', config)
        self.assertIn('primaryColor = "#D3071D"', config)
        self.assertIn('backgroundColor = "#E8F3FC"', config)
        self.assertNotIn('address =', config)
        self.assertNotIn('port =', config)
        app_testes = (self.destino / 'tests/test_dashboard_app.py').read_text(encoding='utf-8')
        self.assertNotIn('/.hermes/installs/', app_testes)
        self.assertNotIn('/.venv/lib/python3.9/site-packages', app_testes)
        self.assertTrue((self.destino / 'tests/test_dashboard_dados.py').is_file())
        self.assertTrue((self.destino / 'tests/test_distribuicao.py').is_file())
        catalogo = json.loads((self.destino / 'dashboard_assets/circuit/catalogo_visual.json').read_text(encoding='utf-8'))
        america = catalogo['circuitos']['americas']
        for ativo in (america['foto'], america['mapa']):
            caminho = self.destino / ativo['caminho']
            self.assertTrue(caminho.is_file(), ativo['caminho'])
            self.assertEqual(sha256(caminho), ativo['sha256'], ativo['caminho'])
        atribuicoes = (self.destino / 'dashboard_assets/circuit/ATRIBUICOES.md').read_text(encoding='utf-8')
        for ativo in (america['foto'], america['mapa']):
            self.assertIn(ativo['autor'], atribuicoes)
            self.assertIn(ativo['licenca'], atribuicoes)
        readme = (self.destino / 'README.md').read_text(encoding='utf-8')
        self.assertIn('python3.12 -m venv .venv', readme)
        self.assertIn('não modifica o ambiente científico original', readme)
        guia = (self.destino / 'GUIA_HOSPEDAGEM.md').read_text(encoding='utf-8')
        self.assertIn('git init -b main', guia)
        self.assertIn('ARQUIVOS_PUBLICACAO.txt', guia)
        self.assertIn('Yup, I have an app', guia)

    def test_origem_e_allowlist_sao_verificadas_no_commit_base(self):
        fontes = self.exportador.FONTES_COPIADAS
        self.assertEqual(len(fontes), len(set(fontes)))
        self.assertTrue(all(not fonte.startswith(('data/', 'models/', '.venv/')) for fonte in fontes))
        self.exportador.validar_fontes_no_commit(RAIZ, BASE)

    def test_data_do_commit_e_normalizada_para_utc_sem_alterar_instante(self):
        data_original = subprocess.run(
            ['git', '-C', str(RAIZ), 'show', '-s', '--format=%cI', BASE],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        ).stdout.strip()

        data_utc = self.exportador._data_do_commit(RAIZ, BASE)

        self.assertEqual(datetime.fromisoformat(data_utc).utcoffset(), timezone.utc.utcoffset(None))
        self.assertEqual(
            datetime.fromisoformat(data_utc),
            datetime.fromisoformat(data_original).astimezone(timezone.utc),
        )


if __name__ == '__main__':
    unittest.main()

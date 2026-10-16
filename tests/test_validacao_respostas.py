"""Regressões sem rede: respostas inválidas nunca substituem dados válidos."""
import io
import copy
from contextlib import redirect_stdout
import json
import re
import shutil
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import coletar_resultados as coleta


class TestRespostasInvalidas(unittest.TestCase):
    def test_erro_de_programacao_nao_e_mascarado(self):
        codigo = (
            'import runpy, sys; from unittest.mock import patch\n'
            'with patch("urllib.request.urlopen", side_effect=AssertionError("Rede proibida")), '
            'patch("csv.DictWriter", side_effect=TypeError("erro interno simulado")):\n'
            '    runpy.run_path(sys.argv[1], run_name="__main__")\n'
        )
        processo = subprocess.run(
            [sys.executable, '-c', codigo, str(RAIZ / 'coletar_resultados.py')],
            capture_output=True, text=True, timeout=30,
        )
        self.assertNotEqual(processo.returncode, 0)
        self.assertIn('Traceback', processo.stderr)
        self.assertIn('TypeError: erro interno simulado', processo.stderr)
        self.assertNotIn('Falha na coleta:', processo.stderr)

    def test_cache_invalido_informa_arquivo_e_preserva_bytes(self):
        for conteudo in [b'[]', b'{"MRData": {}}', b'{"MRData":', b'\xff']:
            with self.subTest(conteudo=conteudo), tempfile.TemporaryDirectory() as pasta:
                cache = Path(pasta) / 'calendario.json'
                cache.write_bytes(conteudo)
                with patch.object(coleta, 'RAIZ', Path(pasta)), patch.object(
                    coleta, 'urlopen', side_effect=AssertionError('Teste não permite rede'),
                ) as abrir:
                    mensagem = 'Cache inválido.*' + re.escape(str(cache)) + '.*backup.*novamente'
                    with self.assertRaisesRegex(ValueError, mensagem):
                        coleta.obter_json(coleta.BASE_API + '/2024/?limit=100', cache)
                    abrir.assert_not_called()
                self.assertEqual(cache.read_bytes(), conteudo)

    def test_rede_calendario_incompleto_nao_cria_cache(self):
        with tempfile.TemporaryDirectory() as pasta:
            cache = Path(pasta) / 'calendario.json'
            with patch.object(coleta, 'ULTIMA_REQUISICAO', None), patch.object(
                coleta, 'urlopen', return_value=io.BytesIO(b'{"MRData": {}}'),
            ):
                with self.assertRaisesRegex(ValueError, 'Resposta inválida.*MRData\\.(RaceTable|total)'):
                    coleta.obter_json(coleta.BASE_API + '/2024/?limit=100', cache)
            self.assertFalse(cache.exists())

    def test_rede_json_lista_nao_cria_cache(self):
        with tempfile.TemporaryDirectory() as pasta:
            cache = Path(pasta) / 'calendario.json'
            with patch.object(coleta, 'ULTIMA_REQUISICAO', None), patch.object(
                coleta, 'urlopen', return_value=io.BytesIO(b'[]'),
            ) as abrir:
                with self.assertRaisesRegex(ValueError, 'Resposta inválida.*objeto'):
                    coleta.obter_json(coleta.BASE_API + '/2024/?limit=100', cache)
                abrir.assert_called_once()
            self.assertFalse(cache.exists())


class TestEstruturasPorEndpoint(unittest.TestCase):
    """Usa cópias das respostas reais para exercitar cada campo necessário."""

    def setUp(self):
        self.originais = {
            'calendario': (RAIZ / 'data/raw/calendario_2024.json').read_bytes(),
            'resultados': (RAIZ / 'data/raw/resultados_sao_paulo_2024.json').read_bytes(),
        }
        self.dados = {nome: json.loads(texto) for nome, texto in self.originais.items()}
        self.rodada = self.dados['resultados']['MRData']['RaceTable']['round']

    def opcoes(self, endpoint):
        return dict(endpoint=endpoint, temporada='2024',
                    rodada=self.rodada if endpoint == 'resultados' else None)

    def verificar_invalida(self, conteudo, endpoint):
        """O mesmo dado deve ser recusado tanto na rede quanto no disco."""
        for origem in ('rede', 'cache'):
            with self.subTest(origem=origem), tempfile.TemporaryDirectory() as pasta:
                cache = Path(pasta) / (endpoint + '.json')
                if origem == 'cache':
                    cache.write_bytes(conteudo)
                efeito = AssertionError('Teste não permite rede') if origem == 'cache' else None
                with patch.object(coleta, 'ULTIMA_REQUISICAO', None), patch.object(
                    coleta, 'urlopen', side_effect=efeito, return_value=io.BytesIO(conteudo),
                ) as abrir, redirect_stdout(io.StringIO()):
                    with self.assertRaises(coleta.RespostaInvalida) as erro:
                        coleta.obter_json('https://api.jolpi.ca/ergast/f1/teste/', cache,
                                          **self.opcoes(endpoint))
                    if origem == 'cache':
                        abrir.assert_not_called()
                        self.assertIn(str(cache), str(erro.exception))
                        self.assertIn('backup', str(erro.exception))
                        self.assertIn('novamente', str(erro.exception))
                    else:
                        abrir.assert_called_once()
                        self.assertIn('Resposta inválida da API', str(erro.exception))
                        self.assertIn('Cache não foi gravado', str(erro.exception))
                if origem == 'cache':
                    self.assertEqual(cache.read_bytes(), conteudo)
                else:
                    self.assertFalse(cache.exists())

    def verificar_campos(self, endpoint, caminhos):
        for caminho in caminhos:
            # Ausência, null, tipo errado e texto vazio são casos independentes.
            for ausente, valor in [(True, None), (False, None), (False, 0),
                                   (False, True), (False, []), (False, '')]:
                with self.subTest(campo=caminho, ausente=ausente, valor=valor):
                    dados = copy.deepcopy(self.dados[endpoint])
                    pai = dados
                    for chave in caminho[:-1]:
                        pai = pai[chave]
                    if ausente:
                        del pai[caminho[-1]]
                    else:
                        pai[caminho[-1]] = valor
                    self.verificar_invalida(json.dumps(dados).encode('utf-8'), endpoint)

    def test_tipos_do_envelope_na_rede_e_no_cache(self):
        for endpoint in self.originais:
            for dados in [[], None, True, 42, 'texto', {}, {'MRData': {}}, {'MRData': []}]:
                with self.subTest(endpoint=endpoint, dados=dados):
                    self.verificar_invalida(json.dumps(dados).encode('utf-8'), endpoint)

    def test_json_malformado_e_utf8_invalido_na_rede_e_no_cache(self):
        for endpoint in self.originais:
            for conteudo in [b'', b'{"MRData":', b'\xff']:
                with self.subTest(endpoint=endpoint, conteudo=conteudo):
                    self.verificar_invalida(conteudo, endpoint)

    def test_campos_obrigatorios_do_calendario_na_rede_e_no_cache(self):
        tabela = ('MRData', 'RaceTable')
        corrida = tabela + ('Races', 0)
        self.verificar_campos('calendario', [
            ('MRData',), ('MRData', 'total'), tabela, tabela + ('season',),
            tabela + ('Races',), corrida,
            corrida + ('season',), corrida + ('round',), corrida + ('raceName',),
            corrida + ('date',), corrida + ('Circuit',),
            corrida + ('Circuit', 'Location'),
            corrida + ('Circuit', 'Location', 'locality'),
            corrida + ('Circuit', 'Location', 'country'),
        ])

    def test_campos_obrigatorios_dos_resultados_na_rede_e_no_cache(self):
        tabela = ('MRData', 'RaceTable')
        corrida = tabela + ('Races', 0)
        resultado = corrida + ('Results', 0)
        self.verificar_campos('resultados', [
            ('MRData',), ('MRData', 'total'), tabela, tabela + ('season',),
            tabela + ('round',), tabela + ('Races',), corrida,
            corrida + ('season',), corrida + ('round',), corrida + ('Results',),
            resultado, resultado + ('Driver',), resultado + ('Driver', 'givenName'),
            resultado + ('Driver', 'familyName'), resultado + ('Constructor',),
            resultado + ('Constructor', 'name'), resultado + ('grid',),
            resultado + ('position',), resultado + ('status',),
        ])

    def test_totais_e_identificadores_incorretos_na_rede_e_no_cache(self):
        for endpoint in self.originais:
            caminhos = [('MRData', 'total'), ('MRData', 'RaceTable', 'season'),
                        ('MRData', 'RaceTable', 'Races', 0, 'season')]
            if endpoint == 'resultados':
                caminhos += [('MRData', 'RaceTable', 'round'),
                             ('MRData', 'RaceTable', 'Races', 0, 'round')]
            for caminho in caminhos:
                with self.subTest(endpoint=endpoint, campo=caminho):
                    dados = copy.deepcopy(self.dados[endpoint])
                    pai = dados
                    for chave in caminho[:-1]:
                        pai = pai[chave]
                    pai[caminho[-1]] = str(int(pai[caminho[-1]]) + 1)
                    self.verificar_invalida(json.dumps(dados).encode('utf-8'), endpoint)

    def test_campos_numericos_invalidos_na_rede_e_no_cache(self):
        for endpoint in self.originais:
            caminhos = [('MRData', 'total'), ('MRData', 'RaceTable', 'Races', 0, 'round')]
            if endpoint == 'resultados':
                resultado = ('MRData', 'RaceTable', 'Races', 0, 'Results', 0)
                caminhos += [resultado + ('grid',), resultado + ('position',)]
            for caminho in caminhos:
                for valor in ['abc', '-1', '1.5', '١']:
                    with self.subTest(endpoint=endpoint, campo=caminho, valor=valor):
                        dados = copy.deepcopy(self.dados[endpoint])
                        pai = dados
                        for chave in caminho[:-1]:
                            pai = pai[chave]
                        pai[caminho[-1]] = valor
                        self.verificar_invalida(json.dumps(dados).encode('utf-8'), endpoint)

    def test_respostas_validas_preservam_conteudo_na_rede_e_no_cache(self):
        for endpoint, conteudo in self.originais.items():
            for origem in ('rede', 'cache'):
                with self.subTest(endpoint=endpoint, origem=origem), tempfile.TemporaryDirectory() as pasta:
                    cache = Path(pasta) / (endpoint + '.json')
                    if origem == 'cache':
                        cache.write_bytes(conteudo)
                        instante = cache.stat().st_mtime_ns
                    with patch.object(coleta, 'ULTIMA_REQUISICAO', None), patch.object(
                        coleta, 'urlopen', return_value=io.BytesIO(conteudo),
                    ) as abrir, redirect_stdout(io.StringIO()):
                        dados = coleta.obter_json('https://api.jolpi.ca/ergast/f1/teste/', cache,
                                                  **self.opcoes(endpoint))
                    self.assertEqual(dados, self.dados[endpoint])
                    self.assertEqual(cache.read_bytes(), conteudo)
                    if origem == 'cache':
                        abrir.assert_not_called()
                        self.assertEqual(cache.stat().st_mtime_ns, instante)
                    else:
                        abrir.assert_called_once()


class TestExecucaoSemRede(unittest.TestCase):
    """Executa o programa de verdade em cópias temporárias, com rede bloqueada."""

    ARQUIVOS = ['data/raw/calendario_2024.json', 'data/raw/resultados_sao_paulo_2024.json',
                'data/resultados_sao_paulo_2024.csv']

    def preparar(self, pasta):
        script = pasta / 'coletar_resultados.py'
        shutil.copyfile(RAIZ / 'coletar_resultados.py', script)
        for nome in self.ARQUIVOS:
            destino = pasta / nome
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes((RAIZ / nome).read_bytes())
        return script

    def executar(self, script, conteudo=None):
        codigo = (
            'import io, runpy, sys; from unittest.mock import patch\n'
            'efeito = [io.BytesIO(bytes.fromhex(sys.argv[2]))] if len(sys.argv) > 2 '
            'else AssertionError("Teste não permite rede")\n'
            'with patch("urllib.request.urlopen", side_effect=efeito), patch("time.sleep"):\n'
            '    runpy.run_path(sys.argv[1], run_name="__main__")\n'
        )
        comando = [sys.executable, '-c', codigo, str(script)]
        if conteudo is not None:
            comando.append(conteudo.hex())
        return subprocess.run(comando, capture_output=True, text=True, timeout=30)

    def test_cache_invalido_saida_1_e_preservacao_de_todos_os_dados(self):
        for nome in self.ARQUIVOS[:2]:
            for conteudo in [b'[]', b'{"MRData": {}}', b'{"MRData":', b'\xff']:
                with self.subTest(arquivo=nome, conteudo=conteudo), tempfile.TemporaryDirectory() as temporario:
                    pasta = Path(temporario)
                    script = self.preparar(pasta)
                    cache = pasta / nome
                    cache.write_bytes(conteudo)
                    antes = {n: (pasta / n).read_bytes() for n in self.ARQUIVOS}
                    processo = self.executar(script)
                    self.assertEqual(processo.returncode, 1, processo.stderr)
                    self.assertIn('Cache inválido', processo.stderr)
                    self.assertIn(str(cache), processo.stderr)
                    self.assertIn('backup', processo.stderr)
                    self.assertIn('novamente', processo.stderr)
                    self.assertNotIn('Traceback', processo.stderr)
                    self.assertEqual(antes, {n: (pasta / n).read_bytes() for n in self.ARQUIVOS})

    def test_recuperacao_manual_preserva_backup_e_demais_dados(self):
        for nome in self.ARQUIVOS[:2]:
            with self.subTest(arquivo=nome), tempfile.TemporaryDirectory() as temporario, tempfile.TemporaryDirectory() as backup_temporario:
                pasta = Path(temporario)
                script = self.preparar(pasta)
                cache = pasta / nome
                invalido = b'{"MRData": {}}'
                cache.write_bytes(invalido)
                outros = {n: (pasta / n).read_bytes() for n in self.ARQUIVOS if n != nome}
                falha = self.executar(script)
                self.assertEqual(falha.returncode, 1, falha.stderr)
                self.assertEqual(cache.read_bytes(), invalido)
                # A movimentação é explícita e feita pelo teste, não pelo coletor.
                backup = Path(backup_temporario) / cache.name
                shutil.move(str(cache), str(backup))
                valido = (RAIZ / nome).read_bytes()
                recuperado = self.executar(script, valido)
                self.assertEqual(recuperado.returncode, 0, recuperado.stderr)
                self.assertEqual(backup.read_bytes(), invalido)
                self.assertEqual(cache.read_bytes(), valido)
                self.assertEqual(outros, {n: (pasta / n).read_bytes() for n in outros})

    def test_rede_invalida_saida_1_sem_cache_novo_e_sem_alterar_dados(self):
        for nome in self.ARQUIVOS[:2]:
            for conteudo in [b'[]', b'{"MRData": {}}', b'{"MRData":', b'\xff']:
                with self.subTest(arquivo=nome, conteudo=conteudo), tempfile.TemporaryDirectory() as temporario:
                    pasta = Path(temporario)
                    script = self.preparar(pasta)
                    cache = pasta / nome
                    cache.unlink()  # Apenas na cópia temporária deste teste.
                    antes = {n: (pasta / n).read_bytes() for n in self.ARQUIVOS if n != nome}
                    processo = self.executar(script, conteudo)
                    self.assertEqual(processo.returncode, 1, processo.stderr)
                    self.assertIn('Resposta inválida da API', processo.stderr)
                    self.assertIn('Cache não foi gravado', processo.stderr)
                    self.assertNotIn('Traceback', processo.stderr)
                    self.assertFalse(cache.exists())
                    self.assertEqual(antes, {n: (pasta / n).read_bytes() for n in antes})


if __name__ == '__main__':
    unittest.main()

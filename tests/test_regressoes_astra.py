"""Regressões Astra: dados simulados e portabilidade dos testes."""
import copy
import importlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def pagina_calendario(temporada, corrida):
    return {'MRData': {'total': '1', 'limit': '100', 'offset': '0',
                       'RaceTable': {'season': temporada, 'Races': [corrida]}}}


class TestRegressoesAstra(unittest.TestCase):
    def test_hora_vazia_validada_e_equivalente_a_ausente_sem_mutar_fonte(self):
        coleta = importlib.import_module('coletar_historico')
        preparacao = importlib.import_module('preparar_historico')
        casos = [
            ('2023', 'Qualifying',
             {'season': '2023', 'round': '1', 'raceName': 'Normal simulada',
              'date': '2023-12-17', 'time': '14:00:00Z',
              'Circuit': {'circuitId': 'teste', 'circuitName': 'Teste'},
              'Qualifying': {'date': '2023-12-16', 'time': ''}},
             'Qualifying', False, '2023-12-16T00:00:00Z'),
            ('2021', 'Sprint',
             {'season': '2021', 'round': '1', 'raceName': 'Sprint simulada',
              'date': '2021-07-18', 'time': '14:00:00Z',
              'Circuit': {'circuitId': 'teste', 'circuitName': 'Teste'},
              'Qualifying': {'date': '2021-07-16', 'time': '17:00:00Z'},
              'Sprint': {'date': '2021-07-17', 'time': ''}},
             'Sprint_2021_2022', True, '2021-07-17T00:00:00Z'),
        ]
        for temporada, sessao, corrida, nome_esperado, legado, limite in casos:
            with self.subTest(sessao=sessao):
                dados = pagina_calendario(temporada, corrida)
                antes = copy.deepcopy(dados)
                self.assertEqual(coleta.validar_pagina(dados, 'calendario', temporada, 0), (1, 1))
                referencia = preparacao.definir_referencia(dados['MRData']['RaceTable']['Races'][0])
                self.assertEqual(dados, antes)
                self.assertEqual(referencia['sessao_referencia'], nome_esperado)
                self.assertEqual(referencia['classificacao_nao_define_grid_gp'], legado)
                self.assertEqual(referencia['limite_inferior_referencia_utc'], limite)
                self.assertEqual(referencia['precisao_referencia'], 'inicio_dia')
                self.assertIsNone(referencia['fim_sessao_referencia_utc'])

    def test_horarios_sem_utc_ou_invalidos_falham_sem_normalizacao(self):
        preparacao = importlib.import_module('preparar_historico')
        for horario in ('10:30:00', 'horario-invalido', '24:00:00Z'):
            corrida = {'season': '2024', 'date': '2024-11-03', 'time': '15:30:00Z',
                       'Qualifying': {'date': '2024-11-03', 'time': horario}}
            with self.subTest(horario=horario), self.assertRaisesRegex(ValueError, 'Horário'):
                preparacao.definir_referencia(corrida)

    def test_importar_modulos_de_teste_nao_altera_tempdir_nem_tmpdir(self):
        with tempfile.TemporaryDirectory() as pasta:
            tmpdir_executor = Path(pasta) / 'tmpdir_executor'
            tmpdir_executor.mkdir()
            codigo = '''
import importlib
import os
from pathlib import Path
import sys
import tempfile

raiz, testes = sys.argv[1:]
sys.path[:0] = [testes, raiz]
antes = (tempfile.tempdir, os.environ.get('TMPDIR'))
importlib.import_module('test_coletar_historico')
importlib.import_module('test_preparar_historico')
depois = (tempfile.tempdir, os.environ.get('TMPDIR'))
assert depois == antes, (antes, depois)
with tempfile.TemporaryDirectory() as temporario:
    assert Path(temporario).parent == Path(os.environ['TMPDIR']), temporario
'''
            ambiente = os.environ.copy()
            ambiente['TMPDIR'] = str(tmpdir_executor)
            processo = subprocess.run(
                [sys.executable, '-c', codigo, str(RAIZ), str(RAIZ / 'tests')],
                capture_output=True, text=True, timeout=30, env=ambiente,
            )
            self.assertEqual(processo.returncode, 0, processo.stdout + processo.stderr)


if __name__ == '__main__':
    unittest.main()

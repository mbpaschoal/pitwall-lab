"""Testes da coleta. A primeira execução usa a API real; depois usa o cache."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import tempfile
from urllib.error import HTTPError

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


class TestLimiteAPI(unittest.TestCase):
    def test_identifica_aplicativo_versao_python_e_timeout(self):
        import coletar_resultados as coleta
        with tempfile.TemporaryDirectory() as pasta:
            erro = HTTPError('https://api.jolpi.ca/', 503, 'Unavailable', {}, None)
            with patch.object(coleta, 'ULTIMA_REQUISICAO', None), patch.object(
                coleta, 'urlopen', side_effect=erro,
            ) as abrir:
                with self.assertRaises(ValueError):
                    coleta.obter_json('https://api.jolpi.ca/', Path(pasta) / 'resposta.json')
                requisicao = abrir.call_args.args[0]
                agente = requisicao.get_header('User-agent')
                self.assertIn('PitwallLab/0.1.0', agente)
                self.assertIn('Python/' + sys.version.split()[0], agente)
                self.assertEqual(abrir.call_args.kwargs['timeout'], 30)

    def test_429_informa_espera_e_nao_repete_requisicao(self):
        import coletar_resultados as coleta
        with tempfile.TemporaryDirectory() as pasta:
            cache = Path(pasta) / 'resposta.json'
            erro = HTTPError('https://api.jolpi.ca/', 429, 'Too Many Requests',
                             {'Retry-After': '120'}, None)
            with patch.object(coleta, 'ULTIMA_REQUISICAO', None), patch.object(
                coleta, 'urlopen', side_effect=erro,
            ) as abrir:
                with self.assertRaisesRegex(ValueError, '429.*Retry-After.*120'):
                    coleta.obter_json('https://api.jolpi.ca/', cache)
                abrir.assert_called_once()
                self.assertFalse(cache.exists())


class TestColeta(unittest.TestCase):
    def test_coleta_real_completa(self):
        processo = subprocess.run(
            [sys.executable, str(RAIZ / 'coletar_resultados.py')],
            capture_output=True, text=True, timeout=90,
        )
        self.assertEqual(processo.returncode, 0, processo.stdout + processo.stderr)
        bruto = json.loads((RAIZ / 'data/raw/resultados_sao_paulo_2024.json').read_text())
        corrida = bruto['MRData']['RaceTable']['Races'][0]
        with (RAIZ / 'data/resultados_sao_paulo_2024.csv').open(newline='', encoding='utf-8') as arquivo:
            leitor = csv.DictReader(arquivo)
            self.assertEqual(leitor.fieldnames, [
                'piloto', 'equipe', 'posicao_largada', 'posicao_final', 'status',
            ])
            linhas = list(leitor)
        resultados = sorted(corrida['Results'], key=lambda item: int(item['position']))
        self.assertGreater(len(linhas), 0)
        self.assertEqual(len(linhas), int(bruto['MRData']['total']))
        self.assertEqual(len({linha['piloto'] for linha in linhas}), len(linhas))
        for linha, resultado in zip(linhas, resultados):
            self.assertEqual(linha, {
                'piloto': resultado['Driver']['givenName'] + ' ' + resultado['Driver']['familyName'],
                'equipe': resultado['Constructor']['name'],
                'posicao_largada': resultado['grid'],
                'posicao_final': resultado['position'],
                'status': resultado['status'],
            })
        self.assertIn('Identificador descoberto', processo.stdout)


if __name__ == '__main__':
    unittest.main()

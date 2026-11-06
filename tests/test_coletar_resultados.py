"""Testes offline da coleta, com respostas preservadas e destino temporário."""
import csv
import json
import io
from contextlib import redirect_stdout
from pathlib import Path
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
    def test_coleta_completa_offline_em_destino_vazio(self):
        import coletar_resultados as coleta
        originals = {
            name: (RAIZ / 'data/raw' / name).read_bytes()
            for name in ('calendario_2024.json', 'resultados_sao_paulo_2024.json')
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = io.StringIO()
            responses = [io.BytesIO(raw) for raw in originals.values()]
            with patch.object(coleta, 'RAIZ', root), \
                    patch.object(coleta, 'ULTIMA_REQUISICAO', None), \
                    patch.object(coleta.time, 'sleep'), \
                    patch.object(coleta, 'urlopen', side_effect=responses) as request, \
                    redirect_stdout(output):
                coleta.coletar()
            self.assertEqual(request.call_count, 2)
            for name, raw in originals.items():
                self.assertEqual((root / 'data/raw' / name).read_bytes(), raw)
                self.assertEqual((RAIZ / 'data/raw' / name).read_bytes(), raw)
            bruto = json.loads(originals['resultados_sao_paulo_2024.json'])
            corrida = bruto['MRData']['RaceTable']['Races'][0]
            with (root / 'data/resultados_sao_paulo_2024.csv').open(newline='', encoding='utf-8') as arquivo:
                leitor = csv.DictReader(arquivo)
                self.assertEqual(leitor.fieldnames, coleta.COLUNAS)
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
            self.assertIn('Identificador descoberto', output.getvalue())


if __name__ == '__main__':
    unittest.main()

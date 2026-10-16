"""Confere o gráfico contra o CSV real, sem dados fictícios de corrida."""
import csv
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

RAIZ = Path(__file__).resolve().parents[1]


class TestGrafico(unittest.TestCase):
    def test_grafico_preserva_csv_e_distingue_status(self):
        fonte = RAIZ / 'data/resultados_sao_paulo_2024.csv'
        hash_antes = hashlib.sha256(fonte.read_bytes()).hexdigest()
        with fonte.open(encoding='utf-8', newline='') as arquivo:
            linhas = list(csv.DictReader(arquivo))
        with tempfile.TemporaryDirectory() as pasta:
            processo = subprocess.run(
                [sys.executable, str(RAIZ / 'gerar_grafico.py'), '--saida-dir', pasta],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(processo.returncode, 0, processo.stdout + processo.stderr)
            svg = ET.parse(Path(pasta) / 'largada_vs_resultado_sp2024.svg').getroot()
            grupos = [g for g in svg.iter() if 'data-piloto' in g.attrib]
            self.assertEqual(len(grupos), len(linhas))
            por_piloto = {linha['piloto']: linha for linha in linhas}
            for grupo in grupos:
                linha = por_piloto[grupo.attrib['data-piloto']]
                self.assertEqual(grupo.attrib['data-grid'], linha['posicao_largada'])
                self.assertEqual(grupo.attrib['data-final'], linha['posicao_final'])
                self.assertEqual(grupo.attrib['data-status'], linha['status'])
                classes = {elemento.attrib.get('class') for elemento in grupo}
                self.assertIn('grid', classes)
                if linha['status'] == 'Finished':
                    self.assertIn('chegada', classes)
                    self.assertIn('conexao', classes)
                else:
                    self.assertIn('especial', classes)
                    self.assertNotIn('conexao', classes)
            html = (Path(pasta) / 'largada_vs_resultado_sp2024.html').read_text(encoding='utf-8')
            self.assertIn('<svg', html)
            self.assertNotIn('<script', html)
        self.assertEqual(hash_antes, hashlib.sha256(fonte.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()

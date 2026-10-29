"""Verificação do acervo portátil, sem produtor, cache bruto ou rede."""
from pathlib import Path
import unittest
from acervo_dashboard_dados import carregar, para_gp, AcervoDashboardErro


RAIZ = Path(__file__).resolve().parents[1]


class TestAcervoPublico(unittest.TestCase):
    def test_australia_tem_clima_e_sessoes_sem_precisar_do_acervo_bruto(self):
        asset = carregar(RAIZ)
        gp = para_gp(asset, 2025, 1, 'albert_park')
        self.assertTrue(gp['clima']['horas'])
        self.assertTrue(gp['sessoes'])
        self.assertTrue(gp['estrategias'])
        self.assertTrue(gp['equipes'])
        self.assertFalse((RAIZ / 'data').exists())
        self.assertFalse((RAIZ / 'models').exists())

    def test_gp_nao_empresta_dados_de_outra_temporada(self):
        asset = carregar(RAIZ)
        gp = para_gp(asset, 2026, 18, 'americas')
        self.assertEqual(gp['identidade']['temporada'], 2026)
        self.assertEqual(gp['identidade']['rodada'], 18)
        self.assertIsNone(para_gp(asset, 2026, 99))
        with self.assertRaises((ValueError, AcervoDashboardErro)):
            para_gp(asset, 2026, 18, 'monza')

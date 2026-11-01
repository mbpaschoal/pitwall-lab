import unittest
from pathlib import Path
from verificar_pacote import validar_pacote, TESTES_PORTATEIS


class PacoteGuardTest(unittest.TestCase):
    def test_raiz_cientifica_nao_pode_ser_cwd(self):
        with self.assertRaisesRegex(ValueError, 'nunca a raiz'):
            validar_pacote(Path(__file__).resolve().parents[1])
        self.assertNotIn('test_metodologia_v2.py', TESTES_PORTATEIS)
        self.assertTrue(all(x.startswith('test_') and '/' not in x for x in TESTES_PORTATEIS))

    def test_novas_artes_e_composicoes_sao_verificadas_no_pacote_isolado(self):
        from exportar_dashboard import RUNTIME_WORKTREE
        for filename in ('test_tarot_catalog.py', 'test_high_resolution_assets.py',
                         'test_fan_journey.py', 'test_fan_composition.py'):
            self.assertIn(filename, TESTES_PORTATEIS)
            self.assertIn('tests/' + filename, RUNTIME_WORKTREE)

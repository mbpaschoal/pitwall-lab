"""Integração de snapshots do acervo sem modificar painéis oficiais ou previsões."""
import copy
from pathlib import Path
import unittest

from acervo_dashboard_dados import carregar, para_gp
from pitwall_ui_dados import carregar_paineis, complementar_paineis, PaineisDadosErro
import pitwall_ui


ROOT = Path(__file__).resolve().parents[1]


class TestPaineisAcervo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.asset = carregar(ROOT)

    def test_australia_recebe_campeonatos_sem_inventar_posicoes_ausentes(self):
        original = carregar_paineis(ROOT, 2025, 1, 'albert_park')
        before = copy.deepcopy(original)
        gp = para_gp(self.asset, 2025, 1, 'albert_park')
        result = complementar_paineis(original, gp)
        self.assertTrue(result['driver_standings']['disponivel'])
        self.assertEqual(result['driver_standings']['classificacao'][0]['piloto_id'], 'norris')
        self.assertTrue(result['driver_standings']['parcial'])
        self.assertIsNone(result['driver_standings']['paginas_validadas'])
        self.assertTrue(any(x['posicao'] is None for x in result['driver_standings']['classificacao']))
        self.assertEqual(original, before)

    def test_painel_oficial_austin_mantem_bytes_logicos_e_proveniencia(self):
        original = carregar_paineis(ROOT, 2026, 18, 'americas')
        result = complementar_paineis(original, para_gp(self.asset, 2026, 18, 'americas'))
        self.assertEqual(result['driver_standings'], original['driver_standings'])
        self.assertEqual(result['constructor_standings'], original['constructor_standings'])
        with self.assertRaises(PaineisDadosErro):
            complementar_paineis(original, para_gp(self.asset, 2025, 1, 'albert_park'))

    def test_todos_gps_preservam_identidade_e_hero_faz_media_descritiva(self):
        for gp in self.asset['gps'].values():
            i = gp['identidade']
            panes = complementar_paineis(carregar_paineis(ROOT, i['temporada'], i['rodada'], i['circuito_id']), gp)
            self.assertEqual(panes['rodada'], i['rodada'])
        gp = para_gp(self.asset, 2025, 1, 'albert_park')
        corrida = {'corrida':'Australian Grand Prix','circuito_nome':'Albert Park','cidade':'Melbourne','pais':'Australia','data':'2025-03-16'}
        panes = carregar_paineis(ROOT, 2025, 1, 'albert_park')
        html = pitwall_ui.visao_geral(corrida, panes, '', '', '', clima=gp['clima'])
        self.assertIn('Open-Meteo · média histórica', html)
        self.assertNotIn('Clima não disponível', html)

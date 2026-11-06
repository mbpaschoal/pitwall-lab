import unittest
from planejar_pendencias_acervo import planejar


class PendenciasTest(unittest.TestCase):
    def test_identidade_estavel_criterios_e_ausencia_sem_imputacao(self):
        lacunas = [dict(temporada='2025', rodada='17', circuito_id='baku', tipo='laps_sessoes', motivo='Q sem voltas')]
        inventario = {'cobertura_por_gp': [dict(temporada=2026, rodada=1, pilotos_resultado_sem_classificacao=['a'])]}
        fila = planejar(lacunas, [], inventario)
        self.assertEqual(len(fila), 3)
        self.assertEqual(fila, planejar(lacunas, [], inventario))
        self.assertEqual(lacunas[0]['motivo'], 'Q sem voltas')
        for p in fila:
            self.assertTrue(p['criterio_encerramento'])
            self.assertEqual(p['estado'], 'aguardando_evidencia')
            self.assertEqual(p['evidencia_resolucao'], '')
            self.assertIn('404', p['restricao'])

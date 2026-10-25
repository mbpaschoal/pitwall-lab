"""Contrato de contexto editorial comum, derivado apenas de calendários locais."""
import json
import tempfile
import unittest
from pathlib import Path

import preparar_contexto_editorial as preparar


RAIZ = Path(__file__).resolve().parents[1]


class TestContextoEditorial(unittest.TestCase):
    def test_gera_contexto_para_todos_os_gps_das_tres_temporadas(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / 'contexto_editorial.json'
            asset = preparar.gerar(RAIZ, destino)
            self.assertEqual(json.loads(destino.read_text(encoding='utf-8')), asset)

        self.assertEqual(asset['versao'], 1)
        self.assertEqual(asset['temporadas'], [2024, 2025, 2026])
        self.assertEqual(len(asset['eventos']), 71)
        self.assertEqual(len({item['circuito_id'] for item in asset['eventos']}), 26)

        por_chave = {(item['temporada'], item['rodada']): item for item in asset['eventos']}
        bahrain = por_chave[(2024, 1)]
        self.assertEqual(bahrain['circuito_id'], 'bahrain')
        self.assertEqual(bahrain['cidade'], 'Sakhir')
        self.assertEqual(bahrain['pais'], 'Bahrain')
        self.assertEqual(bahrain['data'], '2024-03-02')

        austin = por_chave[(2026, 18)]
        self.assertEqual(austin['circuito_id'], 'americas')
        self.assertEqual(austin['cidade'], 'Austin')
        self.assertEqual(austin['pais'], 'USA')
        self.assertEqual(austin['data'], '2026-10-25')

    def test_recusa_calendario_local_incompleto_ou_duplicado(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / 'data/historico/2024/raw').mkdir(parents=True)
            (raiz / 'data/historico/2025/raw').mkdir(parents=True)
            (raiz / 'frontend_assets').mkdir()
            calendario = {'MRData': {'RaceTable': {'Races': []}}}
            for ano in (2024, 2025):
                (raiz / 'data/historico' / str(ano) / 'raw/calendario_offset_0000.json').write_text(
                    json.dumps(calendario), encoding='utf-8'
                )
            (raiz / 'frontend_assets/race_weekend.json').write_text(
                json.dumps({'dados_2026': {'corridas': []}}), encoding='utf-8'
            )
            with self.assertRaisesRegex(ValueError, 'Calendário 2024'):
                preparar.gerar(raiz, raiz / 'frontend_assets/contexto_editorial.json')


if __name__ == '__main__':
    unittest.main()

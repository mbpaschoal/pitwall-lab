"""Painéis de apresentação não transferem snapshots entre GPs ou temporadas."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from pitwall_ui_dados import (
    ASSET, INVENTARIO_AUSTIN, PaineisDadosErro, _snapshot_do_inventario,
    carregar_paineis, gerar_asset,
)


RAIZ = Path(__file__).resolve().parents[1]


class TestPaineisEditorias(unittest.TestCase):
    def test_asset_real_reproduz_oficiais_completos_e_preserva_empate_de_pontos(self):
        with tempfile.TemporaryDirectory() as tmp:
            asset = gerar_asset(RAIZ, Path(tmp) / 'painel.json')
        por_tipo = {s['tipo']: s for s in asset['snapshots']}
        pilotos = por_tipo['driver_standings']
        equipes = por_tipo['constructor_standings']
        self.assertEqual(len(pilotos['classificacao']), 23)
        self.assertEqual(len(equipes['classificacao']), 11)
        self.assertEqual(pilotos['classificacao'][4]['piloto_id'], 'leclerc')
        self.assertEqual(pilotos['classificacao'][4]['pontos'], 233.0)
        self.assertEqual(equipes['classificacao'][2]['pontos'], 355.0)
        self.assertEqual(equipes['classificacao'][3]['pontos'], 355.0)
        self.assertEqual([s['equipe_id'] for s in equipes['classificacao'][2:4]], ['red_bull', 'mclaren'])

    def test_snapshot_disponivel_apenas_para_o_gp_correspondente(self):
        austin = carregar_paineis(RAIZ, 2026, 18, 'americas')
        self.assertTrue(austin['driver_standings']['disponivel'])
        self.assertTrue(austin['constructor_standings']['disponivel'])
        self.assertEqual(austin['circuit_info']['comprimento_km'], 5.513)
        for ano, rodada, circuito in ((2026, 1, 'albert_park'), (2024, 19, 'americas'), (2025, 19, 'americas')):
            painel = carregar_paineis(RAIZ, ano, rodada, circuito)
            self.assertFalse(painel['driver_standings']['disponivel'])
            self.assertFalse(painel['constructor_standings']['disponivel'])
            self.assertEqual(painel['driver_standings']['classificacao'], [])
        with self.assertRaisesRegex(PaineisDadosErro, 'Circuito'):
            carregar_paineis(RAIZ, 2026, 18, 'monza')

    def test_contexto_cota_tem_fontes_e_dados_2026_nao_sao_retroprojetados(self):
        for ano, rodada in ((2024, 19), (2025, 19), (2026, 18)):
            info = carregar_paineis(RAIZ, ano, rodada, 'americas')['circuit_info']
            self.assertEqual(info['comprimento_km'], 5.513)
            self.assertEqual(info['curvas'], 20)
            self.assertEqual(info['sentido'], 'Anti-horário')
            self.assertEqual(info['primeiro_gp'], 2012)
            self.assertIsNone(info['altitude_m'])
            self.assertIsNone(info['zonas_drs'])
            self.assertEqual(len(info['fontes']), 2)
            self.assertIn('Não integra o modelo', info['escopo'])
            if ano == 2026:
                self.assertEqual(info['voltas'], 56)
                self.assertEqual(info['distancia_corrida_km'], 308.432)
                self.assertEqual(info['recorde_volta'], '1:36.169 · Charles Leclerc (2019)')
            else:
                self.assertIsNone(info['voltas'])
                self.assertIsNone(info['distancia_corrida_km'])
                self.assertIsNone(info['recorde_volta'])
        outro = carregar_paineis(RAIZ, 2026, 1, 'albert_park')['circuit_info']
        self.assertIsNone(outro['comprimento_km'])

    def test_hash_raw_paginacao_e_identidade_sao_verificados_antes_de_normalizar(self):
        fonte_raiz = RAIZ / Path(INVENTARIO_AUSTIN).parent
        inventario = json.loads((RAIZ / INVENTARIO_AUSTIN).read_text())
        fonte = next(f for f in inventario['fontes'] if f.get('endpoint') == 'classificacao_equipes')
        original = json.loads((fonte_raiz / fonte['arquivo']).read_text())
        for campo in ('hash', 'offset', 'round', 'total', 'ids'):
            with self.subTest(campo=campo), tempfile.TemporaryDirectory() as tmp:
                raiz = Path(tmp)
                inv = copy.deepcopy(inventario)
                raw = copy.deepcopy(original)
                metadado = next(f for f in inv['fontes'] if f.get('endpoint') == 'classificacao_equipes')
                if campo == 'offset':
                    raw['MRData']['offset'] = '100'
                elif campo == 'round':
                    raw['MRData']['StandingsTable']['StandingsLists'][0]['round'] = '17'
                elif campo == 'total':
                    raw['MRData']['total'] = '10'
                elif campo == 'ids':
                    linhas = raw['MRData']['StandingsTable']['StandingsLists'][0]['ConstructorStandings']
                    linhas[1]['Constructor']['constructorId'] = linhas[0]['Constructor']['constructorId']
                conteudo = json.dumps(raw).encode()
                caminho = raiz / Path(INVENTARIO_AUSTIN).parent / metadado['arquivo']
                caminho.parent.mkdir(parents=True)
                caminho.write_bytes(conteudo)
                metadado['sha256'] = '0' * 64 if campo == 'hash' else hashlib.sha256(conteudo).hexdigest()
                with self.assertRaises(PaineisDadosErro):
                    _snapshot_do_inventario(raiz, INVENTARIO_AUSTIN, inv, 'constructor_standings')

    def test_asset_portatil_funciona_sem_brutos_e_invalidez_nao_vira_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / 'frontend_assets').mkdir()
            (raiz / 'frontend_assets/contexto_editorial.json').write_bytes((RAIZ / 'frontend_assets/contexto_editorial.json').read_bytes())
            (raiz / ASSET).write_bytes((RAIZ / ASSET).read_bytes())
            painel = carregar_paineis(raiz, 2026, 18, 'americas')
            self.assertTrue(painel['constructor_standings']['disponivel'])
            asset = json.loads((raiz / ASSET).read_text())
            asset['snapshots'][1]['classificacao'][0]['pontos'] = float('nan')
            (raiz / ASSET).write_text(json.dumps(asset))
            painel = carregar_paineis(raiz, 2026, 18, 'americas')
            self.assertFalse(painel['driver_standings']['disponivel'])
            self.assertFalse(painel['constructor_standings']['disponivel'])
            self.assertEqual(painel['constructor_standings']['classificacao'], [])


if __name__ == '__main__':
    unittest.main()

"""Contrato portátil do acervo: identidades, ausências e leitura sem produtores."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from acervo_dashboard_dados import (
    ASSET, SCHEMA, VERSAO, AcervoDashboardErro, carregar, conteudo_sha256, para_gp,
)


def asset_minimo():
    gp = {
        'identidade': {'temporada': 2025, 'rodada': 1, 'circuito_id': 'albert_park'},
        'sessoes': [{'session_key': 1001, 'nome': 'Practice 1', 'tipo': 'Practice',
            'inicio_utc': '2025-03-14T01:00:00Z', 'fim_utc': '2025-03-14T02:00:00Z',
            'n_voltas': 0, 'tempos': [{'numero': 1, 'piloto': 'Piloto', 'posicao': 1,
                'voltas': 0, 'duracao': None, 'gap': '0.000 s', 'q1': None, 'q2': None, 'q3': None}]}],
        'clima': {'horas': [{'data_utc': '2025-03-14T01:00Z', 'temperatura_c': 0,
            'umidade': None, 'precipitacao_mm': 0, 'vento_ms': 0, 'pressao_hpa': None}]},
        'estrategias': [], 'paradas': [], 'equipes': [], 'cobertura': [], 'historico': {},
    }
    gps = {'2025:1': gp}
    return {'schema': SCHEMA, 'versao': VERSAO, 'gps': gps,
            'cobertura': {'gps': 1, 'sessoes': 1}, 'conteudo_sha256': conteudo_sha256(gps)}


def write_asset(root, asset):
    path = Path(root) / ASSET
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asset, ensure_ascii=False), encoding='utf-8')
    return path


class TestAcervoDashboardDados(unittest.TestCase):
    def test_portatil_preserva_ausencia_zero_e_nao_acessa_rede(self):
        with tempfile.TemporaryDirectory() as folder:
            write_asset(folder, asset_minimo())
            with patch('urllib.request.urlopen', side_effect=AssertionError('Rede proibida')):
                loaded = carregar(folder)
            gp = para_gp(loaded, 2025, 1, 'albert_park')
            hour = gp['clima']['horas'][0]
            self.assertEqual(hour['temperatura_c'], 0)
            self.assertEqual(hour['precipitacao_mm'], 0)
            self.assertIsNone(hour['umidade'])
            self.assertEqual(gp['sessoes'][0]['tempos'][0]['voltas'], 0)

    def test_mesma_rodada_outro_ano_ou_circuito_nao_empresta_dados(self):
        with tempfile.TemporaryDirectory() as folder:
            write_asset(folder, asset_minimo()); loaded = carregar(folder)
            self.assertIsNone(para_gp(loaded, 2024, 1))
            self.assertIsNone(para_gp(loaded, 2026, 18))
            with self.assertRaises(AcervoDashboardErro):
                para_gp(loaded, 2025, 1, 'americas')

    def test_alteracao_de_bytes_com_mtime_igual_nao_reusa_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            asset = asset_minimo(); path = write_asset(folder, asset)
            before = path.stat().st_mtime_ns
            self.assertEqual(carregar(folder)['gps']['2025:1']['clima']['horas'][0]['temperatura_c'], 0)
            asset['gps']['2025:1']['clima']['horas'][0]['temperatura_c'] = 9
            asset['conteudo_sha256'] = conteudo_sha256(asset['gps'])
            write_asset(folder, asset); os.utime(path, ns=(before, before))
            self.assertEqual(carregar(folder)['gps']['2025:1']['clima']['horas'][0]['temperatura_c'], 9)

    def test_hash_divergente_e_rejeitado(self):
        with tempfile.TemporaryDirectory() as folder:
            asset = asset_minimo(); asset['gps']['2025:1']['identidade']['circuito_id'] = 'outro'
            write_asset(folder, asset)
            with self.assertRaises(AcervoDashboardErro):
                carregar(folder)

    def test_sessao_nao_pode_ser_reutilizada_em_outro_gp(self):
        with tempfile.TemporaryDirectory() as folder:
            asset = asset_minimo(); other = deepcopy(asset['gps']['2025:1'])
            other['identidade']['rodada'] = 2; other['identidade']['circuito_id'] = 'shanghai'
            asset['gps']['2025:2'] = other; asset['cobertura']['gps'] = 2
            asset['cobertura']['sessoes'] = 2; asset['conteudo_sha256'] = conteudo_sha256(asset['gps'])
            write_asset(folder, asset)
            with self.assertRaisesRegex(AcervoDashboardErro, 'Sessão duplicada'):
                carregar(folder)

    def test_hora_repetida_e_timestamp_sem_fuso_falham(self):
        with tempfile.TemporaryDirectory() as folder:
            asset = asset_minimo(); hours = asset['gps']['2025:1']['clima']['horas']; hours.append(deepcopy(hours[0]))
            asset['conteudo_sha256'] = conteudo_sha256(asset['gps']); write_asset(folder, asset)
            with self.assertRaisesRegex(AcervoDashboardErro, 'Hora meteorológica'):
                carregar(folder)
            hours.pop(); hours[0]['data_utc'] = '2025-03-14T01:00'
            asset['conteudo_sha256'] = conteudo_sha256(asset['gps']); write_asset(folder, asset)
            with self.assertRaisesRegex(AcervoDashboardErro, 'Horário UTC'):
                carregar(folder)

    def test_estrategia_de_treino_nao_e_publicada_como_estrategia_de_corrida(self):
        with tempfile.TemporaryDirectory() as folder:
            asset = asset_minimo()
            asset['gps']['2025:1']['estrategias'] = [{'session_key': 1001, 'modalidade': 'Practice 1', 'sequencia_stints': []}]
            asset['conteudo_sha256'] = conteudo_sha256(asset['gps']); write_asset(folder, asset)
            with self.assertRaisesRegex(AcervoDashboardErro, 'Estratégia'):
                carregar(folder)
            asset['gps']['2025:1']['estrategias'][0]['modalidade'] = 'Race'
            asset['conteudo_sha256'] = conteudo_sha256(asset['gps']); write_asset(folder, asset)
            with self.assertRaisesRegex(AcervoDashboardErro, 'Modalidade'):
                carregar(folder)

    def test_sessao_com_fim_anterior_ao_inicio_falha(self):
        with tempfile.TemporaryDirectory() as folder:
            asset = asset_minimo()
            asset['gps']['2025:1']['sessoes'][0]['fim_utc'] = '2025-03-13T01:00:00Z'
            asset['conteudo_sha256'] = conteudo_sha256(asset['gps']); write_asset(folder, asset)
            with self.assertRaisesRegex(AcervoDashboardErro, 'Fim da sessão'):
                carregar(folder)

    def test_arquivo_ausente_versao_invalida_e_symlink_falham(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(AcervoDashboardErro):carregar(folder)
            asset = asset_minimo(); asset['versao'] = 'outra'; write_asset(folder, asset)
            with self.assertRaises(AcervoDashboardErro):carregar(folder)
            (Path(folder) / ASSET).unlink()
            original = Path(folder) / 'original.json'; original.write_text(json.dumps(asset_minimo()))
            (Path(folder) / ASSET).symlink_to(original)
            with self.assertRaises(AcervoDashboardErro):carregar(folder)

    def test_retorno_do_gp_nao_modifica_asset_compartilhado(self):
        asset = asset_minimo(); gp = para_gp(asset, 2025, 1)
        gp['identidade']['circuito_id'] = 'outro'
        self.assertEqual(asset['gps']['2025:1']['identidade']['circuito_id'], 'albert_park')

    def test_asset_real_tem_66_gps_e_lacuna_baku_explicita(self):
        root = Path(__file__).resolve().parents[1]
        if not (root / ASSET).exists():self.skipTest('Asset ainda não gerado neste ambiente')
        asset = carregar(root)
        self.assertEqual(asset['cobertura']['gps'], 66)
        self.assertEqual(asset['cobertura']['sessoes'], 330)
        gp = para_gp(asset, 2025, 17, 'baku')
        qualifying = next(s for s in gp['sessoes'] if s['nome'] == 'Qualifying')
        self.assertEqual(qualifying['n_voltas'], 0)
        self.assertTrue(qualifying['tempos'])
        self.assertTrue(any(c['tipo']=='laps_sessoes' and c['estado']=='parcial' for c in gp['cobertura']))
        self.assertNotIn('/Users/', (root / ASSET).read_text())
        self.assertNotIn('probabilidade_modelo', (root / ASSET).read_text())
        self.assertEqual(len(para_gp(asset, 2026, 18, 'americas')['sessoes']), 5)


if __name__ == '__main__':
    unittest.main()

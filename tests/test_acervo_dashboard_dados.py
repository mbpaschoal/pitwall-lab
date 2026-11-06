"""Contrato portátil do acervo: identidades, ausências e leitura sem produtores."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from collections import defaultdict
from hashlib import sha256

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


class TestProjecaoAcervo(unittest.TestCase):
    """Offline producer boundaries, independent of the real acquisition folder."""

    def create_gps(self, folder):
        from pitwall.data.dashboard_projection import _iniciar_gps
        directory = Path(folder) / 'local'
        directory.mkdir()
        events = [{'temporada': 2025, 'rodada': 1, 'circuito_id': 'albert_park',
                   'corrida': 'GP de teste', 'data_corrida': '2025-03-16'}]
        (directory / 'eventos.json').write_text(json.dumps(events))
        return _iniciar_gps(Path(folder))

    def race_session(self):
        return dict(session_key='1001', session_name='Race', session_type='Race',
                    date_start='2025-03-16T04:00:00Z', date_end='2025-03-16T06:00:00Z',
                    metodo_mapeamento='identidade', data_corrida_calendario='2025-03-16')

    def test_duplicate_session_is_rejected_before_it_can_overwrite_the_first(self):
        from pitwall.data.dashboard_projection import _projetar_sessoes
        with tempfile.TemporaryDirectory() as folder:
            gp = self.create_gps(folder)['2025:1']
            row = self.race_session()
            with self.assertRaisesRegex(ValueError, 'Sessão duplicada'):
                _projetar_sessoes(lambda layer, name: [row, dict(row)], lambda row: gp)
            self.assertEqual(len(gp['sessoes']), 1)
            self.assertEqual(gp['sessoes'][0]['session_key'], 1001)

    def test_times_cannot_be_attached_to_another_gp_object(self):
        from pitwall.data.dashboard_projection import _projetar_tempos
        recorded, selected = {}, {}
        with self.assertRaisesRegex(ValueError, 'sessão/GP incorreto'):
            _projetar_tempos(lambda layer, name: [dict(session_key='1001')],
                            lambda row: selected, lambda row: {},
                            {1001: (recorded, {})})

    def test_qualifying_keeps_missing_phases_and_zero_laps(self):
        from pitwall.data.dashboard_projection import _projetar_tempos
        gp, session = {}, {'tempos': []}
        row = dict(session_key='1001', duration_original_json='[90.0, null, null]',
                   gap_to_leader_original_json='[0.0, null, null]',
                   position='1', number_of_laps='0')
        _projetar_tempos(lambda layer, name: [row], lambda row: gp,
                        lambda row: {'numero': 1}, {1001: (gp, session)})
        shown = session['tempos'][0]
        self.assertEqual(shown['duracao'], '1:30.000')
        self.assertEqual(shown['q1'], '1:30.000')
        self.assertIsNone(shown['q2'])
        self.assertIsNone(shown['q3'])
        self.assertEqual(shown['voltas'], 0)
        self.assertEqual(shown['duracao_original'], [90.0, None, None])

    def test_weather_keeps_zero_missingness_and_source_semantics(self):
        from pitwall.data.dashboard_projection import (
            _projetar_clima, _finalizar_gps, _projetar_sessoes,
        )
        with tempfile.TemporaryDirectory() as folder:
            gps = self.create_gps(folder)
            gp = gps['2025:1']
            sessions = _projetar_sessoes(lambda layer, name: [self.race_session()], lambda row: gp)
            tables = {
                'clima_open_meteo.csv': [dict(date_utc='2025-03-16T04:00:00Z',
                    temperature_2m='0', relative_humidity_2m='', precipitation='0',
                    wind_speed_10m='0', surface_pressure='', model='ecmwf_ifs',
                    origin='archived_forecast')],
                'clima_pista.csv': [dict(temporada='2025', rodada='1', session_key='1001',
                    air_temperature='0', track_temperature='', humidity='',
                    wind_speed='0', rainfall='0')],
            }
            _projetar_clima(lambda layer, name: tables[name], lambda row: gp, gps, sessions)
            _finalizar_gps(gps, defaultdict(list), defaultdict(list), {})
            self.assertEqual(gp['clima']['resumo']['temperatura_media_c'], 0)
            self.assertEqual(gp['clima']['resumo']['precipitacao_total_mm'], 0)
            track = gp['clima']['pista_sessoes'][0]
            self.assertEqual(track['temperatura_ar_min_c'], 0)
            self.assertIsNone(track['temperatura_pista_min_c'])
            self.assertIsNone(track['umidade_media'])
            self.assertIs(track['chuva_observada'], False)
            self.assertIn('não é medição', gp['clima']['origem'])
            self.assertEqual(gp['campeonato_pilotos']['obtido_em_utc'], 'desconhecida')
            self.assertIs(gp['campeonato_pilotos']['disponivel'], False)

    def test_source_hash_and_symlink_checks_are_retained(self):
        from pitwall.data.dashboard_projection import _carregar_fontes
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'local').mkdir()
            (root / 'normalizado').mkdir()
            source = root / 'local/sample.csv'
            source.write_bytes(b'original\n')
            manifest = {'arquivos_sha256': {'sample.csv': sha256(source.read_bytes()).hexdigest()}}
            (root / 'local/inventario_local.json').write_text(json.dumps(manifest))
            (root / 'normalizado/manifesto.json').write_text(json.dumps({'arquivos': {}}))
            _carregar_fontes(root)
            source.write_bytes(b'changed\n')
            with self.assertRaisesRegex(ValueError, 'Fonte do acervo divergente'):
                _carregar_fontes(root)
            source.unlink()
            preserved = root / 'preserved.csv'
            preserved.write_bytes(b'original\n')
            source.symlink_to(preserved)
            with self.assertRaisesRegex(ValueError, 'Fonte do acervo divergente'):
                _carregar_fontes(root)
            self.assertEqual(preserved.read_bytes(), b'original\n')


if __name__ == '__main__':
    unittest.main()

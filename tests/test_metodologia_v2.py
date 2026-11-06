import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


class MetodologiaV2Test(unittest.TestCase):
    def test_auditoria_archive_sem_divergencias_preserva_cabecalho_e_fontes(self):
        import csv
        from unittest.mock import patch
        from pitwall.research import archive_audit_v2
        tables = {
            'races.csv': 'raceId,year,round\n1,2021,1\n',
            'drivers.csv': 'driverId,driverRef\n1,alpha\n',
            'constructors.csv': 'constructorId,constructorRef\n1,team\n',
            'circuits.csv': 'circuitId,circuitRef\n1,fixture\n',
            'qualifying.csv': 'raceId,driverId,position\n1,1,1\n',
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'archive'
            archive.mkdir()
            for name, text in tables.items():
                (archive / name).write_text(text)
            base = root / 'data/preparado/base_historica.csv'
            base.parent.mkdir(parents=True)
            base.write_text('temporada,rodada,piloto_id,posicao_classificacao\n2021,1,alpha,1\n')
            destination = root / 'audit'
            with patch.object(archive_audit_v2, 'RAIZ', root), patch.object(archive_audit_v2, 'ARCHIVE', archive):
                self.assertEqual(archive_audit_v2.executar(destination), (3, 0))
            with (destination / 'conflitos_campos_v2.csv').open(newline='') as stream:
                reader = csv.DictReader(stream)
                self.assertIn('status_decisao', reader.fieldnames)
                self.assertEqual(list(reader), [])
            manifest = json.loads((destination / 'manifesto_archive_v2.json').read_text())
            self.assertEqual(manifest['divergencias_qualifying'], 0)
            self.assertEqual(len(manifest['fontes']), 5)
            for name, text in tables.items():
                self.assertEqual((archive / name).read_bytes(), text.encode())

    def test_coletor_b1_rejeita_fronteiras_sem_fuso_explicito(self):
        from coletar_ritmo_v2 import validar_sessao_antes_do_corte
        for fim, corte in (
            ('2021-03-08T09:00:00', '2021-03-08T14:00:00Z'),
            ('2021-03-08T09:00:00Z', '2021-03-08T14:00:00'),
        ):
            with self.subTest(fim=fim, corte=corte):
                self.assertFalse(validar_sessao_antes_do_corte(fim, corte))

    def test_offset_negativo_fastf1_preserva_meia_hora_e_dias_assinados(self):
        from coletar_ritmo_v2 import normalizar_horarios_fastf1
        for offset, esperado in (('-03:30:00', '2022-03-18T13:30:00Z'),
                                 ('-1 days +21:00:00', '2022-03-18T13:00:00Z'),
                                 ('+05:30:00', '2022-03-18T04:30:00Z')):
            with self.subTest(offset=offset):
                inicio, _ = normalizar_horarios_fastf1(dict(
                    StartDate='2022-03-18 10:00:00', EndDate='2022-03-18 11:00:00',
                    GmtOffset=offset))
                self.assertEqual(inicio, esperado)

    def test_coletor_b1_preserva_destino_preexistente_antes_de_chamar_sdk(self):
        from coletar_ritmo_v2 import coletar
        for existing in ('manifesto_coleta.json', '2022-r01-fp1.json'):
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / existing
                path.write_bytes(b'previous immutable evidence\n')
                sdk = Mock()
                with self.assertRaises(FileExistsError):
                    coletar(tmp, fastf1_module=sdk, coorte=())
                self.assertEqual(path.read_bytes(), b'previous immutable evidence\n')
                sdk.Cache.enable_cache.assert_not_called()
                sdk.get_session.assert_not_called()

    def _linhas(self):
        return [
            {'temporada': 2021, 'rodada': 1, 'piloto_id': 'alpha', 'circuito_id': 'a', 'data_corrida': '2021-03-01', 'equipe_id_entrada': 'team_a', 'posicao_classificacao': 1, 'classificacao_ausente': 0, 'referencia_temporal_ausente': 0, 'limite_inferior_referencia_utc': '2021-03-01T10:00:00Z', 'podio': 1},
            {'temporada': 2021, 'rodada': 1, 'piloto_id': 'bravo', 'circuito_id': 'a', 'data_corrida': '2021-03-01', 'equipe_id_entrada': 'team_a', 'posicao_classificacao': 2, 'classificacao_ausente': 0, 'referencia_temporal_ausente': 0, 'limite_inferior_referencia_utc': '2021-03-01T10:00:00Z', 'podio': 0},
            {'temporada': 2021, 'rodada': 2, 'piloto_id': 'alpha', 'circuito_id': 'b', 'data_corrida': '2021-03-08', 'equipe_id_entrada': 'team_a', 'posicao_classificacao': 3, 'classificacao_ausente': 0, 'referencia_temporal_ausente': 0, 'limite_inferior_referencia_utc': '2021-03-08T10:00:00Z', 'podio': 0},
            {'temporada': 2021, 'rodada': 2, 'piloto_id': 'bravo', 'circuito_id': 'b', 'data_corrida': '2021-03-08', 'equipe_id_entrada': 'team_a', 'posicao_classificacao': 1, 'classificacao_ausente': 0, 'referencia_temporal_ausente': 0, 'limite_inferior_referencia_utc': '2021-03-08T10:00:00Z', 'podio': 1},
        ]

    def test_contrato_rejeita_2026_e_resultado_atual_na_matriz(self):
        from metodologia_v2 import validar_linhas_pre_corrida, ErroContratoV2
        linhas = self._linhas()
        linhas[0]['resultado_ausente'] = 0
        with self.assertRaisesRegex(ErroContratoV2, 'proibido'):
            validar_linhas_pre_corrida(linhas)
        linhas = self._linhas()
        linhas[0]['temporada'] = 2026
        with self.assertRaisesRegex(ErroContratoV2, '2021'):
            validar_linhas_pre_corrida(linhas)

    def test_feature_equipe_nao_usa_resultado_do_companheiro_da_mesma_corrida(self):
        from metodologia_v2 import construir_features_a3
        linhas = self._linhas()
        primeira = construir_features_a3(linhas)
        alteradas = [dict(item) for item in linhas]
        alteradas[3]['podio'] = 0
        segunda = construir_features_a3(alteradas)
        chave = (2021, 2, 'alpha')
        self.assertEqual(primeira[chave]['taxa_podios_equipe_5'], segunda[chave]['taxa_podios_equipe_5'])
        self.assertEqual(primeira[chave]['taxa_podios_equipe_5'], 0.5)

    def test_permutar_linhas_nao_muda_features_e_alvo_futuro_nao_vaza(self):
        from metodologia_v2 import construir_features_a3
        linhas = self._linhas()
        normal = construir_features_a3(linhas)
        invertidas = construir_features_a3(list(reversed(linhas)))
        futuro = [dict(item) for item in linhas]
        futuro[2]['podio'] = 1
        mudado = construir_features_a3(futuro)
        chave = (2021, 2, 'alpha')
        self.assertEqual(normal, invertidas)
        self.assertEqual(normal[chave]['taxa_podios_piloto_5'], mudado[chave]['taxa_podios_piloto_5'])

    def test_manifesto_recusa_hash_divergente_e_preserva_desconhecido(self):
        from metodologia_v2 import criar_manifesto_fontes, ErroContratoV2
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            origem = raiz / 'origem.csv'
            origem.write_text('a,b\n1,2\n', encoding='utf-8')
            manifesto = criar_manifesto_fontes(raiz, ['origem.csv'])
            self.assertIsNone(manifesto['fontes'][0]['publicado_em_utc'])
            origem.write_text('a,b\n1,3\n', encoding='utf-8')
            with self.assertRaisesRegex(ErroContratoV2, 'hash'):
                criar_manifesto_fontes(raiz, ['origem.csv'], manifesto_existente=manifesto)

    def test_b1_recusa_sessao_posterior_ao_corte_sem_fabricar_ritmo(self):
        from metodologia_v2 import normalizar_ritmo_b1, ErroContratoV2
        sessao = {'sessao': 'FP2', 'fim_utc': '2021-03-08T11:00:00Z', 'linhas': []}
        with self.assertRaisesRegex(ErroContratoV2, 'posterior'):
            normalizar_ritmo_b1(sessao, '2021-03-08T10:00:00Z')

    def test_metricas_probabilisticas_usam_mesmas_linhas_e_brier_independente(self):
        from metodologia_v2 import metricas_probabilisticas
        metricas = metricas_probabilisticas([0, 1], [0.25, 0.75])
        self.assertEqual(metricas['n'], 2)
        self.assertAlmostEqual(metricas['brier'], 0.0625)
        self.assertAlmostEqual(metricas['log_loss'], 0.287682072, places=8)

    def test_coorte_b1_e_fixa_sem_substituir_gp_indisponivel(self):
        from coletar_ritmo_v2 import COORTE_B1
        self.assertEqual([(item['temporada'], item['rodada']) for item in COORTE_B1], [(2021, 1), (2021, 10), (2022, 1), (2022, 10), (2023, 1), (2023, 10), (2024, 1), (2024, 10), (2025, 1), (2025, 10)])
        self.assertEqual(COORTE_B1[6]['circuito_id'], 'bahrain')
        self.assertEqual(COORTE_B1[7]['circuito_id'], 'catalunya')

    def test_coletor_b1_recusa_sessao_posterior_ao_corte_no_fluxo_de_coleta(self):
        from coletar_ritmo_v2 import validar_sessao_antes_do_corte
        self.assertFalse(validar_sessao_antes_do_corte('2021-03-08T10:00:01Z', '2021-03-08T10:00:00Z'))
        self.assertTrue(validar_sessao_antes_do_corte('2021-03-08T09:59:59Z', '2021-03-08T10:00:00Z'))

    def test_execucao_v2_recusa_destino_fora_do_relatorio_v2(self):
        from executar_metodologia_v2 import validar_destino
        with self.assertRaises(ValueError):
            validar_destino(Path('/tmp/fora-do-contrato'))

    def test_fastf1_start_end_e_offset_naive_convertem_para_utc_sem_fuso_do_host(self):
        from coletar_ritmo_v2 import normalizar_horarios_fastf1
        info = {'StartDate': '2022-03-18 15:00:00', 'EndDate': '2022-03-18 16:00:00', 'GmtOffset': '0 days 03:00:00'}
        inicio, fim = normalizar_horarios_fastf1(info)
        self.assertEqual(inicio, '2022-03-18T12:00:00Z')
        self.assertEqual(fim, '2022-03-18T13:00:00Z')

    def test_separa_previsao_de_metricas_sem_excluir_alvo_desconhecido(self):
        from executar_metodologia_v2 import separar_previsao_e_metricas
        linhas = [{'piloto_id': 'a', 'alvo_conhecido': 1}, {'piloto_id': 'b', 'alvo_conhecido': 0}]
        previsao, metricas = separar_previsao_e_metricas(linhas)
        self.assertEqual([item['piloto_id'] for item in previsao], ['a', 'b'])
        self.assertEqual([item['piloto_id'] for item in metricas], ['a'])

    def test_agrega_brier_por_gp_com_denominador_explicito(self):
        from executar_metodologia_v2 import brier_por_gp
        linhas = [
            {'temporada': 2022, 'rodada': 1, 'podio': 1, 'probabilidade': .8, 'alvo_conhecido': 1},
            {'temporada': 2022, 'rodada': 1, 'podio': 0, 'probabilidade': .2, 'alvo_conhecido': 1},
            {'temporada': 2022, 'rodada': 2, 'podio': '', 'probabilidade': .3, 'alvo_conhecido': 0},
        ]
        agregado = brier_por_gp(linhas)
        self.assertEqual([{k: v for k, v in item.items() if k != 'brier'} for item in agregado], [{'temporada': 2022, 'rodada': 1, 'n': 2}])
        self.assertAlmostEqual(agregado[0]['brier'], 0.04)

    def test_runner_valida_base_real_e_preserva_equipe_ausente_com_indicador(self):
        from executar_metodologia_v2 import validar_base_v2, construir_linhas_v2
        linhas = self._linhas()
        for linha in linhas:
            linha.update({'posicao_classificacao_ausente': 0, 'posicao_classificacao_repetida': 0,
                          'fim_sessao_referencia_utc': '', 'status': '', 'posicao_final': '', 'pontos': '',
                          'resultado_ausente': 1, 'grid_resultado': ''})
        linhas[0]['equipe_id_entrada'] = ''
        validar_base_v2(linhas)
        construidas, _ = construir_linhas_v2(linhas)
        self.assertEqual(construidas[0]['equipe_entrada_ausente'], 1)
        duplicadas = linhas + [dict(linhas[0])]
        with self.assertRaisesRegex(ValueError, 'duplicada'):
            validar_base_v2(duplicadas)
        sem_utc = [dict(linha) for linha in linhas]
        sem_utc[0]['limite_inferior_referencia_utc'] = '2021-03-01T10:00:00'
        with self.assertRaisesRegex(ValueError, 'UTC'):
            validar_base_v2(sem_utc)

    def test_historico_so_libera_gp_no_dia_utc_seguinte_ao_gp_anterior(self):
        from executar_metodologia_v2 import _historico
        anterior = {'temporada': 2021, 'rodada': 1, 'piloto_id': 'a', 'data_corrida': '2021-03-01'}
        atual = {'temporada': 2021, 'rodada': 2, 'piloto_id': 'a', 'data_corrida': '2021-03-02',
                 'limite_inferior_referencia_utc': '2021-03-01T23:59:59Z'}
        self.assertEqual(_historico([anterior, atual], atual), [])
        atual['limite_inferior_referencia_utc'] = '2021-03-02T00:00:00Z'
        self.assertEqual(_historico([anterior, atual], atual), [anterior])

    def test_coletor_real_com_fixture_sdk_normaliza_voltas_e_nao_usa_rede(self):
        import pandas as pd
        from coletar_ritmo_v2 import coletar
        class Cache:
            @staticmethod
            def enable_cache(_): pass
        class Sessao:
            session_info = {'StartDate': '2022-03-18 15:00:00', 'EndDate': '2022-03-18 16:00:00', 'GmtOffset': '0 days 03:00:00'}
            laps = pd.DataFrame([{'Driver': 'VER', 'DriverNumber': '1', 'LapNumber': 3, 'LapTime': pd.Timedelta(seconds=91.25),
                                  'Compound': 'SOFT', 'TyreLife': 2, 'Stint': 1, 'TrackStatus': '1', 'Deleted': False,
                                  'FastF1Generated': False, 'IsAccurate': True, 'PitInTime': pd.NaT, 'PitOutTime': pd.NaT}])
            def load(self, **kwargs): self.kwargs = kwargs
        sessao = Sessao()
        sdk = SimpleNamespace(Cache=Cache, get_session=lambda *args: sessao)
        coorte = ({'temporada': 2022, 'rodada': 1, 'circuito_id': 'bahrain', 'corrida': 'Bahrain Grand Prix'},)
        with tempfile.TemporaryDirectory() as temporario:
            registros = coletar(temporario, limite_bytes=1000000, fastf1_module=sdk, coorte=coorte,
                                corte_fn=lambda _: '2022-03-18T14:00:00Z')
            self.assertEqual(registros[0]['estado'], 'coletado')
            payload = json.loads((Path(temporario) / registros[0]['arquivo']).read_text())
            self.assertEqual(payload['schema'], 'metodologia-v2-b1-sessao-v2')
            self.assertEqual(payload['voltas'][0]['lap_time_s'], 91.25)
            self.assertIsNone(payload['voltas'][0]['pit_in_s'])
            self.assertTrue(sessao.kwargs['messages'])


if __name__ == '__main__':
    unittest.main()

import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from operacao2026 import fontes


class TestRegistroEmissoes(unittest.TestCase):
    def test_registro_explicito_valida_evento_e_arquivo_de_probabilidades(self):
        from registro_emissoes import carregar

        raiz = Path(__file__).resolve().parents[1]
        registro = carregar(raiz)
        chave = (2026, 17, 'marina_bay')
        emissao = registro[chave]
        self.assertEqual(emissao['modo'], 'ENSAIO_RETROSPECTIVO')
        self.assertEqual(emissao['snapshot'], 'coleta-20261020T020130Z')
        self.assertEqual(emissao['evento'], {'temporada': 2026, 'rodada': 17, 'circuito_id': 'marina_bay'})
        self.assertTrue((raiz / emissao['diretorio'] / 'probabilidades.csv').is_file())

    def test_registro_rejeita_declaracao_com_evento_diferente_do_manifesto(self):
        from registro_emissoes import RegistroEmissoesErro, validar_declaracoes

        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            pasta = raiz / 'emissao'
            pasta.mkdir()
            (pasta / 'probabilidades.csv').write_text('piloto_id,probabilidade_modelo\np1,0.1\n', encoding='utf-8')
            (pasta / 'manifesto.json').write_text(json.dumps({
                'modo': 'ENSAIO_RETROSPECTIVO',
                'evento': {'temporada': '2026', 'rodada': '1', 'circuito_id': 'bahrain'},
            }), encoding='utf-8')
            with self.assertRaisesRegex(RegistroEmissoesErro, 'identidade'):
                validar_declaracoes(raiz, ({
                    'temporada': 2026, 'rodada': 2, 'circuito_id': 'bahrain', 'snapshot': 'teste', 'diretorio': 'emissao',
                },))

    def test_registro_vincula_snapshot_e_hash_da_q_declarados_no_manifesto(self):
        from registro_emissoes import RegistroEmissoesErro, validar_declaracoes

        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            raw = json.dumps({'MRData': {'limit': '100', 'offset': '0', 'total': '1', 'RaceTable': {
                'season': '2026', 'Races': [{'season': '2026', 'round': '18', 'date': '2026-10-25', 'time': '20:00:00Z',
                'Circuit': {'circuitId': 'americas'}, 'QualifyingResults': [{
                    'Driver': {'driverId': 'p1'}, 'Constructor': {'constructorId': 't1'}, 'position': '1',
                }]}]}}}).encode('utf-8')
            base = raiz / 'data' / 'operacao_2026' / 'snapshots'
            fontes.gravar_snapshot(base, 'q-canonica', {'classificacao': [{
                'bytes': raw, 'parametros': {'offset': 0, 'limit': 100}, 'status': 200,
                'url_solicitada': 'https://fixture.invalid/q', 'url_real': 'https://fixture.invalid/q',
                'obtido_em_utc': '2026-10-24T22:01:00Z', 'origem': 'fixture', 'rodada': '18',
            }]})
            indice = fontes.ler_indice(base, 'q-canonica')
            q = next(item for item in indice['fontes'] if item['endpoint'] == 'classificacao')
            pasta = raiz / 'emissao'
            pasta.mkdir()
            conteudo = b'piloto_id,probabilidade_modelo\np1,0.1\n'
            (pasta / 'probabilidades.csv').write_bytes(conteudo)
            manifesto = {
                'modo': 'PROSPECTIVO', 'evento': {'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas'},
                'source_snapshots': ['q-canonica'], 'fontes': [q], 'emitido_em_utc': '2026-10-24T22:30:00Z',
                'corte_temporal': {'qualificacao_inicio_utc': '2026-10-24T21:00:00Z',
                                   'qualificacao_encerrada_em_utc': '2026-10-24T22:00:00Z',
                                   'qualificacao_disponivel_em_utc': '2026-10-24T22:01:00Z',
                                   'corte_utc': '2026-10-24T22:20:00Z',
                                   'corrida_programada_em_utc': '2026-10-25T20:00:00Z',
                                   'resultado_alvo_incluido': False},
                'modelos': {'modelo': 'v1', 'metadados': 'm1', 'esquema': 's1'},
                'hashes_saidas': {'probabilidades.csv': hashlib.sha256(conteudo).hexdigest()},
            }
            (pasta / 'manifesto.json').write_text(json.dumps(manifesto), encoding='utf-8')
            declaracao = ({'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas', 'snapshot': 'q-canonica',
                           'diretorio': 'emissao', 'modo': 'PROSPECTIVO'},)
            self.assertIn('fontes_qualificacao', validar_declaracoes(raiz, declaracao)[(2026, 18, 'americas')])
            manifesto['source_snapshots'] = ['q-outra']
            (pasta / 'manifesto.json').write_text(json.dumps(manifesto), encoding='utf-8')
            with self.assertRaisesRegex(RegistroEmissoesErro, 'Snapshot declarado'):
                validar_declaracoes(raiz, declaracao)
            manifesto['source_snapshots'] = ['q-canonica']
            manifesto['fontes'] = [dict(q, sha256='0' * 64)]
            (pasta / 'manifesto.json').write_text(json.dumps(manifesto), encoding='utf-8')
            with self.assertRaisesRegex(RegistroEmissoesErro, 'Fonte de classificação'):
                validar_declaracoes(raiz, declaracao)

    def test_registro_rejeita_prospectivo_sem_corte_temporal_comprovado(self):
        from registro_emissoes import RegistroEmissoesErro, validar_declaracoes

        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            pasta = raiz / 'emissao'
            pasta.mkdir()
            conteudo = b'piloto_id,probabilidade_modelo\np1,0.1\n'
            (pasta / 'probabilidades.csv').write_bytes(conteudo)
            (pasta / 'manifesto.json').write_text(json.dumps({
                'modo': 'PROSPECTIVO',
                'evento': {'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas'},
                'emitido_em_utc': '2026-10-24T20:00:00Z',
                'modelos': {'modelo': 'v1', 'metadados': 'm1', 'esquema': 's1'},
                'hashes_saidas': {'probabilidades.csv': hashlib.sha256(conteudo).hexdigest()},
            }), encoding='utf-8')
            with self.assertRaisesRegex(RegistroEmissoesErro, 'corte temporal'):
                validar_declaracoes(raiz, ({
                    'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas', 'snapshot': 'teste',
                    'diretorio': 'emissao', 'modo': 'PROSPECTIVO',
                },))

    def test_registro_rejeita_q_comprovada_obtida_depois_do_corte_mesmo_com_hash_igual(self):
        from registro_emissoes import RegistroEmissoesErro, validar_declaracoes

        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            raw = json.dumps({'MRData': {'limit': '100', 'offset': '0', 'total': '1', 'RaceTable': {
                'season': '2026', 'Races': [{'season': '2026', 'round': '18', 'date': '2026-10-25', 'time': '20:00:00Z',
                'Circuit': {'circuitId': 'americas'}, 'QualifyingResults': [{
                    'Driver': {'driverId': 'p1'}, 'Constructor': {'constructorId': 't1'}, 'position': '1',
                }]}]}}}).encode('utf-8')
            base = raiz / 'data' / 'operacao_2026' / 'snapshots'
            fontes.gravar_snapshot(base, 'q-canonica', {'classificacao': [{
                'bytes': raw, 'parametros': {'offset': 0, 'limit': 100}, 'status': 200,
                'url_solicitada': 'https://fixture.invalid/q', 'url_real': 'https://fixture.invalid/q',
                'obtido_em_utc': '2026-10-24T22:01:00Z', 'origem': 'fixture', 'rodada': '18',
            }]})
            indice_path = base / 'q-canonica' / 'indice.json'
            indice = json.loads(indice_path.read_text(encoding='utf-8'))
            indice['fontes'][0]['obtido_em_utc'] = '2026-10-24T23:00:00Z'
            indice_path.write_text(json.dumps(indice), encoding='utf-8')
            pasta = raiz / 'emissao'
            pasta.mkdir()
            conteudo = b'piloto_id,probabilidade_modelo\np1,0.1\n'
            (pasta / 'probabilidades.csv').write_bytes(conteudo)
            manifesto = {
                'modo': 'PROSPECTIVO', 'evento': {'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas'},
                'source_snapshots': ['q-canonica'], 'fontes': indice['fontes'], 'emitido_em_utc': '2026-10-24T22:30:00Z',
                'corte_temporal': {'qualificacao_inicio_utc': '2026-10-24T21:00:00Z',
                                   'qualificacao_encerrada_em_utc': '2026-10-24T22:00:00Z',
                                   'qualificacao_disponivel_em_utc': '2026-10-24T22:01:00Z',
                                   'corte_utc': '2026-10-24T22:20:00Z',
                                   'corrida_programada_em_utc': '2026-10-25T20:00:00Z',
                                   'resultado_alvo_incluido': False},
                'modelos': {'modelo': 'v1', 'metadados': 'm1', 'esquema': 's1'},
                'hashes_saidas': {'probabilidades.csv': hashlib.sha256(conteudo).hexdigest()},
            }
            (pasta / 'manifesto.json').write_text(json.dumps(manifesto), encoding='utf-8')
            declaracao = ({'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas', 'snapshot': 'q-canonica',
                           'diretorio': 'emissao', 'modo': 'PROSPECTIVO'},)
            with self.assertRaisesRegex(RegistroEmissoesErro, 'UTC'):
                validar_declaracoes(raiz, declaracao)


if __name__ == '__main__':
    unittest.main()

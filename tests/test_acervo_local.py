"""Fixtures pequenas do acervo descritivo; sem consultas ou modelos científicos."""
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import acervo_local as m


def gravar_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def gravar_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows(rows)


def ler_csv(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


class TestAcervoLocal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'projeto'
        self.archive = Path(self.tmp.name) / 'archive'
        self.destino = Path(self.tmp.name) / 'destino'
        self.as_of = datetime(2026, 10, 27, tzinfo=timezone.utc)
        self.bases = {}
        for year in (2024, 2025):
            calendar = {'season': str(year), 'round': '1', 'raceName': 'GP simulado',
                'date': '{}-03-01'.format(year), 'time': '15:00:00Z',
                'Circuit': {'circuitId': 'teste', 'Location': {'lat': '1.5', 'long': '-2.5'}},
                'FirstPractice': {'date': '{}-02-28'.format(year), 'time': '10:00:00Z'},
                'Qualifying': {'date': '{}-02-28'.format(year), 'time': '15:00:00Z'}}
            person = {'driverId': 'a', 'givenName': 'Piloto', 'familyName': 'A'}
            result = {'Driver': person, 'Constructor': {'constructorId': 'equipe'},
                'position': '1', 'points': '25', 'grid': '2', 'laps': '1', 'status': 'Finished'}
            qualifying = {'Driver': person, 'Constructor': {'constructorId': 'equipe'},
                'position': '1', 'Q1': '1:20.000'}
            races = {'calendario': [calendar], 'resultados': [dict(calendar, Results=[result])],
                     'classificacao': [dict(calendar, QualifyingResults=[qualifying])]}
            sources = []
            base = self.root / 'data/historico' / str(year)
            for endpoint, race in races.items():
                filename = 'raw/{}_offset_0000.json'.format(endpoint)
                p = base / filename
                gravar_json(p, {'MRData': {'RaceTable': {'Races': race}}})
                sources.append({'arquivo': filename, 'endpoint': endpoint,
                    'sha256': m._sha(p), 'obtido_em_utc': 'desconhecida',
                    'url_consultada': 'https://example.test/{}'.format(endpoint)})
            for name in ('manifesto.json', 'verificacao.json'):
                gravar_json(base / name, {'fixture': True})
            self.bases[str(year)] = dict(races, proveniencia=sources)
        self._archive_fixture()

    def _archive_fixture(self):
        tables = {
            'drivers': (['driverId', 'driverRef', 'forename', 'surname'],
                        [{'driverId': '1', 'driverRef': 'a', 'forename': 'Piloto', 'surname': 'A'}]),
            'constructors': (['constructorId', 'constructorRef'],
                             [{'constructorId': '1', 'constructorRef': 'equipe'}]),
            'circuits': (['circuitId', 'circuitRef'], [{'circuitId': '1', 'circuitRef': 'teste'}]),
            'status': (['statusId', 'status'], [{'statusId': '1', 'status': 'Finished'}]),
            'races': (['raceId', 'year', 'round', 'circuitId', 'date'],
                [{'raceId': str(i), 'year': str(y), 'round': '1', 'circuitId': '1',
                  'date': '{}-03-01'.format(y)} for i, y in enumerate((2024, 2025), 1)]),
            'lap_times': (['raceId', 'driverId', 'lap', 'position', 'time', 'milliseconds'],
                [{'raceId': str(i), 'driverId': '1', 'lap': '1', 'position': '1',
                  'time': '1:30.000', 'milliseconds': '90000'} for i in (1, 2)]),
            'pit_stops': (['raceId', 'driverId', 'stop', 'lap', 'time', 'duration', 'milliseconds'],
                [{'raceId': str(i), 'driverId': '1', 'stop': '1', 'lap': '1',
                  'time': '15:03:00', 'duration': '23.400', 'milliseconds': '23400'} for i in (1, 2)]),
            'sprint_results': (['raceId', 'driverId', 'constructorId', 'number', 'positionOrder',
                'positionText', 'points', 'grid', 'laps', 'statusId', 'time', 'milliseconds', 'fastestLap', 'fastestLapTime'],
                [{'raceId': str(i), 'driverId': '1', 'constructorId': '1', 'number': '10',
                  'positionOrder': '1', 'positionText': '1', 'points': '8', 'grid': '2', 'laps': '1',
                  'statusId': '1', 'time': '1:30.000', 'milliseconds': '90000',
                  'fastestLap': '\\N', 'fastestLapTime': '\\N'} for i in (1, 2)]),
            'constructor_standings': (['raceId', 'constructorId', 'position', 'points', 'wins'],
                [{'raceId': str(i), 'constructorId': '1', 'position': '1', 'points': '25', 'wins': '1'} for i in (1, 2)]),
            'driver_standings': (['raceId', 'driverId', 'position', 'points', 'wins'],
                [{'raceId': str(i), 'driverId': '1', 'position': '1', 'points': '25', 'wins': '1'} for i in (1, 2)]),
            'qualifying': (['raceId', 'driverId', 'position', 'q1', 'q2', 'q3'],
                [{'raceId': str(i), 'driverId': '1', 'position': '2', 'q1': '1:20.000', 'q2': '\\N', 'q3': '\\N'} for i in (1, 2)]),
        }
        for name, (fields, rows) in tables.items():
            gravar_csv(self.archive / (name + '.csv'), fields, rows)
        self._manifesto_archive()

    def _manifesto_archive(self):
        gravar_json(self.root / m.AUDITORIA_ARCHIVE, {'fontes': [
            {'arquivo': p.name, 'sha256': m._sha(p)} for p in self.archive.glob('*.csv')]})

    def preparar(self, as_of=None):
        with patch.object(m, 'carregar_temporada', side_effect=lambda year, **kw: self.bases[year]):
            return m.preparar_local(self.root, self.archive, self.destino, as_of or self.as_of)

    def test_preserva_classificacao_separa_sprint_e_mantem_proveniencia_desconhecida(self):
        previous = {p: m._sha(p) for p in self.root.rglob('*') if p.is_file()}
        previous.update({p: m._sha(p) for p in self.archive.glob('*.csv')})
        report = self.preparar()
        local = self.destino / 'local'
        q = ler_csv(local / 'classificacao.csv')
        conflicts = ler_csv(local / 'conflitos_classificacao.csv')
        self.assertEqual([r['posicao_classificacao'] for r in q], ['1', '1'])
        self.assertEqual([(r['campo'], r['valor_canonico'], r['valor_archive']) for r in conflicts],
                         [('posicao_classificacao', '1', '2')] * 2)
        self.assertEqual([r['pontos'] for r in ler_csv(local / 'resultados.csv')], ['25', '25'])
        self.assertEqual([r['pontos'] for r in ler_csv(local / 'sprint_resultados.csv')], ['8', '8'])
        laps = ler_csv(local / 'voltas_corrida.csv')
        self.assertEqual([r['piloto_id'] for r in laps], ['a', 'a'])
        self.assertEqual([r['tempo_segundos'] for r in laps], ['90.0', '90.0'])
        self.assertTrue(all(r['obtido_em_utc'] == 'desconhecida' for r in laps))
        self.assertEqual([e['latitude'] for e in report['eventos']], [1.5, 1.5])
        self.assertTrue(all(m._sha(p) == digest for p, digest in previous.items()))
        for filename, digest in report['inventario']['arquivos_sha256'].items():
            self.assertEqual(m._sha(local / filename), digest)

    def test_exclui_evento_futuro_e_todos_seus_complementos(self):
        report = self.preparar(datetime(2025, 1, 1, tzinfo=timezone.utc))
        self.assertEqual([e['temporada'] for e in report['eventos']], [2024])
        for name in m.SCHEMAS:
            self.assertTrue(all(r['temporada'] == '2024' for r in ler_csv(self.destino / 'local' / name)))

    def test_qualifying_ausente_nao_e_substituido_pelo_archive(self):
        self.bases['2025']['classificacao'] = []
        report = self.preparar()
        self.assertEqual([r['temporada'] for r in ler_csv(self.destino / 'local/classificacao.csv')], ['2024'])
        gaps = [g for g in report['inventario']['lacunas'] if g.get('tipo') == 'resultado_sem_classificacao']
        self.assertEqual([(g['temporada'], g['pilotos']) for g in gaps], [(2025, ['a'])])

    def test_archive_alterado_falha_antes_de_publicar_saida(self):
        path = self.archive / 'lap_times.csv'
        path.write_text(path.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'SHA-256 divergente'):
            self.preparar()
        self.assertFalse((self.destino / 'local').exists())

    def test_chave_de_volta_duplicada_falha_sem_output_completo(self):
        path = self.archive / 'lap_times.csv'
        rows = ler_csv(path)
        gravar_csv(path, list(rows[0]), rows + [rows[0]])
        self._manifesto_archive()
        with self.assertRaisesRegex(ValueError, 'Chave duplicada'):
            self.preparar()
        self.assertFalse((self.destino / 'local').exists())

    def test_identidade_de_circuito_divergente_nao_empresta_complementos(self):
        path = self.archive / 'circuits.csv'
        gravar_csv(path, ['circuitId', 'circuitRef'], [{'circuitId': '1', 'circuitRef': 'outro'}])
        self._manifesto_archive()
        report = self.preparar()
        self.assertEqual(len(report['eventos']), 2)
        self.assertEqual(ler_csv(self.destino / 'local/voltas_corrida.csv'), [])
        self.assertEqual(len(report['inventario']['conflitos_identidade']), 2)

    def test_destino_existente_e_as_of_sem_fuso_sao_recusados(self):
        with self.assertRaisesRegex(ValueError, 'fuso'):
            m.preparar_local(self.root, self.archive, self.destino, datetime(2026, 10, 27))
        local = self.destino / 'local'
        local.mkdir(parents=True)
        original = local / 'original.txt'
        original.write_text('preservar')
        with self.assertRaises(FileExistsError):
            self.preparar()
        self.assertEqual(original.read_text(), 'preservar')

    def test_raw_austin_com_hash_divergente_e_recusado(self):
        data = m._Acervo(self.root, self.archive, self.as_of)
        key = (2026, 18)
        data.eventos[key] = {'circuito_id': 'americas', 'data_corrida': '2026-10-25'}
        base = self.root / m.AUSTIN
        raw = base / 'raw/voltas.json'
        gravar_json(raw, {'MRData': {}})
        gravar_json(base / 'inventario.json', {'estado': 'coleta_concluida',
            'identidade': {'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas', 'data': '2026-10-25'},
            'fontes': [{'endpoint': 'voltas', 'arquivo': 'raw/voltas.json',
                        'parametros': {'offset': 0}, 'sha256': '0' * 64}]})
        with self.assertRaisesRegex(ValueError, 'SHA-256 divergente'):
            data.complementar_austin()


if __name__ == '__main__':
    unittest.main()
